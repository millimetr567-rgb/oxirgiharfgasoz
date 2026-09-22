"""
Vercel Serverless Function — FastAPI Entrypoint.

Marshrutlar:
- GET /                     -> Asosiy Web UI (HTML)
- POST /api/start           -> Yangi o'yin boshlash va kompyuterning ilk so'zi
- POST /api/submit-word     -> O'yinchi so'zini qabul qilish va AI bilan tekshirish
- POST /api/computer-turn   -> Kompyuter navbati uchun yangi so'z topish
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Asosiy loyiha papkasini sys.path ga qo'shish
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ozbek_letters import clean_word, get_first_letter, get_last_letter, display_letter, letters_match
from word_database import db
from gemini_service import GeminiService
from word_validator import WordValidator
from game import LastLetterGame

app = FastAPI(title="«So‘nggi harf» API", description="Kutubxona intellektual o'yini")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_html_content() -> str:
    """HTML faylni turli serverless yo'llaridan xavfsiz o'qish."""
    candidates = [
        PROJECT_ROOT / "public" / "index.html",
        CURRENT_DIR.parent / "public" / "index.html",
        Path("public/index.html"),
        CURRENT_DIR / "index.html",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
    return "<h1>«So‘nggi harf» — Veb interfeysi yuklanmoqda...</h1>"


# Pydantic modellar
class StartGameRequest(BaseModel):
    api_key: Optional[str] = None


class SubmitWordRequest(BaseModel):
    word: str
    expected_letter: str
    used_words: List[str] = []
    api_key: Optional[str] = None


class ComputerTurnRequest(BaseModel):
    starting_letter: str
    used_words: List[str] = []
    api_key: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Asosiy Web sahifani qaytarish."""
    content = _get_html_content()
    return HTMLResponse(content=content)


@app.post("/api/start")
async def start_game(req: StartGameRequest):
    """Yangi o'yinni boshlash."""
    start_info = db.get_random_starting_word()
    initial_word = start_info["word"]
    ends = get_last_letter(initial_word)

    return {
        "success": True,
        "current_word": initial_word,
        "current_explanation": start_info.get("explanation", ""),
        "expected_letter": ends,
        "expected_letter_display": display_letter(ends),
    }


@app.post("/api/submit-word")
async def submit_word(req: SubmitWordRequest):
    """O'yinchi so'zini tekshirish."""
    # Agar so'rovda API key berilgan bo'lsa, maxsus servis yaratish
    ai_service = GeminiService(api_key=req.api_key) if req.api_key else None
    validator = WordValidator(database=db, ai_service=ai_service) if ai_service else WordValidator(database=db)

    result = validator.validate(
        raw_word=req.word,
        expected_letter=req.expected_letter,
        used_words=set(req.used_words),
    )

    return {
        "success": result.is_valid,
        "is_valid": result.is_valid,
        "word": result.word,
        "starts_with": result.starts_with,
        "ends_with": result.ends_with,
        "is_library_related": result.is_library_related,
        "is_duplicate": result.is_duplicate,
        "explanation": result.explanation,
        "error_message": result.error_message,
    }


@app.post("/api/computer-turn")
async def computer_turn(req: ComputerTurnRequest):
    """Kompyuter navbati: avval mahalliy bazadan, so'ng Gemini AI dan so'z topish."""
    target_letter = clean_word(req.starting_letter)
    used_set = {clean_word(w) for w in req.used_words}

    # 1. Mahalliy kutubxona bazasidan qidirish
    candidate = db.get_random_word_starting_with(
        letter=target_letter,
        excluded_words=used_set,
    )

    if candidate:
        chosen_word = candidate["word"]
        explanation = candidate.get("explanation", "Kutubxona atamasi.")
        ends = candidate.get("ends_with", get_last_letter(chosen_word))
        starts = candidate.get("starts_with", get_first_letter(chosen_word))

        return {
            "success": True,
            "word": chosen_word,
            "starts_with": starts,
            "ends_with": ends,
            "expected_letter": ends,
            "expected_letter_display": display_letter(ends),
            "explanation": explanation,
            "source": "database",
        }

    # 2. Mahalliy bazada qolmasa, Gemini AI dan so'rash
    ai_service = GeminiService(api_key=req.api_key) if req.api_key else GeminiService()
    ai_suggestion = ai_service.suggest_word(
        starting_letter=target_letter,
        used_words=used_set,
    )

    if ai_suggestion.get("success") and "word" in ai_suggestion:
        ai_word = ai_suggestion["word"]
        c_word = clean_word(ai_word)

        if c_word not in used_set and letters_match(target_letter, get_first_letter(c_word)):
            ends = get_last_letter(c_word)
            expl = ai_suggestion.get("explanation", "Kutubxona atamasi.")
            category = ai_suggestion.get("category", "Kutubxonachilik")
            db.add_verified_word(c_word, category, expl)

            return {
                "success": True,
                "word": c_word,
                "starts_with": get_first_letter(c_word),
                "ends_with": ends,
                "expected_letter": ends,
                "expected_letter_display": display_letter(ends),
                "explanation": expl,
                "source": "gemini",
            }

    # Kompyuter so'z topa olmadi
    disp = display_letter(target_letter)
    return {
        "success": False,
        "reason": f"Taslim! Kompyuter «{disp}» harfi bilan boshlanuvchi boshqa kutubxona atamasini topa olmadi. Siz g'olib bo'ldingiz!",
    }


# Mahalliy sinov uchun
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="127.0.0.1", port=8000, reload=True)
