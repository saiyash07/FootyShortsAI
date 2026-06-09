from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class VideoBase(BaseModel):
    filename: str
    drive_file_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    youtube_video_id: Optional[str] = None
    status: str
    upload_attempts: int

class VideoCreate(BaseModel):
    filename: str
    drive_file_id: str

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    youtube_video_id: Optional[str] = None
    status: Optional[str] = None
    upload_attempts: Optional[int] = None
    uploaded_at: Optional[datetime] = None

class VideoResponse(VideoBase):
    id: int
    created_at: datetime
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total: int
    pending: int
    metadata_generated: int
    uploading: int
    uploaded: int
    failed: int
