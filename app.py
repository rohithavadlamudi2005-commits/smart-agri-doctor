import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
from gtts import gTTS
import requests

# ---------------- GROQ API ----------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ---------------- PAGE SETTINGS ----------------
st.set_page_config(page_title="Smart Agri Doctor", layout="wide")

st.title("🌱 Smart Agri Doctor")
st.caption("AI-powered crop disease detection and advisory system")

# ---------------- SESSION STATE ----------------
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = None

# ---------------- SIDEBAR ----------------
st.sidebar.title("Control Panel")

language = st.sidebar.selectbox(
    "🌍 Select Language",
    ["English", "Hindi", "Telugu"],
    index=0
)

# ---------------- WEATHER ----------------
st.sidebar.subheader("🌦 Weather Risk")

city = st.sidebar.text_input("Enter City")

if city:
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
        geo_data = requests.get(geo_url).json()

        if "results" not in geo_data:
            st.sidebar.error("City not found")
        else:
            lat = geo_data["results"][0]["latitude"]
            lon = geo_data["results"][0]["longitude"]

            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m"
            weather_data = requests.get(weather_url).json()

            temp = weather_data["current"]["temperature_2m"]
            humidity = weather_data["current"]["relative_humidity_2m"]

            st.sidebar.write("Temperature:", temp, "°C")
            st.sidebar.write("Humidity:", humidity, "%")

            if humidity > 70:
                st.sidebar.warning("⚠ High fungal disease risk")
            else:
                st.sidebar.success("Low disease risk")

    except:
        st.sidebar.error("Weather service error")

# ---------------- DISEASE SEARCH ----------------
st.sidebar.subheader("🔎 Disease Information")

disease_query = st.sidebar.text_input("Search Disease")

if disease_query:

    prompt = f"""
Explain plant disease {disease_query}.

Include:
Symptoms
Causes
Treatment
Prevention
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role":"user","content":prompt}]
    )

    st.sidebar.write(response.choices[0].message.content)

# ---------------- IMAGE INPUT ----------------
st.subheader("📷 Upload or Capture Leaf Image")

option = st.radio(
    "Choose Image Source",
    ["Upload Image","Use Camera"]
)

image = None

if option == "Upload Image":

    uploaded_file = st.file_uploader(
        "Upload crop leaf image",
        type=["jpg","jpeg","png"]
    )

    if uploaded_file:
        image = Image.open(uploaded_file)

elif option == "Use Camera":

    camera_image = st.camera_input("Capture leaf photo")

    if camera_image:
        image = Image.open(camera_image)

# ---------------- IMAGE DISPLAY ----------------
if image:

    col1, col2 = st.columns(2)

    with col1:
        st.image(image, caption="Leaf Image", width="stretch")

    with col2:

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        if st.button("🔍 Analyze Disease"):

            analysis_prompt = """
You are an expert agronomist.

Analyze the plant leaf image and provide:

1. Plant Type
2. Disease Name
3. Symptoms
4. Treatment Recommendations
5. Prevention Tips
6. Confidence Score

Respond clearly in English.
"""

            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role":"user",
                        "content":[
                            {"type":"text","text":analysis_prompt},
                            {
                                "type":"image_url",
                                "image_url":{
                                    "url":f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ]
            )

            english_result = response.choices[0].message.content

            final_result = english_result

            if language != "English":

                translate_prompt = f"""
Translate the following agricultural diagnosis into {language}.
Do not change plant names or disease names.

Text:
{english_result}
"""

                translation = client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[{"role":"user","content":translate_prompt}]
                )

                final_result = translation.choices[0].message.content

            st.session_state.diagnosis_result = final_result

# ---------------- RESULT DISPLAY ----------------
if st.session_state.diagnosis_result:

    st.subheader("🌿 Diagnosis Report")
    st.success(st.session_state.diagnosis_result)

    voice_lang = {
        "English":"en",
        "Hindi":"hi",
        "Telugu":"te"
    }

    if st.button("🔊 Listen to Diagnosis"):

        tts = gTTS(
            text=st.session_state.diagnosis_result,
            lang=voice_lang[language]
        )

        tts.save("diagnosis.mp3")

        audio_file = open("diagnosis.mp3","rb")

        st.audio(audio_file.read())

    st.download_button(
        "📥 Download Report",
        data=st.session_state.diagnosis_result,
        file_name="diagnosis_report.txt"
    )