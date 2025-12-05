import uvicorn
import shutil
import base64
import os
import time
import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from openai import OpenAI
from dotenv import load_dotenv

import PyPDF2  # For loading HR PDF

# --- LOAD ENV & API KEYS ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import your handlers (unchanged)
from stt_handler import transcribe_file
from tts_handler import synthesize
from config import MURF_API_KEY, DEEPGRAM_API_KEY

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

# --- ⚙️ CONFIGURATION ---
MAX_INTERVIEW_DURATION = 300  # 5 Minutes safety cutoff

# Used by the analysis engine
HR_COMPETENCIES = {
    "Technical Knowledge": 0.40,
    "Communication Skills": 0.30,
    "Problem Solving": 0.20,
    "Cultural Fit": 0.10,
}

# --- 📄 HR PDF PATHS ---
HR_PDF_PATH = "hr_docs/hr_guide.pdf"                   # HR guide uploaded by HR
QUESTIONNAIRE_PDF_PATH = "static/hr_questionnaire.pdf"  # Generated from LaTeX

os.makedirs(os.path.dirname(HR_PDF_PATH), exist_ok=True)


def load_pdf(path: str) -> str:
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
        print(f"✅ Loaded HR PDF from {path}")
        return text
    except Exception as e:
        print(f"⚠️ Failed to load HR PDF: {e}")
        return ""


# Loaded once at startup; can be updated via /upload_hr_pdf
HR_GUIDE = load_pdf(HR_PDF_PATH)

# --- SESSION STATE ---
# history will store panelist too: {"role": "...", "panelist": "HR Manager"/"Tech Lead"/"", "text": "..."}
session_state = {
    "start_time": 0,
    "current_q_index": 0,
    "follow_up_count": 0,
    "last_question": "",
    "history": [],
}

# --- 🧠 PANEL LLM HELPERS ---


def build_panel_system_prompt() -> str:
    """
    Panel-style interviewer: HR Manager + Tech Lead.
    Behavior fully driven by HR PDF contents.
    """
    weights_str = ", ".join([f"{k} ({v*100}%)" for k, v in HR_COMPETENCIES.items()])

    return f"""
You are simulating a PANEL INTERVIEW with TWO interviewers for the role described
in the following HR guide PDF.

This PDF defines:
- the role (title, level, team)
- required skills
- domain knowledge
- red flags
- evaluation themes
- cultural expectations

You MUST treat it as authoritative input from the hiring manager.

================= HR GUIDE (DO NOT REVEAL TO CANDIDATE) =================
{HR_GUIDE}
==============================================================================

PANEL MEMBERS:
1) HR Manager (Calm, professional, people-focused)
   - Focuses on behavioral questions, culture fit, communication, ownership,
     motivation, teamwork, ethics.
   - Tone: warm, composed, structured.

2) Tech Lead (Deep technical expert)
   - Focuses on technical depth, architecture, tradeoffs, debugging,
     real-world system design, and role-specific skills.
   - Tone: direct but fair, precise, technical language.

INTERVIEW RULES:
- ALWAYS output your messages starting with EXACTLY ONE of these tags:
    [HR_MANAGER]  or  [TECH_LEAD]
  followed by a space and what they say.

  Examples:
    [HR_MANAGER] Good afternoon, thanks for joining us...
    [TECH_LEAD] Let's dive into your experience with distributed systems...

- Only one interviewer speaks per turn.
- HR Manager typically:
  * opens the interview,
  * handles intros, background, behavioral, culture,
  * may hand over to Tech Lead when it's time for technical discussion.
- Tech Lead:
  * focuses on technical and domain-specific questions as implied in the HR guide.

- Ask ONE clear question per turn.
- Use the candidate’s previous answers to ask sharp follow-ups.
- All questions must be tightly aligned with the ROLE described in the HR guide.

COMPETENCIES TO KEEP IN MIND (weights):
{weights_str}
HOW TO END SMOOTHLY:
- Do not let the interview go on forever. Keep it focused.
- When the Tech Lead is done, they should say: "[TECH_LEAD] I'm satisfied with the technical side. handing it back to you, [HR Manager Name]."
- Then, in the NEXT turn, the HR Manager ask questions if he wants to 
- CRITICAL: WHEN the HR Manager says the final goodbye, append the token <END_INTERVIEW> at the very end.

Example of Ending:
[HR_MANAGER] Thank you for coming in today. We have all the info we need and will get back to you by Friday. Have a great day! <END_INTERVIEW>
ENDING THE INTERVIEW:
- When the panel has enough information:
  1) HR Manager gives a friendly closing message to the candidate.
  2) Append the EXACT token <END_INTERVIEW> at the VERY END of that message.
- Do NOT use <END_INTERVIEW> until the interview is truly complete.
- Do NOT output JSON.
- Do NOT show the [HR_MANAGER]/[TECH_LEAD] tags to the candidate; they are for the system only.
"""


