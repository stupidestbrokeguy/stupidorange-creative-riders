"""
Creative Daily - Complete with Full Debug & Thumbnail Support
Extracts from PDF, creates sliding animation video, uploads to YouTube
FEATURES:
- Full debug output for every step
- 60% zoomed image for large readable text
- Yellow background
- Background music support
- GitHub artifact upload
- AUTO THUMBNAIL from image content (no yellow background)
"""

import os
import re
import sys
import pickle
import socket
from datetime import datetime
import fitz  # PyMuPDF

# ========== CONFIGURATION ==========
PLAYLIST_TITLE = "Secure Creative Entreprenuer Mindset | Stupid Orange Dubai | Stupid Orange Riders Dubai"
PLAYLIST_DESCRIPTION = """Are you ready for a Dubai Business Setup or have you already started your journey? Whether you're in the Dubai Fashion Business, enjoy Dubai Shopping, or simply keep up with Dubai news, cultivating the right Entrepreneur Mindset is everything.\n\n

In this video, discover how to Secure a Creative Entrepreneur Mindset by using simple Daily Affirmations in Dubai. Say these powerful lines every time you visit Burj Khalifa, Dubai Mall, or a Dubai Restaurant—even while doing Dubai Tourism. Speak to nature with a Creative Royalty Tracking Mindset, and train your brain to default toward building a Passive Wealth System.\n\n

Whether you're out enjoying the city or working on your business, let these affirmations align you with success, abundance, and creativity. Watch now and start thinking like a true creative entrepreneur in Dubai.\n\n.

#Dubai #creativedaily #stupidestbrokeguy #UAE #talabat #careem #deliveroo #dubai #rider #delivery #bikerider"""
# ===================================

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

def detect_page_title(page_text: str) -> str:
    """Detect title from page structure"""
    print(f"   🔍 DEBUG: detect_page_title called with {len(page_text)} chars")
    lines = page_text.split('\n')
    clean_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.isdigit() and not re.search(r'Page\s+\d+', line):
            clean_lines.append(line)
    
    print(f"   🔍 DEBUG: Found {len(clean_lines)} clean lines")
    
    found_creative_daily = False
    for i, line in enumerate(clean_lines):
        if found_creative_daily and line and len(line) > 2 and not line.startswith('#'):
            print(f"   🔍 DEBUG: Title found at line {i}: '{line}'")
            return line
        if "Creative Daily" in line or "creative daily" in line.lower():
            found_creative_daily = True
            print(f"   🔍 DEBUG: Found 'Creative Daily' at line {i}")
    
    print(f"   🔍 DEBUG: No title found, using default")
    return "Creative Daily"

