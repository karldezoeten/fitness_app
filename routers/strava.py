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
def sync_activities(db: Session = Depends(get_db)):
    """
    Step 3 - Pull your recent activities from Strava
    and save them to the local database.
    """
    user = db.query(UserSettings).first()
    if not user or not user.strava_access_token:
        raise HTTPException(status_code=400, detail="Not connected to Strava yet")

    # Fetch last 30 activities from Strava
    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {user.strava_access_token}"},
        params={"per_page": 30}
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch activities from Strava")

    activities = response.json()

    # Save each activity to the database
    from models.activity import Activity
    saved = 0
    skipped = 0

    for a in activities:
        # Check if we already have this activity
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

        activity = Activity(
            strava_id=str(a["id"]),
            name=a.get("name"),
            activity_type=a.get("type"),
            date=activity_date,
            distance_miles=distance_miles,
            duration_minutes=duration_minutes,
            elevation_gain_ft=elevation_gain_ft,
            avg_heart_rate=a.get("average_heartrate"),
            start_lat=a.get("start_latlng", [None, None])[0],
            start_lon=a.get("start_latlng", [None, None])[1],
            imported_from_strava=True
        )
        db.add(activity)
        saved += 1

    db.commit()

    return {
        "message": "Sync complete",
        "saved": saved,
        "skipped": skipped,
        "total_processed": len(activities)
    }