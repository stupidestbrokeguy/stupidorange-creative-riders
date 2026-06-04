#!/usr/bin/env python3
"""
Create a YouTube Shorts video with 3 A.I. prompts, using intro/prompt/background state.
Generates custom thumbnail from intro text + background image (cycled via state).
Text rendering uses the same proven method as the affirmation script.

UPDATED: Fixed audio loop for moviepy 2.x, added MAX_PROMPTS to keep video under 60s.
"""

import os
import sys
import json
import pickle
import socket
import subprocess
import textwrap
from datetime import datetime
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips
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

# Limit prompts to keep video under 60 seconds (5+7*5+10 = 50s). Adjust as needed.
MAX_PROMPTS = 7   # Set to None to use all prompts

# YouTube playlist settings
PLAYLIST_TITLE = "3 A.I. Prompts | Stupidest Broke Guy"
PLAYLIST_DESCRIPTION = """Weekly prompts to go from broke to Fortune 500 using AI.

#StupidestBrokeGuy #AIprompts #Fortune500 #Dubai #UAE #Shorts"""

# Thumbnail settings (16:9, 1280x720)
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
    print(f"💾 State saved to {STATE_FILE}: intro_index={state.get('intro_index')}, background_index={state.get('background_index')}, thumbnail_bg_index={state.get('thumbnail_bg_index', 0)}")

def get_next_item(state_key, items, state):
    if not items:
        return None
    idx = state.get(state_key, 0) % len(items)
    item = items[idx]
    state[state_key] = (idx + 1) % len(items)
    save_state(state)
    print(f"   🔄 {state_key}: was {idx}, now {state[state_key]} (next: {item[:40]}...)")
    return item

# ===== TEXT RENDERING for video (9:16) =====
def create_text_overlay(text, duration, font_size=90, bg_color=(0,0,0,200)):
    """Renders text on a transparent background, composites over a semi‑transparent black panel."""
    img = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load font
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

    # Wrap text
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

# ===== THUMBNAIL generation (16:9) with background image + intro text =====
def create_thumbnail_from_intro(intro_text, background_image_path, output_path):
    """Create a 1280x720 thumbnail using a background image and intro text."""
    print(f"🖼️ Creating thumbnail: {output_path}")
    bg = Image.open(background_image_path).convert('RGB')
    bg = bg.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(bg)

    # Load font (slightly smaller for thumbnail)
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

    # Clean and wrap intro text
    clean_text = intro_text.replace('\n', ' ')
    wrapped = textwrap.wrap(clean_text, width=25)  # 25 chars fits 1280px

    line_height = font_size + 15
    total_h = len(wrapped) * line_height
    start_y = (THUMB_HEIGHT - total_h) // 2

    # Add semi-transparent black bar behind text
    bar_height = total_h + 40
    bar_y = start_y - 20
    bar = Image.new('RGBA', (THUMB_WIDTH, bar_height), (0, 0, 0, 180))
    bg.paste(bar, (0, bar_y), bar)

    # Draw text
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

