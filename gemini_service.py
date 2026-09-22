"""
Google Gemini API bilan integratsiya xizmati.

Rasmiy SDK yordamida:
- O'yinchi kiritgan so'zni tekshirish (haqiqiyligi, kutubxona sohasiga aloqasi, izohi).
- Kompyuter uchun berilgan harf bilan boshlanuvchi yangi so'z so'rash.
- Timeout, qayta urinish (retry) va tarmoq/kalit xatolarini o'zbek tilida boshqarish.
"""

import os
import json
import time
import socket
from typing import Dict, Any, Optional, Set

from config import GEMINI_API_KEY, GEMINI_MODEL, API_TIMEOUT_SECONDS, API_MAX_RETRIES
from ozbek_letters import clean_word, get_first_letter, get_last_letter


class GeminiService:
    """Google Gemini AI bilan aloqa qilish xizmati."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
        self.model_name = model_name or os.getenv("GEMINI_MODEL", GEMINI_MODEL)
        self._client = None
        self._init_sdk()

    def _init_sdk(self):
        """SDK mijozini initsializatsiya qilish."""
        if not self.api_key:
            return

        # 1. google-genai yangi rasmiy SDK ni tekshirish
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            self._sdk_type = "google-genai"
            return
        except Exception:
            pass

        # 2. google-generativeai kutubxonasi
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=self.api_key)
            self._client = legacy_genai.GenerativeModel(self.model_name)
            self._sdk_type = "google-generativeai"
            return
        except Exception as e:
            self._client = None
            self._sdk_type = None
            print(f"Gemini SDK yuklashda xatolik: {e}")

    def update_key(self, api_key: str):
        """API kalitini yangilash."""
        self.api_key = api_key.strip()
        self._init_sdk()

    def _execute_prompt_with_retry(self, prompt: str) -> str:
        """Promptni timeout va qayta urinishlar bilan bajarish."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY topilmadi! Iltimos, .env fayliga API kalitingizni kiriting.")

        if not self._client:
            self._init_sdk()
            if not self._client:
                raise RuntimeError("Gemini SDK mijozini ishga tushirib bo'lmadi.")

        last_error = None
        for attempt in range(1, API_MAX_RETRIES + 2):
            try:
                if self._sdk_type == "google-genai":
                    # Yangi rasmiy SDK
                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config={
                            "response_mime_type": "application/json",
                            "temperature": 0.2,
                        }
                    )
                    if hasattr(response, "text") and response.text:
                        return response.text
                    raise ValueError("Gemini bo'sh javob qaytardi.")

                elif self._sdk_type == "google-generativeai":
                    # Standart SDK
                    response = self._client.generate_content(
                        prompt,
                        generation_config={
                            "response_mime_type": "application/json",
                            "temperature": 0.2,
                        },
                    )
                    if hasattr(response, "text") and response.text:
                        return response.text
                    raise ValueError("Gemini bo'sh javob qaytardi.")

            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()

                # API kalit xatosi bo'lsa qayta urinishdan foyda yo'q
                if "api_key_invalid" in err_str or "invalid api key" in err_str or "403" in err_str:
                    raise PermissionError(
                        "Google Gemini API kaliti noto'g'ri yoki ruxsati cheklangan! "
                        "Iltimos, kalitni tekshiring."
                    ) from exc

                # Quota chegarasi
                if "resourceexhausted" in err_str or "429" in err_str or "quota" in err_str:
                    raise ResourceWarning(
                        "Gemini API so'rovlar limiti (quota) tugadi. Biroz kuting va qayta urinib ko'ring."
                    ) from exc

                # Internet aloqasi yoki timeout xatolari
                if isinstance(exc, (socket.timeout, TimeoutError, ConnectionError)) or "connection" in err_str:
                    if attempt <= API_MAX_RETRIES:
                        time.sleep(1.0 * attempt)
                        continue
                    raise ConnectionError(
                        "Internet aloqasi mavjud emas yoki Gemini serveriga ulanib bo'lmadi."
                    ) from exc

                if attempt <= API_MAX_RETRIES:
                    time.sleep(1.0)
                    continue

        raise last_error or RuntimeError("Gemini so'rovini bajarib bo'lmadi.")

    def validate_word(
        self,
        word: str,
        expected_letter: str,
        used_words: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        O'yinchi kiritgan so'zni Gemini AI orqali tekshirish.

        Kutilayotgan JSON formati:
        {
          "is_valid": true,
          "word": "kutubxona",
          "starts_with": "k",
          "ends_with": "a",
          "is_library_related": true,
          "is_duplicate": false,
          "explanation": "..."
        }
        """
        cleaned = clean_word(word)
        used_words_list = list(used_words) if used_words else []
        is_dup = cleaned in {clean_word(w) for w in used_words_list}

        prompt = f"""
Sen o'zbek tili va axborot-kutubxona sohasining oliy toifali mutaxassisisan.
Biz «So'nggi harf» intellektual o'yinini o'ynayapmiz.
Mavzu: Kutubxona, kitobxonlik, adabiyot, bibliografiya, nashriyot, poligrafiya, raqamli arxiv va axborot-kutubxona faoliyati.

Tekshiriladigan so'z: "{word}"
Kutilayotgan boshlang'ich harf: "{expected_letter}"
Oldin ishlatilgan so'zlar: {json.dumps(used_words_list, ensure_ascii=False)}

Vazifang:
1. Bu so'z o'zbek tilida haqiqatdan ham mavjudmi?
2. Bu so'z kutubxona, kitobxonlik, adabiyot, bibliografiya, nashriyot, elektron kutubxona yoki axborot sohasiga tegishlimi?
3. So'zning o'zbek lotin imlosidagi boshlanish va tugash harflarini aniqla (sh, ch, o', g', ng kabi harflarga e'tibor ber).
4. So'z oldin ishlatilganmi?
5. So'zning ma'nosi va kutubxona sohasiga aloqadorligi haqida 1-2 jumlada qisqa, tushunarli izoh ber.

Qat'iy ravishda FAQAT quyidagi JSON formatida javob qaytar:
{{
  "is_valid": true yoki false,
  "word": "{cleaned}",
  "starts_with": "boshlanish harfi",
  "ends_with": "tugash harfi",
  "is_library_related": true yoki false,
  "is_duplicate": {str(is_dup).lower()},
  "explanation": "So'zning o'zbek tilidagi qisqa izohi va sohaga bog'liqligi"
}}
"""
        try:
            raw_response = self._execute_prompt_with_retry(prompt)
            # JSON ni parse qilish
            # Ehtimoliy markdown codeblocklarni tozalash
            text = raw_response.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)

            # Majburiy maydonlarni tekshirish
            required_keys = ["is_valid", "word", "starts_with", "ends_with", "is_library_related", "explanation"]
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"AI javobida '{key}' maydoni yetishmaydi.")

            return data

        except json.JSONDecodeError:
            return {
                "is_valid": False,
                "word": cleaned,
                "starts_with": get_first_letter(cleaned),
                "ends_with": get_last_letter(cleaned),
                "is_library_related": False,
                "is_duplicate": is_dup,
                "explanation": "AI javobini JSON formatida o'qib bo'lmadi.",
                "error": "JSON_PARSE_ERROR"
            }
        except Exception as e:
            return {
                "is_valid": False,
                "word": cleaned,
                "starts_with": get_first_letter(cleaned),
                "ends_with": get_last_letter(cleaned),
                "is_library_related": False,
                "is_duplicate": is_dup,
                "explanation": str(e),
                "error": type(e).__name__
            }

    def suggest_word(
        self,
        starting_letter: str,
        used_words: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """
        Kompyuter navbati uchun Gemini AI dan berilgan harf bilan boshlanadigan
        kutubxona atamasini topib berishni so'rash.
        """
        cleaned_letter = clean_word(starting_letter)
        used_list = list(used_words) if used_words else []

        prompt = f"""
Sen kutubxona va kitobxonlik sohasi bo'yicha intellektual o'yin o'ynayotgan kompyutersan.
Senga navbat keldi.
Vazifang:
O'zbek lotin alifbosidagi "{cleaned_letter}" harfi bilan boshlanadigan,
kutubxona, bibliografiya, kitobxonlik, adabiyot, nashriyot, axborot texnologiyalari yoki arxiv sohasiga oid 
bitta aniq, to'g'ri so'z taklif qil.

Muhim talablar:
1. So'z QAT'IY ravishda "{cleaned_letter}" harfi bilan boshlansin.
2. Quyidagi oldin ishlatilgan so'zlarni aslo takrorlama:
{json.dumps(used_list, ensure_ascii=False)}
3. So'z birikma emas, bitta so'z bo'lsin.
4. O'zbek tilida to'g'ri yozilgan bo'lsin.

Javobni FAQAT quyidagi JSON formatida qaytar:
{{
  "success": true,
  "word": "taklif qilingan so'z",
  "category": "yo'nalishi (masalan Kutubxonachilik)",
  "starts_with": "{cleaned_letter}",
  "ends_with": "so'zning oxirgi harfi",
  "explanation": "so'zning qisqa mazmuni"
}}
"""
        try:
            raw_response = self._execute_prompt_with_retry(prompt)
            text = raw_response.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            if data.get("success") and "word" in data:
                # Olingan so'zni tozalash
                s_word = clean_word(data["word"])
                data["word"] = s_word
                data["starts_with"] = get_first_letter(s_word)
                data["ends_with"] = get_last_letter(s_word)
                return data

            return {"success": False, "error": "Mos so'z topilmadi"}

        except Exception as e:
            return {"success": False, "error": str(e)}


# Yagona nusxa
gemini_service = GeminiService()