def extract_thumbnail_from_video(video_path: str, output_path: str = None, time_seconds: float = 2.0) -> str:
    """
    Extract thumbnail from video - cropping to JUST the image content (no yellow background)
    
    At 0 seconds, the image is positioned starting from bottom center.
    This function extracts just the image region, removing the yellow background.
    
    Args:
        video_path: Path to video file
        output_path: Where to save thumbnail (auto-generated if None)
        time_seconds: Time in seconds to capture frame (default 0.0 = first frame)
    
    Returns:
        Path to saved thumbnail image (image-only, cropped)
    """
    print(f"\n🎬 DEBUG: extract_thumbnail_from_video START")
    print(f"   📹 Video: {video_path}")
    print(f"   ⏱️  Time: {time_seconds} seconds")
    
    if output_path is None:
        output_path = video_path.replace('.mp4', '_thumbnail.png')
    
    try:
        # Try using moviepy first
        from moviepy import VideoFileClip
        print(f"   ✅ Using moviepy for thumbnail extraction")
        
        clip = VideoFileClip(video_path)
        frame = clip.get_frame(time_seconds)
        clip.close()
        
        from PIL import Image
        import numpy as np
        
        # Convert frame to PIL Image
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        
        print(f"   📸 Original frame size: {img.size}")
        
        # Detect and crop out the yellow background
        # The yellow background is RGB (255, 215, 0)
        # We'll find where the image content starts and ends
        
        # Convert to numpy array for analysis
        img_array = np.array(img)
        
        # Define yellow color range (with some tolerance)
        yellow_lower = np.array([240, 200, 0])   # Lower bound for yellow
        yellow_upper = np.array([255, 230, 50])  # Upper bound for yellow
        
        # Find non-yellow pixels (these are the image content)
        is_not_yellow = np.any((img_array < yellow_lower) | (img_array > yellow_upper), axis=2)
        
        # Find bounding box of non-yellow pixels
        non_yellow_coords = np.argwhere(is_not_yellow)
        
        if len(non_yellow_coords) > 0:
            y_min = non_yellow_coords[:, 0].min()
            y_max = non_yellow_coords[:, 0].max()
            x_min = non_yellow_coords[:, 1].min()
            x_max = non_yellow_coords[:, 1].max()
            
            # Add small padding (optional)
            padding = 5
            y_min = max(0, y_min - padding)
            y_max = min(img.height, y_max + padding)
            x_min = max(0, x_min - padding)
            x_max = min(img.width, x_max + padding)
            
            # Crop to just the image content
            cropped_img = img.crop((x_min, y_min, x_max, y_max))
            print(f"   ✂️ Cropped to: {cropped_img.size} (removed yellow background)")
            
            cropped_img.save(output_path, quality=90)
        else:
            # Fallback: save full frame if detection fails
            print(f"   ⚠️ Could not detect image content, saving full frame")
            img.save(output_path, quality=90)
        
        print(f"   ✅ Thumbnail saved: {output_path} ({os.path.getsize(output_path)} bytes)")
        
    except ImportError:
        try:
            # Fallback to OpenCV
            import cv2
            print(f"   ✅ Using OpenCV for thumbnail extraction")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Cannot open video")
            
            # Set frame position
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_num = int(time_seconds * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                
                # Same cropping logic as above
                img_array = np.array(img)
                yellow_lower = np.array([240, 200, 0])
                yellow_upper = np.array([255, 230, 50])
                is_not_yellow = np.any((img_array < yellow_lower) | (img_array > yellow_upper), axis=2)
                non_yellow_coords = np.argwhere(is_not_yellow)
                
                if len(non_yellow_coords) > 0:
                    y_min = non_yellow_coords[:, 0].min()
                    y_max = non_yellow_coords[:, 0].max()
                    x_min = non_yellow_coords[:, 1].min()
                    x_max = non_yellow_coords[:, 1].max()
                    
                    padding = 5
                    y_min = max(0, y_min - padding)
                    y_max = min(img.height, y_max + padding)
                    x_min = max(0, x_min - padding)
                    x_max = min(img.width, x_max + padding)
                    
                    cropped_img = img.crop((x_min, y_min, x_max, y_max))
                    cropped_img.save(output_path, quality=90)
                else:
                    cv2.imwrite(output_path, frame)
                
                print(f"   ✅ Thumbnail saved: {output_path}")
            else:
                raise Exception("Cannot read frame")
            
            cap.release()
            
        except ImportError:
            # Fallback to ffmpeg with cropping
            print(f"   ✅ Using ffmpeg for thumbnail extraction")
            import subprocess
            
            # First extract frame
            temp_frame = output_path.replace('.png', '_temp_frame.png')
            cmd_extract = [
                'ffmpeg', '-y',
                '-ss', str(time_seconds),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                temp_frame
            ]
            
            result = subprocess.run(cmd_extract, capture_output=True, text=True)
            if result.returncode == 0:
                # Now crop using PIL
                from PIL import Image
                import numpy as np
                
                img = Image.open(temp_frame)
                img_array = np.array(img)
                yellow_lower = np.array([240, 200, 0])
                yellow_upper = np.array([255, 230, 50])
                is_not_yellow = np.any((img_array < yellow_lower) | (img_array > yellow_upper), axis=2)
                non_yellow_coords = np.argwhere(is_not_yellow)
                
                if len(non_yellow_coords) > 0:
                    y_min = non_yellow_coords[:, 0].min()
                    y_max = non_yellow_coords[:, 0].max()
                    x_min = non_yellow_coords[:, 1].min()
                    x_max = non_yellow_coords[:, 1].max()
                    
                    padding = 5
                    y_min = max(0, y_min - padding)
                    y_max = min(img.height, y_max + padding)
                    x_min = max(0, x_min - padding)
                    x_max = min(img.width, x_max + padding)
                    
                    cropped_img = img.crop((x_min, y_min, x_max, y_max))
                    cropped_img.save(output_path, quality=90)
                else:
                    img.save(output_path, quality=90)
                
                # Cleanup
                if os.path.exists(temp_frame):
                    os.remove(temp_frame)
                
                print(f"   ✅ Thumbnail saved: {output_path}")
            else:
                raise Exception(f"ffmpeg error: {result.stderr}")
    
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path) / 1024
        print(f"   📁 Thumbnail size: {file_size:.1f} KB")
        print(f"🎬 DEBUG: extract_thumbnail_from_video COMPLETE")
        return output_path
    else:
        print(f"   ❌ Failed to extract thumbnail")
        return None

