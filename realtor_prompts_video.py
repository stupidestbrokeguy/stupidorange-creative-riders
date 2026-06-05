#!/usr/bin/env python3
"""
Realtor Channel – YouTube Shorts with real estate prompts.
Rotates prompts, custom thumbnail, audio loop, keeps video under 60s.
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
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np

IMAGES_DIR = "images"
OUTPUT_VIDEO = "realtor_prompts_video.mp4"
ASSIGNMENT_DURATION = 5
OUTRO_DURATION = 10
INTRO_DURATION = 5
VIDEO_SIZE = (1080, 1920)
MUSIC_FILE = "background_music.mp3"
STATE_FILE = "state_realtor_prompts.json"
INTROS_FILE = "intros_realtor_prompts.json"
PROMPTS_FILE = "prompts_realtor.json"
MAX_PROMPTS = 7

PLAYLIST_TITLE = "Realtor Success | Real Estate AI Prompts"
PLAYLIST_DESCRIPTION = """Daily AI prompts for real estate agents – lead generation, closing scripts, marketing.

#realtor #realestate #AIprompts #shorts"""

THUMB_WIDTH, THUMB_HEIGHT = 1280, 720

def find_free_port(start=8080, end=8090):
    for port in range(start, end):
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
    print(f"   🔄 {state_key}: {idx} -> {state[state_key]}")
    return item

def create_text_overlay(text, duration, font_size=90, bg_color=(0,0,0,200)):
    img = Image.new('RGBA', VIDEO_SIZE, (0,0,0,0))
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
    wrapped = textwrap.wrap(text, width=max_chars)
    line_h = font_size + 15
    total_h = len(wrapped) * line_h
    start_y = (VIDEO_SIZE[1] - total_h) // 2
    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0,0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (VIDEO_SIZE[0] - w) // 2
        y = start_y + i * line_h
        draw.text((x, y), line, fill=(255,255,255), font=font)
    panel = Image.new('RGBA', VIDEO_SIZE, bg_color)
    final = Image.alpha_composite(panel, img)
    return ImageClip(np.array(final), duration=duration)

def create_thumbnail_from_intro(intro_text, bg_path, out_path):
    print(f"🖼️ Thumbnail: {out_path}")
    bg = Image.open(bg_path).convert('RGB')
    bg = bg.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(bg)
    try:
        if sys.platform == "win32":
            font = ImageFont.truetype("arialbd.ttf", 80)
        else:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()
    clean = intro_text.replace('\n', ' ')
    wrapped = textwrap.wrap(clean, width=25)
    line_h = 95
    total_h = len(wrapped) * line_h
    start_y = (THUMB_HEIGHT - total_h) // 2
    bar_h = total_h + 40
    bar_y = start_y - 20
    bar = Image.new('RGBA', (THUMB_WIDTH, bar_h), (0,0,0,180))
    bg.paste(bar, (0, bar_y), bar)
    draw = ImageDraw.Draw(bg)
    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0,0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (THUMB_WIDTH - w) // 2
        y = start_y + i * line_h
        draw.text((x, y), line, fill=(255,255,255), font=font)
    bg.save(out_path, quality=90)
    return out_path

