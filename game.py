"""
«So'nggi harf» o'yinining asosiy mantiqiy dvigateli (Game Engine).

Navbatlarni boshqaradi:
- O'yinchi navbati (7 soniyalik vaqt nazorati)
- Kompyuter navbati (mahalliy baza + Gemini AI qidiruvi)
- Hisob (score), rekordlar, ishlatilgan so'zlar tarixi
- O'yin holati (Game State)
"""

from typing import Dict, Any, List, Set, Optional, Tuple
from enum import Enum

from config import TURN_TIME_LIMIT
from ozbek_letters import (
    clean_word,
    get_first_letter,
    get_last_letter,
    display_letter,
    letters_match,
)
from word_database import db, WordDatabase
from gemini_service import gemini_service, GeminiService
from word_validator import validator, WordValidator, ValidationResult


class GameStatus(Enum):
    NOT_STARTED = "not_started"
    PLAYER_TURN = "player_turn"
    AI_THINKING = "ai_thinking"
    GAME_OVER = "game_over"


class LastLetterGame:
    """«So'nggi harf» intellektual o'yin tizimi."""

    def __init__(
        self,
        database: WordDatabase = db,
        ai_service: GeminiService = gemini_service,
        word_validator: WordValidator = validator,
    ):
        self.db = database
        self.ai = ai_service
        self.validator = word_validator

        # O'yin holati
        self.status: GameStatus = GameStatus.NOT_STARTED
        self.score: int = 0
        self.streak: int = 0
        self.current_word: str = ""
        self.current_explanation: str = ""
        self.expected_letter: str = ""
        self.used_words: Set[str] = set()
        self.history: List[Dict[str, Any]] = []
        self.game_over_reason: str = ""

    def start_game(self) -> Dict[str, Any]:
        """Yangi o'yinni boshlash. Kompyuter dastlabki so'zni tanlaydi."""
        self.score = 0
        self.streak = 0
        self.used_words.clear()
        self.history.clear()
        self.game_over_reason = ""

        # Boshlang'ich so'z
        start_info = self.db.get_random_starting_word()
        initial_word = start_info["word"]
        self.current_word = initial_word
        self.current_explanation = start_info.get("explanation", "")
        self.expected_letter = get_last_letter(initial_word)

        # Ishlatilganlar ro'yxatiga qo'shish
        self.used_words.add(clean_word(initial_word))

        history_item = {
            "author": "Kompyuter",
            "word": initial_word,
            "starts_with": get_first_letter(initial_word),
            "ends_with": self.expected_letter,
            "explanation": self.current_explanation,
            "is_valid": True,
        }
        self.history.append(history_item)

        self.status = GameStatus.PLAYER_TURN

        return {
            "status": self.status.value,
            "current_word": self.current_word,
            "current_explanation": self.current_explanation,
            "expected_letter": self.expected_letter,
            "expected_letter_display": display_letter(self.expected_letter),
            "score": self.score,
        }

    def process_player_word(self, raw_word: str) -> Tuple[bool, ValidationResult]:
        """
        O'yinchi kiritgan so'zni qabul qilish va tekshirish.
        Returns: (success: bool, result: ValidationResult)
        """
        if self.status != GameStatus.PLAYER_TURN:
            res = ValidationResult(
                is_valid=False,
                word=raw_word,
                starts_with="",
                ends_with="",
                is_library_related=False,
                is_duplicate=False,
                explanation="Hozir o'yinchining navbati emas.",
                error_message="O'yinchi navbati emas!",
            )
            return False, res

        val_result = self.validator.validate(
            raw_word=raw_word,
            expected_letter=self.expected_letter,
            used_words=self.used_words,
        )

        if not val_result.is_valid:
            # Xato so'z! O'yin yakunlanadi
            self.game_over_reason = val_result.error_message or val_result.explanation
            self.status = GameStatus.GAME_OVER
            return False, val_result

        # So'z to'g'ri!
        c_word = val_result.word
        self.used_words.add(clean_word(c_word))
        self.score += 10 + (self.streak * 2)
        self.streak += 1
        self.current_word = c_word
        self.current_explanation = val_result.explanation
        self.expected_letter = val_result.ends_with

        self.history.append({
            "author": "O'yinchi",
            "word": c_word,
            "starts_with": val_result.starts_with,
            "ends_with": val_result.ends_with,
            "explanation": val_result.explanation,
            "is_valid": True,
        })

        return True, val_result

    def handle_player_timeout(self) -> Dict[str, Any]:
        """O'yinchi 7 soniyada javob bera olmagan holat."""
        self.status = GameStatus.GAME_OVER
        self.game_over_reason = "Vaqt tugadi! 7 soniya ichida javob berilmadi."
        return {
            "status": self.status.value,
            "score": self.score,
            "reason": self.game_over_reason,
        }

    def play_computer_turn(self) -> Dict[str, Any]:
        """
        Kompyuterning navbati:
        1. O'yinchining oxirgi so'zining oxirgi harfini oladi.
        2. Mahalliy kutubxona bazasidan mos so'z qidiradi.
        3. Topilmasa, Gemini AI dan so'raydi.
        4. AI bergan so'zni tekshiradi.
        5. So'zni qabul qiladi va navbatni o'yinchiga topshiradi.
        """
        self.status = GameStatus.AI_THINKING
        target_letter = self.expected_letter

        # 1. Mahalliy bazadan qidirish
        candidate = self.db.get_random_word_starting_with(
            letter=target_letter,
            excluded_words=self.used_words,
        )

        if candidate:
            chosen_word = candidate["word"]
            explanation = candidate.get("explanation", "")
            starts = candidate.get("starts_with", get_first_letter(chosen_word))
            ends = candidate.get("ends_with", get_last_letter(chosen_word))

            self.current_word = chosen_word
            self.current_explanation = explanation
            self.expected_letter = ends
            self.used_words.add(clean_word(chosen_word))

            self.history.append({
                "author": "Kompyuter",
                "word": chosen_word,
                "starts_with": starts,
                "ends_with": ends,
                "explanation": explanation,
                "is_valid": True,
            })

            self.status = GameStatus.PLAYER_TURN
            return {
                "success": True,
                "word": chosen_word,
                "starts_with": starts,
                "ends_with": ends,
                "explanation": explanation,
                "expected_letter": self.expected_letter,
                "expected_letter_display": display_letter(self.expected_letter),
                "source": "database",
            }

        # 2. Agar bazadan topilmasa, Gemini AI dan yangi so'z so'rash
        ai_suggestion = self.ai.suggest_word(
            starting_letter=target_letter,
            used_words=self.used_words,
        )

        if ai_suggestion.get("success") and "word" in ai_suggestion:
            ai_word = ai_suggestion["word"]
            c_ai_word = clean_word(ai_word)

            # AI so'zini qat'iy tekshirish
            # 1. Takror emasmi?
            if c_ai_word in {clean_word(w) for w in self.used_words}:
                self.status = GameStatus.GAME_OVER
                self.game_over_reason = f"Kompyuter takroriy so'z taklif qildi ({ai_word}). Siz g'olib bo'ldingiz!"
                return {"success": False, "reason": self.game_over_reason, "player_won": True}

            # 2. Harf mosmi?
            ai_first = get_first_letter(c_ai_word)
            if not letters_match(target_letter, ai_first):
                self.status = GameStatus.GAME_OVER
                self.game_over_reason = f"Kompyuter noto'g'ri harfli so'z aytdi ({ai_word}). Siz g'olib bo'ldingiz!"
                return {"success": False, "reason": self.game_over_reason, "player_won": True}

            # Tasdiqlangach, bazaga ham kiritish
            explanation = ai_suggestion.get("explanation", "Kutubxona va kitobxonlik atamasi.")
            category = ai_suggestion.get("category", "Kutubxonachilik")
            self.db.add_verified_word(c_ai_word, category, explanation)

            ends = get_last_letter(c_ai_word)
            self.current_word = c_ai_word
            self.current_explanation = explanation
            self.expected_letter = ends
            self.used_words.add(c_ai_word)

            self.history.append({
                "author": "Kompyuter",
                "word": c_ai_word,
                "starts_with": ai_first,
                "ends_with": ends,
                "explanation": explanation,
                "is_valid": True,
            })

            self.status = GameStatus.PLAYER_TURN
            return {
                "success": True,
                "word": c_ai_word,
                "starts_with": ai_first,
                "ends_with": ends,
                "explanation": explanation,
                "expected_letter": self.expected_letter,
                "expected_letter_display": display_letter(self.expected_letter),
                "source": "gemini",
            }

        # Agar kompyuter hech qanday so'z topa olmasa
        self.status = GameStatus.GAME_OVER
        disp_letter = display_letter(target_letter)
        self.game_over_reason = (
            f"Taslim! Kompyuter «{disp_letter}» harfi bilan boshlanadigan boshqa kutubxona atamasini topa olmadi. "
            "Tabriklaymiz, siz g'olib bo'ldingiz!"
        )
        return {
            "success": False,
            "reason": self.game_over_reason,
            "player_won": True,
        }

    def get_summary(self) -> Dict[str, Any]:
        """O'yin yakuni bo'yicha to'liq hisobot."""
        return {
            "score": self.score,
            "streak": self.streak,
            "total_words": len(self.history),
            "player_words_count": sum(1 for h in self.history if h["author"] == "O'yinchi"),
            "computer_words_count": sum(1 for h in self.history if h["author"] == "Kompyuter"),
            "reason": self.game_over_reason,
            "history": self.history,
        }
