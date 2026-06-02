"""
Daily Picture to YouTube Shorts - Auto Rotate Through Images
Automatically rotates through images in daily_images folder
USAGE: python daily_shorts.py
"""

import os
import sys
import json
import pickle
import socket
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ========== CONFIGURATION ==========
VIDEO_TITLE = "Stupid Broke Money, What Happened? - Stupid Orange, Stupidest Broke Guy, Creative Daily"
HASHTAGS = "#stupidorange #creativedaily #stupidestbrokeguy #Dubai #UAE #fyp"
VIDEO_DURATION = 15  # seconds
IMAGES_FOLDER = "daily_images"  # Folder containing 1.png to 15.png
STATE_FILE = "shorts_state.json"
# ===================================

def load_state():
    """Load the state file to know which image to use next"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        print(f"📂 Loaded state: last used image {state.get('last_image', 'none')} on {state.get('last_date', 'never')}")
        return state
    else:
        print(f"📂 No state file found, starting fresh")
        return {'last_index': 0, 'last_date': None, 'last_image': None}

def save_state(state):
    """Save current state"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"💾 State saved")

def get_next_image():
    """Determine which image to use today (1.png to 15.png from daily_images folder)"""
    state = load_state()

    # Check if we already posted today
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get('last_date') == today:
        print(f"⚠️ Already posted today ({today}), skipping...")
        return None, None, state

    # Check if images folder exists
    if not os.path.exists(IMAGES_FOLDER):
        print(f"❌ Images folder not found: {IMAGES_FOLDER}")
        print(f"💡 Please create '{IMAGES_FOLDER}' folder and add your images (1.png to 15.png)")
        return None, None, state

    # Find all images in the folder (1.png to 15.png)
    available_images = []
    for i in range(1, 16):  # 1 to 15
        for ext in ['.png', '.jpg', '.jpeg']:
            img_path = os.path.join(IMAGES_FOLDER, f"{i}{ext}")
            if os.path.exists(img_path):
                available_images.append((i, img_path))
                break

    if not available_images:
        print(f"❌ No images found in '{IMAGES_FOLDER}' folder!")
        print(f"💡 Looking for: 1.png, 2.png, ... 15.png")
        print(f"📁 Files in folder: {os.listdir(IMAGES_FOLDER) if os.path.exists(IMAGES_FOLDER) else 'folder not found'}")
        return None, None, state

    print(f"📁 Found {len(available_images)} images in '{IMAGES_FOLDER}':")
    for num, path in available_images:
        print(f"   - {num}.png")

    # Get next index (rotate through all available images)
    last_index = state.get('last_index', 0)
    next_position = last_index % len(available_images)
    next_num, next_image = available_images[next_position]

    print(f"🖼️ Selected image #{next_num}: {os.path.basename(next_image)}")
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

