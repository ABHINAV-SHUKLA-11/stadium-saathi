from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, func
from app.core.database import Base

class StadiumLocation(Base):
    __tablename__ = "stadium_locations"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)        # gate, section, food_stall, washroom, first_aid, exit, escalator
    level = Column(Integer, nullable=False)     # 0=Ground, 1=Concourse, 2=Upper
    zone = Column(String, nullable=False)        # North, South, East, West
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    nearby_ids = Column(Text, nullable=True)     # Comma separated list of IDs for SQLite simple graph
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # Store JSON representation as text for SQLite

class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    fan_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    detected_language = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    is_emergency = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class CrowdDensity(Base):
    __tablename__ = "crowd_density"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(String, index=True, nullable=False)
    density = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, server_default=func.now(), nullable=False)
