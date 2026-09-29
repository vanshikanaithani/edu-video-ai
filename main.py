import streamlit as st
import os
import pypdf
import asyncio
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from google import genai

# Setup folders safely
UPLOAD_DIR = "uploaded_notes"
OUTPUT_DIR = "generated_lessons"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    client = genai.Client()
except Exception:
    client = None

def rewrite_text_with_gemini(raw_text):
    if not client:
        return raw_text
    prompt = f"""
    You are an elite educator in India. Explain this complex topic simply to college students.
    Break it down into 3 clear, easy-to-read bullet points.
    Keep it conversational, natural, and concise enough to be spoken in 30 seconds.
    Raw text: {raw_text}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception:
        return raw_text

def draw_visual_slide(text_content, output_img_path, page_num):
    img = Image.new('RGB', (1920, 1080), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 40, 1080], fill=(99, 102, 241))
    
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
    
    draw.text((120, 120), f"🎓 SECTION {page_num}", fill=(99, 102, 241))
    draw.text((120, 240), formatted_text, fill=(241, 245, 249), spacing=24)
    img.save(output_img_path)

st.set_page_config(page_title="EduVideo AI", layout="centered")
st.title("🎓 EduVideo AI")
st.subheader("Turn Boring Teacher Notes into Engaging Video Lessons")

uploaded_file = st.file_uploader("📂 Upload your lecture notes (PDF only)", type=["pdf"])
voice_dict = {
    "🇮🇳 Female Accent": "en-IN-NeerjaNeural",
    "🇮🇳 Male Accent": "en-IN-PrabhatNeural"
}
voice_choice = st.selectbox("🗣️ Select Instructor Accent:", list(voice_dict.keys()))
selected_voice_id = voice_dict[voice_choice]

if uploaded_file and st.button("Convert to Video Lecture 🚀"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    try:
        status_text.text("Step 1/5: Loading document...")
        pdf_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        progress_bar.progress(20)

        reader = pypdf.PdfReader(pdf_path)
        # Limit prototype to first 2 pages to guarantee instant rendering without server lag
        pages_to_process = min(len(reader.pages), 2)
        video_slide_clips = []
        
        for index in range(pages_to_process):
            raw_text = reader.pages[index].extract_text()
            if not raw_text or not raw_text.strip():
                continue

            status_text.text(f"Step 2/5: AI is rewriting page {index + 1}...")
            simplified_script = rewrite_text_with_gemini(raw_text)
            
            audio_track_path = os.path.join(OUTPUT_DIR, f"track_{index}.mp3")
            slide_frame_path = os.path.join(OUTPUT_DIR, f"frame_{index}.png")
            
            status_text.text(f"Step 3/5: Recording AI audio voiceover for page {index + 1}...")
            
            # SAFE SYNC AUDIO RUN
            communicate = edge_tts.Communicate(simplified_script, selected_voice_id)
            asyncio.run(communicate.save(audio_track_path))
            
            draw_visual_slide(simplified_script, slide_frame_path, index + 1)
            
            audio_segment = AudioFileClip(audio_track_path)
            single_slide_clip = ImageClip(slide_frame_path).set_duration(audio_segment.duration).set_audio(audio_segment)
            video_slide_clips.append(single_slide_clip)
            progress_bar.progress(20 + int((index + 1) / pages_to_process * 50))

        if video_slide_clips:
            status_text.text("Step 4/5: Stitching video timeline...")
            master_video_composition = concatenate_videoclips(video_slide_clips, method="compose")
            progress_bar.progress(85)
            
            status_text.text("Step 5/5: Compiling final video (this will take 10 seconds)...")
            final_mp4_output = os.path.join(OUTPUT_DIR, "final_student_course.mp4")
            
            # LOCKED SYSTEM PARAMETERS TO FORCE IMMEDIATE CONVERSION
            master_video_composition.write_videofile(
                final_mp4_output, 
                fps=8, # Lowered frame rate to make conversion 3x faster on cloud servers
                codec="libx264", 
                audio_codec="aac", 
                logger=None,
                verbose=False,
                progress_bar=False
            )
            
            progress_bar.progress(100)
            status_text.success("🎉 Video Lecture Rendered Successfully!")
            st.video(final_mp4_output)
            
            with open(final_mp4_output, "rb") as video_file:
                st.download_button(label="📥 Download Finished MP4 Course File", data=video_file, file_name="AI_Visual_Lecture.mp4", mime="video/mp4")
    except Exception as general_error:
        st.error(f"System Error: {general_error}")
