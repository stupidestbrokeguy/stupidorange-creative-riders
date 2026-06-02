#!/usr/bin/env python3
"""
Creative Daily - Affirmation with Canva Template (FIXED - No sayings included)
"""

import os
import re
import sys
import pickle
import socket
from datetime import datetime
import fitz  # PyMuPDF

# ========== CONFIGURATION ==========
PLAYLIST_TITLE = "Creative Daily Affirmations | Stupid Orange"
PLAYLIST_DESCRIPTION = """Daily affirmations from Creative Daily to help you start collecting royalties from your creativity. Stupid Orange is a fashion brand helping people to fastrack to collecting their first royalty and live a true royal lifestyle"""

TEMPLATE_PATH = "affirmation_template.png"

def find_free_port(start_port=8080, end_port=8090):
    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except socket.error:
                continue
    return 8080

def extract_affirmation_from_text(page_text: str) -> str:
    """
    Extract ONLY the affirmation text from a page.
    STOPS at 'Related Saying' - nothing after that should be included.
    """
    print(f"   🔍 Looking for affirmation in {len(page_text)} chars...")
    
    # Find the exact position of "Affirmation" in the text
    text_lower = page_text.lower()
    affirmation_pos = text_lower.find('affirmation')
    
    if affirmation_pos == -1:
        print(f"   ⚠️ 'Affirmation' keyword not found")
        return None
    
    # Look for "Related Saying" after the affirmation
    related_pos = text_lower.find('related saying', affirmation_pos)
    
    # Extract from after "Affirmation:" to either "Related Saying" or end
    if related_pos != -1:
        raw_text = page_text[affirmation_pos:related_pos]
        print(f"   📍 Found 'Related Saying' - stopping there")
    else:
        raw_text = page_text[affirmation_pos:]
        print(f"   📍 No 'Related Saying' found")
    
    # Process the raw text
    lines = raw_text.split('\n')
    affirmation_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip the line that contains "Affirmation" itself
        if 'affirmation' in line_stripped.lower():
            if ':' in line_stripped:
                parts = line_stripped.split(':', 1)
                if len(parts) > 1 and parts[1].strip():
                    line_stripped = parts[1].strip()
                else:
                    continue
            else:
                continue
        
        # Stop at any marker that indicates end of affirmation
        stop_markers = [
            'related saying', 'creativelydaily', 'www.', 'http://', 'https://',
            'saying', 'mark cuban', 'tony robbins', 'albert einstein', 
            'steve jobs', 'walt disney', 'benjamin franklin', 'marcus aurelius',
            'barbara corcoran', 'maya angelou', 'elon musk', 'lao tsu'
        ]
        
        should_stop = False
        for marker in stop_markers:
            if line_stripped.lower().startswith(marker) or marker in line_stripped.lower():
                print(f"   🛑 Stopping at marker: '{marker}'")
                should_stop = True
                break
        
        if should_stop:
            break
        
        # Also stop at quoted text that looks like a saying
        if line_stripped.startswith('"') or line_stripped.startswith('“'):
            print(f"   🛑 Stopping at quoted text")
            break
        
        # Stop at lines with dash followed by a name
        if re.match(r'^-\s*[A-Z][a-z]+\s+[A-Z][a-z]+', line_stripped):
            print(f"   🛑 Stopping at attribution line")
            break
        
        # Keep the line if it's not empty
        if line_stripped and not line_stripped.isdigit():
            # Remove any quotes
            line_stripped = line_stripped.strip('"\'""')
            if line_stripped:
                affirmation_lines.append(line_stripped)
    
    if affirmation_lines:
        result = ' '.join(affirmation_lines).strip()
        # Final cleanup
        result = re.sub(r'\s+', ' ', result)  # Normalize spaces
        result = result.strip()
        
        # Remove any trailing quote or attribution
        result = re.sub(r'\s*[""].*$', '', result)
        result = re.sub(r'\s*-\s*[A-Z][a-z]+\s+[A-Z][a-z]+.*$', '', result)
        
        print(f"   ✅ Found affirmation ({len(result)} chars)")
        print(f"   📝 First 100 chars: {result[:100]}...")
        return result
    
    print(f"   ⚠️ No affirmation found")
    return None

