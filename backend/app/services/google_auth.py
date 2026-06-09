import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from backend.app.config import settings

logger = logging.getLogger("app.google_auth")

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file"
]

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def get_drive_credentials():
    """Gets valid Google Drive credentials."""
    token_path = os.path.abspath("drive_token.json")
    secrets_path = os.path.abspath(settings.GOOGLE_CLIENT_SECRETS_FILE)

    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, DRIVE_SCOPES)
        except Exception as e:
            logger.error(f"Error loading Drive credentials: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                return creds
            except Exception as e:
                logger.error(f"Error refreshing Drive token: {e}")

        if not os.path.exists(secrets_path):
            raise FileNotFoundError(f"Client secrets file not found at {secrets_path}.")

        flow = InstalledAppFlow.from_client_secrets_file(secrets_path, DRIVE_SCOPES)
        logger.warning("Starting local OAuth server for Google Drive. Approve using your PERSONAL account.")
        # Listen on a different port to avoid conflicts
        creds = flow.run_local_server(port=8091, access_type="offline", prompt="consent")
        
        with open(token_path, "w") as token:
            token.write(creds.to_json())
        logger.info("Saved Google Drive credentials.")

    return creds


def get_youtube_credentials():
    """Gets valid YouTube credentials."""
    token_path = os.path.abspath("youtube_token.json")
    secrets_path = os.path.abspath(settings.GOOGLE_CLIENT_SECRETS_FILE)

    creds = None
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, YOUTUBE_SCOPES)
        except Exception as e:
            logger.error(f"Error loading YouTube credentials: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                return creds
            except Exception as e:
                logger.error(f"Error refreshing YouTube token: {e}")

        if not os.path.exists(secrets_path):
            raise FileNotFoundError(f"Client secrets file not found at {secrets_path}.")

        flow = InstalledAppFlow.from_client_secrets_file(secrets_path, YOUTUBE_SCOPES)
        logger.warning("Starting local OAuth server for YouTube. Approve using your BRAND channel (FootballVault).")
        creds = flow.run_local_server(port=8092, access_type="offline", prompt="consent")
        
        with open(token_path, "w") as token:
            token.write(creds.to_json())
        logger.info("Saved YouTube credentials.")

    return creds
