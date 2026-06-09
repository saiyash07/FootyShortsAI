# AI Football Shorts Automation Platform

FootyShorts AI is a production-ready YouTube Shorts automation system that monitors a Google Drive folder for new football clips (`.mp4`), generates viral YouTube Shorts metadata (titles, descriptions, hashtags) using Gemini AI, uploads them to YouTube, and presents a dark-mode glassmorphic analytics dashboard.

---

## Architecture & Workflow

1. **Google Drive Watcher**: Every 5 minutes, a background scheduler scans the specified Drive folder. Any new `.mp4` video is registered in SQLite in a `pending` state.
2. **Gemini AI Engine**: The system identifies `pending` videos and requests Gemini to write a high-CTR title, descriptive context, and 15-20 viral hashtags (adhering to exact constraints). The video is updated to `metadata_generated`.
3. **YouTube Resumable Uploader**: The system downloads the video locally, uploads it to YouTube Shorts using the Resumable upload protocol, moves the processed file on Google Drive into an `Uploaded` folder, cleans up local disk temp files, and marks the record as `uploaded`.
4. **Interactive Dashboard**: A beautiful, real-time UI showing upload statistics, search, queue status, and the ability to manually trigger actions.

---

## Prerequisites & Google Console Configuration

This platform integrates with **Google Drive API**, **YouTube Data API v3**, and the **Gemini AI API**.

### 1. Google Cloud Console Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable the following APIs:
   - **Google Drive API**
   - **YouTube Data API v3**
4. Configure the **OAuth Consent Screen**:
   - Choose User Type: **External** (or Internal if using Workspace).
   - Add your email and developer contact info.
   - Under Scopes, add:
     - `https://www.googleapis.com/auth/drive.readonly`
     - `https://www.googleapis.com/auth/drive.file`
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/youtube`
   - **Crucial**: Add your testing Google Account email under **Test Users**. If your project is in Desktop/Testing status, only added test users can authorize it.
5. Create Credentials:
   - Click **Create Credentials** -> **OAuth client ID**.
   - Application type: **Desktop app**.
   - Download the JSON credential file and rename it to `credentials.json`, then place it in the root folder of this project.

### 2. Gemini API Key
- Generate an API key from the [Google AI Studio](https://aistudio.google.com/).
- Place it in your `.env` configuration file under `GEMINI_API_KEY`.

---

## Environment Variables (`.env`)

Create a `.env` file in the root directory:

```env
PORT=8000
HOST=0.0.0.0

# Database
DATABASE_URL=sqlite:///./automation.db

# API Keys
GEMINI_API_KEY=your_gemini_key

# Drive Folder configurations
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
# Optional: if left empty, an 'Uploaded' folder will be created inside the GOOGLE_DRIVE_FOLDER_ID
GOOGLE_DRIVE_UPLOADED_FOLDER_ID=

# Paths (relative to root)
GOOGLE_CLIENT_SECRETS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
```

---

## Database Table Structure

### `videos`
- `id` (INTEGER, Primary Key, Auto-increment)
- `filename` (VARCHAR)
- `drive_file_id` (VARCHAR, Unique, Indexed)
- `title` (VARCHAR, Nullable)
- `description` (VARCHAR, Nullable)
- `hashtags` (VARCHAR, Nullable)
- `youtube_video_id` (VARCHAR, Nullable)
- `status` (VARCHAR) - `pending`, `metadata_generated`, `uploading`, `uploaded`, `failed`
- `upload_attempts` (INTEGER, default 0)
- `uploaded_at` (DATETIME, Nullable)
- `created_at` (DATETIME, Auto-timestamp)

---

## Local Setup & Run

### Step 1: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### Step 3: Run the Application
Start the FastAPI server:
```bash
python -m backend.app.main
```
The application will start on `http://localhost:8000`.

*Note on First Run (Authentication):* On the very first run (or when `token.json` is missing), the terminal will spawn a local browser window asking you to authenticate with Google. Confirm the permissions. This generates `token.json`, and subsequent runs will be fully autonomous.

---

## Running with Docker

You can containerize and run the platform using docker-compose.

1. Ensure your `credentials.json` and `.env` files exist in the root folder.
2. Build and start containers:
```bash
docker-compose up --build -d
```
*Note on Docker Auth Flow*: Because authorization requires a browser login to generate `token.json`, it is highly recommended to run the app locally once to create `token.json` first, and then run it inside Docker. Docker-compose mounts `token.json` from your local root folder directly.

---

## VPS Deployment Instructions

Deploying this app to a VPS (Ubuntu/Debian) ensures it runs 24/7.

### Step 1: Server Setup & Prerequisites
Connect to your VPS and install Docker and Git:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose git -y
```

### Step 2: Clone & Configure
Clone your repository onto the VPS:
```bash
git clone <your-repo-url> yt-shorts-automation
cd yt-shorts-automation
```

Configure your `.env` and upload your `credentials.json` and `token.json` (generate `token.json` locally first, then upload it to avoid needing a browser flow on the headless VPS server):
```bash
nano .env
# Paste configurations
# SCP or transfer token.json and credentials.json to this directory
```

### Step 3: Start Containers
Run the Docker container in detached mode:
```bash
sudo docker-compose up --build -d
```

### Step 4: Reverse Proxy with Nginx (Optional, for HTTPS)
If you want to access the dashboard on a domain name via HTTPS:
1. Install Nginx:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   ```
2. Configure a block: `/etc/nginx/sites-available/shorts-dashboard`
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
3. Enable and secure:
   ```bash
   sudo ln -s /etc/nginx/sites-available/shorts-dashboard /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   sudo certbot --nginx -d yourdomain.com
   ```