def create_affirmation_image_from_template(affirmation_text: str, target_date: str, output_path: str = None, template_path: str = TEMPLATE_PATH) -> str:
    """Uses a Canva template as background and overlays the affirmation text and date."""
    
    if output_path is None:
        output_path = f"affirmation_{target_date}.png"
    
    print(f"\n🎨 Creating affirmation image from Canva template...")
    print(f"   📅 Date: {target_date}")
    
    if not os.path.exists(template_path):
        print(f"   ❌ Template not found: {template_path}")
        return None
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        try:
            font_affirmation = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 52)
            font_date = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 40)
        except:
            try:
                font_affirmation = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttf", 52)
                font_date = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
            except:
                font_affirmation = ImageFont.load_default()
                font_date = ImageFont.load_default()
        
        # Format date
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")
        
        # =====================================================
        # ADJUST THESE COORDINATES FOR YOUR TEMPLATE
        # =====================================================
        text_x = 200
        text_y = 450
        date_y = 200
        
        # Wrap and draw affirmation text
        wrapped_text = textwrap.wrap(affirmation_text, width=45)
        line_height = 70
        current_y = text_y
        
        for line in wrapped_text:
            draw.text((text_x, current_y), line, fill=(255, 255, 255), font=font_affirmation)
            current_y += line_height
        
        # Draw date
        date_bbox = draw.textbbox((0, 0), formatted_date, font=font_date)
        date_width = date_bbox[2] - date_bbox[0]
        date_x = (img.width - date_width) // 2
        draw.text((date_x, date_y), formatted_date, fill=(255, 255, 255), font=font_date)
        
        img.save(output_path, quality=95)
        print(f"   ✅ Image saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Image creation failed: {e}")
        return None