def create_sliding_animation_video(image_path: str, text_content: str = None,
                                    output_path: str = None,
                                    bg_color: tuple = (255, 215, 0),
                                    slide_duration: int = 18,
                                    audio_file: str = None) -> str:
    """Create video with image sliding up - FULL DEBUG"""
    
    if output_path is None:
        output_path = image_path.replace('.png', '_video.mp4')
    
    print(f"\n🎬 DEBUG: create_sliding_animation_video START")
    print(f"   📷 Image path: {image_path}")
    print(f"   📁 Image exists: {os.path.exists(image_path)}")
    print(f"   📏 Image size: {os.path.getsize(image_path) if os.path.exists(image_path) else 'N/A'} bytes")
    print(f"   ⏱️  Duration: {slide_duration} seconds")
    print(f"   🎵 Audio file: {audio_file if audio_file else 'None'}")
    print(f"   📁 Audio exists: {os.path.exists(audio_file) if audio_file else 'N/A'}")
    
    # Import moviepy modules with fallbacks
    try:
        from moviepy import ImageClip, CompositeVideoClip, ColorClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        print(f"   ✅ DEBUG: moviepy v2.0+ imported successfully")
    except ImportError:
        try:
            from moviepy.editor import ImageClip, CompositeVideoClip, ColorClip, AudioFileClip
            print(f"   ✅ DEBUG: moviepy legacy imported successfully")
        except ImportError as e:
            print(f"   ❌ DEBUG: moviepy import failed: {e}")
            return None
    
    screen_width, screen_height = 1920, 1080
    print(f"   📺 DEBUG: Screen dimensions: {screen_width}x{screen_height}")
    
    try:
        from PIL import Image
        print(f"   ✅ DEBUG: PIL imported successfully")
        
        # Load and process image
        print(f"   📸 DEBUG: Opening image...")
        pil_img = Image.open(image_path)
        img_width, img_height = pil_img.size
        print(f"   📸 DEBUG: Original image size: {img_width}x{img_height}")
        
        # 60% ZOOM for larger, readable text
        fit_scale = min(screen_width / img_width, screen_height / img_height)
        zoom_factor = 1.6
        scale = fit_scale * zoom_factor
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        print(f"   🔍 DEBUG: Fit scale: {fit_scale:.4f}")
        print(f"   🔍 DEBUG: Zoom factor: {zoom_factor}")
        print(f"   🔍 DEBUG: Final scale: {scale:.4f}")
        print(f"   📐 DEBUG: Resized dimensions: {new_width}x{new_height}")
        
        # High quality resize
        print(f"   🔄 DEBUG: Resizing image...")
        try:
            pil_img_resized = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"   ✅ DEBUG: Resized with LANCZOS (PIL 10+)")
        except AttributeError:
            try:
                pil_img_resized = pil_img.resize((new_width, new_height), Image.LANCZOS)
                print(f"   ✅ DEBUG: Resized with LANCZOS (PIL 9)")
            except:
                pil_img_resized = pil_img.resize((new_width, new_height))
                print(f"   ✅ DEBUG: Resized with default method")
        
        temp_img_path = image_path.replace('.png', '_temp_resized.png')
        pil_img_resized.save(temp_img_path)
        print(f"   💾 DEBUG: Saved temp image: {temp_img_path}")
        
        # Create image clip with sliding animation
        print(f"   🎬 DEBUG: Creating ImageClip...")
        image_clip = ImageClip(temp_img_path, duration=slide_duration)
        
        # Calculate animation positions (starts visible at 4.8s position)
        start_y_original = screen_height
        end_y_original = -new_height + screen_height * 0.2
        progress_at_4_8s = 4.8 / slide_duration
        eased_at_4_8s = progress_at_4_8s * progress_at_4_8s * (3 - 2 * progress_at_4_8s)
        y_at_4_8s = start_y_original + (end_y_original - start_y_original) * eased_at_4_8s
        
        new_start_y = y_at_4_8s
        new_end_y = end_y_original
        
        print(f"   📍 DEBUG: Animation calculation:")
        print(f"      start_y_original: {start_y_original}")
        print(f"      end_y_original: {end_y_original}")
        print(f"      progress_at_4.8s: {progress_at_4_8s:.4f}")
        print(f"      eased_at_4.8s: {eased_at_4_8s:.4f}")
        print(f"      y_at_4.8s: {y_at_4_8s:.1f}")
        print(f"      NEW start_y: {new_start_y:.1f}")
        print(f"      NEW end_y: {new_end_y:.1f}")
        
        def image_slide_position(t):
            progress = min(1.0, t / slide_duration)
            eased = progress * progress * (3 - 2 * progress)
            y = new_start_y + (new_end_y - new_start_y) * eased
            return ('center', y)
        
        image_clip = image_clip.with_position(image_slide_position)
        print(f"   ✅ DEBUG: Position animation set")
        
        # Create yellow background
        print(f"   🎨 DEBUG: Creating yellow background...")
        background = ColorClip(size=(screen_width, screen_height), color=bg_color, duration=slide_duration)
        print(f"   ✅ DEBUG: Background created")
        
        # Composite
        print(f"   🔄 DEBUG: Compositing video layers...")
        final_clip = CompositeVideoClip([background, image_clip], size=(screen_width, screen_height))
        print(f"   ✅ DEBUG: Composite created")
        
        # =========================================================
        # IMPROVED AUDIO HANDLING WITH DEBUGGING
        # =========================================================
        
        audio_added = False
        
        def add_audio_to_clip(clip, audio_path, volume=0.25):
            try:
                print(f"   🎵 DEBUG: Loading audio: {audio_path}")
                
                if not os.path.exists(audio_path):
                    print(f"   ⚠️ DEBUG: File not found: {audio_path}")
                    return clip, False
                
                file_size = os.path.getsize(audio_path)
                print(f"   📁 DEBUG: Audio file size: {file_size} bytes ({file_size/1024:.1f} KB)")
                
                audio = AudioFileClip(audio_path)
                print(f"   🎵 DEBUG: Audio duration: {audio.duration:.2f}s")
                
                # Loop if shorter than video
                if audio.duration < slide_duration:
                    loops = int(slide_duration / audio.duration) + 1
                    print(f"   🔁 DEBUG: Looping audio {loops} times")
                    audio = audio.loop(loops)
                
                # Trim to exact duration
                audio = audio.subclipped(0, slide_duration)
                print(f"   ✂️ DEBUG: Trimmed audio: {audio.duration:.2f}s")
                
                # Adjust volume
                try:
                    audio = audio.with_volume_scaled(volume)
                    print(f"   🔊 DEBUG: Volume set to {volume*100}% (with_volume_scaled)")
                except AttributeError:
                    try:
                        audio = audio.volumex(volume)
                        print(f"   🔊 DEBUG: Volume set to {volume*100}% (volumex)")
                    except Exception as e:
                        print(f"   ⚠️ DEBUG: Could not adjust volume: {e}")
                
                return clip.with_audio(audio), True
                
            except Exception as e:
                print(f"   ❌ DEBUG: Audio error: {e}")
                import traceback
                traceback.print_exc()
                return clip, False
        
        # Try specified audio file first
        if audio_file:
            print(f"   🎵 DEBUG: Using specified audio: {audio_file}")
            final_clip, audio_added = add_audio_to_clip(final_clip, audio_file, 0.25)
        
        # Try common audio files
        if not audio_added:
            common_audio = [
                "background_music.mp3", 
                "audio.mp3", 
                "music.mp3", 
                "bgm.mp3",
                "ambient.mp3",
                "soundtrack.mp3"
            ]
            
            print(f"   🔍 DEBUG: Searching for audio files...")
            print(f"   📁 Current directory: {os.getcwd()}")
            
            # List all MP3 files in directory
            all_mp3 = [f for f in os.listdir('.') if f.endswith('.mp3')]
            if all_mp3:
                print(f"   📁 DEBUG: Found MP3 files: {all_mp3}")
            else:
                print(f"   📁 DEBUG: No MP3 files found in current directory")
            
            for audio in common_audio:
                if os.path.exists(audio):
                    print(f"   🎵 DEBUG: Found audio: {audio}")
                    final_clip, audio_added = add_audio_to_clip(final_clip, audio, 0.25)
                    if audio_added:
                        break
        
        if not audio_added:
            print(f"   ℹ️ DEBUG: No audio added - video will be silent")
        
        # Write video
        print(f"   💾 DEBUG: Starting video rendering...")
        
        audio_codec = 'aac' if audio_added else None
        print(f"   🎬 DEBUG: Audio codec: {audio_codec if audio_codec else 'None'}")
        
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
            print(f"   ✅ DEBUG: write_videofile succeeded")
        except TypeError as e:
            print(f"   ⚠️ DEBUG: First write attempt failed: {e}")
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec=audio_codec,
                fps=30,
                bitrate="5000k",
                preset='medium'
            )
            print(f"   ✅ DEBUG: write_videofile succeeded (legacy params)")
        
        # Cleanup
        final_clip.close()
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
            print(f"   🧹 DEBUG: Removed temp image: {temp_img_path}")
        
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        audio_status = "with audio" if audio_added else "without audio"
        print(f"   ✅ DEBUG: Video created: {os.path.basename(output_path)} ({file_size_mb:.1f} MB, {audio_status})")
        print(f"🎬 DEBUG: create_sliding_animation_video COMPLETE")
        return output_path
        
    except Exception as e:
        print(f"   ❌ DEBUG: Error in create_sliding_animation_video: {e}")
        import traceback
        traceback.print_exc()
        return None


