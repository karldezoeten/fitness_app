from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user_settings import UserSettings
from models.trail import Trail
from services.osm_service import query_trails_near_location
from datetime import datetime

router = APIRouter(
    prefix="/trails",
    tags=["trails"]
)

# Salt Lake City coordinates as default
DEFAULT_LAT = 40.7608
DEFAULT_LON = -111.8910

@router.get("/search")
def search_trails(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    radius_miles: float = 60.0,
    min_distance_miles: float = None,
    max_distance_miles: float = None,
    min_elevation_gain_ft: float = None,
    max_elevation_gain_ft: float = None,
    db: Session = Depends(get_db)
):
    """
    Search for trails near a location matching the given criteria.
    Defaults to Salt Lake City with a 60 mile radius.
    """
    results = query_trails_near_location(
        lat=lat,
        lon=lon,
        radius_miles=radius_miles,
        min_distance_miles=min_distance_miles,
        max_distance_miles=max_distance_miles,
        min_elevation_gain_ft=min_elevation_gain_ft,
        max_elevation_gain_ft=max_elevation_gain_ft,
    )

    return results

@router.get("/search/long_run")
def search_long_run_trails(
    db: Session = Depends(get_db)
):
    """
    Search for trails matching your current long run targets
    based on your active goal.
    """
    from models.goal import Goal
    user = db.query(UserSettings).first()
    if not user or not user.active_goal_id:
        raise HTTPException(status_code=404, detail="No active goal found")

    goal = db.query(Goal).filter(Goal.id == user.active_goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    lat = user.location_lat or DEFAULT_LAT
    lon = user.location_lon or DEFAULT_LON

    results = query_trails_near_location(
        lat=lat,
        lon=lon,
        radius_miles=user.trail_search_radius_miles or 60.0,
        min_distance_miles=goal.long_run_min_miles,
        max_distance_miles=goal.long_run_max_miles,
    )

    return {
        "searching_for": f"Long run trails {goal.long_run_min_miles} - {goal.long_run_max_miles} miles",
        "phase": goal.current_phase,
        **results
    }

@router.get("/search/vert_day")
def search_vert_day_trails(
    db: Session = Depends(get_db)
):
    """
    Search for trails matching your current vert day targets
    based on your active goal.
    """
    from models.goal import Goal
    user = db.query(UserSettings).first()
    if not user or not user.active_goal_id:
        raise HTTPException(status_code=404, detail="No active goal found")

    goal = db.query(Goal).filter(Goal.id == user.active_goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    lat = user.location_lat or DEFAULT_LAT
    lon = user.location_lon or DEFAULT_LON

    results = query_trails_near_location(
        lat=lat,
        lon=lon,
        radius_miles=user.trail_search_radius_miles or 60.0,
        min_elevation_gain_ft=goal.vert_day_min_gain_ft,
        max_elevation_gain_ft=goal.vert_day_max_gain_ft,
    )

    return {
        "searching_for": f"Vert day trails {goal.vert_day_min_gain_ft} - {goal.vert_day_max_gain_ft} ft gain",
        "phase": goal.current_phase,
        **results
    }