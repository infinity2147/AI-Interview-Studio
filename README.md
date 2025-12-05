# 🎙️ AI Interview Studio  
### Autonomous Dual-Persona Panel Interview Simulator

**AI Interview Studio** is a next-gen recruitment system that simulates a *live joint panel interview*.  
Instead of a single chatbot, it orchestrates two fully independent AI personas:

- **HR Manager** – evaluates soft skills, culture fit, and behavioral signals  
- **Tech Lead** – probes technical depth, systems thinking, and domain mastery  

Both agents talk to the candidate **in real-time voice**, dynamically switching turns just like a real human panel.

The entire interview strategy is **derived from your uploaded HR Guide PDF**, making the system completely role-agnostic.

---

## 🧠 System Architecture

The pipeline is designed to behave like a real human conversation:

1. **Audio Capture (Frontend)**  
   Browser records the user’s microphone input with silence detection.

2. **Transcoding (Backend)**  
   Raw `.webm` audio is received by FastAPI and converted via **FFmpeg**.

3. **Hearing (STT)**  
   OpenAI **Whisper v1** converts speech → text with high fidelity.

4. **Thinking (LLM)**  
   **GPT-4o** processes the transcript, referencing the uploaded HR Guide PDF.

5. **Orchestration Logic**  
   Internally decides:
   - Who speaks next (HR or Tech Lead)  
   - Whether to drill deeper or shift topics  

6. **Stage Manager**  
   Determines when the interview reaches a natural conclusion.

7. **Speaking (TTS)**  
   **Murf.ai** generates hyper-realistic speech:
   - *Natalie* → HR persona  
   - *Cooper* → Tech Lead persona  

8. **Playback & UI Update**  
   Frontend plays the generated audio and updates the chat timeline.

---

## ✨ Key Features

### 👥 Dual-Persona Interview Panel
- **HR Manager**
  - Behavioral questions  
  - Psychological cues, red flags  
  - Time management & cultural fit scoring  

- **Tech Lead**
  - System design, architecture, debugging  
  - Domain-specific deep dives (e.g., HFT, fintech concurrency, ML pipelines)

➡️ Both personas explicitly hand over control:  
“**[TECH_LEAD] I’m done. Passing it to HR.**”

---

### 📄 PDF-Driven Brain (Zero Hardcoding)

Upload **any** HR Guide PDF and the system instantly adopts:
- A new interviewing style  
- New question patterns  
- New evaluation rubrics  

No code edits needed.  
Your PDF *is* the interview’s “brain.”

---

### 📊 Automated Hiring Report

At the end, the system outputs a structured JSON report containing:

- **Scores (0–10):**  
  - Technical Knowledge  
  - Communication  
  - Problem Solving  
  - Cultural Fit  
- **Pros & Cons:** Based on actual answers  
- **Hiring Recommendation:**  
  *No Hire / Weak Hire / Hire / Strong Hire*

This can be stored, forwarded, or consumed by downstream ATS systems.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|----------|------------|---------|
| Backend | FastAPI (Python 3.9+) | High-performance API server |
| LLM Engine | OpenAI GPT-4o | Reasoning + conversation flow |
| Speech-to-Text | OpenAI Whisper v1 | Converts voice → text |
| Text-to-Speech | Murf.ai | Realistic multi-voice output |
| Frontend | HTML5 + Vanilla JS | Lightweight UI & Audio Context |
| Audio Tools | FFmpeg | WebM transcoding |
| PDF Parsing | PyPDF2 | Extracts text from HR Guide |

---

## 🚀 Installation & Setup

### 1️⃣ Prerequisites
- Python **3.9+**
- **FFmpeg** installed

**Mac**
brew install ffmpeg
**Linux**
sudo apt install ffmpeg
**Windows**
winget install ffmpeg

### 1️2️⃣ Clone the Repository
git clone https://github.com/infinity2147/AI-Interview-Studio.git
cd ai-interview-studio
### 3️⃣ Install Dependencies
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
### 4️⃣ Environment Configuration
Create a .env in the root folder:
# OpenAI (LLM + STT)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx

# Murf.ai (TTS)
MURF_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Server Config
HOST=0.0.0.0
PORT=8000
## 🏃‍♂️ Usage Guide
### ▶️ Step 1 — Start the Server
uvicorn main:app --reload
Server will start on:
http://0.0.0.0:8000
### ▶️ Step 2 — Configure the Role (Upload HR Guide)
1. Open the browser UI:
   http://localhost:8000
2. Go to the HR Panel tab.
3. Upload a role guide PDF (e.g., fintech_guide.pdf, frontend_engineer_guide.pdf).
  The entire interview strategy instantly adapts.
### ▶️ Step 3 — Start Speaking
- Click Start Interview
- The system begins with the HR Manager
- Tech Lead jumps in when needed
- Conversation continues until the Stage Manager ends the flow
You receive:
- Live audio responses
- Transcript UI updates
- Final JSON report

## 🧩 Folder Structure
ai-interview-studio/
│
├── backend/
│   ├── api.py
│   ├── orchestrator.py
│   ├── tts_handler.py
│   ├── stt_handler.py
│   ├── pdf_parser.py
│
├── frontend/
│   ├── index.html
│   ├── script.js
│
├── main.py
├── requirements.txt
├── README.md
└── .env
## 🔮 Future Progress

### 🌍 1. Multi-Language Interview Support
The next major upgrade is enabling fully multilingual interviews.  
The system will support:

- **Real-time STT + LLM reasoning** in any target language  
- **Dynamic switching** (e.g., HR in English, Tech Lead in Hindi)  
- **Murf Falcon multilingual TTS** output  
- Automatic detection of candidate speech language and seamless translation

This turns the platform into a globally usable interview agent capable of adapting to regional hiring requirements without changing core logic.

---

### 🎭 2. Emotion-Aware Interviewers (Adaptive Persona Styles)
Future versions will incorporate **emotionally expressive AI personas**, allowing HR and Tech Lead to:

- Speak with *empathetic*, *neutral*, *strict*, or *challenging* tones  
- Adjust tone mid-interview based on candidate performance  
- Use Murf Falcon’s expressive controls (pitch, pace, warmth)  
- Respond differently when detecting stress, confidence, hesitation, or deception in the candidate

This introduces a more realistic simulation of human interview behavior.

---

### 🧠 3. Real-Time Emotion Tracking of the Interviewee
We aim to integrate emotion detection pipelines that analyze:

- **Voice tone** (stress, confidence, hesitation)  
- **Speech patterns** (pauses, filler words, fluctuations)  
- **Transcript sentiment** (positive, negative, neutral, nervous)  
- **Behavioral signals** (consistency, defensiveness, assertiveness)

The detected emotional state will feed into:

- Dynamic questioning difficulty  
- HR/Tech Lead reaction adjustment  
- More accurate hiring recommendations  
- A new *“Emotional Intelligence & Composure”* score in the final report

This gives the panel true psychological evaluation capability and elevates the interview from informational assessment to behavioral assessment.

---

### 🚀 Summary of Future Capabilities
- Multilingual conversations  
- Emotionally adaptive AI personas  
- Emotion tracking of candidates  
- Fully personalized interview flow based on real-time emotional signals  

These enhancements will bring the AI Interview Studio closer to a **human-level interview experience**, enabling recruiters to assess not just what the candidate says — but *how* they say it.

