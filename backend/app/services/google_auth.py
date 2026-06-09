import os
import json
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
    """Gets valid Google Drive credentials from Env JSON or file."""
    # Check if loaded from Env Var (useful for Render/Cloud hosting)
    env_token = os.environ.get("GOOGLE_DRIVE_TOKEN_JSON")
    creds = None
    
    if env_token:
        try:
            token_info = json.loads(env_token)
            creds = Credentials.from_authorized_user_info(token_info, DRIVE_SCOPES)
            logger.info("Loaded Drive credentials from GOOGLE_DRIVE_TOKEN_JSON env var.")
        except Exception as e:
            logger.error(f"Error parsing GOOGLE_DRIVE_TOKEN_JSON env var: {e}")
            
    if not creds:
        token_path = os.path.abspath("drive_token.json")
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, DRIVE_SCOPES)
            except Exception as e:
                logger.error(f"Error loading Drive credentials from file: {e}")

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save if it's a file, otherwise print warning
            token_path = os.path.abspath("drive_token.json")
            if not env_token:
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            logger.info("Refreshed Drive credentials successfully.")
            return creds
        except Exception as e:
            logger.error(f"Error refreshing Drive token: {e}")

    if not creds:
        # Require OAuth Client configuration
        creds = run_oauth_flow(DRIVE_SCOPES, port=8091)
        # Save token locally
        token_path = os.path.abspath("drive_token.json")
        with open(token_path, "w") as token:
            token.write(creds.to_json())
            
    return creds


def get_youtube_credentials():
    """Gets valid YouTube credentials from Env JSON or file."""
    env_token = os.environ.get("GOOGLE_YOUTUBE_TOKEN_JSON")
    creds = None
    
    if env_token:
        try:
            token_info = json.loads(env_token)
            creds = Credentials.from_authorized_user_info(token_info, YOUTUBE_SCOPES)
            logger.info("Loaded YouTube credentials from GOOGLE_YOUTUBE_TOKEN_JSON env var.")
        except Exception as e:
            logger.error(f"Error parsing GOOGLE_YOUTUBE_TOKEN_JSON env var: {e}")
            
    if not creds:
        token_path = os.path.abspath("youtube_token.json")
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, YOUTUBE_SCOPES)
            except Exception as e:
                logger.error(f"Error loading YouTube credentials from file: {e}")

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path = os.path.abspath("youtube_token.json")
            if not env_token:
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
            logger.info("Refreshed YouTube credentials successfully.")
            return creds
        except Exception as e:
            logger.error(f"Error refreshing YouTube token: {e}")

    if not creds:
        creds = run_oauth_flow(YOUTUBE_SCOPES, port=8092)
        token_path = os.path.abspath("youtube_token.json")
        with open(token_path, "w") as token:
            token.write(creds.to_json())
            
    return creds


def run_oauth_flow(scopes, port):
    """Runs InstalledAppFlow locally using client config."""
    # Check if client config is in Env Var
    env_secrets = os.environ.get("GOOGLE_CLIENT_SECRETS_JSON")
    secrets_path = os.path.abspath(settings.GOOGLE_CLIENT_SECRETS_FILE)
    
    if env_secrets:
        try:
            client_config = json.loads(env_secrets)
            flow = InstalledAppFlow.from_client_config(client_config, scopes)
        except Exception as e:
            logger.error(f"Error parsing GOOGLE_CLIENT_SECRETS_JSON env var: {e}")
            raise e
    else:
        if not os.path.exists(secrets_path):
            raise FileNotFoundError(
                f"Client secrets not found. Please provide GOOGLE_CLIENT_SECRETS_JSON environment variable "
                f"or place credentials.json in project root."
            )
        flow = InstalledAppFlow.from_client_secrets_file(secrets_path, scopes)
        
    logger.warning(f"Starting local OAuth server on port {port}. Complete authentication in browser.")
    return flow.run_local_server(port=port, access_type="offline", prompt="consent")
