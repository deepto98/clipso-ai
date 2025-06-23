from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
import uuid

def generate_uuid():
    """Generate a short UUID for share links"""
    return str(uuid.uuid4()).replace('-', '')[:12]

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True, nullable=False)
    r2_key = Column(String, nullable=True)  # Actual key in R2 storage
    final_r2_key = Column(String, nullable=True)  # Key for the processed final video
    user_id = Column(String, nullable=True)
    status = Column(String, default="uploaded")
    share_id = Column(String, unique=True, index=True, nullable=False, default=generate_uuid)  # Short UUID for sharing
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    transcript = relationship("Transcript", back_populates="video", uselist=False)

class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    text = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    video = relationship("Video", back_populates="transcript")
