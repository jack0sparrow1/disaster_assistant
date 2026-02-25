from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from groq import Groq
from deep_translator import GoogleTranslator
import speech_recognition as sr
import io
import os
import subprocess
import re
from dotenv import load_dotenv
import warnings
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize Flask app


# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)


# Setup Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Supported languages
LANGUAGES = {
    'hi': 'Hindi', 'te': 'Telugu', 'ta': 'Tamil', 'bn': 'Bengali',
    'mr': 'Marathi', 'ml': 'Malayalam', 'kn': 'Kannada', 'en': 'English'
}

def translate_text(text: str, target_lang: str, source_lang: str = 'auto') -> str:
    """Translates input text to the target language."""
    try:
        if source_lang == target_lang:
            return text
        return GoogleTranslator(source=source_lang, target=target_lang).translate(text)
    except Exception as e:
        warnings.warn(f"Translation failed: {str(e)}")
        return text

def get_groq_response(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """Gets AI response in English (Groq always returns English)."""
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Groq API error: {str(e)}")

# ------------------------------
# TTS FUNCTION (EDGE-TTS STREAMING)
# ------------------------------

# Map simple language codes to high-quality Microsoft Edge Neural Voices
VOICE_MAP = {
    "en": "en-US-JennyNeural",
    "hi": "hi-IN-SwaraNeural",
    "bn": "bn-IN-TanishaaNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "pa": "pa-IN-OjasNeural",
    "ur": "ur-IN-GulNeural"
}

@app.route("/speak", methods=["GET"])
def speak_stream():
    """Streams audio back to the browser on the fly using edge-tts CLI"""
    text = request.args.get("text", "")
    lang_code = request.args.get("lang", "en")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    voice = VOICE_MAP.get(lang_code, "en-US-JennyNeural")
    
    def generate():
        cmd = ["edge-tts", "--voice", voice, "--text", text]
        # Popen runs the process, and we read stdout as it streams from Microsoft's servers
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        while True:
            data = process.stdout.read(4096)
            if not data:
                break
            yield data
            
    return Response(stream_with_context(generate()), mimetype="audio/mpeg")

@app.route("/languages", methods=["GET"])
def get_languages():
    """Returns the available languages."""
    return jsonify(LANGUAGES)

@app.route("/chat", methods=["POST"])
def chat():
    """Handles user input text and returns AI response in the target language."""
    data = request.get_json()
    user_input = data.get("input")
    lang_code = data.get("lang_code", "en")

    if not user_input:
        return jsonify({"error": "Missing input text"}), 400

    # Translate user input to English
    english_input = translate_text(user_input, 'en', lang_code)
    
    # If input is too short, add context
    if len(english_input.strip().split()) < 3:
        english_input = f"This is a disaster-related question: {english_input}"

    # Static English intro
    # static_intro_en = "Welcome to AidChain — a blockchain-based platform ensuring transparent and instant disaster relief."

    # # Translate the intro to user's language
    # static_intro_local = translate_text(static_intro_en, lang_code, 'en')

    # Get Groq response in English  
    groq_response = get_groq_response(english_input)

    # Combine translated static intro with Groq response
    response_text = f"{groq_response}"
    # Translate the response to the target language
    translated_response = translate_text(response_text, lang_code, 'en')

    # Clean the response for TTS readability
    cleaned_response = re.sub(r"[•*+→\-\–\—▶️🌐🎙️📝🚨🔈💡❗✅🔁📍📢🔥]", "", translated_response)

    return jsonify({
        "response": cleaned_response.strip()
    })



@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Handles audio blob upload from frontend and returns transcription."""
    lang_code = request.form.get("lang_code", "en")
    
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
        
    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()
    
    try:
        # Transcribe using Groq Whisper model (handles webm natively)
        transcription = client.audio.transcriptions.create(
            file=("audio.webm", audio_bytes),
            model="whisper-large-v3",
            language=lang_code
        )
        user_input = transcription.text
        if not user_input or not user_input.strip():
             return jsonify({"error": "No speech detected"}), 400
             
        return jsonify({"transcript": user_input.strip()})

    except Exception as e:
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500

# --- FRONTEND ROUTES (COMMENTED OUT FOR API ONLY USAGE) ---

# @app.route("/")
# def index():
#     return send_from_directory('frontend', 'index.html')

# @app.route("/<path:path>")
# def static_files(path):
#     return send_from_directory('frontend', path)

if __name__ == "__main__":
    # Set host to '0.0.0.0' and port from the environment
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

