from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime
import os

from backend.app.database import get_db
from backend.app.models import Video
from backend.app.schemas import VideoResponse, StatsResponse, VideoUpdate
from backend.app.services.scheduler import scan_drive_job, generate_metadata_job, upload_videos_job, TEMP_DIR
from backend.app.services.drive_service import drive_service
from backend.app.services.youtube_service import youtube_service
from backend.app.config import settings

router = APIRouter()

@router.get("/videos", response_model=List[VideoResponse])
def get_videos(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Video)
    
    if status:
        query = query.filter(Video.status == status)
        
    if q:
        query = query.filter(
            or_(
                Video.filename.like(f"%{q}%"),
                Video.title.like(f"%{q}%"),
                Video.description.like(f"%{q}%")
            )
        )
        
    return query.order_by(Video.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("/scan-drive")
def trigger_scan_drive(background_tasks: BackgroundTasks):
    background_tasks.add_task(scan_drive_job)
    return {"message": "Drive scan triggered in background"}


@router.post("/generate-metadata")
def trigger_generate_metadata(background_tasks: BackgroundTasks):
    background_tasks.add_task(generate_metadata_job)
    return {"message": "Gemini metadata generation triggered in background"}


@router.post("/upload-video")
def trigger_upload_video(
    background_tasks: BackgroundTasks,
    video_id: Optional[int] = Query(None, description="Specific video ID to upload"),
    db: Session = Depends(get_db)
):
    if video_id is not None:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Trigger single video upload in background
        background_tasks.add_task(upload_single_video_task, video.id)
        return {"message": f"Upload for video ID {video.id} triggered in background"}
    
    # Otherwise trigger general upload job for all pending metadata videos
    background_tasks.add_task(upload_videos_job)
    return {"message": "General YouTube upload job triggered in background"}


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    counts = db.query(Video.status, func.count(Video.id)).group_by(Video.status).all()
    stats_dict = {
        "total": db.query(Video).count(),
        "pending": 0,
        "metadata_generated": 0,
        "uploading": 0,
        "uploaded": 0,
        "failed": 0
    }
    
    for status, count in counts:
        if status in stats_dict:
            stats_dict[status] = count
            
    return stats_dict


def upload_single_video_task(video_id: int):
    """Worker task to download, upload, and move a specific video."""
    db = Depends(get_db) # We need standard session
    # Let's open a manual session to ensure thread safety
    from backend.app.database import SessionLocal
    db = SessionLocal()
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        db.close()
        return

    local_path = os.path.join(TEMP_DIR, f"{video.id}_{video.filename}")
    try:
        video.status = "uploading"
        video.upload_attempts += 1
        db.commit()

        # Download
        drive_service.download_file(video.drive_file_id, local_path)

        # Upload
        yt_id = youtube_service.upload_short(
            file_path=local_path,
            title=video.title or video.filename,
            description=video.description or "",
            hashtags=video.hashtags or ""
        )

        # Move file on drive
        try:
            uploaded_folder_id = drive_service.get_or_create_uploaded_folder(settings.GOOGLE_DRIVE_FOLDER_ID)
            drive_service.move_file_to_uploaded(
                file_id=video.drive_file_id,
                current_parent_id=settings.GOOGLE_DRIVE_FOLDER_ID,
                uploaded_folder_id=uploaded_folder_id
            )
        except Exception as move_err:
            print(f"Failed to move file in Drive: {move_err}")

        # Update
        video.youtube_video_id = yt_id
        video.status = "uploaded"
        video.uploaded_at = datetime.now()
        db.commit()

    except Exception as e:
        print(f"Failed to upload video ID {video.id}: {e}")
        video.status = "failed"
        db.commit()
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass
    finally:
        db.close()
