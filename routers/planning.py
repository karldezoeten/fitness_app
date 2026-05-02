from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.goal import Goal
from models.plan import Plan, PlanSlot
from models.user_settings import UserSettings
from models.activity import Activity
from services.ai_planner import generate_weekly_plan
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/planning",
    tags=["planning"]
)

def get_week_start(date: datetime) -> datetime:
    """Get the Monday of the week containing the given date."""
    days_since_monday = date.weekday()
    return (date - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

@router.get("/week")
def get_week_plan(
    week_offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get the plan for a specific week.
    week_offset: 0 = current week, 1 = next week, -1 = last week
    """
    today = datetime.utcnow()
    week_start = get_week_start(today) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    # Find existing plan for this week
    plan = db.query(Plan).filter(
        Plan.week_start_date >= week_start,
        Plan.week_start_date < week_start + timedelta(days=1)
    ).first()

    if not plan:
        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "week_offset": week_offset,
            "plan_exists": False,
            "slots": []
        }

    # Get slots for this plan
    slots = db.query(PlanSlot).filter(
        PlanSlot.plan_id == plan.id
    ).all()

    # Check for completed Strava activities this week
    activities = db.query(Activity).filter(
        Activity.date >= week_start,
        Activity.date <= week_end
    ).all()

    # Match activities to slots
    activity_map = {}
    for a in activities:
        if a.date:
            day_name = a.date.strftime("%A")
            if day_name not in activity_map:
                activity_map[day_name] = []
            activity_map[day_name].append(a)

    slots_data = []
    for slot in slots:
        # Check if there's a matching activity
        day_activities = activity_map.get(slot.day_of_week, [])
        completed_activity = None
        for act in day_activities:
            if not act.plan_slot_id:
                completed_activity = act
                break

        slots_data.append({
            "id": slot.id,
            "day": slot.day_of_week,
            "type": slot.workout_type,
            "label": slot.workout_label,
            "target_miles": slot.target_miles,
            "target_vert_ft": slot.target_vert_ft,
            "target_time_hours": slot.target_time_hours,
            "suggested_trail": slot.trail_name,
            "notes": slot.target_notes,
            "completed": slot.completed,
            "skipped": slot.skipped,
            "actual_miles": slot.actual_miles,
            "actual_vert_ft": slot.actual_vert_ft,
        })

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "week_offset": week_offset,
        "plan_exists": True,
        "plan_id": plan.id,
        "phase": plan.phase,
        "week_notes": plan.week_notes,
        "target_weekly_miles": plan.target_weekly_miles,
        "target_weekly_vert_ft": plan.target_weekly_vert_ft,
        "slots": slots_data
    }

@router.post("/generate")
def generate_plan(
    week_offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Generate a new AI training plan for the given week.
    """
    # Get active goal
    user = db.query(UserSettings).first()
    if not user or not user.active_goal_id:
        raise HTTPException(status_code=404, detail="No active goal found")

    goal = db.query(Goal).filter(Goal.id == user.active_goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Get recent activities for context (last 30)
    recent_activities = db.query(Activity).order_by(
        Activity.date.desc()
    ).limit(30).all()

    recent_list = [
        {
            "name": a.name,
            "activity_type": a.activity_type,
            "distance_miles": a.distance_miles,
            "elevation_gain_ft": a.elevation_gain_ft,
            "duration_minutes": a.duration_minutes,
            "date": a.date.isoformat() if a.date else None
        }
        for a in recent_activities
    ]

    # Calculate week start
    today = datetime.utcnow()
    week_start = get_week_start(today) + timedelta(weeks=week_offset)

    # Build goal dict for AI
    from routers.goals import get_active_goal
    goal_data = {
        "race_name": goal.race_name,
        "race_date": goal.race_date.isoformat() if goal.race_date else None,
        "race_distance_miles": goal.race_distance_miles,
        "race_elevation_gain_ft": goal.race_elevation_gain_ft,
        "weeks_to_race": goal.weeks_to_race,
        "current_phase": goal.current_phase,
        "training_targets": {
            "target_weekly_miles": goal.target_weekly_miles,
            "target_weekly_vert_ft": goal.target_weekly_vert_ft,
            "long_run_range_miles": f"{goal.long_run_min_miles} - {goal.long_run_max_miles}",
            "long_run_vert_range_ft": f"{goal.long_run_min_vert_ft} - {goal.long_run_max_vert_ft}",
            "vert_day_range_ft": f"{goal.vert_day_min_gain_ft} - {goal.vert_day_max_gain_ft}",
        }
    }

    # Call AI planner
    result = generate_weekly_plan(
        goal=goal_data,
        recent_activities=recent_list,
        week_start=week_start
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    ai_plan = result["plan"]

    # Delete existing plan for this week if any
    existing_plan = db.query(Plan).filter(
        Plan.week_start_date >= week_start,
        Plan.week_start_date < week_start + timedelta(days=1)
    ).first()

    if existing_plan:
        db.query(PlanSlot).filter(
            PlanSlot.plan_id == existing_plan.id
        ).delete()
        db.delete(existing_plan)
        db.commit()

    # Create new plan
    plan = Plan(
        goal_id=goal.id,
        week_start_date=week_start,
        phase=goal.current_phase,
        target_weekly_miles=goal.target_weekly_miles,
        target_weekly_vert_ft=goal.target_weekly_vert_ft,
        week_notes=ai_plan.get("week_notes"),
        ai_reasoning=str(ai_plan),
        generated_by_ai=True
    )
    db.add(plan)
    db.flush()

    # Create slots
    for w in ai_plan.get("workouts", []):
        slot = PlanSlot(
            plan_id=plan.id,
            day_of_week=w.get("day"),
            workout_type=w.get("type"),
            workout_label=w.get("label"),
            target_miles=w.get("target_miles"),
            target_vert_ft=w.get("target_vert_ft"),
            target_time_hours=w.get("target_time_hours"),
            trail_name=w.get("suggested_trail"),
            target_notes=w.get("notes")
        )
        db.add(slot)

    db.commit()

    return {
        "success": True,
        "message": "Plan generated successfully",
        "week_start": week_start.isoformat(),
        "week_notes": ai_plan.get("week_notes"),
        "workouts": ai_plan.get("workouts", [])
    }

@router.put("/slot/{slot_id}/move")
def move_slot(
    slot_id: int,
    new_day: str,
    db: Session = Depends(get_db)
):
    """
    Move a workout slot to a different day.
    Used for drag and drop.
    """
    slot = db.query(PlanSlot).filter(PlanSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    valid_days = ["Monday", "Tuesday", "Wednesday", 
                  "Thursday", "Friday", "Saturday", "Sunday"]
    if new_day not in valid_days:
        raise HTTPException(status_code=400, detail="Invalid day")

    slot.day_of_week = new_day
    db.commit()

    return {"success": True, "slot_id": slot_id, "new_day": new_day}

@router.put("/slot/{slot_id}/complete")
def complete_slot(
    slot_id: int,
    actual_miles: float = None,
    actual_vert_ft: float = None,
    actual_time_hours: float = None,
    db: Session = Depends(get_db)
):
    """Mark a workout slot as completed."""
    slot = db.query(PlanSlot).filter(PlanSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.completed = True
    slot.actual_miles = actual_miles
    slot.actual_vert_ft = actual_vert_ft
    slot.actual_time_hours = actual_time_hours
    db.commit()

    return {"success": True}

@router.put("/slot/{slot_id}/skip")
def skip_slot(
    slot_id: int,
    reason: str = None,
    db: Session = Depends(get_db)
):
    """Mark a workout slot as skipped."""
    slot = db.query(PlanSlot).filter(PlanSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.skipped = True
    slot.skip_reason = reason
    db.commit()

    return {"success": True}