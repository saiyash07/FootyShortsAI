from sqlalchemy import Column, Integer, String, DateTime, func
from backend.app.database import Base

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, nullable=False)
    drive_file_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    hashtags = Column(String, nullable=True)
    youtube_video_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, metadata_generated, uploading, uploaded, failed
    upload_attempts = Column(Integer, default=0, nullable=False)
    uploaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
