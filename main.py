import streamlit as st
import os
import pypdf
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from google import genai

# Setup separate stable folders for cache handling
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
    # Set up a high-quality widescreen slide canvas configuration
    img = Image.new('RGB', (1200, 675), color=(15, 23, 42)) # Indigo space theme
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 25, 675], fill=(99, 102, 241)) # Layout side accent bar
    
    words = text_content.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + " " + word) <= 45:
            current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    if current_line:
        lines.append(current_line.strip())
    formatted_text = "\n".join(lines[:10])
    
    try:
        font = ImageFont.load_default()
    except:
        font = None
        
    draw.text((80, 80), f"🎓 STUDY TOPIC MODULE - SLIDE {page_num}", fill=(99, 102, 241))
    draw.text((80, 160), formatted_text, fill=(241, 245, 249), spacing=18)
    img.save(output_img_path)

st.set_page_config(page_title="EduVideo AI", layout="centered")
st.title("🎓 EduVideo AI Presentation Deck")
st.subheader("Turn Boring Teacher Notes into Engaging Interactive Lectures")

uploaded_file = st.file_uploader("📂 Upload your professor's lecture notes (PDF only)", type=["pdf"])
voice_dict = {
    "🇮🇳 Female Accent": "en-IN-NeerjaNeural",
    "🇮🇳 Male Accent": "en-IN-PrabhatNeural"
}
voice_choice = st.selectbox("🗣️ Select Instructor Accent:", list(voice_dict.keys()))
selected_voice_id = voice_dict[voice_choice]

# Initialize state trackers to hold variables safely across web interactions
if "deck_ready" not in st.session_state:
    st.session_state.deck_ready = False
    st.session_state.slides = []
    st.session_state.audios = []

if uploaded_file and st.button("Generate Lecture Presentation 🚀"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    try:
        status_text.text("Step 1/3: Reading note contents...")
        pdf_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        progress_bar.progress(30)

        reader = pypdf.PdfReader(pdf_path)
        pages_to_process = min(len(reader.pages), 3) # Process first 3 pages max
        
        slides_cache = []
        audios_cache = []
        
        for index in range(pages_to_process):
            raw_text = reader.pages[index].extract_text()
            if not raw_text or not raw_text.strip():
                continue

            status_text.text(f"Step 2/3: Gemini is clarifying page {index + 1}...")
            simplified_script = rewrite_text_with_gemini(raw_text)
            
            audio_track_path = os.path.join(OUTPUT_DIR, f"track_{index}.mp3")
            slide_frame_path = os.path.join(OUTPUT_DIR, f"frame_{index}.png")
            
            status_text.text(f"Step 3/3: Processing audio streams for page {index + 1}...")
            communicate = edge_tts.Communicate(simplified_script, selected_voice_id)
            asyncio.run(communicate.save(audio_track_path))
            
            draw_visual_slide(simplified_script, slide_frame_path, index + 1)
            
            slides_cache.append(slide_frame_path)
            audios_cache.append(audio_track_path)
            progress_bar.progress(30 + int((index + 1) / pages_to_process * 70))

        if slides_cache:
            st.session_state.slides = slides_cache
            st.session_state.audios = audios_cache
            st.session_state.deck_ready = True
            status_text.success("🎉 Your Interactive Lecture Deck is Ready Below!")
            
    except Exception as general_error:
        st.error(f"System Error: {general_error}")

# Render the presentation deck module once compiled smoothly
if st.session_state.deck_ready:
    st.markdown("---")
    st.subheader("📺 Interactive Presentation Player")
    
    # Create tab segments acting as active slideshow buttons
    tab_labels = [f"Slide {i+1}" for i in range(len(st.session_state.slides))]
    tabs = st.tabs(tab_labels)
    
    for idx, tab in enumerate(tabs):
        with tab:
            # Display computed canvas graphics layout
            st.image(st.session_state.slides[idx], use_container_width=True)
            # Embed matching synced voice narration track player underneath
            st.audio(st.session_state.audios[idx], format="audio/mp3")
