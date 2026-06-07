#!/usr/bin/env python3
"""
Create a YouTube Shorts video for Daily Affirmations – 7 affirmations per video, with rotation and state tracking.
UPDATED: Affirmation rotation, thumbnail delay, duration check, and full state management.
"""

import os
import sys
import json
import pickle
import socket
import subprocess
import textwrap
import time
from datetime import datetime
import yaml
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ========== CONFIGURATION ==========
IMAGES_DIR = "images"
OUTPUT_VIDEO = "affirmations_video.mp4"
ASSIGNMENT_DURATION = 5
OUTRO_DURATION = 10
INTRO_DURATION = 5
VIDEO_SIZE = (1080, 1920)
MUSIC_FILE = "background_music.mp3"
STATE_FILE = "state_affirmations.json"
INTROS_FILE = "intros_affirmations.json"
AFFIRMATIONS_FILE = "affirmations.yaml"

MAX_AFFIRMATIONS = 7     # keep video under 60s (5+35+10=50s)

PLAYLIST_TITLE = "Secure Creative Entreprenuer Mindset | Positive Mindset | Manifestation | Stupid Orange Dubai"
PLAYLIST_DESCRIPTION = """Are you ready for a Dubai Business Setup or have you already started your journey? Whether you're in the Dubai Fashion Business, enjoy Dubai Shopping, or simply keep up with Dubai news, cultivating the right Entrepreneur Mindset is everything.

In this video, discover how to Secure a Creative Entrepreneur Mindset by using simple Daily Affirmations in Dubai. Say these powerful lines every time you visit Burj Khalifa, Dubai Mall, or a Dubai Restaurant—even while doing Dubai Tourism. Speak to nature with a Creative Royalty Tracking Mindset, and train your brain to default toward building a Passive Wealth System.

Whether you're out enjoying the city or working on your business, let these affirmations align you with success, abundance, and creativity. Watch now and start thinking like a true creative entrepreneur in Dubai..

#affirmations #dailymotivation #positivity #manifestation #shorts"""

THUMB_WIDTH, THUMB_HEIGHT = 1280, 720

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
    print(f"💾 State saved to {STATE_FILE}")

def get_next_item(state_key, items, state):
    if not items:
        return None
    idx = state.get(state_key, 0) % len(items)
    item = items[idx]
    state[state_key] = (idx + 1) % len(items)
    save_state(state)
    print(f"   🔄 {state_key}: was {idx}, now {state[state_key]}")
    return item

def create_text_overlay(text, duration, font_size=90, bg_color=(0,0,0,200)):
    img = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        if sys.platform == "win32":
            font = ImageFont.truetype("arialbd.ttf", font_size)
        else:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    max_chars = 30
    wrapped_lines = textwrap.wrap(text, width=max_chars)
    line_height = font_size + 15
    total_height = len(wrapped_lines) * line_height
    start_y = (VIDEO_SIZE[1] - total_height) // 2
    for i, line in enumerate(wrapped_lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (VIDEO_SIZE[0] - line_width) // 2
        y = start_y + i * line_height
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
    panel = Image.new('RGBA', VIDEO_SIZE, bg_color)
    final = Image.alpha_composite(panel, img)
    return ImageClip(np.array(final), duration=duration)

def create_thumbnail_from_intro(intro_text, background_image_path, output_path):
    print(f"🖼️ Creating thumbnail: {output_path}")
    bg = Image.open(background_image_path).convert('RGB')
    bg = bg.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(bg)
    font_size = 80
    try:
        if sys.platform == "win32":
            font = ImageFont.truetype("arialbd.ttf", font_size)
        else:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    clean_text = intro_text.replace('\n', ' ')
    wrapped = textwrap.wrap(clean_text, width=25)
    line_height = font_size + 15
    total_h = len(wrapped) * line_height
    start_y = (THUMB_HEIGHT - total_h) // 2
    bar_height = total_h + 40
    bar_y = start_y - 20
    bar = Image.new('RGBA', (THUMB_WIDTH, bar_height), (0, 0, 0, 180))
    bg.paste(bar, (0, bar_y), bar)
    draw = ImageDraw.Draw(bg)
    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (THUMB_WIDTH - line_w) // 2
        y = start_y + i * line_height
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
    bg.save(output_path, quality=90)
    print(f"   ✅ Thumbnail saved: {output_path}")
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
    print(f"✅ Video uploaded, ID: {video_id}")

    # Wait for YouTube to process before setting thumbnail
    print("⏳ Waiting 3 seconds for YouTube to process...")
    time.sleep(3)

    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("   ✅ Custom thumbnail set successfully on the video")
        except Exception as e:
            print(f"   ⚠️ Could not set custom thumbnail: {e}")
    else:
        print("   ⚠️ No thumbnail file found, skipping thumbnail upload")

    youtube.playlistItems().insert(
        part='snippet',
        body={
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {'kind': 'youtube#video', 'videoId': video_id}
            }
        }
    ).execute()
    print(f"   📂 Added to playlist: {PLAYLIST_TITLE}")
    return video_url

