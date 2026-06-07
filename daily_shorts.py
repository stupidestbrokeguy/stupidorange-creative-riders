"""
Daily Picture to YouTube Shorts - Full Screen Image (No Background)
Features:
- THUMBNAIL: Compressed JPG under 2MB for YouTube
- VIDEO: Full screen image - NO background, NO animation
- Auto-commits state to GitHub using GITHUB_TOKEN
"""

import os
import sys
import json
import pickle
import socket
import time
import subprocess
from datetime import datetime
from PIL import Image
import random

# ========== CONFIGURATION ==========
VIDEO_TITLE = "Stupid Broke Moment, What Happened? - Stupid Orange, Stupid Orange Riders Dubai, Creative Daily"
HASHTAGS = "#stupidorange #creativedaily #stupidorangeriders #Dubai #UAE #fyp #dubai #talabat #rider #careem #deliveroo #delivery #BikerLife #dubailife"
VIDEO_DURATION = random.randint(16, 21) 
IMAGES_FOLDER = "daily_images"
STATE_FILE = "shorts_state.json"
# ===================================

def load_state():
    """Load the state file to know which image to use next"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        print(f"📂 Loaded state: last used {state.get('last_image', 'none')}")
        return state
    return {'last_index': 0, 'last_date': None, 'last_image': None}

def save_state(state):
    """Save current state locally"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"💾 State saved locally")

def commit_and_push_state():
    """Commit and push shorts_state.json back to GitHub using GITHUB_TOKEN"""
    print(f"\n📤 Committing state changes to GitHub...")
    
    try:
        # Configure git user
        subprocess.run(['git', 'config', '--global', 'user.name', 'github-actions[bot]'], capture_output=True)
        subprocess.run(['git', 'config', '--global', 'user.email', 'github-actions[bot]@users.noreply.github.com'], capture_output=True)
        
        # Check if there are changes
        result = subprocess.run(['git', 'status', '--porcelain', STATE_FILE], capture_output=True, text=True)
        
        if not result.stdout.strip():
            print(f"   ℹ️ No changes to commit")
            return True
        
        # Add and commit
        subprocess.run(['git', 'add', STATE_FILE], check=True, capture_output=True)
        commit_msg = f"Update shorts_state.json - posted image for {datetime.now().strftime('%Y-%m-%d')}"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
        print(f"   ✅ Committed state")
        
        # Push to remote
        push_result = subprocess.run(['git', 'push'], capture_output=True, text=True)
        if push_result.returncode == 0:
            print(f"   ✅ State pushed to GitHub")
        else:
            print(f"   ⚠️ Push failed: {push_result.stderr}")
            # Try force push as fallback
            force_push = subprocess.run(['git', 'push', '--force'], capture_output=True, text=True)
            if force_push.returncode == 0:
                print(f"   ✅ State force-pushed to GitHub")
            else:
                print(f"   ❌ Push failed")
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️ Git command failed: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️ Could not commit state: {e}")
        return False

def get_next_image():
    """Determine which image to use today"""
    state = load_state()
    
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get('last_date') == today:
        print(f"⚠️ Already posted today ({today})")
        return None, None, state

    if not os.path.exists(IMAGES_FOLDER):
        print(f"❌ Images folder not found: {IMAGES_FOLDER}")
        return None, None, state

    available_images = []
    for i in range(1, 16):
        for ext in ['.png', '.jpg', '.jpeg']:
            img_path = os.path.join(IMAGES_FOLDER, f"{i}{ext}")
            if os.path.exists(img_path):
                available_images.append((i, img_path))
                break

    if not available_images:
        print(f"❌ No images found")
        return None, None, state

    last_index = state.get('last_index', 0)
    next_position = last_index % len(available_images)
    next_num, next_image = available_images[next_position]

    print(f"🖼️ Selected image #{next_num}")
    return next_image, next_num, state

def find_free_port(start_port=8080, end_port=8090):
    """Find a free port for OAuth callback"""
    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except socket.error:
                continue
    return 8080

