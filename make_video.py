import os
import json
from moviepy import ImageClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ===== CONFIGURATION =====
IMAGES_DIR = "images"
OUTPUT_VIDEO = "broke_to_fortune_500.mp4"
ASSIGNMENT_DURATION = 5        # seconds per prompt
OUTRO_DURATION = 10
INTRO_DURATION = 5
VIDEO_SIZE = (1080, 1920)      # 9:16 vertical
MUSIC_FILE = "background_music.mp3"
STATE_FILE = "state.json"
INTROS_FILE = "intros.json"
PROMPTS_FILE = "prompts.json"

# ===== Helper: load JSON with fallback =====
def load_json(filepath, default_list):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default_list

# ===== Helper: save state =====
def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

# ===== Helper: get next item from a list with state =====
def get_next_item(state_key, items):
    if not items:
        return None
    idx = state.get(state_key, 0) % len(items)
    item = items[idx]
    # update state for next time
    state[state_key] = (idx + 1) % len(items)
    save_state(state)
    return item

# ===== Helper: create text overlay with semi‑transparent panel =====
def create_text_overlay(text, duration, font_size=60, margin=80, bg_alpha=180):
    # Create transparent image
    img = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
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

    # Measure text block
    line_height = font_size + 10
    total_h = len(lines) * line_height + 40  # padding top/bottom
    total_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        total_w = max(total_w, bbox[2] - bbox[0])
    total_w += 40  # horizontal padding

    # Position of the background panel
    panel_x = (VIDEO_SIZE[0] - total_w) // 2
    panel_y = (VIDEO_SIZE[1] - total_h) // 2

    # Draw semi‑transparent black panel
    panel_img = Image.new('RGBA', (total_w, total_h), (0, 0, 0, bg_alpha))
    img.paste(panel_img, (panel_x, panel_y), panel_img)

    # Draw text on top
    draw = ImageDraw.Draw(img)
    y_text = panel_y + 20
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (VIDEO_SIZE[0] - line_w) // 2
        draw.text((x, y_text), line, fill=(255, 255, 255), font=font)
        y_text += line_height

    return ImageClip(np.array(img), duration=duration)

# ===== Main =====
def main():
    global state
    print("="*60)
    print("🎬 Video Creator with State (intros, prompts, backgrounds, music)")
    print("="*60)

    # Load state (if exists)
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {
            "intro_index": 0,
            "prompt_index": 0,
            "background_index": 0
        }

    # Load intros and prompts from JSON
    intros = load_json(INTROS_FILE, ["🔥 3 A.I. Prompts\nFrom Broke to Fortune 500"])
    prompts = load_json(PROMPTS_FILE, [])
    if not prompts:
        print("❌ No prompts found in prompts.json. Add at least one.")
        return

    # Check background images
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
        print(f"❌ Please put at least one image in '{IMAGES_DIR}/' and rerun.")
        return
    bg_files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not bg_files:
        print(f"❌ No images found in '{IMAGES_DIR}/'. Add some.")
        return
    bg_files = [os.path.join(IMAGES_DIR, f) for f in sorted(bg_files)]
    print(f"✅ Found {len(bg_files)} background images")

    # We'll cycle backgrounds manually using state
    def get_next_background():
        idx = state["background_index"] % len(bg_files)
        state["background_index"] = (idx + 1) % len(bg_files)
        save_state(state)
        return bg_files[idx]

    # ----- Create clips -----
    clips = []

    # 1. Intro clip (5s) – background + intro text
    intro_text = get_next_item("intro_index", intros)
    bg_intro = get_next_background()
    bg_intro_clip = ImageClip(bg_intro).resized(VIDEO_SIZE).with_duration(INTRO_DURATION)
    text_intro = create_text_overlay(intro_text, duration=INTRO_DURATION, font_size=70)
    intro_clip = CompositeVideoClip([bg_intro_clip, text_intro])
    clips.append(intro_clip)

    # 2. Assignment prompts (each 5s) – background + prompt text
    # Get the number of prompts to show (we'll take one cycle or up to N)
    # Here we show all prompts in the JSON file (could be more than 7)
    for i, prompt_text in enumerate(prompts):
        bg_path = get_next_background()
        bg_clip = ImageClip(bg_path).resized(VIDEO_SIZE).with_duration(ASSIGNMENT_DURATION)
        # Add "Prompt X" prefix if not already there
        display_text = f"Prompt {i+1}\n\n{prompt_text}" if not prompt_text.startswith("Prompt") else prompt_text
        text_clip = create_text_overlay(display_text, duration=ASSIGNMENT_DURATION, font_size=45)
        combined = CompositeVideoClip([bg_clip, text_clip])
        clips.append(combined)
        print(f"   Added prompt {i+1}: {prompt_text[:50]}...")

    # 3. Outro clip (10s)
    outro_text = "✅ Thank you for watching!\n\n👉 Click the link in description\n👉 Join the Creative Daily\n👉 Start your Fortune 500 journey"
    bg_outro = get_next_background()
    bg_outro_clip = ImageClip(bg_outro).resized(VIDEO_SIZE).with_duration(OUTRO_DURATION)
    text_outro = create_text_overlay(outro_text, duration=OUTRO_DURATION, font_size=55)
    outro_clip = CompositeVideoClip([bg_outro_clip, text_outro])
    clips.append(outro_clip)

    # ----- Concatenate video -----
    print("🎬 Concatenating video clips...")
    final_video = concatenate_videoclips(clips, method="compose")

    # ----- Add background music (loop if needed) -----
    if os.path.exists(MUSIC_FILE):
        print(f"🎵 Loading music: {MUSIC_FILE}")
        audio = AudioFileClip(MUSIC_FILE)
        total_duration = final_video.duration
        if audio.duration < total_duration:
            # loop music
            loops = int(total_duration / audio.duration) + 1
            audio = audio.loop(loops)
        audio = audio.subclipped(0, total_duration)
        audio = audio.with_volume_scaled(0.3)  # 30% volume
        final_video = final_video.with_audio(audio)
    else:
        print(f"⚠️ No music file found: {MUSIC_FILE}. Video will be silent.")

    # ----- Render -----
    print("💾 Rendering final video...")
    final_video.write_videofile(OUTPUT_VIDEO, fps=24, codec='libx264', audio_codec='aac')
    size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
    print(f"✅ Video saved as {OUTPUT_VIDEO} ({size_mb:.1f} MB)")
    print(f"📌 State saved. Next run will continue where it left off.")

if __name__ == "__main__":
    main()
