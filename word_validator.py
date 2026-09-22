"""
So'zlarni tekshirish (validatsiya) moduli.

Dastur kodi va Google Gemini AI tekshiruvlarini o'zaro birlashtiradi:
- Mahalliy tekshiruv: Bo'sh joylar, takrorlanish (used_words), harf mosligi.
- AI tekshiruvi: O'zbek tilida mavjudligi, kutubxona sohasiga aloqadorligi, izohi.
- Ikkala tomon qarorlarini solishtirish va tasdiqlash.
"""

from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

from ozbek_letters import (
    clean_word,
    get_first_letter,
    get_last_letter,
    letters_match,
    display_letter,
)
from word_database import db
from gemini_service import gemini_service
from config import is_api_configured


@dataclass
class ValidationResult:
    """Tekshiruv natijasi ma'lumotlar modeli."""
    is_valid: bool
    word: str
    starts_with: str
    ends_with: str
    is_library_related: bool
    is_duplicate: bool
    explanation: str
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "word": self.word,
            "starts_with": self.starts_with,
            "ends_with": self.ends_with,
            "is_library_related": self.is_library_related,
            "is_duplicate": self.is_duplicate,
            "explanation": self.explanation,
            "error_message": self.error_message,
        }


class WordValidator:
    """So'zlarni tekshiruvchi asosiy sinf."""

    def __init__(self, database=db, ai_service=gemini_service):
        self.db = database
        self.ai = ai_service

    def validate(
        self,
        raw_word: str,
        expected_letter: str,
        used_words: Set[str],
    ) -> ValidationResult:
        """
        Kiritilgan so'zni har tomonlama tekshirish.
        1-bosqich: Dasturiy qat'iy tekshiruv
        2-bosqich: Gemini AI orqali tekshirish
        """
        # 1. Tozalash va normallashtirish
        cleaned = clean_word(raw_word)

        if not cleaned:
            return ValidationResult(
                is_valid=False,
                word=raw_word,
                starts_with="",
                ends_with="",
                is_library_related=False,
                is_duplicate=False,
                explanation="Hech qanday so'z kiritilmadi.",
                error_message="Iltimos, so'z kiriting!",
            )

        # 2. Harflarni dastur kodi orqali aniqlash
        prog_first = get_first_letter(cleaned)
        prog_last = get_last_letter(cleaned)

        # 3. Takroriy so'z tekshiruvi (dasturiy)
        normalized_used = {clean_word(w) for w in used_words}
        if cleaned in normalized_used:
            return ValidationResult(
                is_valid=False,
                word=cleaned,
                starts_with=prog_first,
                ends_with=prog_last,
                is_library_related=True,
                is_duplicate=True,
                explanation=f"«{raw_word}» so'zi o'yinda avval ishlatilgan.",
                error_message=f"«{raw_word}» so'zi oldin ishlatilgan! Yangi so'z toping.",
            )

        # 4. Harf mosligini dasturiy tekshirish
        if expected_letter and not letters_match(expected_letter, prog_first):
            exp_disp = display_letter(expected_letter)
            act_disp = display_letter(prog_first)
            return ValidationResult(
                is_valid=False,
                word=cleaned,
                starts_with=prog_first,
                ends_with=prog_last,
                is_library_related=False,
                is_duplicate=False,
                explanation=f"Kutilgan harf: '{exp_disp}', kiritilgan so'z boshlanishi: '{act_disp}'",
                error_message=f"Noto'g'ri harf! So'z «{exp_disp}» harfidan boshlanishi shart (siz «{act_disp}» yozdingiz).",
            )

        # 5. Mahalliy bazada bormi?
        local_info = self.db.get_word_info(cleaned)

        # 6. Gemini AI orqali tekshiruv
        if is_api_configured():
            ai_res = self.ai.validate_word(cleaned, expected_letter, used_words)

            # Agar AI tizimida tarmoq yoki kalit xatosi bo'lsa
            if "error" in ai_res:
                # Agar mahalliy bazada bo'lsa, o'yin to'xtab qolmasligi uchun mahalliy bazaga tayanamiz
                if local_info:
                    return ValidationResult(
                        is_valid=True,
                        word=cleaned,
                        starts_with=prog_first,
                        ends_with=prog_last,
                        is_library_related=True,
                        is_duplicate=False,
                        explanation=local_info["explanation"],
                    )
                else:
                    return ValidationResult(
                        is_valid=False,
                        word=cleaned,
                        starts_with=prog_first,
                        ends_with=prog_last,
                        is_library_related=False,
                        is_duplicate=False,
                        explanation=ai_res.get("explanation", "AI tekshiruvida xatolik"),
                        error_message=ai_res.get("explanation", "AI bilan aloqa uzildi."),
                    )

            ai_is_valid = ai_res.get("is_valid", False)
            ai_is_lib = ai_res.get("is_library_related", False)
            ai_expl = ai_res.get("explanation", "")
            ai_starts = ai_res.get("starts_with", "")

            # Dastur va AI mosligi:
            # Agar AI bosh harfni boshqacha aniqlagan bo'lsa ham dasturiy tahlilga solishtiramiz
            if not letters_match(expected_letter, ai_starts) and not letters_match(expected_letter, prog_first):
                return ValidationResult(
                    is_valid=False,
                    word=cleaned,
                    starts_with=prog_first,
                    ends_with=prog_last,
                    is_library_related=ai_is_lib,
                    is_duplicate=False,
                    explanation="So'zning bosh harfi talab qilingan harfga mos kelmadi.",
                    error_message=f"So'z «{display_letter(expected_letter)}» bilan boshlanishi kerak!",
                )

            if not ai_is_valid:
                return ValidationResult(
                    is_valid=False,
                    word=cleaned,
                    starts_with=prog_first,
                    ends_with=prog_last,
                    is_library_related=False,
                    is_duplicate=False,
                    explanation=ai_expl or "Bunday so'z o'zbek tilida mavjud emas yoki imlosi noto'g'ri.",
                    error_message="Bu so'z o'zbek tilida topilmadi yoki xato yozilgan.",
                )

            if not ai_is_lib:
                return ValidationResult(
                    is_valid=False,
                    word=cleaned,
                    starts_with=prog_first,
                    ends_with=prog_last,
                    is_library_related=False,
                    is_duplicate=False,
                    explanation=ai_expl or "Bu so'z kutubxona, adabiyot yoki kitobxonlik sohasiga tegishli emas.",
                    error_message="Bu so'z kutubxona yoki kitob sohasiga tegishli emas!",
                )

            # Agar AI so'zni tasdiqlasa va u mahalliy bazada hali bo'lmasa, bazaga qo'shamiz
            if not local_info:
                self.db.add_verified_word(cleaned, "AI tasdiqlagan", ai_expl)

            return ValidationResult(
                is_valid=True,
                word=cleaned,
                starts_with=prog_first,
                ends_with=prog_last,
                is_library_related=True,
                is_duplicate=False,
                explanation=ai_expl or (local_info["explanation"] if local_info else "To'g'ri so'z!"),
            )

        else:
            # API sozlanmagan holatda: mahalliy tasdiqlangan bazadan tekshirish
            if local_info:
                return ValidationResult(
                    is_valid=True,
                    word=cleaned,
                    starts_with=prog_first,
                    ends_with=prog_last,
                    is_library_related=True,
                    is_duplicate=False,
                    explanation=local_info["explanation"],
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    word=cleaned,
                    starts_with=prog_first,
                    ends_with=prog_last,
                    is_library_related=False,
                    is_duplicate=False,
                    explanation="Gemini API kaliti ulanmagan va so'z mahalliy kutubxona lug'atida topilmadi.",
                    error_message="So'z tasdiqlangan bazada topilmadi. Gemini API kalitini kiritishingiz tavsiya etiladi.",
                )


# Yagona nusxa
validator = WordValidator()