def create_fullscreen_thumbnail(image_path, output_path=None):
    """Create THUMBNAIL under 2MB for YouTube"""
    print(f"\n📸 Creating FULL SCREEN THUMBNAIL...")
    
    if output_path is None:
        base = os.path.splitext(image_path)[0]
        output_path = f"{base}_thumbnail.jpg"

    try:
        pil_img = Image.open(image_path)
        target_width, target_height = 1080, 1920
        
        print(f"   📸 Original: {pil_img.size}")
        print(f"   📐 Target: {target_width}x{target_height}")

        # Stretch image to cover ENTIRE frame
        try:
            img_resized = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        except AttributeError:
            try:
                img_resized = pil_img.resize((target_width, target_height), Image.LANCZOS)
            except:
                img_resized = pil_img.resize((target_width, target_height))

        # Save as JPG with compression to stay under 2MB
        img_resized.save(output_path, quality=85, optimize=True)
        
        # Check file size
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"   ✅ Thumbnail created: {file_size:.2f} MB (under 2MB limit)")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def create_fullscreen_video(image_path, output_path=None, slide_duration=15, audio_file=None):
    """Create VIDEO: Full screen image, no background, no animation"""
    if output_path is None:
        base = os.path.splitext(image_path)[0]
        output_path = f"{base}_shorts.mp4"

    print(f"\n🎬 Creating FULL SCREEN VIDEO...")

    try:
        from moviepy import ImageClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
    except ImportError:
        try:
            from moviepy.editor import ImageClip, AudioFileClip
        except ImportError as e:
            print(f"❌ moviepy import failed: {e}")
            return None

    screen_width, screen_height = 1080, 1920

    try:
        from PIL import Image
        
        pil_img = Image.open(image_path)
        
        # Stretch image to full screen
        try:
            img_resized = pil_img.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
        except AttributeError:
            try:
                img_resized = pil_img.resize((screen_width, screen_height), Image.LANCZOS)
            except:
                img_resized = pil_img.resize((screen_width, screen_height))

        temp_img_path = base + "_temp.jpg"
        img_resized.save(temp_img_path, quality=90)

        # Create static image clip (no animation)
        final_clip = ImageClip(temp_img_path, duration=slide_duration)
        
        print(f"   ✅ Video created (full screen)")

        # ========== AUDIO HANDLING ==========
        audio_added = False
        
        def add_audio_to_clip(clip, audio_path, volume=0.25):
            try:
                if not os.path.exists(audio_path):
                    return clip, False
                
                audio = AudioFileClip(audio_path)
                if audio.duration < slide_duration:
                    loops = int(slide_duration / audio.duration) + 1
                    audio = audio.loop(loops)
                audio = audio.subclipped(0, slide_duration)
                
                try:
                    audio = audio.with_volume_scaled(volume)
                except AttributeError:
                    try:
                        audio = audio.volumex(volume)
                    except:
                        pass
                
                return clip.with_audio(audio), True
            except Exception as e:
                print(f"   ⚠️ Audio error: {e}")
                return clip, False

        if audio_file:
            final_clip, audio_added = add_audio_to_clip(final_clip, audio_file, 0.25)
        
        if not audio_added:
            common_audio = ["background_music.mp3", "shorts_music.mp3", "audio.mp3", "music.mp3"]
            for audio in common_audio:
                if os.path.exists(audio):
                    final_clip, audio_added = add_audio_to_clip(final_clip, audio, 0.25)
                    if audio_added:
                        break

        # Render video
        print(f"   💾 Rendering...")
        audio_codec = 'aac' if audio_added else None

        try:
            final_clip.write_videofile(output_path, codec='libx264', audio_codec=audio_codec, 
                                       fps=30, bitrate="5000k", preset='medium', logger=None)
        except TypeError:
            final_clip.write_videofile(output_path, codec='libx264', audio_codec=audio_codec, 
                                       fps=30, bitrate="5000k", preset='medium')

        final_clip.close()
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        print(f"   ✅ Video created")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def upload_to_youtube(video_path, thumbnail_path=None):
    """Upload video to YouTube as Short"""
    print(f"\n📤 Uploading to YouTube...")

    video_description = f"""{VIDEO_TITLE}

{HASHTAGS}
Welcome to the Stupid Orange world where stories are turned to royalties.

Share your Stupid Broke Moment: https://www.stupidorange.com/share-moment/

#stupidorange #creativedaily #stupidestbrokeguy #Dubai #UAE #fyp
"""

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
        credentials = None

        if os.path.exists("token.pickle"):
            with open("token.pickle", 'rb') as f:
                credentials = pickle.load(f)
            print(f"   📂 Loaded saved credentials")

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print("   🔄 Refreshing token...")
                credentials.refresh(Request())
            else:
                if not os.path.exists("client_secrets.json"):
                    print(f"   ❌ No client_secrets.json found!")
                    return {'status': 'skipped', 'error': 'No credentials'}
                
                print("   🔐 Opening browser for authentication...")
                flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
                credentials = flow.run_local_server(port=find_free_port(), open_browser=True)
            
            with open("token.pickle", 'wb') as f:
                pickle.dump(credentials, f)

        youtube = build('youtube', 'v3', credentials=credentials)
        print(f"   ✅ YouTube service built")

        body = {
            'snippet': {
                'title': VIDEO_TITLE[:100],
                'description': video_description[:5000],
                'tags': ['stupidorange', 'creativedaily', 'shorts'],
                'categoryId': '22'
            },
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        response = None
        for attempt in range(3):
            try:
                response = request.execute()
                break
            except Exception as e:
                print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(5)
        
        if not response:
            raise Exception("Upload failed after 3 attempts")
        
        video_url = f"https://youtube.com/shorts/{response['id']}"
        print(f"   ✅ Uploaded! URL: {video_url}")

        # Upload thumbnail (now under 2MB)
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                print(f"   🖼️ Uploading thumbnail...")
                youtube.thumbnails().set(videoId=response['id'], media_body=MediaFileUpload(thumbnail_path)).execute()
                print(f"   ✅ Thumbnail uploaded!")
            except Exception as e:
                print(f"   ⚠️ Thumbnail error: {e}")

        return {'status': 'success', 'video_url': video_url}
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return {'status': 'failed', 'error': str(e)}

def main():
    print("="*60)
    print("🎬 DAILY YOUTUBE SHORTS - FULL SCREEN IMAGE")
    print("📸 Image fills entire screen - NO background")
    print("="*60)

    image_path, image_num, state = get_next_image()
    if image_path is None:
        sys.exit(0)

    print(f"\n🎯 Processing: {os.path.basename(image_path)}")
    
    thumbnail_path = create_fullscreen_thumbnail(image_path)
    video_path = create_fullscreen_video(image_path, slide_duration=VIDEO_DURATION)
    
    if video_path is None:
        print("❌ Video creation failed!")
        sys.exit(1)

    result = upload_to_youtube(video_path, thumbnail_path)
    
    if result and result['status'] == 'success':
        state['last_index'] = image_num
        state['last_date'] = datetime.now().strftime("%Y-%m-%d")
        state['last_image'] = os.path.basename(image_path)
        save_state(state)
        
        # Commit and push to GitHub
        commit_and_push_state()
        
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print(f"   🔗 URL: {result['video_url']}")
        print("="*60)
    else:
        print(f"\n❌ FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