class CompleteCalendarExtractor:
    def __init__(self, pdf_path: str, output_dir: str = "extracted_date_pages"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.date_patterns = [
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b',
        ]
        os.makedirs(output_dir, exist_ok=True)
        self.playlist_id = None
        print(f"🔧 DEBUG: CompleteCalendarExtractor initialized")
        print(f"   📁 PDF path: {pdf_path}")
        print(f"   📁 Output dir: {output_dir}")

    def extract_date_from_text(self, text: str) -> str:
        print(f"   🔍 DEBUG: extract_date_from_text called with {len(text)} chars")
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    dt = datetime.strptime(match.strip(), "%d %B %Y")
                    result = dt.strftime("%Y-%m-%d")
                    print(f"   ✅ DEBUG: Date found: {result} (format: %d %B %Y)")
                    return result
                except:
                    try:
                        dt = datetime.strptime(match.strip(), "%B %d, %Y")
                        result = dt.strftime("%Y-%m-%d")
                        print(f"   ✅ DEBUG: Date found: {result} (format: %B %d, %Y)")
                        return result
                    except:
                        continue
        print(f"   ⚠️ DEBUG: No date found in text")
        return None

    def find_all_date_pages(self) -> dict:
        print(f"📄 DEBUG: find_all_date_pages START")
        print(f"   📁 PDF path: {self.pdf_path}")
        
        if not os.path.exists(self.pdf_path):
            print(f"❌ DEBUG: PDF not found: {self.pdf_path}")
            return {}

        doc = fitz.open(self.pdf_path)
        print(f"   📄 DEBUG: PDF opened, {len(doc)} pages total")
        date_page_map = {}

        for page_num in range(len(doc)):
            print(f"   🔍 DEBUG: Processing page {page_num + 1}/{len(doc)}")
            page = doc[page_num]
            text = page.get_text()
            date_str = self.extract_date_from_text(text)

            if date_str:
                if date_str not in date_page_map:
                    date_page_map[date_str] = []
                
                date_page_map[date_str].append({
                    'page_num': page_num,
                    'display_num': page_num + 1,
                    'date': date_str,
                    'text': text
                })
                print(f"   ✅ DEBUG: Page {page_num + 1} -> {date_str}")

        doc.close()
        print(f"📊 DEBUG: Found {len(date_page_map)} unique dates")
        return date_page_map

    def convert_page_to_image(self, page_info: dict, dpi: int = 150) -> str:
        print(f"   🖼️ DEBUG: convert_page_to_image START")
        print(f"   📄 Page: {page_info['display_num']}, Date: {page_info['date']}")
        
        doc = fitz.open(self.pdf_path)
        page = doc[page_info['page_num']]

        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        date_obj = datetime.strptime(page_info['date'], "%Y-%m-%d")
        filename = f"{date_obj.day}_{date_obj.strftime('%B')}_{date_obj.year}_page_{page_info['display_num']}.png"
        image_path = os.path.join(self.output_dir, filename)

        pix.save(image_path)
        print(f"   💾 DEBUG: Image saved: {filename} ({os.path.getsize(image_path)} bytes)")

        text_file = image_path.replace('.png', '_text.txt')
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(page_info['text'])
        print(f"   📝 DEBUG: Text saved: {os.path.basename(text_file)}")

        doc.close()
        print(f"   🖼️ DEBUG: convert_page_to_image COMPLETE")
        return image_path

    def ensure_image_for_date(self, target_date: str, dpi: int = 150) -> dict:
        print(f"🔍 DEBUG: ensure_image_for_date START - Target: {target_date}")
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        pattern = f"{date_obj.day}_{date_obj.strftime('%B')}_{date_obj.year}_page_"
        print(f"   📁 Pattern: {pattern}")

        if os.path.exists(self.output_dir):
            files = os.listdir(self.output_dir)
            print(f"   📁 Output dir has {len(files)} files")
            for file in files:
                if file.startswith(pattern) and file.endswith('.png'):
                    print(f"   ✅ DEBUG: Found existing image: {file}")
                    return {'status': 'exists', 'image_path': os.path.join(self.output_dir, file)}

        print(f"   🔍 DEBUG: Image not found, scanning PDF...")
        date_map = self.find_all_date_pages()
        
        if target_date in date_map:
            page_info = date_map[target_date][0]
            print(f"   📄 DEBUG: Found on page {page_info['display_num']}")
            image_path = self.convert_page_to_image(page_info, dpi)
            return {'status': 'extracted', 'image_path': image_path, 'page_num': page_info['display_num']}
        else:
            print(f"❌ DEBUG: Date {target_date} not found in PDF!")
            return {'status': 'not_found', 'image_path': None, 'page_num': None}

    def get_page_text_content(self, image_path: str) -> str:
        print(f"📝 DEBUG: get_page_text_content for {os.path.basename(image_path)}")
        text_file = image_path.replace('.png', '_text.txt')
        if os.path.exists(text_file):
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                cleaned = []
                for line in lines:
                    line = line.strip()
                    if line and not line.isdigit() and not line.startswith('Page'):
                        cleaned.append(line)
                result = '\n\n'.join(cleaned)
                print(f"   📝 DEBUG: Extracted {len(result)} characters from {len(lines)} lines")
                return result
        print(f"   ⚠️ DEBUG: No text file found for {image_path}")
        return ""

    def get_page_title(self, image_path: str) -> str:
        print(f"📝 DEBUG: get_page_title for {os.path.basename(image_path)}")
        text_file = image_path.replace('.png', '_text.txt')
        if os.path.exists(text_file):
            with open(text_file, 'r', encoding='utf-8') as f:
                page_text = f.read()
                title = detect_page_title(page_text)
                print(f"   📝 DEBUG: Detected title: '{title}'")
                return title
        print(f"   ⚠️ DEBUG: No text file, returning default")
        return "Creative Daily"

    def create_or_get_playlist(self, youtube) -> str:
        print(f"📁 DEBUG: create_or_get_playlist START")
        playlists = youtube.playlists().list(part='snippet', mine=True, maxResults=50).execute()
        print(f"   📁 DEBUG: Found {len(playlists.get('items', []))} playlists")
        
        for playlist in playlists.get('items', []):
            if playlist['snippet']['title'] == PLAYLIST_TITLE:
                print(f"   ✅ DEBUG: Found existing playlist: {playlist['id']}")
                return playlist['id']

        print(f"   📝 DEBUG: Creating new playlist...")
        response = youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {'title': PLAYLIST_TITLE, 'description': PLAYLIST_DESCRIPTION},
                'status': {'privacyStatus': 'public'}
            }
        ).execute()
        print(f"   ✅ DEBUG: Created playlist: {response['id']}")
        return response['id']

    def upload_to_youtube(self, video_path: str, target_date: str, page_text: str = "", video_title: str = "") -> dict:
        print(f"\n📤 DEBUG: upload_to_youtube START")
        print(f"   📹 Video path: {video_path}")
        print(f"   📁 Video exists: {os.path.exists(video_path)}")
        print(f"   📏 Video size: {os.path.getsize(video_path) / (1024*1024):.1f} MB")

        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%B %d, %Y")

        if video_title and video_title != "Creative Daily":
            main_title = video_title
        else:
            main_title = f"Creative Daily | {formatted_date} | Stupid Orange | Stupid Orange Riders"

        full_title = f"{main_title} | {formatted_date} | Creative Daily | Stupid Orange | Stupid Orange Riders | #creativedaily #stupidestbrokeguy #UAE #Dubai #talabat #careem #deliveroo #dubai #rider #delivery #bikerider"
        print(f"   📝 Title: {full_title[:80]}...")

        video_description = f"""{page_text[:4500] if page_text else ''}
        
- Help someone collect their first royalty from creativity : join Stupid Solomon Fashion Line Waiting List, Please Visit Here and join waiting list- | www.stupidorange.com |
- Secure a copy of the latest Creative Daily and get daily messages that will fasttrack you to collecting your first royalty Please Visit Here and Subscribe - | creativedaily.stupidorange.com |
- Help a stranger improve their chances to access this video and get today's message of the Creative Daily that fastracks them to collecting their first royalty, Please - | Like/Share this video |
- Have you successfuly finished doing today's Creative Daily Assignment? Please share your screenshots and comment on this post to motivate a someone in our commnity to continou practising, Please - | Leave a comment on this video and Tag #creativedaily when you post |


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨{main_title} |  {formatted_date} | Creative Daily | Stupid Orange | Stupid Orange Riders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 #creativedaily #creativedaily #stupidestbrokeguy #UAE #Dubai #fyp #talabat #careem #deliveroo #dubai #rider #delivery #bikerider
"""
        print(f"   📝 Description length: {len(video_description)} chars")

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            print(f"   ✅ DEBUG: Google libraries imported")

            SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
            CLIENT_SECRETS_FILE = "client_secrets.json"
            TOKEN_FILE = "token.pickle"

            credentials = None

            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'rb') as f:
                    credentials = pickle.load(f)
                print(f"   📂 DEBUG: Loaded saved credentials from {TOKEN_FILE}")
            else:
                print(f"   ⚠️ DEBUG: No token file found at {TOKEN_FILE}")

            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    print("   🔄 DEBUG: Refreshing expired token...")
                    credentials.refresh(Request())
                else:
                    if not os.path.exists(CLIENT_SECRETS_FILE):
                        print(f"   ❌ DEBUG: No client_secrets.json found!")
                        return {'status': 'skipped', 'error': 'No credentials'}
                    
                    print("   🔐 DEBUG: Opening browser for authentication...")
                    free_port = find_free_port()
                    print(f"   🔌 DEBUG: Using port: {free_port}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
                    try:
                        credentials = flow.run_local_server(port=free_port, open_browser=True)
                        print(f"   ✅ DEBUG: Authentication successful")
                    except OSError:
                        print(f"   🔄 DEBUG: Retrying with automatic port...")
                        credentials = flow.run_local_server(open_browser=True)
                
                with open(TOKEN_FILE, 'wb') as f:
                    pickle.dump(credentials, f)
                print(f"   💾 DEBUG: Saved credentials to {TOKEN_FILE}")

            youtube = build('youtube', 'v3', credentials=credentials)
            print(f"   ✅ DEBUG: YouTube service built")

            if self.playlist_id is None:
                self.playlist_id = self.create_or_get_playlist(youtube)

            # EXTRACT THUMBNAIL FROM VIDEO (at 0 seconds, cropping out yellow background)
            print(f"\n   🖼️ DEBUG: Extracting thumbnail from video...")
            thumbnail_path = extract_thumbnail_from_video(video_path, time_seconds=0.0)
            
            body = {
                'snippet': {
                    'title': full_title[:100],
                    'description': video_description[:5000],
                    'tags': ['Dubai', 'creativedaily', 'stupidestbrokeguy', 'UAE','talabat', 'careem' ,'deliveroo' ,'dubai' ,'rider' ,'delivery' ,'bikerider', target_date],
                    'categoryId': '22'
                },
                'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
            }
            print(f"   📦 DEBUG: Request body prepared")

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            print(f"   ⬆️ DEBUG: Uploading video...")
            
            request = youtube.videos().insert(
                part=','.join(body.keys()), 
                body=body, 
                media_body=media
            )
            response = request.execute()
            video_url = f"https://youtu.be/{response['id']}"
            print(f"   ✅ DEBUG: Upload successful! Video ID: {response['id']}")
            print(f"   📹 DEBUG: URL: {video_url}")

            # UPLOAD CUSTOM THUMBNAIL if we extracted one
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    print(f"   🖼️ DEBUG: Uploading custom thumbnail...")
                    youtube.thumbnails().set(
                        videoId=response['id'],
                        media_body=MediaFileUpload(thumbnail_path)
                    ).execute()
                    print(f"   ✅ DEBUG: Custom thumbnail uploaded successfully!")
                    
                    # Clean up thumbnail file
                    os.remove(thumbnail_path)
                    print(f"   🧹 DEBUG: Removed temporary thumbnail file")
                except Exception as e:
                    print(f"   ⚠️ DEBUG: Could not upload custom thumbnail: {e}")
                    print(f"   💡 Note: YouTube requires channel verification for custom thumbnails")
            else:
                print(f"   ℹ️ DEBUG: No thumbnail to upload (extraction failed)")

            # Add to playlist
            print(f"   📁 DEBUG: Adding to playlist {self.playlist_id}...")
            youtube.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': self.playlist_id,
                        'resourceId': {'kind': 'youtube#video', 'videoId': response['id']}
                    }
                }
            ).execute()
            print(f"   ✅ DEBUG: Added to playlist: {PLAYLIST_TITLE}")

            print(f"📤 DEBUG: upload_to_youtube COMPLETE - SUCCESS")
            return {'status': 'success', 'video_url': video_url}

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ DEBUG: Upload error: {error_msg}")
            import traceback
            traceback.print_exc()
            return {'status': 'failed', 'error': error_msg}

    def process_date(self, target_date: str, post_to_youtube: bool = True, 
                     slide_duration: int = 18, audio_file: str = None) -> dict:
        print("="*60)
        print("📅 CREATIVE DAILY - COMPLETE WITH THUMBNAIL SUPPORT")
        print("🎬 60% zoom | Yellow background | Auto thumbnail (image only)")
        print("="*60)
        print(f"📅 Target Date: {target_date}")
        print(f"⏱️  Duration: {slide_duration} seconds")
        print(f"🎵 Audio: {audio_file if audio_file else 'Auto-detect or silent'}")
        print(f"📹 YouTube Upload: {'ON' if post_to_youtube else 'OFF'}")
        print("="*60)

        print(f"\n🔍 DEBUG: process_date - Step 1: Ensuring image for date")
        result = self.ensure_image_for_date(target_date)
        if result['status'] == 'not_found':
            print(f"\n❌ DEBUG: Date {target_date} not found in PDF")
            return {'status': 'not_found', 'date': target_date}

        print(f"\n✅ DEBUG: Image ready: {os.path.basename(result['image_path'])}")

        print(f"\n🔍 DEBUG: process_date - Step 2: Extracting text content")
        page_text = self.get_page_text_content(result['image_path'])
        print(f"   📝 Text length: {len(page_text)} characters")
        
        print(f"\n🔍 DEBUG: process_date - Step 3: Detecting page title")
        page_title = self.get_page_title(result['image_path'])
        print(f"   📝 Detected title: '{page_title}'")

        print(f"\n🔍 DEBUG: process_date - Step 4: Creating video")
        video_path = create_sliding_animation_video(
            image_path=result['image_path'],
            text_content=page_text,
            slide_duration=slide_duration,
            audio_file=audio_file
        )

        if video_path is None:
            print(f"\n❌ DEBUG: Video creation failed")
            return {'status': 'conversion_failed', 'date': target_date}

        print(f"\n✅ DEBUG: Video created: {video_path}")

        youtube_result = None
        if post_to_youtube:
            print(f"\n🔍 DEBUG: process_date - Step 5: Uploading to YouTube")
            youtube_result = self.upload_to_youtube(video_path, target_date, page_text, page_title)
        else:
            print(f"\n⏭️ DEBUG: YouTube upload skipped (post_to_youtube=False)")

        print(f"\n🔍 DEBUG: process_date COMPLETE")
        return {
            'status': 'success',
            'date': target_date,
            'image_path': result['image_path'],
            'video_path': video_path,
            'page_num': result['page_num'],
            'detected_title': page_title,
            'youtube': youtube_result
        }


