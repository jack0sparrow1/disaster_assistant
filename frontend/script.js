const API_BASE_URL = 'http://localhost:5000';

const dom = {
    chatContainer: document.getElementById('chat-container'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    voiceBtn: document.getElementById('voice-btn'),
    langSelect: document.getElementById('language-select')
};

let currentPlayingAudio = null;
let currentPlayingBtn = null;

// Application Initialization
async function init() {
    await fetchLanguages();

    // Wire up event listeners
    dom.sendBtn.addEventListener('click', handleSendText);
    dom.chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSendText();
    });

    dom.voiceBtn.addEventListener('click', handleVoiceInput);
}

// Fetch supported languages from backend API
async function fetchLanguages() {
    try {
        const res = await fetch(`${API_BASE_URL}/languages`);
        if (!res.ok) throw new Error('API failed');
        const languages = await res.json();

        dom.langSelect.innerHTML = '';
        const defaultLang = 'en';

        for (const [code, name] of Object.entries(languages)) {
            const option = document.createElement('option');
            option.value = code;
            option.textContent = name;
            if (code === defaultLang) option.selected = true;
            dom.langSelect.appendChild(option);
        }
    } catch (error) {
        console.error('Failed to load languages:', error);
        // Fallback options if API fails initially
        dom.langSelect.innerHTML = '<option value="en">English (Fallback)</option>';
    }
}

// Handle text submission
async function handleSendText() {
    const text = dom.chatInput.value.trim();
    if (!text) return;

    // Clear the welcome message from UI when chatting begins
    const welcomeMsg = dom.chatContainer.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    // Display user's message
    appendMessage(text, 'user');
    dom.chatInput.value = '';

    // Show typing animation
    const typingId = appendTypingIndicator();

    const langCode = dom.langSelect.value;

    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: text, lang_code: langCode })
        });

        // Remove typing indication once server responds
        removeElement(typingId);

        if (!response.ok) throw new Error('Server error');

        const data = await response.json();

        // Render bot response & display Play button
        appendMessage(data.response, 'bot', true);

    } catch (error) {
        removeElement(typingId);
        appendMessage('Sorry, I encountered an error connecting to the server. Is the Flask backend running?', 'bot');
        console.error(error);
    }
}

let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// Handle Native Voice Input execution via Browser MediaRecorder API
async function handleVoiceInput() {
    const welcomeMsg = dom.chatContainer.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    if (isRecording) {
        // Stop recording
        mediaRecorder.stop();
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstart = () => {
            isRecording = true;
            dom.voiceBtn.classList.add('recording');
            dom.voiceBtn.innerHTML = '<i class="fa-solid fa-stop"></i>';
            dom.chatInput.value = "";
            dom.chatInput.placeholder = "Listening... Speak now, then click stop.";
            dom.chatInput.disabled = true;
        };

        mediaRecorder.onstop = async () => {
            isRecording = false;
            dom.voiceBtn.classList.remove('recording');
            dom.voiceBtn.innerHTML = '<i class="fa-solid fa-microphone"></i>';
            stream.getTracks().forEach(track => track.stop());

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

            dom.chatInput.placeholder = "Processing your voice...";

            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            formData.append('lang_code', dom.langSelect.value);

            try {
                const response = await fetch(`${API_BASE_URL}/transcribe`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error('Server error');
                const data = await response.json();

                dom.chatInput.value = data.transcript || "";
            } catch (error) {
                console.error(error);
                alert('Sorry, an error occurred transcribing the audio.');
            } finally {
                dom.chatInput.placeholder = "Type your message here...";
                dom.chatInput.disabled = false;
                dom.chatInput.focus();
            }
        };

        mediaRecorder.start();

    } catch (e) {
        alert("Microphone access denied or not available. Please allow microphone permissions in Brave.");
        console.error(e);
    }
}

// Utility: Appends an entire HTML element containing logic and display bounds onto the DOM
function appendMessage(text, sender, addAudioBtn = false, forceId = null) {
    const msgId = forceId || ('msg-' + Date.now());
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.id = msgId;

    const avatar = sender === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

    const contentHtml = document.createElement('div');
    contentHtml.className = 'msg-content';

    const textSpan = document.createElement('span');
    textSpan.innerHTML = text.replace(/\n/g, '<br>');
    contentHtml.appendChild(textSpan);

    // Append TTS logic controls conditionally inline without unsafe global template injection
    if (addAudioBtn) {
        const audioCtrl = document.createElement('div');
        audioCtrl.className = 'audio-controls';

        const btn = document.createElement('button');
        btn.className = 'play-audio-btn';
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Play';

        let audioObj = null;

        btn.onclick = async () => {
            if (audioObj) {
                if (audioObj.paused) {
                    if (currentPlayingAudio && currentPlayingAudio !== audioObj) {
                        currentPlayingAudio.pause();
                        if (currentPlayingBtn) currentPlayingBtn.innerHTML = '<i class="fa-solid fa-play"></i> Play';
                    }
                    audioObj.play().catch(e => console.error(e));
                    btn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
                    currentPlayingAudio = audioObj;
                    currentPlayingBtn = btn;
                } else {
                    audioObj.pause();
                    btn.innerHTML = '<i class="fa-solid fa-play"></i> Play';
                }

                audioObj.onended = () => {
                    btn.innerHTML = '<i class="fa-solid fa-play"></i> Play';
                };
                return;
            }

            // First time playing: trigger the HTTP streaming request immediately
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
            btn.disabled = true;

            const langCode = dom.langSelect.value;
            // The browser streams this endpoint instantly chunk-by-chunk
            audioObj = new Audio(`${API_BASE_URL}/speak?text=${encodeURIComponent(text)}&lang=${langCode}`);

            audioObj.onended = () => {
                btn.innerHTML = '<i class="fa-solid fa-play"></i> Play';
            };

            audioObj.oncanplay = () => {
                btn.disabled = false;
                if (audioObj.paused) {
                    if (currentPlayingAudio && currentPlayingAudio !== audioObj) {
                        currentPlayingAudio.pause();
                        if (currentPlayingBtn) currentPlayingBtn.innerHTML = '<i class="fa-solid fa-play"></i> Play';
                    }
                    audioObj.play().catch(e => console.error(e));
                    btn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
                    currentPlayingAudio = audioObj;
                    currentPlayingBtn = btn;
                }
            };

            audioObj.onerror = (e) => {
                console.error('Audio stream error:', e);
                alert('Audio streaming failed.');
                btn.innerHTML = '<i class="fa-solid fa-play"></i> Play';
                btn.disabled = false;
            };

            // Start the network request to fetch the stream
            audioObj.load();
        };

        audioCtrl.appendChild(btn);
        contentHtml.appendChild(audioCtrl);
    }

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'avatar';
    avatarDiv.innerHTML = avatar;

    div.appendChild(avatarDiv);
    div.appendChild(contentHtml);

    dom.chatContainer.appendChild(div);
    scrollToBottom();
    return msgId;
}

// Utility: Appends typing bubble
function appendTypingIndicator() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.className = 'message bot';
    div.id = id;

    div.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="msg-content" style="padding: 0.8rem 1.25rem;">
            <div class="typing-indicator">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        </div>
    `;

    dom.chatContainer.appendChild(div);
    scrollToBottom();
    return id;
}

function removeElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
}

// Kickstart script
init();
