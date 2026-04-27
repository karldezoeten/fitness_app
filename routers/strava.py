from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models.user_settings import UserSettings
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

router = APIRouter(
    prefix="/strava",
    tags=["strava"]
)

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI")

# The permissions we are requesting from Strava
STRAVA_SCOPE = "read,activity:read_all"

@router.get("/login")
def strava_login():
    """
    Step 1 - Send the user to Strava to log in and approve access.
    """
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={STRAVA_SCOPE}"
    )
    return RedirectResponse(auth_url)

@router.get("/callback")
def strava_callback(code: str, db: Session = Depends(get_db)):
    """
    Step 2 - Strava sends the user back here after they approve access.
    We exchange the temporary code for real access tokens.
    """
    # Exchange the code for tokens
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to connect to Strava")

    data = response.json()

    # Save the tokens to the database
    user = db.query(UserSettings).first()
    if not user:
        user = UserSettings()
        db.add(user)

    user.strava_athlete_id = str(data["athlete"]["id"])
    user.strava_access_token = data["access_token"]
    user.strava_refresh_token = data["refresh_token"]
    user.name = data["athlete"]["firstname"]
    db.commit()

    return {
        "message": f"Successfully connected to Strava!",
        "athlete": data["athlete"]["firstname"],
        "athlete_id": data["athlete"]["id"]
    }

@router.get("/sync")
def sync_activities(
    db: Session = Depends(get_db),
    months_back: int = 1        # default to 1 month, user can override
):
    """
    Pull activities from Strava and save to local database.
    - First time: call with ?months_back=12 for a full year
    - Ongoing: call with no params for last month only
    """
    user = db.query(UserSettings).first()
    if not user or not user.strava_access_token:
        raise HTTPException(status_code=400, detail="Not connected to Strava yet")

    # Calculate how far back to fetch
    from datetime import timedelta
    after_date = datetime.utcnow() - timedelta(days=30 * months_back)
    after_timestamp = int(after_date.timestamp())

    # Fetch activities from Strava after the calculated date
    all_activities = []
    page = 1

    while True:
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {user.strava_access_token}"},
            params={
                "after": after_timestamp,
                "per_page": 100,        # max allowed by Strava
                "page": page
            }
        )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch from Strava")

        batch = response.json()
        if not batch:
            break                       # no more activities to fetch

        all_activities.extend(batch)
        page += 1

    # Save each activity to the database
    from models.activity import Activity
    saved = 0
    skipped = 0

    for a in all_activities:
        # Skip if already in database
        existing = db.query(Activity).filter(
            Activity.strava_id == str(a["id"])
        ).first()

        if existing:
            skipped += 1
            continue

        # Convert Strava date string to Python datetime
        date_str = a.get("start_date")
        activity_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ") if date_str else None

        # Convert meters to miles and feet
        distance_miles = round(a.get("distance", 0) * 0.000621371, 2)
        elevation_gain_ft = round(a.get("total_elevation_gain", 0) * 3.28084, 0)
        duration_minutes = round(a.get("moving_time", 0) / 60, 1)

        # Safely extract coordinates - some activities have no GPS data
        latlng = a.get("start_latlng") or []
        start_lat = latlng[0] if len(latlng) >= 2 else None
        start_lon = latlng[1] if len(latlng) >= 2 else None

        activity = Activity(
            strava_id=str(a["id"]),
            name=a.get("name"),
            activity_type=a.get("type"),
            date=activity_date,
            distance_miles=distance_miles,
            duration_minutes=duration_minutes,
            elevation_gain_ft=elevation_gain_ft,
            avg_heart_rate=a.get("average_heartrate"),
            start_lat=start_lat,
            start_lon=start_lon,
            imported_from_strava=True
        )
        db.add(activity)
        saved += 1

    # Update last sync time
    user.last_strava_sync = datetime.utcnow()
    db.commit()

    return {
        "message": "Sync complete",
        "saved": saved,
        "skipped": skipped,
        "total_processed": len(all_activities),
        "months_fetched": months_back,
        "last_sync": user.last_strava_sync
    }

