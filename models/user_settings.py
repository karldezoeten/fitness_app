from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from database import Base
from datetime import datetime

class UserSettings(Base):
    __tablename__ = "user_settings"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic user info
    name = Column(String, default="Athlete")
    email = Column(String, nullable=True)
    location_city = Column(String, nullable=True)    # e.g. "Salt Lake City"
    location_state = Column(String, nullable=True)   # e.g. "Utah"
    location_lat = Column(Float, nullable=True)      # for trail searches nearby
    location_lon = Column(Float, nullable=True)

    # Their definition of each workout type
    # These are the defaults - user can change them anytime
    easy_run_min_miles = Column(Float, default=3.0)
    easy_run_max_miles = Column(Float, default=6.0)

    long_run_min_miles = Column(Float, default=12.0)
    long_run_max_miles = Column(Float, default=24.0)
    long_run_max_gain_ft = Column(Float, default=3000.0)   # keeps it runnable

    steep_hike_min_gain_ft = Column(Float, default=3000.0)
    steep_hike_max_gain_ft = Column(Float, default=6000.0)
    steep_hike_max_miles = Column(Float, default=12.0)

    track_workout_preference = Column(String, default="intervals")  # "intervals", "tempo", "fartlek"

    # Search radius for trail suggestions
    trail_search_radius_miles = Column(Float, default=60.0)

    # Race program settings
    following_race_program = Column(Boolean, default=False)
    active_goal_id = Column(Integer, nullable=True)   # links to goal.py

    # Strava connection
    strava_athlete_id = Column(String, nullable=True)
    strava_access_token = Column(String, nullable=True)
    strava_refresh_token = Column(String, nullable=True)
    strava_token_expires_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserSettings for {self.name}>"