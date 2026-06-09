import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from backend.app.services.google_auth import get_youtube_credentials

logger = logging.getLogger("app.youtube_service")

class YoutubeService:
    def __init__(self):
        self._service = None

    @property
    def service(self):
        if not self._service:
            creds = get_youtube_credentials()
            self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def upload_short(self, file_path: str, title: str, description: str, hashtags: str) -> str:
        """Uploads a video to YouTube as a Short with specified metadata."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found at: {file_path}")

        logger.info(f"Uploading {file_path} to YouTube Shorts...")
        
        # Prepare title - Shorts titles should have #shorts and fit within 100 chars
        full_title = title or "Football Short"
        if not isinstance(full_title, str):
            full_title = str(full_title)
            
        if "#shorts" not in full_title.lower():
            if len(full_title) + len(" #shorts") <= 100:
                full_title = f"{full_title} #shorts"
            else:
                full_title = f"{full_title[:90]} #shorts"

        desc_text = description or ""
        hash_text = hashtags or ""
        full_description = f"{desc_text}\n\n{hash_text}"

        body = {
            "snippet": {
                "title": full_title,
                "description": full_description,
                "tags": [tag.strip("#") for tag in hashtags.split()],
                "categoryId": "17" # Sports category
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        # Media upload setup (resumable = True)
        media = MediaFileUpload(
            file_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024*1024
        )

        try:
            request = self.service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"YouTube Upload Progress: {int(status.progress() * 100)}%")
            
            video_id = response.get("id")
            logger.info(f"YouTube Upload successful! Video ID: {video_id}")
            return video_id

        except Exception as e:
            logger.error(f"Error uploading video to YouTube: {e}")
            raise e
        finally:
            # Clean up local file after upload attempts
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up local file: {file_path}")
                except Exception as cleanup_err:
                    logger.error(f"Failed to delete local file {file_path}: {cleanup_err}")

youtube_service = YoutubeService()