def build_llm_messages_from_history():
    """
    Convert session_state['history'] to OpenAI chat messages.
    For the LLM, all interviewer messages are 'assistant' with the panel tag removed.
    Candidate messages are 'user'.
    """
    messages = [
        {
            "role": "system",
            "content": build_panel_system_prompt(),
        }
    ]

    for entry in session_state["history"]:
        role = entry["role"]
        text = entry["text"]
        if role == "Interviewer":
            messages.append({"role": "assistant", "content": text})
        elif role == "Candidate":
            messages.append({"role": "user", "content": text})

    return messages


def generate_next_panel_turn() -> str:
    """
    Calls OpenAI to get the next panel message (must start with [HR_MANAGER] or [TECH_LEAD]).
    """
    messages = build_llm_messages_from_history()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=256,
        temperature=0.7,
    )
    return response.choices[0].message.content


def parse_panel_speaker_and_text(raw: str):
    """
    Parse panelist label and clean text from model output.

    Expected format:
      [HR_MANAGER] some sentence...
      [TECH_LEAD] another sentence...
    Possibly with <END_INTERVIEW> at the end.
    """
    raw = raw.strip()
    speaker_role = "HR Manager"
    text = raw

    if raw.startswith("[HR_MANAGER]"):
        speaker_role = "HR Manager"
        text = raw[len("[HR_MANAGER]") :].lstrip()
    elif raw.startswith("[TECH_LEAD]"):
        speaker_role = "Tech Lead"
        text = raw[len("[TECH_LEAD]") :].lstrip()

    # Strip end token if present (we'll check separately)
    end_token = "<END_INTERVIEW>"
    interview_done = end_token in text
    text = text.replace(end_token, "").strip()

    return speaker_role, text, interview_done


# --- 🧠 FINAL HR REPORT (PDF-driven, general) ---


