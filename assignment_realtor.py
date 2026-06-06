#!/usr/bin/env python3
"""
Creative Daily - Assignment Extractor (Realtor Channel)
Extracts the daily assignment from PDF, overlays on Canva template, creates 30-second video
"""

import os
import re
import sys
import pickle
import socket
from datetime import datetime
import fitz  # PyMuPDF

# ========== REALTOR CONFIGURATION ==========
PLAYLIST_TITLE = "Creative Daily Assignments | Stupid Orange Realtors"
PLAYLIST_DESCRIPTION = """Daily assignments from Creative Daily to help real estate professionals and property investors take action and start collecting royalties from their creativity."""

# Template file name (your Canva design for assignments)
TEMPLATE_PATH = "assignment_template.png"  # Change this to your assignment template filename

def find_free_port(start_port=8080, end_port=8090):
    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except socket.error:
                continue
    return 8080

def extract_assignment_from_text(page_text: str) -> str:
    """
    Extract ONLY the assignment text from a page.
    Looks for 'Assignment:' and stops at 'Affirmation' or 'Related Saying' or 'Good luck'
    """
    print(f"   🔍 Looking for assignment in {len(page_text)} chars...")
    
    text_lower = page_text.lower()
    assignment_pos = text_lower.find('assignment')
    
    if assignment_pos == -1:
        print(f"   ⚠️ 'Assignment' keyword not found")
        return None
    
    stop_markers = ['affirmation', 'related saying', 'good luck', 'creativelydaily']
    stop_pos = len(page_text)
    
    for marker in stop_markers:
        marker_pos = text_lower.find(marker, assignment_pos + 10)
        if marker_pos != -1 and marker_pos < stop_pos:
            stop_pos = marker_pos
            print(f"   📍 Found stop marker: '{marker}' at position {marker_pos}")
    
    raw_text = page_text[assignment_pos:stop_pos]
    
    lines = raw_text.split('\n')
    assignment_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        if 'assignment' in line_stripped.lower():
            if ':' in line_stripped:
                parts = line_stripped.split(':', 1)
                if len(parts) > 1 and parts[1].strip():
                    line_stripped = parts[1].strip()
                else:
                    continue
            else:
                continue
        
        if line_stripped == '' and len(assignment_lines) > 0:
            continue
        
        if line_stripped and not line_stripped.isdigit():
            if 'good luck' in line_stripped.lower():
                line_stripped = line_stripped.split('Good luck')[0].strip()
            if line_stripped:
                assignment_lines.append(line_stripped)
    
    if assignment_lines:
        result = ' '.join(assignment_lines).strip()
        result = re.sub(r'\s+', ' ', result)
        result = result.strip()
        
        print(f"   ✅ Found assignment ({len(result)} chars)")
        print(f"   📝 First 100 chars: {result[:100]}...")
        return result
    
    print(f"   ⚠️ No assignment found")
    return None

