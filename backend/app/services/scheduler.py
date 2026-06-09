import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database import SessionLocal, engine, Base
from backend.app.models import Video
from backend.app.services.drive_service import drive_service
from backend.app.services.gemini_service import gemini_service
from backend.app.services.youtube_service import youtube_service

logger = logging.getLogger("app.scheduler")

# Create Temp directory for video downloads
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

def scan_drive_job():
    """Scans the configured Google Drive folder for new MP4 files and inserts them into SQLite."""
    logger.info("Starting scheduled Google Drive scan...")
    db: Session = SessionLocal()
    try:
        folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        if not folder_id:
            logger.error("GOOGLE_DRIVE_FOLDER_ID not set. Skipping scan.")
            return

        files = drive_service.list_mp4_files(folder_id)
        new_files_count = 0

        for f in files:
            file_id = f["id"]
            name = f["name"]

            # Check if video already exists in db
            existing = db.query(Video).filter(Video.drive_file_id == file_id).first()
            if not existing:
                new_video = Video(
                    filename=name,
                    drive_file_id=file_id,
                    status="pending"
                )
                db.add(new_video)
                new_files_count += 1
                logger.info(f"Detected new video: {name} (ID: {file_id})")

        if new_files_count > 0:
            db.commit()
            logger.info(f"Added {new_files_count} new videos to database.")
        else:
            logger.info("No new videos found.")

    except Exception as e:
        logger.error(f"Error in scan_drive_job: {e}")
    finally:
        db.close()


def generate_metadata_job():
    """Generates viral metadata for pending videos using Gemini AI."""
    logger.info("Starting metadata generation job...")
    db: Session = SessionLocal()
    try:
        # Process pending videos OR failed videos that do not have a title generated yet
        pending_videos = db.query(Video).filter(
            (Video.status == "pending") | 
            ((Video.status == "failed") & (Video.title.is_(None)))
        ).all()
        logger.info(f"Found {len(pending_videos)} videos pending metadata generation.")

        import time
        for video in pending_videos:
            try:
                # Add delay to avoid rate limit (max 15 requests per minute on free tier)
                time.sleep(5)
                metadata = gemini_service.generate_shorts_metadata(video.filename)
                video.title = metadata["title"]
                video.description = metadata["description"]
                video.hashtags = metadata["hashtags"]
                video.status = "metadata_generated"
                db.commit()
                logger.info(f"Generated metadata for video ID {video.id}: {video.title}")
            except Exception as e:
                logger.error(f"Failed to generate metadata for video ID {video.id}: {e}")
                video.status = "failed"
                db.commit()
    except Exception as e:
        logger.error(f"Error in generate_metadata_job: {e}")
    finally:
        db.close()


def upload_videos_job():
    """Downloads, uploads to YouTube, and moves processed files in Drive."""
    logger.info("Starting YouTube upload job...")
    db: Session = SessionLocal()
    try:
        # Get videos that have metadata generated OR have failed but have < 3 attempts (and must have title generated)
        videos_to_upload = db.query(Video).filter(
            ((Video.status == "metadata_generated") | (Video.status == "failed")) & 
            (Video.upload_attempts < 3) &
            (Video.title.is_not(None))
        ).all()

        logger.info(f"Found {len(videos_to_upload)} videos ready for upload.")

        for video in videos_to_upload:
            local_path = os.path.join(TEMP_DIR, f"{video.id}_{video.filename}")
            
            try:
                # Mark as uploading
                video.status = "uploading"
                video.upload_attempts += 1
                db.commit()

                # Step 1: Download from Drive
                drive_service.download_file(video.drive_file_id, local_path)

                # Step 2: Upload to YouTube
                yt_id = youtube_service.upload_short(
                    file_path=local_path,
                    title=video.title,
                    description=video.description,
                    hashtags=video.hashtags
                )

                # Step 3: Move in Google Drive to 'Uploaded' folder
                try:
                    uploaded_folder_id = drive_service.get_or_create_uploaded_folder(settings.GOOGLE_DRIVE_FOLDER_ID)
                    drive_service.move_file_to_uploaded(
                        file_id=video.drive_file_id,
                        current_parent_id=settings.GOOGLE_DRIVE_FOLDER_ID,
                        uploaded_folder_id=uploaded_folder_id
                    )
                except Exception as move_err:
                    logger.error(f"Failed to move file {video.filename} on Google Drive: {move_err}")

                # Success
                video.youtube_video_id = yt_id
                video.status = "uploaded"
                video.uploaded_at = datetime.now()
                db.commit()
                logger.info(f"Successfully automated video ID {video.id} to YouTube.")

            except Exception as e:
                logger.error(f"Failed to upload video ID {video.id}: {e}")
                video.status = "failed"
                db.commit()
                # Ensure clean up of local file on error (failsafe)
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except:
                        pass
    except Exception as e:
        logger.error(f"Error in upload_videos_job: {e}")
    finally:
        db.close()


def run_full_pipeline():
    """Runs scanning, metadata generation, and uploading in sequence."""
    logger.info("Running full automation pipeline...")
    scan_drive_job()
    generate_metadata_job()
    upload_videos_job()
    logger.info("Automation pipeline complete.")


# Initialize APScheduler
scheduler = BackgroundScheduler()

def start_scheduler():
    """Starts the background scheduler jobs."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    # Run full pipeline once on startup
    scheduler.add_job(run_full_pipeline, 'date', run_date=datetime.now())
    
    # Schedule full pipeline to run every 5 minutes
    scheduler.add_job(run_full_pipeline, 'interval', minutes=5, id='football_shorts_pipeline')
    
    scheduler.start()
    logger.info("Scheduler started. Pipeline set to run every 5 minutes.")

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