async def generate_final_report():
    print("📊 Generating HR Report...")

    transcript_text = "\n".join(
        [
            f"{entry['role']}{(' - ' + entry.get('panelist', '')) if entry['role'] == 'Interviewer' else ''}: {entry['text']}"
            for entry in session_state["history"]
        ]
    )

    # Last candidate statement (for UI completeness)
    last_candidate_text = ""
    for entry in reversed(session_state["history"]):
        if entry["role"] == "Candidate":
            last_candidate_text = entry["text"]
            break

    weights_str = ", ".join([f"{k} ({v*100}%)" for k, v in HR_COMPETENCIES.items()])

    prompt = f"""
You are a Senior HR hiring evaluator.

Your job is to produce a rigorous evaluation for the specific role defined in 
the HR GUIDE PDF below.

This PDF defines:
- role expectations
- required skills and competencies
- domain / business context
- red flags
- cultural expectations

DO NOT reveal or quote the PDF, but strictly use it for reasoning.

================= HR GUIDE (DO NOT REVEAL) =================
{HR_GUIDE}
=================================================================

INTERVIEW TRANSCRIPT (Panel: HR Manager + a Tech Lead, Candidate):
{transcript_text}

EVALUATION CRITERIA (Base weights):
{weights_str}

TASK:
1. Score each competency from 0–10 based on the transcript AND HR guide expectations:
   - Technical Knowledge
   - Communication Skills
   - Problem Solving
   - Cultural Fit
2. Compute a weighted overall score (0–10) using the given weights.
3. Provide a recommendation: "Strong Hire", "Hire", "Weak Hire", or "No Hire".
4. List EXACTLY 3 Pros and EXACTLY 3 Cons, aligned with the role & HR guide.
5. Write a short summary tailored to THIS ROLE and COMPANY CONTEXT
   (use domain-relevant language from the HR guide where appropriate).

OUTPUT STRICT JSON (NO EXTRA TEXT):
{{
  "scores": {{
    "Technical Knowledge": 0,
    "Communication Skills": 0,
    "Problem Solving": 0,
    "Cultural Fit": 0
  }},
  "overall_score": 0.0,
  "recommendation": "No Hire",
  "pros": ["...", "...", "..."],
  "cons": ["...", "...", "..."],
  "summary": "..."
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a JSON-outputting HR analysis engine. Always return STRICT JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        report_json = json.loads(response.choices[0].message.content)

        closing_msg = (
            f"Interview complete. Overall Score: {report_json['overall_score']:.1f}/10. "
            f"Result: {report_json['recommendation']}."
        )

        audio_bytes = synthesize(closing_msg, "HR Manager") # later: route to HR voice if you want
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        return JSONResponse(
            {
                "user_transcript": last_candidate_text,
                "ai_response_text": closing_msg,
                "ai_audio_base64": audio_base64,
                "speaker_role": "HR Manager",
                "is_end": True,
                "report": report_json,
            }
        )

    except Exception as e:
        print(f"Report Error: {e}")
        return JSONResponse(
            {"error": "Failed to generate report"}, status_code=500
        )


# --- 🎙️ CHAT ENDPOINT (panel + silence handling) ---


@app.post("/chat")
async def chat(file: UploadFile):
    try:
        elapsed_time = time.time() - session_state["start_time"]
        if elapsed_time > MAX_INTERVIEW_DURATION:
            return await generate_final_report()

        # 1. Save & Transcribe User Audio
        user_audio_path = TEMP_DIR / "latest_answer.webm"
        with open(user_audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        stt_result = transcribe_file(str(user_audio_path))
        user_text = stt_result.get("transcript", "").strip()

        # If no user input detected → don't advance the panel, just ask to repeat
        if not user_text:
            ai_text_clean = "Come again? I didn’t hear anything."
            speaker_role = "HR Manager"  # default to HR for clarification

            session_state["history"].append(
                {"role": "Interviewer", "panelist": speaker_role, "text": ai_text_clean}
            )

            audio_bytes = synthesize(ai_text_clean, speaker_role)
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            return JSONResponse(
                {
                    "user_transcript": "",
                    "ai_response_text": ai_text_clean,
                    "ai_audio_base64": audio_base64,
                    "speaker_role": speaker_role,
                    "is_end": False,
                }
            )

        # Otherwise append candidate message
        session_state["history"].append(
            {"role": "Candidate", "panelist": "", "text": user_text}
        )

        # 2. Let the panel LLM decide the next move
        ai_text_raw = generate_next_panel_turn().strip()
        speaker_role, ai_text_clean, interview_done = parse_panel_speaker_and_text(
            ai_text_raw
        )

        # Log interviewer message
        if ai_text_clean:
            session_state["history"].append(
                {
                    "role": "Interviewer",
                    "panelist": speaker_role,
                    "text": ai_text_clean,
                }
            )
            session_state["last_question"] = ai_text_clean

        if interview_done:
            # Final turn – hand off to HR report generator
            return await generate_final_report()

        # 3. Generate audio for this panelist
        # NOTE: synthesize() currently has no voice param.
        # Later you can route speaker_role -> voice here.
        audio_bytes = synthesize(ai_text_clean, speaker_role)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        return JSONResponse(
            {
                "user_transcript": user_text,
                "ai_response_text": ai_text_clean,
                "ai_audio_base64": audio_base64,
                "speaker_role": speaker_role,
                "is_end": False,
            }
        )

    except Exception as e:
        print(f"Error in /chat: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- 🚀 START INTERVIEW (panel opens) ---


@app.get("/start")
async def start_interview_endpoint():
    # Reset session
    session_state["start_time"] = time.time()
    session_state["history"] = []
    session_state["current_q_index"] = 0
    session_state["follow_up_count"] = 0
    session_state["last_question"] = ""

    # Let the panel generate intro + first question (usually HR Manager)
    ai_text_raw = generate_next_panel_turn()
    speaker_role, ai_text_clean, interview_done = parse_panel_speaker_and_text(
        ai_text_raw
    )

    session_state["history"].append(
        {"role": "Interviewer", "panelist": speaker_role, "text": ai_text_clean}
    )
    session_state["last_question"] = ai_text_clean

    audio_bytes = synthesize(ai_text_clean, speaker_role)
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    return JSONResponse(
        {
            "text": ai_text_clean,
            "audio_base64": audio_base64,
            "speaker_role": speaker_role,
        }
    )


# --- 📤 HR: UPLOAD HR GUIDE PDF ---


@app.post("/upload_hr_pdf")
async def upload_hr_pdf(file: UploadFile = File(...)):
    """
    HR uploads a new HR guide PDF from the frontend.
    Saves to HR_PDF_PATH and reloads HR_GUIDE.
    """
    try:
        contents = await file.read()
        with open(HR_PDF_PATH, "wb") as f:
            f.write(contents)

        global HR_GUIDE
        HR_GUIDE = load_pdf(HR_PDF_PATH)

        return JSONResponse(
            {"status": "ok", "message": "HR guide uploaded and loaded successfully."}
        )
    except Exception as e:
        print(f"Error in /upload_hr_pdf: {e}")
        return JSONResponse(
            {"status": "error", "message": "Failed to upload HR guide."},
            status_code=500,
        )


# --- 📄 HR QUESTIONNAIRE PDF (DOWNLOAD/VIEW) ---


@app.get("/hr_questionnaire")
async def get_hr_questionnaire():
    """
    Serve the HR questionnaire PDF (from static/).
    """
    if not os.path.exists(QUESTIONNAIRE_PDF_PATH):
        return JSONResponse(
            {
                "error": "Questionnaire PDF not found. Put hr_questionnaire.pdf in static/."
            },
            status_code=404,
        )

    return FileResponse(
        QUESTIONNAIRE_PDF_PATH,
        media_type="application/pdf",
        filename="HR_Interview_Setup_Form.pdf",
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
