# Disaster Assistant Service

This Flask-based API provides translation, AI chat, text-to-speech, and transcription features tailored for disaster response communication.

## Available Endpoints

### `GET /languages`
- **Description:** Returns a JSON object listing supported language codes and their full names.
- **Response example:**
  ```json
  {
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "bn": "Bengali",
    "mr": "Marathi",
    "ml": "Malayalam",
    "kn": "Kannada",
    "en": "English"
  }
  ```

### `POST /chat`
- **Description:** Receives user input text and language code, translates it to English, sends to AI (Groq) for a response, then translates back to the requested language.
- **Request Body:** JSON object with fields:
  - `input` (string) – the user text.
  - `lang_code` (string) – target language code (e.g. "en", "hi"). Defaults to "en".

- **Responses:**
  - `200 OK` with JSON:
    ```json
    { "response": "<AI-generated reply in requested language>" }
    ```
  - `400 Bad Request` if `input` is missing.

### `POST /transcribe`
- **Description:** Accepts an audio file and returns a text transcription using Groq Whisper.
- **Form parameters:**
  - `audio` – file upload (e.g., from an HTML form or multipart request).
  - `lang_code` (optional) – language code for transcription defaulting to "en".

- **Responses:**
  - `200 OK` with JSON:
    ```json
    { "transcript": "<transcribed text>" }
    ```
  - `400 Bad Request` for missing audio or empty transcription.
  - `500 Internal Server Error` if transcription fails.

### `GET /speak`
- **Description:** Streams back an audio pronunciation of provided text using Microsoft Edge TTS voices.
- **Query Parameters:**
  - `text` (string) – text to read aloud (required).
  - `lang` (string) – language code to choose the voice (default: "en").

- **Responses:**
  - `200 OK` with `audio/mpeg` stream.
  - `400 Bad Request` if `text` is omitted.

## Local Setup

1. Install dependencies:
   ```bash
   python -m venv venv
   .\\venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
2. Create a `.env` file at the project root with:
   ```ini
   GROQ_API_KEY=your_groq_key_here
   ```
3. Run the app:
   ```bash
   python translate.py
   ```
4. By default the service listens on `http://localhost:5000`.

## Notes

- Ensure `.env` is added to `.gitignore` to protect your API keys.
- CORS is enabled for cross-origin requests from any frontend.
- The `/speak` endpoint requires the `edge-tts` CLI to be installed system-wide.