def create_assignment_image_from_template(assignment_text: str, target_date: str, output_path: str = None, template_path: str = TEMPLATE_PATH) -> str:
    if output_path is None:
        output_path = f"assignment_realtor_{target_date}.png"
    
    print(f"\n🎨 Creating assignment image from Canva template...")
    print(f"   📅 Date: {target_date}")
    print(f"   📁 Template path: {template_path}")
    print(f"   💬 Text: {assignment_text[:80]}...")
    
    if not os.path.exists(template_path):
        print(f"   ❌ Template not found: {template_path}")
        print(f"   📁 Looking for: {os.path.abspath(template_path)}")
        print(f"   📁 Files in directory: {os.listdir('.')}")
        return None
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)
        print(f"   📐 Template size: {img.width}x{img.height}")
        
        try:
            font_assignment = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 48)
            font_date = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 40)
            font_label = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 60)
            print(f"   ✅ Loaded Liberation fonts")
        except:
            try:
                font_assignment = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttf", 48)
                font_date = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
                font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttf", 60)
                print(f"   ✅ Loaded Helvetica fonts")
            except:
                font_assignment = ImageFont.load_default()
                font_date = ImageFont.load_default()
                font_label = ImageFont.load_default()
                print(f"   ⚠️ Using default fonts")
        
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")
        
        label_x = img.width // 2
        label_y = 150
        date_y = 250
        text_x = 200
        text_y = 350
        line_height = 65
        
        label_text = "📋 DAILY ASSIGNMENT 📋"
        label_bbox = draw.textbbox((0, 0), label_text, font=font_label)
        label_width = label_bbox[2] - label_bbox[0]
        label_x_centered = (img.width - label_width) // 2
        
        draw.text((label_x_centered + 2, label_y + 2), label_text, fill=(0, 0, 0, 100), font=font_label)
        draw.text((label_x_centered, label_y), label_text, fill=(255, 140, 0), font=font_label)
        
        date_bbox = draw.textbbox((0, 0), formatted_date, font=font_date)
        date_width = date_bbox[2] - date_bbox[0]
        date_x_centered = (img.width - date_width) // 2
        
        pill_padding = 25
        pill_height = 55
        draw.rounded_rectangle(
            [(date_x_centered - pill_padding, date_y - 15),
             (date_x_centered + date_width + pill_padding, date_y + pill_height - 20)],
            radius=25,
            fill=(255, 140, 0),
            outline=(255, 200, 100),
            width=2
        )
        draw.text((date_x_centered, date_y), formatted_date, fill=(255, 255, 255), font=font_date)
        
        chars_per_line = 50
        wrapped_text = textwrap.wrap(assignment_text, width=chars_per_line)
        print(f"   📝 Wrapped assignment into {len(wrapped_text)} lines")
        
        current_y = text_y
        
        for i, line in enumerate(wrapped_text):
            if line.strip().startswith(('1', '2', '3', '4', '5', '•', '-', '*')):
                display_line = line
            else:
                display_line = f"✓ {line}"
            
            line_bbox = draw.textbbox((0, 0), display_line, font=font_assignment)
            line_width = line_bbox[2] - line_bbox[0]
            
            bg_padding = 30
            bg_height = 55
            draw.rounded_rectangle(
                [(text_x - bg_padding, current_y - 10),
                 (text_x + line_width + bg_padding, current_y + bg_height - 15)],
                radius=15,
                fill=(0, 0, 0, 80),
                outline=(255, 200, 100),
                width=1
            )
            
            draw.text((text_x, current_y), display_line, fill=(255, 255, 255), font=font_assignment)
            current_y += line_height
        
        bottom_y = img.height - 80
        website = "creativelydaily.stupidorange.com"
        
        web_bbox = draw.textbbox((0, 0), website, font=font_date)
        web_width = web_bbox[2] - web_bbox[0]
        web_bg_padding = 25
        
        draw.rounded_rectangle(
            [((img.width - web_width) // 2 - web_bg_padding, bottom_y - 10),
             ((img.width - web_width) // 2 + web_width + web_bg_padding, bottom_y + 40)],
            radius=25,
            fill=(255, 140, 0),
            outline=(255, 200, 100),
            width=1
        )
        draw.text(((img.width - web_width) // 2, bottom_y), website, fill=(255, 255, 255), font=font_date)
        
        img.save(output_path, quality=95)
        print(f"   ✅ Assignment image saved: {output_path} ({os.path.getsize(output_path)} bytes)")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Image creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_thumbnail_from_video(video_path: str, output_path: str = None, time_seconds: float = 0.0) -> str:
    print(f"\n🎬 Extracting thumbnail...")
    
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
        
        print(f"   ✅ Thumbnail saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Thumbnail extraction failed: {e}")
        return None

def create_assignment_video(image_path: str, output_path: str = None, slide_duration: int = 30, audio_file: str = None) -> str:
    if output_path is None:
        output_path = image_path.replace('.png', '_video.mp4')
    
    print(f"\n🎬 Creating 30-second assignment video...")
    print(f"   📷 Image: {image_path}")
    print(f"   ⏱️  Duration: {slide_duration} seconds")
    
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
        
        audio_added = False
        
        if audio_file and os.path.exists(audio_file):
            try:
                audio = AudioFileClip(audio_file)
                if audio.duration < slide_duration:
                    loops = int(slide_duration / audio.duration) + 1
                    audio = audio.loop(loops)
                audio = audio.subclipped(0, slide_duration)
                clip = clip.with_audio(audio)
                audio_added = True
                print(f"   🎵 Audio added: {audio_file}")
            except Exception as e:
                print(f"   ⚠️ Audio error: {e}")
        
        if not audio_added:
            for audio in ["background_music.mp3", "audio.mp3", "music.mp3", "bgm.mp3"]:
                if os.path.exists(audio):
                    try:
                        audio_clip = AudioFileClip(audio)
                        if audio_clip.duration < slide_duration:
                            audio_clip = audio_clip.loop(int(slide_duration / audio_clip.duration) + 1)
                        audio_clip = audio_clip.subclipped(0, slide_duration)
                        clip = clip.with_audio(audio_clip)
                        audio_added = True
                        print(f"   🎵 Auto-detected audio: {audio}")
                        break
                    except:
                        continue
        
        clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac' if audio_added else None,
            fps=30,
            bitrate="5000k",
            preset='medium'
        )
        
        clip.close()
        print(f"   ✅ Video created: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

class AssignmentExtractor:
    def __init__(self, pdf_path: str, output_dir: str = "assignment_pages"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.playlist_id = None
        print(f"🔧 AssignmentExtractor initialized")
        print(f"   📁 PDF path: {pdf_path}")
        print(f"   📁 Output dir: {output_dir}")

    def find_page_for_date(self, target_date: str) -> dict:
        print(f"📄 Searching PDF for {target_date}...")
        
        if not os.path.exists(self.pdf_path):
            print(f"   ❌ PDF not found: {self.pdf_path}")
            return None

        doc = fitz.open(self.pdf_path)
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        
        date_formats = [
            f"{date_obj.day} {date_obj.strftime('%B')} {date_obj.year}",
            f"{date_obj.strftime('%B')} {date_obj.day}, {date_obj.year}",
            f"{date_obj.day}-{date_obj.strftime('%B')}-{date_obj.year}",
        ]
        
        print(f"   🔍 Looking for date formats: {date_formats}")
        
        for page_num in range(len(doc)):
            text = doc[page_num].get_text()
            for date_format in date_formats:
                if date_format in text:
                    print(f"   ✅ Found on page {page_num + 1}")
                    doc.close()
                    return {
                        'page_num': page_num,
                        'display_num': page_num + 1,
                        'date': target_date,
                        'text': text
                    }
        
        doc.close()
        print(f"   ❌ Date {target_date} not found in PDF")
        return None

    def get_assignment_from_page(self, page_info: dict) -> str:
        return extract_assignment_from_text(page_info['text'])

    def create_or_get_playlist(self, youtube) -> str:
        playlists = youtube.playlists().list(part='snippet', mine=True, maxResults=50).execute()
        
        for playlist in playlists.get('items', []):
            if playlist['snippet']['title'] == PLAYLIST_TITLE:
                print(f"   ✅ Found existing playlist: {playlist['id']}")
                return playlist['id']

        response = youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {'title': PLAYLIST_TITLE, 'description': PLAYLIST_DESCRIPTION},
                'status': {'privacyStatus': 'public'}
            }
        ).execute()
        print(f"   ✅ Created new playlist: {response['id']}")
        return response['id']

    def upload_to_youtube(self, video_path: str, target_date: str, assignment_text: str) -> dict:
        print(f"\n📤 Uploading to YouTube...")
        
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")

        full_title = f"Stop Being Broke, Do This, | {formatted_date} | Stupid Orange Realtors"
        
        video_description = f"""📋Stop Being Broke, Do This, DAILY ASSIGNMENT - {formatted_date} 📋

{assignment_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Join the Creative Daily community and start collecting royalties from your creativity!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 www.stupidorange.com
📘 creativedaily.stupidorange.com

💡 After completing today's assignment:
1. Take a screenshot of your work
2. Comment "DONE" in the community
3. Share your results!

#assignment #dailyassignment #creativedaily #stupidorangerealtor #UAE #DubaiRealEstate #PropertyInvestment #action
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
                print(f"   ✅ Loaded credentials from {TOKEN_FILE}")

            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    print(f"   🔄 Refreshing expired token...")
                    credentials.refresh(Request())
                else:
                    if not os.path.exists(CLIENT_SECRETS_FILE):
                        return {'status': 'failed', 'error': 'No credentials'}
                    
                    free_port = find_free_port()
                    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                    credentials = flow.run_local_server(port=free_port, open_browser=True)
                    print(f"   ✅ Authentication successful")
                
                with open(TOKEN_FILE, 'wb') as f:
                    pickle.dump(credentials, f)
                print(f"   💾 Saved credentials to {TOKEN_FILE}")

            youtube = build('youtube', 'v3', credentials=credentials)
            print(f"   ✅ YouTube service built")

            if self.playlist_id is None:
                self.playlist_id = self.create_or_get_playlist(youtube)

            thumbnail_path = extract_thumbnail_from_video(video_path, time_seconds=0.0)
            
            body = {
                'snippet': {
                    'title': full_title[:100],
                    'description': video_description[:5000],
                    'tags': ['assignment', 'dailyassignment', 'creativedaily', 'StupidOrangeRealtor', 'DubaiRealEstate', 'action'],
                    'categoryId': '22'
                },
                'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
            }

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
            response = request.execute()
            video_url = f"https://youtu.be/{response['id']}"
            print(f"   ✅ Video uploaded! ID: {response['id']}")

            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    youtube.thumbnails().set(
                        videoId=response['id'],
                        media_body=MediaFileUpload(thumbnail_path)
                    ).execute()
                    os.remove(thumbnail_path)
                    print(f"   ✅ Thumbnail uploaded!")
                except Exception as e:
                    print(f"   ⚠️ Thumbnail upload failed: {e}")

            youtube.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': self.playlist_id,
                        'resourceId': {'kind': 'youtube#video', 'videoId': response['id']}
                    }
                }
            ).execute()
            print(f"   ✅ Added to playlist: {PLAYLIST_TITLE}")

            return {'status': 'success', 'video_url': video_url}

        except Exception as e:
            print(f"   ❌ Upload failed: {e}")
            return {'status': 'failed', 'error': str(e)}

    def process_date(self, target_date: str, post_to_youtube: bool = True, audio_file: str = None) -> dict:
        print("="*60)
        print("📋 CREATIVE DAILY - ASSIGNMENT EXTRACTOR (REALTOR CHANNEL)")
        print("="*60)
        print(f"📅 Target Date: {target_date}")
        print(f"📹 YouTube Upload: {'ON' if post_to_youtube else 'OFF'}")
        print("="*60)

        page_info = self.find_page_for_date(target_date)
        if not page_info:
            return {'status': 'not_found', 'date': target_date}

        print(f"✅ Found on page {page_info['display_num']}")

        assignment = self.get_assignment_from_page(page_info)
        if not assignment:
            return {'status': 'no_assignment', 'date': target_date}

        print(f"\n📝 ASSIGNMENT extracted:")
        print(f"   {assignment[:200]}...")
        print(f"   Total length: {len(assignment)} characters")

        image_path = create_assignment_image_from_template(
            assignment, 
            target_date, 
            os.path.join(self.output_dir, f"assignment_realtor_{target_date}.png")
        )

        if not image_path:
            return {'status': 'image_failed', 'date': target_date}

        video_path = create_assignment_video(
            image_path=image_path,
            slide_duration=30,
            audio_file=audio_file
        )

        if video_path is None:
            return {'status': 'conversion_failed', 'date': target_date}

        youtube_result = None
        if post_to_youtube:
            youtube_result = self.upload_to_youtube(video_path, target_date, assignment)

        return {
            'status': 'success',
            'date': target_date,
            'assignment': assignment,
            'image_path': image_path,
            'video_path': video_path,
            'youtube': youtube_result
        }

if __name__ == "__main__":
    print("="*60)
    print("📋 ASSIGNMENT EXTRACTOR - REALTOR CHANNEL")
    print("="*60)
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"📁 Files: {os.listdir('.')}")
    print("="*60)

    PDF_PATH = "your_document.pdf"
    OUTPUT_DIR = "assignment_pages"

    target_date = None
    post_to_youtube = True
    audio_file = None

    for arg in sys.argv[1:]:
        if arg == "--no-youtube":
            post_to_youtube = False
        elif arg.startswith("--audio="):
            audio_file = arg.split("=")[1]
        elif re.match(r'\d{4}-\d{2}-\d{2}', arg):
            target_date = arg

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    print(f"📅 Target Date: {target_date}")
    print(f"📹 YouTube Upload: {'ON' if post_to_youtube else 'OFF'}")

    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF not found: {PDF_PATH}")
        sys.exit(1)

    processor = AssignmentExtractor(PDF_PATH, OUTPUT_DIR)
    result = processor.process_date(target_date, post_to_youtube, audio_file)

    print("\n" + "="*60)
    print("📋 FINAL RESULT")
    print("="*60)

    if result['status'] == 'success':
        print(f"✅ SUCCESS!")
        print(f"   📅 Date: {result['date']}")
        print(f"   📝 Assignment: {result['assignment'][:150]}...")
        print(f"   🖼️ Image: {result.get('image_path', 'N/A')}")
        print(f"   🎬 Video: {result.get('video_path', 'N/A')}")
        
        if result.get('youtube') and result['youtube']['status'] == 'success':
            print(f"\n📹 POSTED TO YOUTUBE!")
            print(f"   🔗 URL: {result['youtube']['video_url']}")
        
        sys.exit(0)
    else:
        print(f"❌ FAILED: {result.get('status')}")
        sys.exit(1)
