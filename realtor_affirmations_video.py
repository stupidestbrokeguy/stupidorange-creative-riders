#!/usr/bin/env python3
"""
Realtor Affirmations – Daily YouTube Shorts with 7 affirmations.
Rotates through list, custom thumbnail, audio loop.
"""

import os, sys, json, pickle, socket, subprocess, textwrap, time, yaml
from datetime import datetime
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips
from PIL import Image, ImageDraw, ImageFont
import numpy as np

IMAGES_DIR = "images"
OUTPUT_VIDEO = "realtor_affirmations_video.mp4"
ASSIGNMENT_DURATION = 5
OUTRO_DURATION = 10
INTRO_DURATION = 5
VIDEO_SIZE = (1080, 1920)
MUSIC_FILE = "background_music.mp3"
STATE_FILE = "state_realtor_affirmations.json"
INTROS_FILE = "intros_realtor_affirmations.json"
AFFIRMATIONS_FILE = "affirmations_realtor.yaml"
MAX_AFFIRMATIONS = 7

PLAYLIST_TITLE = "Secure Creative Realtor Entreprenuer Mindset | Daily Affirmations for Agents,Dubai"
PLAYLIST_DESCRIPTION = """Are you ready for a Dubai Business Setup or have you already started your journey? Whether you're in the Dubai Fashion Business, enjoy Dubai Shopping, or simply keep up with Dubai news, cultivating the right Entrepreneur Mindset is everything.

In this video, discover how to Secure a Creative Entrepreneur Mindset by using simple Daily Affirmations in Dubai. Say these powerful lines every time you visit Burj Khalifa, Dubai Mall, or a Dubai Restaurant—even while doing Dubai Tourism. Speak to nature with a Creative Royalty Tracking Mindset, and train your brain to default toward building a Passive Wealth System.

Whether you're out enjoying the city or working on your business, let these affirmations align you with success, abundance, and creativity. Watch now and start thinking like a true creative entrepreneur in Dubai.Powerful affirmations for real estate agents – build confidence, close more deals.

#realtor #affirmations #realestate #mindset #shorts"""

THUMB_WIDTH, THUMB_HEIGHT = 1280, 720

# (Reuse all helper functions from realtor_prompts_video.py – identical logic, just change playlist title, etc.)
# To avoid duplication, we include them here but you can copy the same functions.
# I'll write a compact version.

def find_free_port(start=8080, end=8090):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except socket.error:
                continue
    return 8080

def load_json(fp, default):
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
    print(f"💾 Saved {STATE_FILE}")

def get_next_item(key, items, state):
    if not items:
        return None
    idx = state.get(key, 0) % len(items)
    item = items[idx]
    state[key] = (idx + 1) % len(items)
    save_state(state)
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

def create_thumbnail(intro_text, bg_path, out_path):
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