def push_state_to_repo():
    try:
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True, capture_output=True)
        subprocess.run(["git", "add", STATE_FILE, INTROS_FILE, AFFIRMATIONS_FILE], check=True, capture_output=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode != 0:
            commit_msg = f"Update affirmations state {datetime.now().isoformat()} [skip ci]"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
            print(f"   ✅ Committed affirmations state")
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
    print("🎬 Affirmations – YouTube Shorts Generator (with Rotation & Thumbnail Fix)")
    print("="*60)

    # Load state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        print(f"📂 Loaded state: {state}")
    else:
        state = {"intro_index": 0, "background_index": 0, "thumbnail_bg_index": 0, "affirmation_offset": 0}
        save_state(state)
        print(f"📂 Created new state: {state}")

    # Load intros (JSON) and affirmations (YAML)
    intros = load_json(INTROS_FILE, ["✨ Daily Affirmations\n\nYou are worthy", "💫 Morning Affirmations\n\nToday is my day", "🌞 Positive Mindset\n\nI attract success"])
    with open(AFFIRMATIONS_FILE, 'r', encoding='utf-8') as f:
        all_affirmations = yaml.safe_load(f)
    if not all_affirmations:
        print("❌ No affirmations found in affirmations.yaml")
        sys.exit(1)

    # --- AFFIRMATION ROTATION ---
    offset = state.get("affirmation_offset", 0)
    affirmations = []
    for i in range(MAX_AFFIRMATIONS):
        idx = (offset + i) % len(all_affirmations)
        affirmations.append(all_affirmations[idx])
    state["affirmation_offset"] = (offset + MAX_AFFIRMATIONS) % len(all_affirmations)
    save_state(state)
    print(f"📋 Using affirmations starting at index {offset} (next offset: {state['affirmation_offset']})")

    # Duration check
    est_duration = INTRO_DURATION + (len(affirmations) * ASSIGNMENT_DURATION) + OUTRO_DURATION
    if est_duration > 60:
        print(f"⚠️ Estimated duration {est_duration}s > 60s. Reduce MAX_AFFIRMATIONS or shorten durations.")
        sys.exit(1)
    else:
        print(f"✅ Estimated duration {est_duration}s (under 60s limit)")

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
        return bg_files[idx]

    intro_text = get_next_item("intro_index", intros, state)
    intro_title = intro_text.replace('\n', ' ').strip()

    clips = []

    # Intro
    intro_bg = next_background()
    intro_bg_clip = ImageClip(intro_bg).resized(VIDEO_SIZE).with_duration(INTRO_DURATION)
    intro_txt = create_text_overlay(intro_text, INTRO_DURATION, font_size=90, bg_color=(0,0,0,200))
    clips.append(CompositeVideoClip([intro_bg_clip, intro_txt]))

    # Affirmations
    for i, aff in enumerate(affirmations):
        display = f"Affirmation {i+1}\n\n{aff}"
        bg = next_background()
        bg_clip = ImageClip(bg).resized(VIDEO_SIZE).with_duration(ASSIGNMENT_DURATION)
        txt_clip = create_text_overlay(display, ASSIGNMENT_DURATION, font_size=75, bg_color=(0,0,0,200))
        clips.append(CompositeVideoClip([bg_clip, txt_clip]))
        print(f"   Added Affirmation {i+1}: {aff[:50]}...")

    # Outro
    outro_text = "🌟 Repeat these daily\n\nYour mind creates your reality\n\nSubscribe for more"
    outro_bg = next_background()
    outro_bg_clip = ImageClip(outro_bg).resized(VIDEO_SIZE).with_duration(OUTRO_DURATION)
    outro_txt = create_text_overlay(outro_text, OUTRO_DURATION, font_size=85, bg_color=(0,0,0,200))
    clips.append(CompositeVideoClip([outro_bg_clip, outro_txt]))

    final_video = concatenate_videoclips(clips, method="compose")

    # Audio loop
    if os.path.exists(MUSIC_FILE):
        audio = AudioFileClip(MUSIC_FILE)
        if audio.duration < final_video.duration:
            n = int(final_video.duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * n)
            audio = audio.subclipped(0, final_video.duration)
        else:
            audio = audio.subclipped(0, final_video.duration)
        audio = audio.with_volume_scaled(0.3)
        final_video = final_video.with_audio(audio)

    final_video.write_videofile(OUTPUT_VIDEO, fps=24, codec='libx264', audio_codec='aac')
    print(f"✅ Video saved: {OUTPUT_VIDEO} ({os.path.getsize(OUTPUT_VIDEO)/(1024*1024):.1f} MB)")

    # Thumbnail
    if "thumbnail_bg_index" not in state:
        state["thumbnail_bg_index"] = 0
    thumb_idx = state["thumbnail_bg_index"] % len(bg_files)
    thumb_bg = bg_files[thumb_idx]
    state["thumbnail_bg_index"] = (thumb_idx + 1) % len(bg_files)
    save_state(state)
    thumbnail_file = OUTPUT_VIDEO.replace('.mp4', '_thumbnail.jpg')
    create_thumbnail_from_intro(intro_text, thumb_bg, thumbnail_file)

    # Metadata
    today = datetime.now().strftime("%B %d, %Y")
    title = f"{intro_title} | {today} | Daily Affirmations Dubai"
    if len(title) > 100:
        title = title[:97] + "..."

    aff_list = "\n".join([f"{i+1}. {a}" for i, a in enumerate(affirmations)])
    description = f"""Start your day with these {len(affirmations)} powerful affirmations.Are you ready for a Dubai Business Setup or have you already started your journey? Whether you're in the Dubai Fashion Business, enjoy Dubai Shopping, or simply keep up with Dubai news, cultivating the right Entrepreneur Mindset is everything.

In this video, discover how to Secure a Creative Entrepreneur Mindset by using simple Daily Affirmations in Dubai. Say these powerful lines every time you visit Burj Khalifa, Dubai Mall, or a Dubai Restaurant—even while doing Dubai Tourism. Speak to nature with a Creative Royalty Tracking Mindset, and train your brain to default toward building a Passive Wealth System.

Whether you're out enjoying the city or working on your business, let these affirmations align you with success, abundance, and creativity. Watch now and start thinking like a true creative entrepreneur in Dubai.

📿 REPEAT THEM:
{aff_list}

💬 Speak them aloud every morning.

#affirmations #dailymotivation #manifestation #positivity #shorts"""

    tags = ["affirmations", "dailymotivation", "manifestation", "positivity", "shorts"]

    print("\n📤 Uploading to YouTube...")
    video_url = upload_to_youtube(OUTPUT_VIDEO, title, description, tags, thumbnail_path=thumbnail_file)

    print("\n📁 Pushing state to GitHub...")
    push_state_to_repo()

    if video_url:
        print(f"✅ YouTube upload successful: {video_url}")
    else:
        print("⚠️ YouTube upload failed, but state saved.")

    if os.path.exists(thumbnail_file):
        os.remove(thumbnail_file)

    print("\n🎉 Affirmations script finished.")

if __name__ == "__main__":
    main()