@router.get("/activities")
def get_activities(db: Session = Depends(get_db)):
    """
    Return all synced activities from the local database.
    """
    from models.activity import Activity
    activities = db.query(Activity).order_by(Activity.date.desc()).all()
    
    return {
        "total": len(activities),
        "activities": [
            {
                "name": a.name,
                "type": a.activity_type,
                "date": a.date,
                "distance_miles": a.distance_miles,
                "elevation_gain_ft": a.elevation_gain_ft,
                "duration_minutes": a.duration_minutes
            }
            for a in activities
        ]
    }
@router.get("/summary")
def get_training_summary(db: Session = Depends(get_db)):
    """
    High level summary of your training history.
    This will power the dashboard.
    """
    from models.activity import Activity
    from datetime import timedelta

    activities = db.query(Activity).all()

    # Group by activity type
    type_groups = {}
    for a in activities:
        t = a.activity_type or "Unknown"
        if t not in type_groups:
            type_groups[t] = []
        type_groups[t].append(a)

    # Friendly category mapping
    run_types = ["Run", "TrailRun"]
    hike_types = ["Hike"]
    ski_types = ["AlpineSki", "NordicSki", "BackcountrySki"]
    bike_types = ["Ride", "MountainBikeRide", "VirtualRide", "GravelRide"]
    walk_types = ["Walk"]

    runs = [a for a in activities if a.activity_type in run_types]
    hikes = [a for a in activities if a.activity_type in hike_types]
    skis = [a for a in activities if a.activity_type in ski_types]
    bikes = [a for a in activities if a.activity_type in bike_types]
    walks = [a for a in activities if a.activity_type in walk_types]

    # Last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent = [a for a in activities if a.date and a.date > thirty_days_ago]

    # Last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    this_week = [a for a in activities if a.date and a.date > seven_days_ago]

    return {
        "all_time": {
            "total_activities": len(activities),
            "total_miles": round(sum(a.distance_miles or 0 for a in activities), 1),
            "total_elevation_ft": round(sum(a.elevation_gain_ft or 0 for a in activities), 0),
            "total_hours": round(sum(a.duration_minutes or 0 for a in activities) / 60, 1),
            "by_type": {
                "runs": len(runs),
                "hikes": len(hikes),
                "ski": len(skis),
                "bike": len(bikes),
                "walks": len(walks),
                "other": len(activities) - len(runs) - len(hikes) - len(skis) - len(bikes) - len(walks)
            }
        },
        "last_30_days": {
            "total_activities": len(recent),
            "total_miles": round(sum(a.distance_miles or 0 for a in recent), 1),
            "total_elevation_ft": round(sum(a.elevation_gain_ft or 0 for a in recent), 0),
            "total_hours": round(sum(a.duration_minutes or 0 for a in recent) / 60, 1),
            "by_type": {
                "runs": len([a for a in recent if a.activity_type in run_types]),
                "hikes": len([a for a in recent if a.activity_type in hike_types]),
                "ski": len([a for a in recent if a.activity_type in ski_types]),
                "bike": len([a for a in recent if a.activity_type in bike_types]),
            }
        },
        "this_week": {
            "total_activities": len(this_week),
            "total_miles": round(sum(a.distance_miles or 0 for a in this_week), 1),
            "total_elevation_ft": round(sum(a.elevation_gain_ft or 0 for a in this_week), 0),
            "total_hours": round(sum(a.duration_minutes or 0 for a in this_week) / 60, 1),
        },
        "personal_bests": {
            "longest_run_miles": round(max((a.distance_miles or 0 for a in runs), default=0), 1),
            "most_vert_single_activity_ft": round(max((a.elevation_gain_ft or 0 for a in activities), default=0), 0),
            "longest_ski_miles": round(max((a.distance_miles or 0 for a in skis), default=0), 1),
            "most_ski_vert_ft": round(max((a.elevation_gain_ft or 0 for a in skis), default=0), 0),
        },
        "all_activity_types_found": list(type_groups.keys())
    }