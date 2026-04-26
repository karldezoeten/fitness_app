from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from database import Base
from datetime import datetime

class Plan(Base):
    __tablename__ = "plans"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Which goal this plan belongs to
    goal_id = Column(Integer, nullable=True)      # links to goal.py
    week_start_date = Column(DateTime)            # Monday of that week
    week_number = Column(Integer, nullable=True)  # e.g. week 8 of 18

    # Current training phase for this week
    phase = Column(String, default="base")        # "base", "build", "peak", "taper"

    # Weekly targets for this specific plan
    target_weekly_miles = Column(Float, nullable=True)
    target_weekly_vert_ft = Column(Float, nullable=True)
    target_weekly_time_hours = Column(Float, nullable=True)

    # Actual totals - filled in as week progresses from Strava
    actual_weekly_miles = Column(Float, default=0.0)
    actual_weekly_vert_ft = Column(Float, default=0.0)
    actual_weekly_time_hours = Column(Float, default=0.0)

    # Was this a back to back week
    is_back_to_back_week = Column(Boolean, default=False)

    # AI generated notes for this week
    week_notes = Column(String, nullable=True)    # e.g. "Focus on vert this week"
    ai_reasoning = Column(String, nullable=True)  # why the AI chose these workouts

    # Status
    is_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Plan week of {self.week_start_date} - phase: {self.phase}>"


class PlanSlot(Base):
    __tablename__ = "plan_slots"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Which plan this slot belongs to
    plan_id = Column(Integer)                     # links to Plan above

    # When and what
    day_of_week = Column(String)                  # "Monday", "Tuesday" etc
    workout_type = Column(String)                 # "long_run", "steep_hike", "easy_run", "track", "rest"
    workout_label = Column(String, nullable=True) # e.g. "Long Trail Run"

    # Suggested trail for this slot
    trail_id = Column(Integer, nullable=True)     # links to trail.py
    trail_name = Column(String, nullable=True)    # stored directly for easy display

    # Targets for this specific workout
    target_miles = Column(Float, nullable=True)
    target_vert_ft = Column(Float, nullable=True)
    target_time_hours = Column(Float, nullable=True)
    target_notes = Column(String, nullable=True)  # e.g. "Keep effort easy, focus on time on feet"

    # Actual results - filled in from Strava after completion
    actual_miles = Column(Float, nullable=True)
    actual_vert_ft = Column(Float, nullable=True)
    actual_time_hours = Column(Float, nullable=True)
    activity_id = Column(Integer, nullable=True)  # links back to activity.py

    # Status
    completed = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    skip_reason = Column(String, nullable=True)   # e.g. "weather", "injury", "life"

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PlanSlot {self.day_of_week} - {self.workout_type}>"