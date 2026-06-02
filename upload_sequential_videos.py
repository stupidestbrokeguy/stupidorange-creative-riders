#!/usr/bin/env python3
"""
Upload videos sequentially from a folder, one per run.
Supports repost videos with custom credits.
Videos must be named with a number (e.g., 1.mp4, 2.mp4, 001.avi, 10.mov).
Credits are defined in credits.json (mapping number -> credit text).
State is saved in video_sequence_state.json and committed to the repo.
"""

import os
import re
import sys
import json
import glob
import pickle
import subprocess
from pathlib import Path
from datetime import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========== CONFIGURATION ==========
VIDEO_FOLDER = "video_of_day"
STATE_FILE = "video_sequence_state.json"
CREDITS_FILE = "credits.json"          # New: per-video credits
CLIENT_SECRETS = "client_secrets.json"
TOKEN_PICKLE = "token.pickle"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
# ===================================


def get_authenticated_service():
    """Get YouTube service using stored credentials or OAuth flow."""
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open(TOKEN_PICKLE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def get_video_files(folder):
    """Return list of (numeric_key, filepath) for all video files in folder."""
    pattern = os.path.join(folder, "*")
    files = glob.glob(pattern)
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    result = []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext not in video_extensions:
            continue
        basename = os.path.basename(f)
        # extract leading number (e.g., "123" from "123.mp4" or "001-anything.mp4")
        match = re.match(r"^(\d+)", basename)
        if match:
            num = int(match.group(1))
            result.append((num, f))
    result.sort(key=lambda x: x[0])
    return result


def load_state():
    """Load previously uploaded video number, or None if no state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_uploaded_number")
    return None


def save_state(number):
    """Save the number of the last uploaded video."""
    with open(STATE_FILE, "w") as f:
        json.dump({"last_uploaded_number": number}, f, indent=2)


def load_credits():
    """Load credits mapping from credits.json (if exists). Returns dict number->credit_string."""
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, "r") as f:
            return json.load(f)
    return {}


def commit_and_push_state():
    """Commit and push the state file back to the repository."""
    try:
        subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
        subprocess.run(["git", "add", STATE_FILE, CREDITS_FILE], check=True)  # also track credits changes
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if any(f in status.stdout for f in [STATE_FILE, CREDITS_FILE]):
            subprocess.run(["git", "commit", "-m", f"Update video sequence state/credits at {datetime.now().isoformat()}"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("✅ State/credits file committed and pushed.")
        else:
            print("ℹ️ No changes to state or credits.")
    except Exception as e:
        print(f"⚠️ Could not commit/push state: {e}")


def upload_video(youtube, video_path, title, description, tags, privacy_status="public"):
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = request.execute()
    return response["id"]


def build_description(number, credit_dict, custom_credits=None):
    """
    Build YouTube description.
    - custom_credits: if provided, use that string directly (per-number)
    - otherwise, use the global format without credits.
    """
    today = datetime.now().strftime("%B %d, %Y")
    base_desc = f"Daily video from Stupid Orange Riders.{today}"
    
    credit_text = credit_dict.get(str(number)) or credit_dict.get(number)
    if credit_text:
        base_desc += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📌 CREDITS:\n{credit_text}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Footer
    base_desc += "\n\n🔗 stupidorange.com\n#stupidorange #creativedaily #VideoOfTheDay #Dubai #dubai #rider #riders #talabat #deliveroo #careem #riders #UAE"
    return base_desc


def main():
    # 1. Get video files
    videos = get_video_files(VIDEO_FOLDER)
    if not videos:
        print("❌ No numbered video files found in", VIDEO_FOLDER)
        sys.exit(1)

    # 2. Determine which video to upload today
    last_uploaded = load_state()
    numbers = [v[0] for v in videos]
    print(f"Available video numbers: {numbers}")
    print(f"Last uploaded number: {last_uploaded}")

    if last_uploaded is None:
        next_number = numbers[0]          # first time: smallest
    else:
        try:
            idx = numbers.index(last_uploaded)
            next_idx = (idx + 1) % len(numbers)
            next_number = numbers[next_idx]
        except ValueError:
            next_number = numbers[0]

    # 3. Get file path for that number
    video_path = None
    for num, path in videos:
        if num == next_number:
            video_path = path
            break

    if not video_path:
        print(f"❌ Could not find file for number {next_number}")
        sys.exit(1)

    print(f"📹 Today's video: {video_path} (number {next_number})")

    # 4. Load credits
    credits = load_credits()
    description = build_description(next_number, credits)
    title = f"Video of the Day | ({datetime.now().strftime('%Y-%m-%d')}) | Stupid Orange Riders"
    tags = ["StupidOrange", "CreativeDaily", "VideoOfTheDay", "UAE","dubai","Dubai","Riders","talabat","careem","deliveroo","rider","DubaiMall"}"]

    # 5. Upload
    youtube = get_authenticated_service()
    try:
        video_id = upload_video(youtube, video_path, title, description, tags, privacy_status="public")
        print(f"✅ Uploaded! Video ID: {video_id}")
        print(f"🔗 https://youtu.be/{video_id}")

        # 6. Update state
        save_state(next_number)
        print(f"💾 Saved state: last_uploaded = {next_number}")

        # 7. Commit and push state (and credits if changed)
        commit_and_push_state()

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
