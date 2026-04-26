from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from database import Base
from datetime import datetime

class Trail(Base):
    __tablename__ = "trails"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Identifiers
    osm_id = Column(String, unique=True, index=True)  # OpenStreetMap's own ID
    name = Column(String)                              # e.g. "Wasatch Crest Trail"
    
    # Location
    region = Column(String)                # e.g. "Big Cottonwood Canyon"
    city = Column(String)                  # e.g. "Salt Lake City"
    state = Column(String)                 # e.g. "Utah"
    start_lat = Column(Float)             
    start_lon = Column(Float)             
    
    # Trail statistics
    distance_miles = Column(Float)         
    elevation_gain_ft = Column(Float)      
    elevation_loss_ft = Column(Float)      
    max_elevation_ft = Column(Float)       
    min_elevation_ft = Column(Float)       
    
    # Trail characteristics
    difficulty = Column(String)            # "easy", "moderate", "hard", "expert"
    surface_type = Column(String)          # "dirt", "rock", "paved", "mixed"
    trail_type = Column(String)            # "out_and_back", "loop", "point_to_point"
    activity_types = Column(String)        # "hiking, trail_running, backpacking"

    # Elevation character
    avg_grade_percent = Column(Float)          # average steepness across whole trail
    max_grade_percent = Column(Float)          # steepest single section
    elevation_gain_per_mile = Column(Float)    # gain divided by distance - key metric

    # Runability indicators
    has_long_flat_sections = Column(Boolean, default=False)   # good for maintaining pace
    has_technical_terrain = Column(Boolean, default=False)    # roots, rocks, scrambling
    has_sustained_steep = Column(Boolean, default=False)      # long unbroken climbs

    # Rich data
    description = Column(String, nullable=True)
    gpx_geometry = Column(String, nullable=True)  # full GPS path stored as text
    
    # Cache control - so we know when to refresh from OSM
    last_queried = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Trail {self.name} - {self.distance_miles}mi, {self.elevation_gain_ft}ft gain>"