if __name__ == "__main__":
    print("="*60)
    print("🎬 CREATIVE DAILY SCRIPT STARTING")
    print("="*60)
    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Current working directory: {os.getcwd()}")
    print(f"📁 Files in directory: {os.listdir('.')}")
    print("="*60)

    PDF_PATH = "your_document.pdf"
    OUTPUT_DIR = "extracted_date_pages"

    target_date = None
    post_to_youtube = True
    slide_duration = 18
    audio_file = None

    # Parse command line arguments
    print(f"\n🔍 DEBUG: Parsing arguments: {sys.argv[1:]}")
    for arg in sys.argv[1:]:
        if arg == "--no-youtube":
            post_to_youtube = False
            print(f"   📹 YouTube upload disabled")
        elif arg.startswith("--duration="):
            slide_duration = int(arg.split("=")[1])
            print(f"   ⏱️ Duration set to {slide_duration}s")
        elif arg.startswith("--audio="):
            audio_file = arg.split("=")[1]
            print(f"   🎵 Audio file specified: {audio_file}")
        elif arg.endswith(".mp3") and os.path.exists(arg):
            audio_file = arg
            print(f"   🎵 Audio file detected: {audio_file}")
        elif re.match(r'\d{4}-\d{2}-\d{2}', arg):
            target_date = arg
            print(f"   📅 Target date: {target_date}")

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")
        print(f"   📅 Using today's date: {target_date}")

    print(f"\n🎯 Final Configuration:")
    print(f"   📅 Target Date: {target_date}")
    print(f"   📹 YouTube Upload: {'ON' if post_to_youtube else 'OFF'}")
    print(f"   ⏱️  Duration: {slide_duration} seconds")
    print(f"   🎵 Audio Source: {audio_file if audio_file else 'Auto-detect'}")
    print(f"   📁 Playlist: {PLAYLIST_TITLE}")
    print(f"   📄 PDF Path: {PDF_PATH}")
    print(f"   📁 Output Dir: {OUTPUT_DIR}")
    print("="*60)

    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF not found: {PDF_PATH}")
        print(f"💡 Make sure '{PDF_PATH}' exists in the current directory")
        print(f"📁 Current directory files: {os.listdir('.')}")
        sys.exit(1)
    else:
        pdf_size = os.path.getsize(PDF_PATH) / (1024 * 1024)
        print(f"✅ PDF found: {PDF_PATH} ({pdf_size:.1f} MB)")

    processor = CompleteCalendarExtractor(PDF_PATH, OUTPUT_DIR)
    result = processor.process_date(target_date, post_to_youtube, 
                                     slide_duration=slide_duration, 
                                     audio_file=audio_file)

    print("\n" + "="*60)
    print("📋 FINAL RESULT")
    print("="*60)

    if result['status'] == 'success':
        print(f"✅ SUCCESS!")
        print(f"   📅 Date: {result['date']}")
        print(f"   📝 Title: {result.get('detected_title', 'N/A')}")
        print(f"   🎬 Video: {result.get('video_path', 'N/A')}")
        
        if os.path.exists(result.get('video_path', '')):
            video_size = os.path.getsize(result['video_path']) / (1024 * 1024)
            print(f"   📏 Video size: {video_size:.1f} MB")

        if result.get('youtube') and result['youtube']['status'] == 'success':
            print(f"\n📹 POSTED TO YOUTUBE!")
            print(f"   🔗 URL: {result['youtube']['video_url']}")
            print(f"   📁 Playlist: {PLAYLIST_TITLE}")
            print(f"   🖼️ Thumbnail: Auto-extracted from image content (no yellow background)")
        elif result.get('youtube') and result['youtube']['status'] == 'failed':
            print(f"\n❌ YouTube upload failed: {result['youtube'].get('error', 'Unknown')}")
        else:
            print(f"\n📹 YouTube upload not attempted or skipped")

        sys.exit(0)
    else:
        print(f"❌ FAILED: {result.get('status')}")
        sys.exit(1)