def create_thumbnail_from_image(image_path: str, output_path: str = None) -> str:
    """
    Create a thumbnail from the source image (full image visible)
    """
    print(f"\n🎬 Creating thumbnail from image...")

    if output_path is None:
        base = os.path.splitext(image_path)[0]
        output_path = f"{base}_thumbnail.png"

    try:
        # Load the image
        pil_img = Image.open(image_path)
        img_width, img_height = pil_img.size
        print(f"   📸 Original image size: {img_width}x{img_height}")

        # Target thumbnail size (YouTube Shorts)
        target_width, target_height = 1080, 1920

        # Calculate scaling to fit ENTIRE image (both sides visible)
        scale = min(target_width / img_width, target_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        print(f"   📐 Scaled to: {new_width}x{new_height} (full image visible)")

        # Resize image with high quality
        try:
            img_resized = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except AttributeError:
            try:
                img_resized = pil_img.resize((new_width, new_height), Image.LANCZOS)
            except:
                img_resized = pil_img.resize((new_width, new_height))

        # Create YELLOW background
        background = Image.new('RGB', (target_width, target_height), (255, 215, 0))

        # Center the image
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2

        background.paste(img_resized, (x_offset, y_offset))

        # Add gradient at bottom for text readability
        overlay = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Bottom gradient
        for i in range(150):
            alpha = int(180 * (1 - i/150))
            draw.rectangle([(0, target_height - i, target_width, target_height - i + 1)],
                          fill=(0, 0, 0, alpha))

        # Composite overlay
        background = background.convert('RGBA')
        background = Image.alpha_composite(background, overlay)

        # Add caption text on thumbnail (fixed anchor issue)
        try:
            draw = ImageDraw.Draw(background)
            # Use default font for GitHub Actions compatibility
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 45)
                except:
                    font = ImageFont.load_default()

            caption = "Stupid Broke Money,\nWhat Happened?"
            # Calculate text position manually (avoid anchor issues)
            text_x = target_width // 2
            text_y = target_height - 150
            
            # Draw text with outline for better visibility
            for offset_x, offset_y in [(-2,-2), (-2,2), (2,-2), (2,2)]:
                draw.text((text_x + offset_x, text_y + offset_y), caption, 
                         fill=(0, 0, 0), font=font, align="center")
            draw.text((text_x, text_y), caption, fill=(255, 215, 0), font=font, align="center")
        except Exception as e:
            print(f"   ⚠️ Could not add text: {e}")

        # Save final thumbnail
        background = background.convert('RGB')
        background.save(output_path, quality=90)

        print(f"   ✅ Thumbnail created: {output_path}")
        return output_path

    except Exception as e:
        print(f"   ❌ Error creating thumbnail: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_shorts_video(image_path: str,
                        output_path: str = None,
                        slide_duration: int = 15,
                        audio_file: str = None) -> str:
    """
    Create YouTube Shorts video with sliding animation
    """

    if output_path is None:
        base = os.path.splitext(image_path)[0]
        output_path = f"{base}_shorts.mp4"

    print(f"\n🎬 Creating YouTube Shorts video...")
    print(f"   📷 Image: {os.path.basename(image_path)}")
    print(f"   ⏱️  Duration: {slide_duration} seconds")

    # Import moviepy modules
    try:
        from moviepy import ImageClip, CompositeVideoClip, ColorClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        print(f"   ✅ moviepy imported")
    except ImportError:
        try:
            from moviepy.editor import ImageClip, CompositeVideoClip, ColorClip, AudioFileClip
            print(f"   ✅ moviepy legacy imported")
        except ImportError as e:
            print(f"   ❌ moviepy import failed: {e}")
            return None

    screen_width, screen_height = 1080, 1920  # YouTube Shorts

    try:
        from PIL import Image

        # Load the image
        pil_img = Image.open(image_path)
        img_width, img_height = pil_img.size
        print(f"   📸 Original: {img_width}x{img_height}")

        # Calculate scaling to fit ENTIRE image
        fit_scale = min(screen_width / img_width, screen_height / img_height)
        scale = fit_scale
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        print(f"   🔍 Scale: {scale:.4f} (full image visible)")
        print(f"   📐 Video size: {new_width}x{new_height}")

        # Resize image
        try:
            pil_img_resized = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except AttributeError:
            try:
                pil_img_resized = pil_img.resize((new_width, new_height), Image.LANCZOS)
            except:
                pil_img_resized = pil_img.resize((new_width, new_height))

        temp_img_path = base + "_temp.png"
        pil_img_resized.save(temp_img_path)

        # Create image clip
        image_clip = ImageClip(temp_img_path, duration=slide_duration)

        # Sliding animation
        start_y = screen_height
        end_y = -new_height + screen_height * 0.1

        print(f"   📍 Animation: from y={start_y} to y={end_y:.0f}")

        def image_slide_position(t):
            progress = min(1.0, t / slide_duration)
            eased = progress * progress * (3 - 2 * progress)
            y = start_y + (end_y - start_y) * eased
            return ('center', y)

        image_clip = image_clip.with_position(image_slide_position)

        # Yellow background
        background = ColorClip(size=(screen_width, screen_height), color=(255, 215, 0), duration=slide_duration)

        # Skip text overlays in video to avoid font issues in GitHub Actions
        # Text will be in description and thumbnail
        clips = [background, image_clip]
        print(f"   ℹ️ Text overlays added to description only (for compatibility)")
        
        final_clip = CompositeVideoClip(clips, size=(screen_width, screen_height))

        # Audio handling
        audio_added = False

        def add_audio_to_clip(clip, audio_path, volume=0.3):
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
            final_clip, audio_added = add_audio_to_clip(final_clip, audio_file, 0.3)

        if not audio_added:
            common_audio = ["background_music.mp3", "shorts_music.mp3", "audio.mp3", "music.mp3"]
            for audio in common_audio:
                if os.path.exists(audio):
                    final_clip, audio_added = add_audio_to_clip(final_clip, audio, 0.3)
                    if audio_added:
                        break

        # Render video
        print(f"   💾 Rendering video...")
        audio_codec = 'aac' if audio_added else None

        try:
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec=audio_codec,
                fps=30,
                bitrate="5000k",
                preset='medium',
                logger=None
            )
        except TypeError:
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec=audio_codec,
                fps=30,
                bitrate="5000k",
                preset='medium'
            )

        final_clip.close()
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"   ✅ Video created: {os.path.basename(output_path)} ({file_size_mb:.1f} MB)")
        return output_path

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def upload_to_youtube(video_path: str, thumbnail_path: str = None) -> dict:
    """Upload video to YouTube as Short"""
    print(f"\n📤 Uploading to YouTube...")
    print(f"   📹 Video: {os.path.basename(video_path)}")

    video_description = f"""{VIDEO_TITLE}

{HASHTAGS}
Welcome to the Stupid Orange world where stories are turned to royalties. We ask strangers to share
their stupid broke moments and we design nice t-shirts from the inspiration, earning the responded
a royalty share for the shirt. Please feel free to go ahead, participate, connect and share the movement.

Share your Stupid Broke Moment and stand a chance to be Today's Winner - (https://www.stupidorange.com/share-moment/)

VIew our Hall of fame of Daily Winners Of the Stupid Orange Challenge - (https://www.stupidorange.com/interviews/)

Connect with Us On Social.

-Youtube connect here  - (https://www.youtube.com/@stupidestbrokeguy)
-Tiktok connect here - (https://www.tiktok.com/@stupidestbrokeguy)

Platforms Links.

- Help someone fastract to collecting their first royalty, join Stupid Solom Fashion Line Waiting List - (stupidorange.com)
- Friday Mondays show, we judge one Artist to evaluate whether overrated or not while deepdiving into creative ecomony - (fridaymondays.stupidorange.club)
- Secure the system that is helping random broke people earn their first royalty, - (creativedaily.stupidorange.com)

✨ Stupid Orange - Helping people start collecting royalties from their creativity.

#stupidorange #creativedaily #stupidestbrokeguy #Dubai #UAE #fyp
"""

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
        CLIENT_SECRETS_FILE = "client_secrets.json"
        TOKEN_FILE = "token.pickle"

        credentials = None

        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'rb') as f:
                    credentials = pickle.load(f)
                print(f"   📂 Loaded saved credentials")
            except Exception as e:
                print(f"   ⚠️ Could not load token: {e}")
                credentials = None

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print("   🔄 Refreshing token...")
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    print(f"   ⚠️ Could not refresh: {e}")
                    credentials = None
            
            if not credentials:
                if not os.path.exists(CLIENT_SECRETS_FILE):
                    print(f"   ❌ No client_secrets.json found!")
                    return {'status': 'skipped', 'error': 'No credentials'}

                print("   🔐 Opening browser for authentication...")
                free_port = find_free_port()
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                try:
                    credentials = flow.run_local_server(port=free_port, open_browser=True)
                except OSError:
                    credentials = flow.run_local_server(open_browser=True)

                with open(TOKEN_FILE, 'wb') as f:
                    pickle.dump(credentials, f)
                    print(f"   💾 Saved credentials")

        youtube = build('youtube', 'v3', credentials=credentials)
        print(f"   ✅ YouTube service built")

        body = {
            'snippet': {
                'title': VIDEO_TITLE[:100],
                'description': video_description[:5000],
                'tags': ['stupidorange', 'creativedaily', 'stupidestbrokeguy', 'Dubai', 'UAE', 'fyp', 'shorts'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        # Upload with retry
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        retry_count = 0
        response = None
        while retry_count < 3 and response is None:
            try:
                response = request.execute()
            except Exception as e:
                retry_count += 1
                print(f"   ⚠️ Upload attempt {retry_count} failed: {e}")
                if retry_count >= 3:
                    raise
                import time
                time.sleep(5)
        
        video_id = response['id']
        video_url = f"https://youtube.com/shorts/{video_id}"
        print(f"   ✅ Video uploaded! URL: {video_url}")

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                print(f"   🖼️ Uploading custom thumbnail...")
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                print(f"   ✅ Custom thumbnail uploaded!")
            except Exception as e:
                print(f"   ⚠️ Could not upload thumbnail: {e}")

        return {'status': 'success', 'video_url': video_url}

    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'failed', 'error': str(e)}

def main():
    print("="*60)
    print("🎬 DAILY PICTURE TO YOUTUBE SHORTS")
    print(f"Auto-rotates through images in '{IMAGES_FOLDER}' folder")
    print("="*60)

    # Check if images folder exists
    if not os.path.exists(IMAGES_FOLDER):
        print(f"❌ Images folder not found: '{IMAGES_FOLDER}'")
        print(f"💡 Please create '{IMAGES_FOLDER}' folder and add your images")
        print(f"   Name them: 1.png, 2.png, 3.png ... 15.png")
        sys.exit(1)

    # Get next image
    image_path, image_num, state = get_next_image()

    if image_path is None:
        print("📅 No image to post today.")
        sys.exit(0)

    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)

    print(f"\n🎯 Configuration:")
    print(f"   🖼️ Image: {os.path.basename(image_path)}")
    print(f"   ⏱️  Duration: {VIDEO_DURATION}s")
    print(f"   📹 YouTube: ON")
    print(f"   📝 Title: {VIDEO_TITLE}")

    # Create thumbnail
    print(f"\n🎨 Creating thumbnail...")
    thumbnail_path = create_thumbnail_from_image(image_path)

    # Create video
    print(f"\n🎬 Creating video...")
    video_path = create_shorts_video(
        image_path=image_path,
        slide_duration=VIDEO_DURATION,
        audio_file=None
    )

    if video_path is None:
        print("❌ Video creation failed!")
        sys.exit(1)

    # Upload to YouTube
    youtube_result = upload_to_youtube(video_path, thumbnail_path)

    # Update state on success
    if youtube_result and youtube_result['status'] == 'success':
        state['last_index'] = image_num
        state['last_date'] = datetime.now().strftime("%Y-%m-%d")
        state['last_image'] = os.path.basename(image_path)
        save_state(state)

    print("\n" + "="*60)
    print("📋 RESULT")
    print("="*60)

    if youtube_result and youtube_result['status'] == 'success':
        print(f"✅ SUCCESS!")
        print(f"   🖼️ Image #{image_num}: {os.path.basename(image_path)}")
        print(f"   🔗 YouTube Shorts: {youtube_result['video_url']}")
        print(f"   📝 Title: {VIDEO_TITLE}")

        # Show next image preview
        next_num = image_num + 1 if image_num < 15 else 1
        print(f"\n📅 Tomorrow's image will be: {next_num}.png")
    else:
        print(f"❌ FAILED: {youtube_result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
