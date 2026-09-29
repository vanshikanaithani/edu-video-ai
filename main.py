import streamlit as st
import os
import pypdf
import asyncio
import edge_tts
# Fixed import structure for compatibility with Streamlit's environment
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from google import genai

# Setup folders for handling cloud file actions
UPLOAD_DIR = "uploaded_notes"
OUTPUT_DIR = "generated_lessons"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Connect to Google Gemini
try:
    client = genai.Client()
except Exception:
    client = None

def rewrite_text_with_gemini(raw_text):
    if not client:
        return raw_text
    prompt = f"""
    You are an elite, highly engaging educator in India known for explaining complex, dry academic topics to college students using a simple, relatable, and storytelling approach (similar to top educational YouTubers).
    Your task is to transform this raw text extracted from a professor's notes into a conversational narration script that will be read aloud by an AI voiceover engine. 
    Strictly follow these rules:
    1. Tone: Keep it enthusiastic, encouraging, and clear. Avoid overly formal corporate jargon or robotic phrasing.
    2. Structure: Break the explanation down into 3 to 4 crisp, punchy bullet points that are visually easy to read on a video slide.
    3. Clarity: Use clear everyday analogies, real-world examples, or simple frameworks relevant to Indian students if it helps explain a complex concept.
    4. Language: Write in plain English, but keep the sentence structure natural and spoken, exactly how a teacher explains things on a whiteboard.
    5. Length Constraints: Keep it concise enough to be naturally spoken in under 30 to 45 seconds (around 60-90 words total). Do not include any meta-text, introductions like "Sure, here is...", or structural labels.
    Here is the raw slide text to transform:
    {raw_text}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        return raw_text

def draw_visual_slide(text_content, output_img_path, page_num):
    width, height = 1920, 1080
    bg_color = (15, 23, 42)        
    accent_color = (99, 102, 241)  
    text_color = (241, 245, 249)    
    
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 40, height], fill=accent_color)
    
    words = text_content.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + " " + word) <= 50:
            current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    if current_line:
        lines.append(current_line.strip())
        
    formatted_text = "\n".join(lines[:12])
    
    try:
        font = ImageFont.load_default()
    except:
        font = None
        
    draw.text((120, 120), f"🎓 CHAPTER SEGMENT - SECTION {page_num}", fill=accent_color)
    draw.text((120, 240), formatted_text, fill=text_color, spacing=24)
    img.save(output_img_path)

st.set_page_config(page_title="EduVideo AI - Indian Learner Platform", layout="centered")
st.title("🎓 EduVideo AI")
st.subheader("Turn Boring Teacher Notes & PPTs into Engaging Video Lessons")
st.write("Designed for visual learners. Upload your college document slides to see them rewritten by Gemini and transformed into clean interactive video tracks.")

uploaded_file = st.file_uploader("📂 Upload your professor's lecture notes (PDF only)", type=["pdf"])
voice_option = st.selectbox("🗣️ Select Preferred AI Instructor Accent Tone:", ["en-IN-NeerjaNeural (Female - Natural Indian Accent)", "en-IN-PrabhatNeural (Male - Natural Indian Accent)"])
selected_voice_id = voice_option.split(" ")

async def generate_voice_over(text_to_speak, output_audio_path, voice_model):
    communicate = edge_tts.Communicate(text_to_speak, voice_model)
    await communicate.save(output_audio_path)

if uploaded_file and st.button("Convert to Video Lecture Course 🚀"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    try:
        status_text.text("Step 1/5: Loading and analyzing study document layout matrix...")
        pdf_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        progress_bar.progress(10)

        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        video_slide_clips = []
        
        for index, page in enumerate(reader.pages):
            raw_text = page.extract_text()
            if not raw_text or not raw_text.strip():
                continue

            status_text.text(f"Step 2/5: Gemini is teachifying slide section {index + 1} of {total_pages}...")
            simplified_script = rewrite_text_with_gemini(raw_text)
            
            audio_track_path = os.path.join(OUTPUT_DIR, f"track_{index}.mp3")
            slide_frame_path = os.path.join(OUTPUT_DIR, f"frame_{index}.png")
            
            status_text.text(f"Step 3/5: Encoding AI speech tracks for section {index + 1}...")
            asyncio.run(generate_voice_over(simplified_script, audio_track_path, selected_voice_id))
            
            draw_visual_slide(simplified_script, slide_frame_path, index + 1)
            
            audio_segment = AudioFileClip(audio_track_path)
            track_duration = audio_segment.duration
            
            single_slide_clip = ImageClip(slide_frame_path).set_duration(track_duration).set_audio(audio_segment)
            video_slide_clips.append(single_slide_clip)
            progress_bar.progress(10 + int((index + 1) / total_pages * 60))

        if video_slide_clips:
            status_text.text("Step 4/5: Merging chronological media chapter sequences...")
            master_video_composition = concatenate_videoclips(video_slide_clips, method="compose")
            progress_bar.progress(85)
            
            status_text.text("Step 5/5: Compiling output presentation .mp4 video file container...")
            final_mp4_output = os.path.join(OUTPUT_DIR, "final_student_course.mp4")
            master_video_composition.write_videofile(final_mp4_output, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
            
            progress_bar.progress(100)
            status_text.success("🎉 Educational Video Course Rendered Successfully via Gemini!")
            st.video(final_mp4_output)
            
            with open(final_mp4_output, "rb") as video_file:
                st.download_button(label="📥 Download Finished MP4 Course File", data=video_file, file_name="AI_Visual_Lecture.mp4", mime="video/mp4")
    except Exception as general_error:
        st.error(f"System Processing Interrupted: {general_error}")