# ===== YouTube upload =====
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
        subprocess.run(["git", "config", "user.name", "github-actions"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True, capture_output=True)
        subprocess.run(["git", "add", STATE_FILE, INTROS_FILE, PROMPTS_FILE], check=True, capture_output=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode != 0:
            commit_msg = f"Update state after video upload {datetime.now().isoformat()} [skip ci]"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
            print(f"   ✅ Committed state with message: {commit_msg[:60]}...")
            push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
            if push_result.returncode == 0:
                print("   ✅ State files pushed to repository")
            else:
                print(f"   ⚠️ Git push failed: {push_result.stderr}")
        else:
            print("   ℹ️ No state changes to push")
    except Exception as e:
        print(f"   ❌ Failed to push state: {e}")

# ===== MAIN =====
def main():
    print("="*60)
    print("🎬 YouTube Shorts Video Creator – Custom Thumbnail with Intro Text & Background")
    print("="*60)

    # Load state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        print(f"📂 Loaded state: {state}")
    else:
        state = {"intro_index": 0, "background_index": 0, "thumbnail_bg_index": 0}
        save_state(state)
        print(f"📂 Created new state: {state}")

    intros = load_json(INTROS_FILE, ["🔥 3 A.I. Prompts\nFrom Broke to Fortune 500"])
    all_prompts = load_json(PROMPTS_FILE, [])
    if not all_prompts:
        print("❌ No prompts found in prompts.json")
        sys.exit(1)

    # Limit prompts if MAX_PROMPTS is set
    if MAX_PROMPTS is not None and len(all_prompts) > MAX_PROMPTS:
        prompts = all_prompts[:MAX_PROMPTS]
        print(f"📋 Using first {len(prompts)} of {len(all_prompts)} prompts (MAX_PROMPTS={MAX_PROMPTS})")
    else:
        prompts = all_prompts
        print(f"📋 Using all {len(prompts)} prompts")

    # Load background images
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

    # Get intro text and cycle state
    intro_text = get_next_item("intro_index", intros, state)
    intro_title = intro_text.replace('\n', ' ').strip()

    # --- Build video clips ---
    clips = []

    # Intro video clip (5s)
    intro_bg = next_background()
    intro_bg_clip = ImageClip(intro_bg).resized(VIDEO_SIZE).with_duration(INTRO_DURATION)
    intro_text_clip = create_text_overlay(intro_text, INTRO_DURATION, font_size=90, bg_color=(0,0,0,200))
    clips.append(CompositeVideoClip([intro_bg_clip, intro_text_clip]))

    # Prompts (each 5s)
    for i, prompt in enumerate(prompts):
        display_text = f"Prompt {i+1}\n\n{prompt}"
        bg = next_background()
        bg_clip = ImageClip(bg).resized(VIDEO_SIZE).with_duration(ASSIGNMENT_DURATION)
        txt_clip = create_text_overlay(display_text, ASSIGNMENT_DURATION, font_size=75, bg_color=(0,0,0,200))
        clips.append(CompositeVideoClip([bg_clip, txt_clip]))
        print(f"   Added Prompt {i+1}")

    # Outro (10s)
    outro_text = "✅ Thank you for watching!\n\n👉 Click the link in description\n👉 Join the Creative Daily\n👉 Start your Fortune 500 journey"
    outro_bg = next_background()
    outro_bg_clip = ImageClip(outro_bg).resized(VIDEO_SIZE).with_duration(OUTRO_DURATION)
    outro_txt_clip = create_text_overlay(outro_text, OUTRO_DURATION, font_size=85, bg_color=(0,0,0,200))
    clips.append(CompositeVideoClip([outro_bg_clip, outro_txt_clip]))

    # Concatenate
    print("🎬 Rendering video...")
    final_video = concatenate_videoclips(clips, method="compose")

    # ===== FIXED AUDIO LOOP (moviepy 2.x compatible) =====
    if os.path.exists(MUSIC_FILE):
        audio = AudioFileClip(MUSIC_FILE)
        if audio.duration < final_video.duration:
            # Loop by concatenating multiple copies
            n = int(final_video.duration / audio.duration) + 1
            audio = concatenate_audioclips([audio] * n)
            audio = audio.subclipped(0, final_video.duration)
        else:
            audio = audio.subclipped(0, final_video.duration)
        audio = audio.with_volume_scaled(0.3)
        final_video = final_video.with_audio(audio)
        print("🎵 Music added")

    final_video.write_videofile(OUTPUT_VIDEO, fps=24, codec='libx264', audio_codec='aac')
    size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
    print(f"✅ Video saved: {OUTPUT_VIDEO} ({size_mb:.1f} MB)")

    total_duration = final_video.duration
    if total_duration > 60:
        print(f"⚠️ Warning: Video duration {total_duration:.1f}s exceeds 60s. It may not be treated as a Short.")
        print(f"   → Reduce MAX_PROMPTS or lower ASSIGNMENT_DURATION.")
    else:
        print(f"✅ Video duration {total_duration:.1f}s → eligible for YouTube Shorts.")

    # --- Create Thumbnail using intro text + a background image (cycled separately) ---
    if "thumbnail_bg_index" not in state:
        state["thumbnail_bg_index"] = 0
    thumb_bg_idx = state["thumbnail_bg_index"] % len(bg_files)
    thumb_bg_path = bg_files[thumb_bg_idx]
    state["thumbnail_bg_index"] = (thumb_bg_idx + 1) % len(bg_files)
    save_state(state)
    print(f"🖼️ Thumbnail background: {os.path.basename(thumb_bg_path)} (index {state['thumbnail_bg_index']})")

    thumbnail_file = OUTPUT_VIDEO.replace('.mp4', '_thumbnail.jpg')
    create_thumbnail_from_intro(intro_text, thumb_bg_path, thumbnail_file)

    # --- Prepare YouTube metadata ---
    today = datetime.now().strftime("%B %d, %Y")
    title = f"{intro_title} | {today} | Stupidest Broke Guy #Shorts"
    if len(title) > 100:
        title = title[:97] + "..."

    prompts_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(prompts)])
    description = f"""In this YouTube Short, we give you copy‑paste ChatGPT prompts to turn your idea into a Fortune 500 strategy, based on real historical research.

🔥 THE PROMPTS (copy & paste into ChatGPT):

{prompts_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 How to use:
1. Copy the prompt that matches your stage (idea, prototype, scaling)
2. Paste into ChatGPT
3. Follow the AI's step‑by‑step plan

Join the Creative Daily community: creativedaily.stupidorange.com

#StupidestBrokeGuy #AIprompts #Fortune500 #Dubai #UAE #ChatGPT #StartupHacks #Shorts
"""
    tags = ["StupidestBrokeGuy", "AIprompts", "Fortune500", "Dubai", "UAE", "ChatGPT", "Startup", "Shorts"]

    # --- Upload to YouTube ---
    print("\n📤 Uploading to YouTube...")
    video_url = upload_to_youtube(OUTPUT_VIDEO, title, description, tags, thumbnail_path=thumbnail_file)

    # --- Push state (including thumbnail bg index) to GitHub ---
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
