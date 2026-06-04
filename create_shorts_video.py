#!/usr/bin/env python3
"""
Create a YouTube Shorts video with 3 A.I. prompts, using intro/prompt/background state,
extract a thumbnail from the intro, upload to YouTube, and push state back to GitHub.
"""

import os
import sys
import json
import pickle
import socket
import subprocess
from datetime import datetime
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ========== CONFIGURATION ==========
IMAGES_DIR = "images"
OUTPUT_VIDEO = "broke_to_fortune_500.mp4"
ASSIGNMENT_DURATION = 5        # seconds per prompt
OUTRO_DURATION = 10
INTRO_DURATION = 5
VIDEO_SIZE = (1080, 1920)      # 9:16 vertical (YouTube Shorts)
MUSIC_FILE = "background_music.mp3"
STATE_FILE = "state.json"
INTROS_FILE = "intros.json"
PROMPTS_FILE = "prompts.json"

# YouTube playlist settings
PLAYLIST_TITLE = "3 A.I. Prompts | Stupidest Broke Guy"
PLAYLIST_DESCRIPTION = """Weekly prompts to go from broke to Fortune 500 using AI.

#StupidestBrokeGuy #AIprompts #Fortune500 #Dubai #UAE #Shorts"""

# Thumbnail settings – YouTube custom thumbnail size (16:9, 1280x720)
THUMBNAIL_SIZE = (1280, 720)

# ========== Helper functions ==========
def find_free_port(start_port=8080, end_port=8090):
    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except socket.error:
                continue
    return 8080

def load_json(filepath, default_list):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default_list

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
    print(f"💾 State saved to {STATE_FILE}: intro_index={state.get('intro_index')}, prompt_index={state.get('prompt_index')}, background_index={state.get('background_index')}")

def get_next_item(state_key, items, state):
    if not items:
        return None
    idx = state.get(state_key, 0) % len(items)
    item = items[idx]
    state[state_key] = (idx + 1) % len(items)
    save_state(state)
    print(f"   🔄 {state_key}: was {idx}, now {state[state_key]} (next: {item[:40]}...)")
    return item

# ===== LARGER FONT SIZES =====
def create_text_overlay(text, duration, font_size=80, margin=60, bg_alpha=220):
    """
    Create a semi‑transparent text overlay on a transparent background.
    Font size increased for better readability on 9:16 vertical video.
    """
    img = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        # Use a bold, larger font
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Word wrap
    max_width = VIDEO_SIZE[0] - 2 * margin
    words = text.split()
    lines = []
    current = []
    for w in words:
        test = ' '.join(current + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(w)
        else:
            lines.append(' '.join(current))
            current = [w]
    if current:
        lines.append(' '.join(current))

    line_height = font_size + 15
    total_h = len(lines) * line_height + 60
    total_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        total_w = max(total_w, bbox[2] - bbox[0])
    total_w += 60

    panel_x = (VIDEO_SIZE[0] - total_w) // 2
    panel_y = (VIDEO_SIZE[1] - total_h) // 2

    panel_img = Image.new('RGBA', (total_w, total_h), (0, 0, 0, bg_alpha))
    img.paste(panel_img, (panel_x, panel_y), panel_img)

    draw = ImageDraw.Draw(img)
    y_text = panel_y + 30
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (VIDEO_SIZE[0] - line_w) // 2
        draw.text((x, y_text), line, fill=(255, 255, 255), font=font)
        y_text += line_height

    return ImageClip(np.array(img), duration=duration)

def extract_thumbnail_from_video(video_path, output_path, time_offset=0.5):
    try:
        from moviepy import VideoFileClip
    except ImportError:
        print("   ❌ moviepy not available for thumbnail extraction")
        return None

    print(f"🎬 Extracting thumbnail from {video_path} at t={time_offset}s")
    clip = VideoFileClip(video_path)
    if time_offset > clip.duration:
        time_offset = clip.duration * 0.5
    frame = clip.get_frame(time_offset)
    clip.close()

    img = Image.fromarray(frame.astype('uint8'), 'RGB')
    original_w, original_h = img.size
    print(f"   Original frame: {original_w}x{original_h}")

    target_ratio = THUMBNAIL_SIZE[0] / THUMBNAIL_SIZE[1]
    current_ratio = original_w / original_h

    if current_ratio > target_ratio:
        new_w = int(original_h * target_ratio)
        offset_x = (original_w - new_w) // 2
        img = img.crop((offset_x, 0, offset_x + new_w, original_h))
    else:
        new_h = int(original_w / target_ratio)
        offset_y = (original_h - new_h) // 2
        img = img.crop((0, offset_y, original_w, offset_y + new_h))

    img = img.resize(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    img.save(output_path, quality=90)
    print(f"   Thumbnail saved to {output_path} ({THUMBNAIL_SIZE[0]}x{THUMBNAIL_SIZE[1]})")
    return output_path

def upload_to_youtube(video_path, title, description, tags, thumbnail_path=None, playlist_id=None):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("❌ Google libraries not installed")
        return None

    SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
    CLIENT_SECRETS_FILE = "client_secrets.json"
    TOKEN_FILE = "token.pickle"

    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            credentials = pickle.load(f)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print("❌ client_secrets.json not found")
                return None
            print("🔐 Starting OAuth flow (will open browser on local machine only)")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            try:
                free_port = find_free_port()
                credentials = flow.run_local_server(port=free_port, open_browser=True)
            except OSError:
                credentials = flow.run_local_server(open_browser=True)
            with open(TOKEN_FILE, 'wb') as f:
                pickle.dump(credentials, f)

    youtube = build('youtube', 'v3', credentials=credentials)

    if not playlist_id:
        playlists = youtube.playlists().list(part='snippet', mine=True, maxResults=50).execute()
        for pl in playlists.get('items', []):
            if pl['snippet']['title'] == PLAYLIST_TITLE:
                playlist_id = pl['id']
                break
        if not playlist_id:
            response = youtube.playlists().insert(
                part='snippet,status',
                body={
                    'snippet': {'title': PLAYLIST_TITLE, 'description': PLAYLIST_DESCRIPTION},
                    'status': {'privacyStatus': 'public'}
                }
            ).execute()
            playlist_id = response['id']

    body = {
        'snippet': {
            'title': title[:100],
            'description': description[:5000],
            'tags': tags,
            'categoryId': '22'
        },
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    response = request.execute()
    video_id = response['id']
    video_url = f"https://youtu.be/{video_id}"

    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print(f"   🖼️ Custom thumbnail uploaded successfully")
        except Exception as e:
            print(f"   ⚠️ Could not upload custom thumbnail: {e}")

    youtube.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {'kind': 'youtube#video', 'videoId': video_id}
            }
        }
    ).execute()
    return video_url

