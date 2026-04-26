from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from database import Base
from datetime import datetime

class Goal(Base):
    __tablename__ = "goals"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Race information
    race_name = Column(String)                    # e.g. "UTMB Snowbasin"
    race_date = Column(DateTime)                  # e.g. September 2025
    race_location = Column(String, nullable=True) # e.g. "Snowbasin, Utah"
    race_website = Column(String, nullable=True)  # link to race info

    # Race demands - what you are training for
    race_distance_miles = Column(Float)           # e.g. 36.0
    race_elevation_gain_ft = Column(Float)        # e.g. 6000.0
    race_elevation_loss_ft = Column(Float, nullable=True)
    race_terrain = Column(String, nullable=True)  # e.g. "mountain, technical, exposed"
    race_difficulty = Column(String, nullable=True) # "local", "regional", "elite"

    # Cut off times - critical for ultra planning
    race_cutoff_hours = Column(Float, nullable=True)    # total time allowed e.g. 14.0
    aid_station_cutoffs = Column(String, nullable=True) # stored as JSON string

    # Your personal goals for the race
    goal_type = Column(String, default="finish")        # "finish", "time", "placement"
    goal_finish_time_hours = Column(Float, nullable=True) # e.g. 10.5 hours
    goal_notes = Column(String, nullable=True)          # e.g. "just want to finish strong"

    # Training phase - where you are in the program right now
    current_phase = Column(String, default="base")      # "base", "build", "peak", "taper"
    weeks_to_race = Column(Integer, nullable=True)      # calculated automatically
    total_program_weeks = Column(Integer, nullable=True)

    # Weekly training targets - adjust automatically by phase
    target_weekly_miles = Column(Float, nullable=True)
    target_weekly_vert_ft = Column(Float, nullable=True)  # vertical feet per week
    target_weekly_time_hours = Column(Float, nullable=True) # time on feet per week

    # Long run targets for current phase
    long_run_min_miles = Column(Float, nullable=True)
    long_run_max_miles = Column(Float, nullable=True)
    long_run_min_vert_ft = Column(Float, nullable=True)
    long_run_max_vert_ft = Column(Float, nullable=True)

    # Steep hike / vert day targets
    vert_day_min_gain_ft = Column(Float, nullable=True)
    vert_day_max_gain_ft = Column(Float, nullable=True)
    vert_day_max_miles = Column(Float, nullable=True)

    # Back to back long efforts - key for ultra training
    back_to_back_long_runs = Column(Boolean, default=False)  # Saturday + Sunday big days
    back_to_back_target_miles = Column(Float, nullable=True) # combined miles for both days
    back_to_back_target_vert_ft = Column(Float, nullable=True)

    # Progress tracking
    longest_run_so_far_miles = Column(Float, default=0.0)
    most_vert_in_week_ft = Column(Float, default=0.0)
    total_miles_in_program = Column(Float, default=0.0)
    total_vert_in_program_ft = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)     # current goal vs past goals
    completed = Column(Boolean, default=False)    # did you finish the race?
    race_result_time = Column(Float, nullable=True) # your actual finish time
    race_result_notes = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Goal {self.race_name} on {self.race_date}>"