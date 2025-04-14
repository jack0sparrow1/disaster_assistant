from groq import Groq
from deep_translator import GoogleTranslator
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
import playsound
import warnings
import re
from dotenv import load_dotenv


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) 
# Language map for display and internal use
LANGUAGES = {
    'hi': 'Hindi',
    'te': 'Telugu',
    'ta': 'Tamil',
    'bn': 'Bengali',
    'mr': 'Marathi',
    'ml': 'Malayalam',   
    'kn': 'Kannada', 
    'en': 'English'
}

import time

def get_voice_input(lang_code: str) -> str:
    """Capture voice input and convert to text using Google Speech Recognition."""
    r = sr.Recognizer()
    r.energy_threshold = 400
    r.dynamic_energy_threshold = True
    r.pause_threshold = 1.5

    with sr.Microphone() as source:
        print("🎙️ Speak now...")
        time.sleep(1.5)  # Let user prepare
        r.adjust_for_ambient_noise(source, duration=2)  # Better noise handling
        print(f"🔊 Calibrated energy threshold: {r.energy_threshold}")
        
        try:
            audio = r.listen(source, timeout=10, phrase_time_limit=15)
            text = r.recognize_google(audio, language=f"{lang_code}-IN")
            print(f"📝 You said: {text}")
            return text
        except sr.UnknownValueError:
            return "Sorry, I could not understand the audio."
        except sr.RequestError as e:
            return f"Could not request results; {e}"

def translate_text(text: str, target_lang: str, source_lang: str = 'auto') -> str:
    """Handle translation with error fallback"""
    try:
        if source_lang == target_lang:
            return text
        return GoogleTranslator(source=source_lang, target=target_lang).translate(text)
    except Exception as e:
        warnings.warn(f"Translation failed: {str(e)}")
        return text
def get_groq_response(prompt: str, lang_code: str, model: str = "llama3-70b-8192") -> str:
    """Get AI response in the target language with clear formatting"""
    language_name = LANGUAGES.get(lang_code, 'your language')

    safe_prompt = f"""
    You are AidBot, a helpful assistant that provides clear, complete, and friendly advice about disasters and emergency preparedness.

    The user is speaking in {language_name}. You MUST reply only in {language_name} using native script and everyday, natural language.

    Avoid special formatting like markdown (no bold, bullets, or numbered lists). Write full, grammatically correct sentences.

    Your response should be smooth and easy to read, in short, meaningful paragraphs. Avoid breaking sentences unnaturally or using fragments.

    The user asked: {prompt}
    """

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": safe_prompt}],
            model=model,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Groq API error: {str(e)}")

def speak_text(text: str, lang: str = 'en'):
    """Convert text to speech and play it, cleaning up temp file properly."""
    try:
        tts = gTTS(text=text, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
        tts.save(temp_path)
        
        playsound.playsound(temp_path)
    except Exception as e:
        print(f"Voice output failed: {e}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_error:
                print(f"Failed to delete temp audio: {cleanup_error}")

def select_language() -> str:
    """Prompt user to select a preferred language code."""
    print("Select your preferred language:")
    for code, name in LANGUAGES.items():
        print(f"{code} - {name}")
    while True:
        choice = input("Enter language code (e.g., te, hi, en): ").strip().lower()
        if choice in LANGUAGES:
            print(f"✅ You selected: {LANGUAGES[choice]}")
            return choice
        else:
            print("Invalid choice. Please try again.")
def main():
    print("🧭 AidChain Multilingual Chatbot")
    print("🌐 Supports: Hindi, Telugu, Tamil, Bengali, Marathi, English\n")

    # Step 1: User selects preferred language
    lang_code = select_language()

    while True:
        try:
            mode = input("\nType 'v' for voice input or press Enter for text ('exit' to quit): ").strip()
            if mode.lower() == 'exit':
                break

            if mode.lower() == 'v':
                user_input = get_voice_input(lang_code)
            else:
                user_input = input("You: ")

            if user_input.lower() in ['exit', 'quit']:
                break

            # Step 2: Translate user input to English
            english_input = translate_text(user_input, 'en', lang_code)

            # Optional: Add context if input is too short
            if len(english_input.strip().split()) < 3:
                english_input = f"This is a disaster-related question: {english_input}"

            # Step 3: Get AI response in native language
            native_response = get_groq_response(english_input, lang_code)

            # Step 4: Show and speak the native language response
            print("\nAidBot:")
            print("-" * 50)
            print(native_response)
            print("-" * 50)

            # Clean response for TTS
            cleaned_response = re.sub(r"[•*+→\-\–\—▶️🌐🎙️📝🚨🔈💡❗✅🔁📍📢🔥]", "", native_response)
            speak_text(cleaned_response.strip(), lang=lang_code)

        except Exception as e:
            print(f"\n⚠️ Error: {str(e)}")
            print("Please try again or check your API keys\n")

if __name__ == "__main__":
    main()
