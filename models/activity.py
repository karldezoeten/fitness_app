from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from database import Base
from datetime import datetime

class Activity(Base):
    __tablename__ = "activities"

    # Primary key - unique ID for each activity
    id = Column(Integer, primary_key=True, index=True)
    
    # Strava's own ID - so we never import the same activity twice
    strava_id = Column(String, unique=True, index=True)
    
    # Basic activity info
    name = Column(String)                    # e.g. "Morning Run on Wasatch Crest"
    activity_type = Column(String)           # e.g. "Run", "Hike", "TrailRun"
    date = Column(DateTime, default=datetime.utcnow)
    
    # Performance data
    distance_miles = Column(Float)           
    duration_minutes = Column(Float)         
    elevation_gain_ft = Column(Float)        
    avg_pace_min_per_mile = Column(Float)    
    avg_heart_rate = Column(Float)           
    
    # Location info
    start_lat = Column(Float)               
    start_lon = Column(Float)               
    city = Column(String)                   
    state = Column(String)                  
    
    # Training plan connections
    trail_id = Column(Integer, nullable=True)      # which trail this was on
    plan_slot_id = Column(Integer, nullable=True)  # which plan slot it fulfilled
    workout_slot = Column(String, nullable=True)   # "long_run", "hike", "easy_run", "track"
    
    # Metadata
    gpx_data = Column(String, nullable=True)       # full GPS route stored as text
    notes = Column(String, nullable=True)          # your personal notes
    imported_from_strava = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Activity {self.name} on {self.date}>"