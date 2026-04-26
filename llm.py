"""
MediAssist AI — Clinical Report Summarizer
llm.py  |  LLM Integration (OpenAI / Groq / fallback)
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
#  DETECT AVAILABLE LLM BACKEND
# ──────────────────────────────────────────────
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_KEY   = os.getenv("GROQ_API_KEY", "")

# Priority: OpenAI → Groq → fallback
if OPENAI_KEY:
    BACKEND = "openai"
elif GROQ_KEY:
    BACKEND = "groq"
else:
    BACKEND = "fallback"

# ──────────────────────────────────────────────
#  OPENAI SETUP
# ──────────────────────────────────────────────
if BACKEND == "openai":
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_KEY)
    except ImportError:
        BACKEND = "fallback"

# ──────────────────────────────────────────────
#  GROQ SETUP
# ──────────────────────────────────────────────
if BACKEND == "groq":
    try:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_KEY)
    except ImportError:
        BACKEND = "fallback"


# ══════════════════════════════════════════════
#  SYSTEM PROMPT — Safety-first medical assistant
# ══════════════════════════════════════════════
SYSTEM_PROMPT = """You are MediAssist AI, a cautious and empathetic medical report assistant.

Your role:
- Explain lab report values in plain, easy-to-understand language
- Highlight any values that appear outside normal range
- Suggest lifestyle considerations or further tests when appropriate
- Always remind users that you are NOT a substitute for professional medical advice

Rules you MUST follow:
1. NEVER diagnose a disease or condition with certainty
2. NEVER prescribe medication or treatment
3. ALWAYS recommend consulting a licensed physician for medical decisions
4. Explain medical terms in simple language
5. Be compassionate and non-alarming in tone
6. Keep responses concise (under 250 words unless asked for detail)

When you don't know something, say so honestly."""


# ══════════════════════════════════════════════
#  CALL LLM — shared internal function
# ══════════════════════════════════════════════
def _call_llm(user_message: str, max_tokens: int = 500) -> str:
    """Route LLM call to available backend."""

    if BACKEND == "openai":
        try:
            response = _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"[OpenAI error] {str(e)}"

    elif BACKEND == "groq":
        try:
            response = _groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"[Groq error] {str(e)}"

    else:
        return _fallback_response(user_message)


# ══════════════════════════════════════════════
#  RULE-BASED FALLBACK (no API key)
# ══════════════════════════════════════════════
_FALLBACK_FACTS = {
    "hemoglobin": "Hemoglobin carries oxygen in red blood cells. Low levels may indicate anemia. High levels can occur with dehydration or certain conditions. Normal: 12–17.5 g/dL.",
    "wbc": "White blood cells fight infections. High WBC may indicate infection or inflammation. Low WBC can reduce infection-fighting ability. Normal: 4,000–11,000 cells/uL.",
    "platelet": "Platelets help blood clot. Low platelets increase bleeding risk; high platelets may increase clotting risk. Normal: 150,000–450,000 /uL.",
    "glucose": "Blood glucose measures sugar levels. High levels may indicate diabetes or pre-diabetes. Normal fasting: 70–100 mg/dL; post-meal: up to 140 mg/dL.",
    "cholesterol": "Cholesterol is a fatty substance. High total cholesterol increases heart disease risk. Normal: below 200 mg/dL.",
    "creatinine": "Creatinine is a kidney waste product. High levels may indicate kidney stress. Normal: 0.6–1.2 mg/dL.",
    "sgot": "SGOT/AST is a liver enzyme. High levels can indicate liver stress. Normal: under 40 U/L.",
    "sgpt": "SGPT/ALT is a liver enzyme. High levels may indicate liver inflammation. Normal: under 40 U/L.",
    "tsh": "TSH regulates thyroid function. High TSH may indicate underactive thyroid. Low TSH may indicate overactive thyroid. Normal: 0.4–4.0 mIU/L.",
    "urea": "Blood urea reflects kidney filtration. High levels may indicate dehydration or kidney stress. Normal: 7–20 mg/dL.",
}

def _fallback_response(question: str) -> str:
    """Simple keyword-based response when no API key is available."""
    q_lower = question.lower()

    for keyword, info in _FALLBACK_FACTS.items():
        if keyword in q_lower:
            return (
                f"ℹ️ {info}\n\n"
                "⚠️ This is a basic automated response. "
                "Add OPENAI_API_KEY or GROQ_API_KEY to the .env file for full AI mode.\n\n"
                "🩺 Always consult a licensed physician."
            )

    return (
        "AI service unavailable.\n\n"
        "Please add OPENAI_API_KEY or GROQ_API_KEY to the .env file.\n\n"
        "🩺 Consult a licensed physician for medical advice."
    )


# ══════════════════════════════════════════════
#  PUBLIC FUNCTION 1 — Generate Report Summary
# ══════════════════════════════════════════════
def generate_summary(
    report_text: str,
    flagged_values: List[Dict[str, Any]],
    max_chars: int = 3000
) -> str:
    """
    Generate a patient-friendly summary of the lab report.
    """

    abnormal_lines = []

    for row in flagged_values:
        if row["Status"] in ("High", "Low"):
            abnormal_lines.append(
                f"- {row['Test']}: {row['Value']} {row['Unit']} "
                f"({row['Status']})"
            )

    abnormal_text = (
        "\n".join(abnormal_lines)
        if abnormal_lines else "No abnormal values detected."
    )

    truncated = report_text[:max_chars] if report_text else "(no text extracted)"

    prompt = f"""You are reviewing a patient's lab report.

--- REPORT TEXT ---
{truncated}

--- DETECTED ABNORMAL VALUES ---
{abnormal_text}

Write a concise, friendly summary for the patient.

Requirements:
1. Mention tests performed
2. Explain abnormal values simply
3. Reassure if many are normal
4. Advise doctor consultation

Under 200 words.
"""

    return _call_llm(prompt, max_tokens=400)


# ══════════════════════════════════════════════
#  PUBLIC FUNCTION 2 — Answer User Questions
# ══════════════════════════════════════════════
def answer_question(
    question: str,
    report_text: str,
    lab_values: List[Dict[str, Any]],
    max_chars: int = 2000
) -> str:
    """
    Answer a user's question about their lab report.
    """

    if lab_values:
        value_lines = [
            f"- {r['Test']}: {r['Value']} {r['Unit']} ({r['Status']})"
            for r in lab_values
        ]
        values_context = "\n".join(value_lines)
    else:
        values_context = "No specific values parsed."

    truncated = report_text[:max_chars] if report_text else "(no report text)"

    prompt = f"""A patient uploaded a lab report.

--- BIOMARKER VALUES ---
{values_context}

--- REPORT TEXT ---
{truncated}

--- QUESTION ---
{question}

Answer clearly in simple language.
Do not diagnose.
Suggest doctor consultation if needed.
"""

    return _call_llm(prompt, max_tokens=450)