def upload_to_youtube(video_path, title, description, tags, thumb_path=None):
    # Same as previous, but we inline minimal version
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("❌ Missing google libs")
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
            port = find_free_port()
            creds = flow.run_local_server(port=port, open_browser=True)
            with open("token.pickle", 'wb') as f:
                pickle.dump(creds, f)
    youtube = build('youtube', 'v3', credentials=creds)
    playlists = youtube.playlists().list(part='snippet', mine=True, maxResults=50).execute()
    playlist_id = None
    for pl in playlists.get('items', []):
        if pl['snippet']['title'] == PLAYLIST_TITLE:
            playlist_id = pl['id']
            break
    if not playlist_id:
        resp = youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {'title': PLAYLIST_TITLE, 'description': PLAYLIST_DESCRIPTION},
                'status': {'privacyStatus': 'public'}
            }
        ).execute()
        playlist_id = resp['id']
    body = {
        'snippet': {'title': title[:100], 'description': description[:5000], 'tags': tags, 'categoryId': '22'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
    response = request.execute()
    video_id = response['id']
    video_url = f"https://youtu.be/{video_id}"
    time.sleep(3)
    if thumb_path and os.path.exists(thumb_path):
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
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

def push_state():
    try:
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True, capture_output=True)
        subprocess.run(["git", "add", STATE_FILE, INTROS_FILE, AFFIRMATIONS_FILE], check=True, capture_output=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True).returncode != 0:
            subprocess.run(["git", "commit", "-m", f"Update realtor affirmations {datetime.now().isoformat()} [skip ci]"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("   ✅ Pushed state")
    except Exception as e:
        print(f"   ❌ Push error: {e}")

def main():
    print("="*60)
    print("🎬 Realtor Affirmations – Daily Shorts")
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
    else:
        state = {"intro_index": 0, "background_index": 0, "thumbnail_bg_index": 0, "affirmation_offset": 0}
        save_state(state)

    intros = load_json(INTROS_FILE, ["✨ Daily Affirmations for Realtors"])
    with open(AFFIRMATIONS_FILE, 'r', encoding='utf-8') as f:
        all_aff = yaml.safe_load(f)
    if not all_aff:
        print("❌ No affirmations in affirmations_realtor.yaml")
        sys.exit(1)

    off = state.get("affirmation_offset", 0)
    affs = []
    for i in range(MAX_AFFIRMATIONS):
        affs.append(all_aff[(off + i) % len(all_aff)])
    state["affirmation_offset"] = (off + MAX_AFFIRMATIONS) % len(all_aff)
    save_state(state)
    print(f"📋 Affirmations offset {off} -> next {state['affirmation_offset']}")

    est = INTRO_DURATION + len(affs)*ASSIGNMENT_DURATION + OUTRO_DURATION
    if est > 60:
        print(f"⚠️ Duration {est}s > 60s")
        sys.exit(1)

    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
        print(f"❌ Create folder {IMAGES_DIR} with images")
        sys.exit(1)
    bg_files = [os.path.join(IMAGES_DIR, f) for f in sorted(os.listdir(IMAGES_DIR)) if f.lower().endswith(('.png','.jpg','.jpeg'))]
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
    clips.append(CompositeVideoClip([ImageClip(bg).resized(VIDEO_SIZE).with_duration(INTRO_DURATION),
                                     create_text_overlay(intro_text, INTRO_DURATION, 90)]))

    for i, a in enumerate(affs):
        bg = next_bg()
        clips.append(CompositeVideoClip([ImageClip(bg).resized(VIDEO_SIZE).with_duration(ASSIGNMENT_DURATION),
                                         create_text_overlay(f"Affirmation {i+1}\n\n{a}", ASSIGNMENT_DURATION, 75)]))

    outro_text = "🌟 Repeat these daily\n\nYour mindset = your business\nSubscribe for more"
    bg = next_bg()
    clips.append(CompositeVideoClip([ImageClip(bg).resized(VIDEO_SIZE).with_duration(OUTRO_DURATION),
                                     create_text_overlay(outro_text, OUTRO_DURATION, 85)]))

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
    create_thumbnail(intro_text, thumb_bg, thumb_file)

    today = datetime.now().strftime("%B %d, %Y")
    title = f"{intro_title} | {today} | Realtor Affirmations"
    if len(title) > 100:
        title = title[:97] + "..."
    aff_list = "\n".join([f"{i+1}. {a}" for i,a in enumerate(affs)])
    desc = f"Daily Creative Entreprenuer Mindset affirmations for real estate agents in Dubai.\n\n📿
    Are you ready for a Dubai Business Setup or have you already started your journey? Whether you're in the Dubai Fashion Business, enjoy Dubai Shopping, or simply keep up with Dubai news, cultivating the right Entrepreneur Mindset is everything.

In this video, discover how to Secure a Creative Entrepreneur Mindset by using simple Daily Affirmations in Dubai. Say these powerful lines every time you visit Burj Khalifa, Dubai Mall, or a Dubai Restaurant—even while doing Dubai Tourism. Speak to nature with a Creative Royalty Tracking Mindset, and train your brain to default toward building a Passive Wealth System.

Whether you're out enjoying the city or working on your business, let these affirmations align you with success, abundance, and creativity. Watch now and start thinking like a true creative entrepreneur in Dubai.REPEAT:\n{aff_list}\n\n#realtor #affirmations #realestate #shorts"
    tags = ["realtor", "affirmations", "realestate", "mindset", "shorts"]

    print("\n📤 Uploading...")
    url = upload_to_youtube(OUTPUT_VIDEO, title, desc, tags, thumb_path=thumb_file)
    push_state()
    if url:
        print(f"✅ {url}")
    else:
        print("⚠️ Upload failed")
    if os.path.exists(thumb_file):
        os.remove(thumb_file)

if __name__ == "__main__":
    main()
