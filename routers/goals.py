from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.goal import Goal
from models.user_settings import UserSettings
from datetime import datetime

router = APIRouter(
    prefix="/goals",
    tags=["goals"]
)

# Constants for activity classification
WALK_TO_HIKE_ELEVATION_THRESHOLD_FT = 500

# Activity type groupings
RUN_TYPES = ["Run", "TrailRun"]
HIKE_TYPES = ["Hike"]
WALK_HIKE_TYPES = ["Walk"]  # classified as hike if elevation > threshold

def classify_activity(activity_type: str, elevation_gain_ft: float) -> str:
    """
    Classify an activity into a training category.
    Returns: "run", "hike", "cross_training", "walk"
    """
    if activity_type in RUN_TYPES:
        return "run"
    if activity_type in HIKE_TYPES:
        return "hike"
    if activity_type in WALK_HIKE_TYPES:
        if (elevation_gain_ft or 0) >= WALK_TO_HIKE_ELEVATION_THRESHOLD_FT:
            return "hike"
        return "walk"
    return "cross_training"

@router.post("/create")
def create_goal(
    race_name: str,
    race_date: str,                        # format: "2025-09-15"
    race_distance_miles: float,
    race_elevation_gain_ft: float,
    goal_type: str = "finish",             # "finish", "time"
    goal_finish_time_hours: float = None,
    race_location: str = None,
    race_website: str = None,
    db: Session = Depends(get_db)
):
    """
    Create a new race goal and calculate initial training targets.
    """
    # Parse the race date
    try:
        race_date_obj = datetime.strptime(race_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in format YYYY-MM-DD")

    # Calculate weeks to race
    today = datetime.utcnow()
    days_to_race = (race_date_obj - today).days
    weeks_to_race = max(0, days_to_race // 7)

    # Determine training phase based on weeks out
    if weeks_to_race >= 16:
        phase = "base"
    elif weeks_to_race >= 10:
        phase = "build"
    elif weeks_to_race >= 4:
        phase = "peak"
    else:
        phase = "taper"

    # Calculate weekly targets based on race demands and phase
    # These percentages are based on standard ultra training principles
    phase_multipliers = {
        "base":  {"weekly_miles": 0.55, "weekly_vert": 0.50, "long_run": 0.55, "long_run_vert": 0.50},
        "build": {"weekly_miles": 0.70, "weekly_vert": 0.65, "long_run": 0.70, "long_run_vert": 0.65},
        "peak":  {"weekly_miles": 0.85, "weekly_vert": 0.80, "long_run": 0.85, "long_run_vert": 0.80},
        "taper": {"weekly_miles": 0.50, "weekly_vert": 0.45, "long_run": 0.60, "long_run_vert": 0.55},
    }

    m = phase_multipliers[phase]

    # Base weekly targets derived from race demands
    # A typical ultra plan has weekly volume at ~3-4x the race distance
    base_weekly_miles = race_distance_miles * 1.5
    base_weekly_vert = race_elevation_gain_ft * 1.5

    target_weekly_miles = round(base_weekly_miles * m["weekly_miles"], 1)
    target_weekly_vert = round(base_weekly_vert * m["weekly_vert"], 0)
    long_run_max = round(race_distance_miles * m["long_run"], 1)
    long_run_min = round(long_run_max * 0.75, 1)
    long_run_max_vert = round(race_elevation_gain_ft * m["long_run_vert"], 0)
    long_run_min_vert = round(long_run_max_vert * 0.75, 0)

    # Create the goal
    goal = Goal(
        race_name=race_name,
        race_date=race_date_obj,
        race_location=race_location,
        race_website=race_website,
        race_distance_miles=race_distance_miles,
        race_elevation_gain_ft=race_elevation_gain_ft,
        goal_type=goal_type,
        goal_finish_time_hours=goal_finish_time_hours,
        current_phase=phase,
        weeks_to_race=weeks_to_race,
        target_weekly_miles=target_weekly_miles,
        target_weekly_vert_ft=target_weekly_vert,
        long_run_min_miles=long_run_min,
        long_run_max_miles=long_run_max,
        long_run_min_vert_ft=long_run_min_vert,
        long_run_max_vert_ft=long_run_max_vert,
        vert_day_min_gain_ft=round(race_elevation_gain_ft * 0.5, 0),
        vert_day_max_gain_ft=round(race_elevation_gain_ft * 0.85, 0),
        vert_day_max_miles=12.0,
        is_active=True
    )

    db.add(goal)
    db.commit()
    db.refresh(goal)

    # Set as active goal in user settings
    user = db.query(UserSettings).first()
    if user:
        user.active_goal_id = goal.id
        user.following_race_program = True
        db.commit()

    return {
        "message": f"Goal created successfully!",
        "goal_id": goal.id,
        "race": race_name,
        "race_date": race_date,
        "weeks_to_race": weeks_to_race,
        "current_phase": phase,
        "training_targets": {
            "target_weekly_miles": target_weekly_miles,
            "target_weekly_vert_ft": target_weekly_vert,
            "long_run_range_miles": f"{long_run_min} - {long_run_max}",
            "long_run_vert_range_ft": f"{long_run_min_vert} - {long_run_max_vert}",
            "vert_day_range_ft": f"{round(race_elevation_gain_ft * 0.5, 0)} - {round(race_elevation_gain_ft * 0.85, 0)}"
        }
    }

@router.get("/active")
def get_active_goal(db: Session = Depends(get_db)):
    """
    Get the current active race goal and training targets.
    """
    user = db.query(UserSettings).first()
    if not user or not user.active_goal_id:
        raise HTTPException(status_code=404, detail="No active goal found")

    goal = db.query(Goal).filter(Goal.id == user.active_goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Recalculate weeks to race
    today = datetime.utcnow()
    days_to_race = (goal.race_date - today).days
    weeks_to_race = max(0, days_to_race // 7)

    return {
        "race_name": goal.race_name,
        "race_date": goal.race_date,
        "race_distance_miles": goal.race_distance_miles,
        "race_elevation_gain_ft": goal.race_elevation_gain_ft,
        "weeks_to_race": weeks_to_race,
        "current_phase": goal.current_phase,
        "training_targets": {
            "target_weekly_miles": goal.target_weekly_miles,
            "target_weekly_vert_ft": goal.target_weekly_vert_ft,
            "long_run_range_miles": f"{goal.long_run_min_miles} - {goal.long_run_max_miles}",
            "long_run_vert_range_ft": f"{goal.long_run_min_vert_ft} - {goal.long_run_max_vert_ft}",
            "vert_day_range_ft": f"{goal.vert_day_min_gain_ft} - {goal.vert_day_max_gain_ft}",
        }
    }