def push_state_to_repo():
    """Commit and push state files back to GitHub with [skip ci] to prevent loops."""
    try:
        # Set git user (required for commit)
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True, capture_output=True)
        
        # Add state files
        subprocess.run(["git", "add", STATE_FILE, INTROS_FILE, PROMPTS_FILE], check=True, capture_output=True)
        
        # Check if there are changes to commit
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode != 0:
            # Commit with [skip ci] to avoid triggering a new workflow
            commit_msg = f"Update state after video upload {datetime.now().isoformat()} [skip ci]"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
            print(f"   ✅ Committed state with message: {commit_msg[:60]}...")
            
            # Push
            push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
            if push_result.returncode == 0:
                print("   ✅ State files pushed to repository")
            else:
                print(f"   ⚠️ Git push failed: {push_result.stderr}")
        else:
            print("   ℹ️ No state changes to push")
    except Exception as e:
        print(f"   ❌ Failed to push state: {e}")

def main():
    print("="*60)
    print("🎬 YouTube Shorts Video Creator (3 A.I. Prompts)")
    print("="*60)

    # Load state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        print(f"📂 Loaded state: {state}")
    else:
        state = {"intro_index": 0, "prompt_index": 0, "background_index": 0}
        save_state(state)
        print(f"📂 Created new state: {state}")

    intros = load_json(INTROS_FILE, ["🔥 3 A.I. Prompts\nFrom Broke to Fortune 500"])
    prompts = load_json(PROMPTS_FILE, [])
    if not prompts:
        print("❌ No prompts found in prompts.json")
        sys.exit(1)

    # Background images
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
        print(f"❌ No images folder – create '{IMAGES_DIR}' and add images")
        sys.exit(1)
    bg_files = [os.path.join(IMAGES_DIR, f) for f in sorted(os.listdir(IMAGES_DIR))
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not bg_files:
        print(f"❌ No images in '{IMAGES_DIR}'")
        sys.exit(1)
    print(f"🖼️ Found {len(bg_files)} background images")

    def next_background():
        idx = state["background_index"] % len(bg_files)
        state["background_index"] = (idx + 1) % len(bg_files)
        save_state(state)
        print(f"   🖼️ background_index: was {idx}, now {state['background_index']} (next bg: {os.path.basename(bg_files[idx])})")
        return bg_files[idx]

    clips = []

    # Intro (font size 100)
    intro_text = get_next_item("intro_index", intros, state)
    bg_intro = next_background()
    intro_bg = ImageClip(bg_intro).resized(VIDEO_SIZE).with_duration(INTRO_DURATION)
    intro_txt = create_text_overlay(intro_text, INTRO_DURATION, font_size=100, margin=50, bg_alpha=220)
    clips.append(CompositeVideoClip([intro_bg, intro_txt]))

    # Prompts (font size 80)
    for i, prompt in enumerate(prompts):
        bg = next_background()
        bg_clip = ImageClip(bg).resized(VIDEO_SIZE).with_duration(ASSIGNMENT_DURATION)
        display = f"Prompt {i+1}\n\n{prompt}"
        txt_clip = create_text_overlay(display, ASSIGNMENT_DURATION, font_size=80, margin=50, bg_alpha=220)
        clips.append(CompositeVideoClip([bg_clip, txt_clip]))
        print(f"   Added Prompt {i+1}")

    # Outro (font size 90)
    outro_text = "✅ Thank you for watching!\n\n👉 Click the link in description\n👉 Join the Creative Daily\n👉 Start your Fortune 500 journey"
    bg_outro = next_background()
    outro_bg = ImageClip(bg_outro).resized(VIDEO_SIZE).with_duration(OUTRO_DURATION)
    outro_txt = create_text_overlay(outro_text, OUTRO_DURATION, font_size=90, margin=50, bg_alpha=220)
    clips.append(CompositeVideoClip([outro_bg, outro_txt]))

    # Concatenate
    print("🎬 Rendering video...")
    final_video = concatenate_videoclips(clips, method="compose")

    if os.path.exists(MUSIC_FILE):
        audio = AudioFileClip(MUSIC_FILE)
        if audio.duration < final_video.duration:
            audio = audio.loop(int(final_video.duration / audio.duration) + 1)
        audio = audio.subclipped(0, final_video.duration).with_volume_scaled(0.3)
        final_video = final_video.with_audio(audio)
        print("🎵 Music added")

    final_video.write_videofile(OUTPUT_VIDEO, fps=24, codec='libx264', audio_codec='aac')
    size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
    print(f"✅ Video saved: {OUTPUT_VIDEO} ({size_mb:.1f} MB)")

    if final_video.duration > 60:
        print(f"⚠️ Warning: Video duration {final_video.duration:.1f}s exceeds 60s. It may not be treated as a Short.")
    else:
        print(f"✅ Video duration {final_video.duration:.1f}s → eligible for YouTube Shorts.")

    # Extract thumbnail
    thumbnail_file = OUTPUT_VIDEO.replace('.mp4', '_thumbnail.jpg')
    extract_thumbnail_from_video(OUTPUT_VIDEO, thumbnail_file, time_offset=1.0)

    # Build description with prompts
    prompts_list_text = "\n".join([f"{i+1}. {p}" for i, p in enumerate(prompts)])
    today = datetime.now().strftime("%B %d, %Y")
    title = f"3 A.I. Prompts to Go from Broke to Fortune 500 | {today} | Stupidest Broke Guy #Shorts"
    description = f"""In this YouTube Short, we give you 3 copy‑paste ChatGPT prompts to turn your idea into a Fortune 500 strategy, based on real historical research.

🔥 THE PROMPTS (copy & paste into ChatGPT):

{prompts_list_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 How to use:
1. Copy the prompt that matches your stage (idea, prototype, scaling)
2. Paste into ChatGPT
3. Follow the AI's step‑by‑step plan

Join the Creative Daily community: creativedaily.stupidorange.com

#StupidestBrokeGuy #AIprompts #Fortune500 #Dubai #UAE #ChatGPT #StartupHacks #Shorts
"""
    tags = ["StupidestBrokeGuy", "AIprompts", "Fortune500", "Dubai", "UAE", "ChatGPT", "Startup", "Shorts"]
    
    # Upload to YouTube
    print("\n📤 Uploading to YouTube...")
    video_url = upload_to_youtube(OUTPUT_VIDEO, title, description, tags, thumbnail_path=thumbnail_file)

    # Always push state, even if upload fails
    print("\n📁 Pushing state to GitHub...")
    push_state_to_repo()

    if video_url:
        print(f"✅ YouTube upload successful: {video_url}")
    else:
        print("⚠️ YouTube upload failed, but state has been saved and pushed.")

    # Cleanup
    if os.path.exists(thumbnail_file):
        os.remove(thumbnail_file)
        print("🧹 Removed temporary thumbnail file")

    print("\n🎉 Script finished.")

if __name__ == "__main__":
    main()