def extract_thumbnail_from_video(video_path: str, output_path: str = None, time_seconds: float = 0.0) -> str:
    """Extract thumbnail from video"""
    if output_path is None:
        output_path = video_path.replace('.mp4', '_thumbnail.png')
    
    THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT = 1280, 720
    
    try:
        from moviepy import VideoFileClip
        from PIL import Image
        
        clip = VideoFileClip(video_path)
        frame = clip.get_frame(time_seconds)
        clip.close()
        
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        img = img.resize((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
        img.save(output_path, quality=90)
        return output_path
    except Exception as e:
        print(f"   ❌ Thumbnail extraction failed: {e}")
        return None

def create_affirmation_video(image_path: str, output_path: str = None, slide_duration: int = 30, audio_file: str = None) -> str:
    """Create 30-second video"""
    if output_path is None:
        output_path = image_path.replace('.png', '_video.mp4')
    
    try:
        from moviepy import ImageClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
    except ImportError:
        try:
            from moviepy.editor import ImageClip, AudioFileClip
        except ImportError as e:
            print(f"   ❌ moviepy import failed: {e}")
            return None
    
    try:
        clip = ImageClip(image_path, duration=slide_duration)
        
        # Add audio if available
        audio_added = False
        if audio_file and os.path.exists(audio_file):
            try:
                audio = AudioFileClip(audio_file)
                if audio.duration < slide_duration:
                    audio = audio.loop(int(slide_duration / audio.duration) + 1)
                audio = audio.subclipped(0, slide_duration)
                clip = clip.with_audio(audio)
                audio_added = True
            except:
                pass
        
        if not audio_added:
            for audio in ["background_music.mp3", "audio.mp3", "music.mp3"]:
                if os.path.exists(audio):
                    try:
                        audio_clip = AudioFileClip(audio)
                        if audio_clip.duration < slide_duration:
                            audio_clip = audio_clip.loop(int(slide_duration / audio_clip.duration) + 1)
                        audio_clip = audio_clip.subclipped(0, slide_duration)
                        clip = clip.with_audio(audio_clip)
                        break
                    except:
                        continue
        
        clip.write_videofile(output_path, codec='libx264', audio_codec='aac' if audio_added else None, fps=30, bitrate="5000k", preset='medium')
        clip.close()
        return output_path
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

class AffirmationExtractor:
    def __init__(self, pdf_path: str, output_dir: str = "affirmation_pages"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.playlist_id = None

    def find_page_for_date(self, target_date: str) -> dict:
        print(f"📄 Searching PDF for {target_date}...")
        if not os.path.exists(self.pdf_path):
            return None

        doc = fitz.open(self.pdf_path)
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        
        date_formats = [
            f"{date_obj.day} {date_obj.strftime('%B')} {date_obj.year}",
            f"{date_obj.strftime('%B')} {date_obj.day}, {date_obj.year}",
        ]
        
        for page_num in range(len(doc)):
            text = doc[page_num].get_text()
            for date_format in date_formats:
                if date_format in text:
                    doc.close()
                    return {
                        'page_num': page_num,
                        'display_num': page_num + 1,
                        'date': target_date,
                        'text': text
                    }
        doc.close()
        return None

    def get_affirmation_from_page(self, page_info: dict) -> str:
        return extract_affirmation_from_text(page_info['text'])

    def create_or_get_playlist(self, youtube) -> str:
        playlists = youtube.playlists().list(part='snippet', mine=True, maxResults=50).execute()
        for playlist in playlists.get('items', []):
            if playlist['snippet']['title'] == PLAYLIST_TITLE:
                return playlist['id']
        response = youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {'title': PLAYLIST_TITLE, 'description': PLAYLIST_DESCRIPTION},
                'status': {'privacyStatus': 'public'}
            }
        ).execute()
        return response['id']

    def upload_to_youtube(self, video_path: str, target_date: str, affirmation_text: str) -> dict:
        print(f"\n📤 Uploading to YouTube...")
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")
        full_title = f"Creative Daily Affirmation | {formatted_date} | Stupid Orange | Stupid Orange Riders"
        
        video_description = f"""🌟 DAILY AFFIRMATION - {formatted_date} 🌟

{affirmation_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Join the Creative Daily community and start collecting royalties from your creativity!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 www.stupidorange.com
📘 creativedaily.stupidorange.com

#affirmation #dailyaffirmation #creativedaily #stupidestbrokeguy #UAE #Dubai #talabat #careem #deliveroo #dubai #rider #delivery #bikerider
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
                with open(TOKEN_FILE, 'rb') as f:
                    credentials = pickle.load(f)

            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    if not os.path.exists(CLIENT_SECRETS_FILE):
                        return {'status': 'failed', 'error': 'No credentials'}
                    free_port = find_free_port()
                    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                    credentials = flow.run_local_server(port=free_port, open_browser=True)
                with open(TOKEN_FILE, 'wb') as f:
                    pickle.dump(credentials, f)

            youtube = build('youtube', 'v3', credentials=credentials)
            if self.playlist_id is None:
                self.playlist_id = self.create_or_get_playlist(youtube)

            thumbnail_path = extract_thumbnail_from_video(video_path)
            body = {
                'snippet': {
                    'title': full_title[:100],
                    'description': video_description[:5000],
                    'tags': ['affirmation', 'dailyaffirmation', 'creativedaily'],
                    'categoryId': '22'
                },
                'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
            }

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
            response = request.execute()
            video_url = f"https://youtu.be/{response['id']}"

            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    youtube.thumbnails().set(videoId=response['id'], media_body=MediaFileUpload(thumbnail_path)).execute()
                    os.remove(thumbnail_path)
                except:
                    pass

            youtube.playlistItems().insert(
                part='snippet',
                body={'snippet': {'playlistId': self.playlist_id, 'resourceId': {'kind': 'youtube#video', 'videoId': response['id']}}}
            ).execute()

            return {'status': 'success', 'video_url': video_url}
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}

    def process_date(self, target_date: str, post_to_youtube: bool = True, audio_file: str = None) -> dict:
        print("="*60)
        print("✨ CREATIVE DAILY - AFFIRMATION WITH CANVA TEMPLATE (FIXED)")
        print("="*60)
        print(f"📅 Target Date: {target_date}")

        page_info = self.find_page_for_date(target_date)
        if not page_info:
            return {'status': 'not_found', 'date': target_date}

        print(f"✅ Found on page {page_info['display_num']}")

        affirmation = self.get_affirmation_from_page(page_info)
        if not affirmation:
            return {'status': 'no_affirmation', 'date': target_date}

        print(f"\n📝 CLEAN AFFIRMATION (no quotes, no sayings):")
        print(f"   {affirmation}")

        image_path = create_affirmation_image_from_template(
            affirmation, target_date, 
            os.path.join(self.output_dir, f"affirmation_{target_date}.png")
        )

        if not image_path:
            return {'status': 'image_failed', 'date': target_date}

        video_path = create_affirmation_video(image_path, slide_duration=30, audio_file=audio_file)
        if not video_path:
            return {'status': 'conversion_failed', 'date': target_date}

        youtube_result = None
        if post_to_youtube:
            youtube_result = self.upload_to_youtube(video_path, target_date, affirmation)

        return {'status': 'success', 'date': target_date, 'affirmation': affirmation, 'video_path': video_path, 'youtube': youtube_result}

if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else "2026-06-15"
    print(f"📅 Target Date: {target_date}")
    
    processor = AffirmationExtractor("your_document.pdf", "affirmation_pages")
    result = processor.process_date(target_date)
    
    if result['status'] == 'success':
        print(f"\n✅ SUCCESS!")
        print(f"   Affirmation: {result['affirmation']}")
        if result.get('youtube') and result['youtube']['status'] == 'success':
            print(f"   YouTube: {result['youtube']['video_url']}")
    else:
        print(f"\n❌ FAILED: {result['status']}")
