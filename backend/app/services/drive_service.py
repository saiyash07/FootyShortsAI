import io
import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from backend.app.config import settings
from backend.app.services.google_auth import get_drive_credentials

logger = logging.getLogger("app.drive_service")

class DriveService:
    def __init__(self):
        self._service = None

    @property
    def service(self):
        if not self._service:
            creds = get_drive_credentials()
            self._service = build("drive", "v3", credentials=creds)
        return self._service

    def list_mp4_files(self, folder_id: str) -> list:
        """Lists all mp4 files in the specified Google Drive folder."""
        query = f"'{folder_id}' in parents and mimeType = 'video/mp4' and trashed = false"
        logger.info(f"Scanning Drive folder '{folder_id}' for mp4 files...")
        
        try:
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            
            files = results.get("files", [])
            logger.info(f"Found {len(files)} files in folder.")
            return files
        except Exception as e:
            logger.error(f"Error listing files from Google Drive: {e}")
            raise e

    def download_file(self, file_id: str, dest_path: str) -> str:
        """Downloads a file from Google Drive to local destination path."""
        logger.info(f"Downloading Drive file ID: {file_id} to {dest_path}...")
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            # Ensure folder exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(dest_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.info(f"Download Progress: {int(status.progress() * 100)}%")
                    
            logger.info(f"Finished downloading file: {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            raise e

    def get_or_create_uploaded_folder(self, parent_folder_id: str) -> str:
        """Finds or creates an 'Uploaded' folder inside the parent folder."""
        if settings.GOOGLE_DRIVE_UPLOADED_FOLDER_ID:
            return settings.GOOGLE_DRIVE_UPLOADED_FOLDER_ID

        query = f"'{parent_folder_id}' in parents and name = 'Uploaded' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        try:
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)"
            ).execute()
            
            folders = results.get("files", [])
            if folders:
                logger.info(f"Found existing 'Uploaded' folder: {folders[0]['id']}")
                return folders[0]["id"]
            
            # Create a new one
            folder_metadata = {
                "name": "Uploaded",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id]
            }
            logger.info("Creating new 'Uploaded' folder...")
            new_folder = self.service.files().create(
                body=folder_metadata,
                fields="id"
            ).execute()
            
            logger.info(f"Created 'Uploaded' folder with ID: {new_folder.get('id')}")
            return new_folder.get("id")
        except Exception as e:
            logger.error(f"Error getting/creating 'Uploaded' folder: {e}")
            raise e

    def move_file_to_uploaded(self, file_id: str, current_parent_id: str, uploaded_folder_id: str):
        """Moves a file from its current folder to the Uploaded folder."""
        logger.info(f"Moving file {file_id} to Uploaded folder {uploaded_folder_id}...")
        try:
            # Retrieve the existing parents to remove
            file = self.service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents", [current_parent_id]))
            
            # Move the file by adding the new parent and removing the old ones
            self.service.files().update(
                fileId=file_id,
                addParents=uploaded_folder_id,
                removeParents=previous_parents,
                fields="id, parents"
            ).execute()
            logger.info(f"File {file_id} successfully moved to Uploaded.")
        except Exception as e:
            logger.error(f"Error moving file {file_id}: {e}")
            raise e

drive_service = DriveService()