def upload_to_youtube(video_path, title, description, tags, thumbnail_path=None, playlist_id=None):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("❌ Google libs missing")
        return None

    SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
            free_port = find_free_port()
            creds = flow.run_local_server(port=free_port, open_browser=True)
            with open("token.pickle", 'wb') as f:
                pickle.dump(creds, f)

    youtube = build('youtube', 'v3', credentials=creds)

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
    print(f"✅ Uploaded video ID: {video_id}")

    time.sleep(3)
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
            print("   ✅ Thumbnail set")
        except Exception as e:
            print(f"   ⚠️ Thumbnail failed: {e}")

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
    try:
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True, capture_output=True)
        subprocess.run(["git", "add", STATE_FILE, INTROS_FILE, PROMPTS_FILE], check=True, capture_output=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode != 0:
            commit_msg = f"Update realtor prompts state {datetime.now().isoformat()} [skip ci]"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print("   ✅ State pushed")
        else:
            print("   ℹ️ No changes")
    except Exception as e:
        print(f"   ❌ Push failed: {e}")

def main():
    print("="*60)
    print("🎬 Realtor Prompts – YouTube Shorts")
    print("="*60)

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
    else:
        state = {"intro_index": 0, "background_index": 0, "thumbnail_bg_index": 0, "prompt_offset": 0}
        save_state(state)

    intros = load_json(INTROS_FILE, ["🏠 Real Estate AI Prompts\n\nClose more deals"])
    all_prompts = load_json(PROMPTS_FILE, [])
    if not all_prompts:
        print("❌ No prompts in prompts_realtor.json")
        sys.exit(1)

    offset = state.get("prompt_offset", 0)
    prompts = []
    for i in range(MAX_PROMPTS):
        idx = (offset + i) % len(all_prompts)
        prompts.append(all_prompts[idx])
    state["prompt_offset"] = (offset + MAX_PROMPTS) % len(all_prompts)
    save_state(state)
    print(f"📋 Prompts starting at {offset} (next {state['prompt_offset']})")

    est = INTRO_DURATION + len(prompts)*ASSIGNMENT_DURATION + OUTRO_DURATION
    if est > 60:
        print(f"⚠️ Duration {est}s > 60s – abort")
        sys.exit(1)
    else:
        print(f"✅ Duration {est}s")

    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
        print(f"❌ Create folder '{IMAGES_DIR}' with images")
        sys.exit(1)
    bg_files = [os.path.join(IMAGES_DIR, f) for f in sorted(os.listdir(IMAGES_DIR))
                if f.lower().endswith(('.png','.jpg','.jpeg'))]
    if not bg_files:
        print(f"❌ No images in {IMAGES_DIR}")
        sys.exit(1)

    def next_bg():
        idx = state["background_index"] % len(bg_files)
        state["background_index"] = (idx + 1) % len(bg_files)
        save_state(state)
        return bg_files[idx]

    intro_text = get_next_item("intro_index", intros, state)
    intro_title = intro_text.replace('\n', ' ').strip()

    clips = []
    bg = next_bg()
    intro_bg_clip = ImageClip(bg).resized(VIDEO_SIZE).with_duration(INTRO_DURATION)
    intro_txt = create_text_overlay(intro_text, INTRO_DURATION, font_size=90)
    clips.append(CompositeVideoClip([intro_bg_clip, intro_txt]))

    for i, p in enumerate(prompts):
        display = f"Prompt {i+1}\n\n{p}"
        bg = next_bg()
        bg_clip = ImageClip(bg).resized(VIDEO_SIZE).with_duration(ASSIGNMENT_DURATION)
        txt_clip = create_text_overlay(display, ASSIGNMENT_DURATION, font_size=75)
        clips.append(CompositeVideoClip([bg_clip, txt_clip]))

    outro_text = "✅ Thank you!\n\nMore prompts in description\nSubscribe for daily realtor success"
    bg = next_bg()
    outro_bg = ImageClip(bg).resized(VIDEO_SIZE).with_duration(OUTRO_DURATION)
    outro_txt = create_text_overlay(outro_text, OUTRO_DURATION, font_size=85)
    clips.append(CompositeVideoClip([outro_bg, outro_txt]))

    final = concatenate_videoclips(clips, method="compose")

    if os.path.exists(MUSIC_FILE):
        audio = AudioFileClip(MUSIC_FILE)
        if audio.duration < final.duration:
            n = int(final.duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * n).subclipped(0, final.duration)
        else:
            audio = audio.subclipped(0, final.duration)
        audio = audio.with_volume_scaled(0.3)
        final = final.with_audio(audio)

    final.write_videofile(OUTPUT_VIDEO, fps=24, codec='libx264', audio_codec='aac')
    print(f"✅ Video saved: {OUTPUT_VIDEO}")

    # Thumbnail
    thumb_idx = state.get("thumbnail_bg_index", 0) % len(bg_files)
    thumb_bg = bg_files[thumb_idx]
    state["thumbnail_bg_index"] = (thumb_idx + 1) % len(bg_files)
    save_state(state)
    thumb_file = OUTPUT_VIDEO.replace('.mp4', '_thumb.jpg')
    create_thumbnail_from_intro(intro_text, thumb_bg, thumb_file)

    today = datetime.now().strftime("%B %d, %Y")
    title = f"{intro_title} | {today} | Realtor AI Prompts"
    if len(title) > 100:
        title = title[:97] + "..."
    prompts_list = "\n".join([f"{i+1}. {p}" for i,p in enumerate(prompts)])
    description = f"""Daily AI prompts for real estate agents.\n\n🔥 PROMPTS:\n{prompts_list}\n\n#realtor #realestate #AIprompts #shorts"""
    tags = ["realtor", "realestate", "AIprompts", "shorts"]

    print("\n📤 Uploading...")
    url = upload_to_youtube(OUTPUT_VIDEO, title, description, tags, thumbnail_path=thumb_file)

    push_state_to_repo()
    if url:
        print(f"✅ {url}")
    else:
        print("⚠️ Upload failed")
    if os.path.exists(thumb_file):
        os.remove(thumb_file)

if __name__ == "__main__":
    main()
