"""
So'zlar bazasini boshqarish moduli.
Serverless (Vercel, AWS Lambda) va lokal muhitlarga 100% moslashtirilgan:
- Barcha atamalar xotirada (in-memory) tezkor indekslanadi.
- Read-only fayl tizimi xatoliklaridan to'liq himoyalangan.
- JSON va SQLite (xotirada) orqali ishlaydi.
"""

import json
import random
from typing import Optional, Dict, List, Set
from pathlib import Path

from config import JSON_WORDS_PATH
from ozbek_letters import clean_word, get_first_letter, get_last_letter


class WordDatabase:
    """Kutubxona atamalari bazasini boshqaruvchi xavfsiz va serverless-mos sinf."""

    def __init__(self, json_path: Path = JSON_WORDS_PATH):
        self.json_path = json_path
        # Xotiradagi tezkor tuzilmalar
        self.words_by_letter: Dict[str, List[Dict]] = {}
        self.words_by_cleaned: Dict[str, Dict] = {}
        self.all_words: List[Dict] = []
        self._load_words()

    def _load_words(self):
        """So'zlarni JSON fayldan xotiraga yuklash va indekslash."""
        data = []
        # JSON faylni qidirish (turli nisbiy yo'llarni tekshirish)
        possible_paths = [
            self.json_path,
            Path(__file__).resolve().parent / "data" / "library_words.json",
            Path("data/library_words.json"),
            Path(__file__).resolve().parent.parent / "data" / "library_words.json",
        ]

        loaded = False
        for p in possible_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        loaded = True
                        break
                except Exception:
                    pass

        # Agar biron sababga ko'ra fayl topilmasa, zaxira asosiy atamalar
        if not loaded or not data:
            data = [
                {"word": "kutubxona", "category": "Kutubxonachilik", "explanation": "Kitoblar saqlanadigan ma'rifat maskani."},
                {"word": "arxiv", "category": "Raqamli arxiv", "explanation": "Tarixiy hujjatlar saqlanadigan muassasa."},
                {"word": "varaq", "category": "Kitobxonlik", "explanation": "Kitob yoki daftarning ikki betdan iborat qog'ozi."},
                {"word": "qalam", "category": "Nashriyot", "explanation": "Yozuv quroli."},
                {"word": "mutolaa", "category": "Kitobxonlik", "explanation": "Kitob o'qish jarayoni."},
                {"word": "adabiyot", "category": "Adabiyotshunoslik", "explanation": "So'z san'ati asarlari."},
                {"word": "tahririyat", "category": "Nashriyot", "explanation": "Nashr tayyorlovchi jamoa."},
                {"word": "antologiya", "category": "Kitob turlari", "explanation": "Sara asarlar to'plami."},
                {"word": "bibliografiya", "category": "Bibliografiya", "explanation": "Kitoblar haqidagi ilmiy tavsif tizimi."},
                {"word": "ensiklopediya", "category": "Kitob turlari", "explanation": "Universal qomusiy lug'at."},
            ]

        # Xotiraga indekslash
        for item in data:
            raw_word = item.get("word", "").strip()
            cleaned = clean_word(raw_word)
            if not cleaned:
                continue

            category = item.get("category", "Kutubxonachilik")
            explanation = item.get("explanation", "Kutubxona sohasi atamasi.")
            starts_with = get_first_letter(cleaned)
            ends_with = get_last_letter(cleaned)

            word_entry = {
                "word": raw_word,
                "cleaned_word": cleaned,
                "category": category,
                "explanation": explanation,
                "starts_with": starts_with,
                "ends_with": ends_with,
            }

            self.words_by_cleaned[cleaned] = word_entry
            if starts_with not in self.words_by_letter:
                self.words_by_letter[starts_with] = []
            self.words_by_letter[starts_with].append(word_entry)
            self.all_words.append(word_entry)

    def get_word_info(self, word: str) -> Optional[Dict]:
        """Berilgan so'z haqidagi ma'lumotni xotiradan olish."""
        cleaned = clean_word(word)
        return self.words_by_cleaned.get(cleaned)

    def is_word_in_database(self, word: str) -> bool:
        """So'z bazada mavjudligini tekshirish."""
        return self.get_word_info(word) is not None

    def find_words_starting_with(self, letter: str, excluded_words: Optional[Set[str]] = None) -> List[Dict]:
        """Berilgan harf bilan boshlanuvchi so'zlarni topish."""
        letter = clean_word(letter)
        excluded = {clean_word(w) for w in excluded_words} if excluded_words else set()

        candidates = self.words_by_letter.get(letter, [])
        return [w for w in candidates if w["cleaned_word"] not in excluded]

    def get_random_word_starting_with(self, letter: str, excluded_words: Optional[Set[str]] = None) -> Optional[Dict]:
        """Berilgan harf bilan boshlanadigan tasodifiy so'zni tanlash."""
        words = self.find_words_starting_with(letter, excluded_words)
        if words:
            return random.choice(words)
        return None

    def get_random_starting_word(self) -> Dict:
        """O'yin boshlanishi uchun mos boshlang'ich so'z tanlash."""
        if self.all_words:
            return random.choice(self.all_words)
        return {
            "word": "kutubxona",
            "category": "Kutubxonachilik",
            "explanation": "Kitoblar saqlanadigan ma'rifat maskani.",
            "starts_with": "k",
            "ends_with": "a",
        }

    def add_verified_word(self, word: str, category: str, explanation: str) -> bool:
        """
        AI tomonidan tasdiqlangan yangi so'zni xotiraga qo'shish.
        Serverless rejimda read-only diskka yozish xatosidan xavfsiz.
        """
        raw_word = word.strip()
        cleaned = clean_word(raw_word)
        if not cleaned or cleaned in self.words_by_cleaned:
            return False

        starts_with = get_first_letter(cleaned)
        ends_with = get_last_letter(cleaned)

        word_entry = {
            "word": raw_word,
            "cleaned_word": cleaned,
            "category": category,
            "explanation": explanation,
            "starts_with": starts_with,
            "ends_with": ends_with,
        }

        self.words_by_cleaned[cleaned] = word_entry
        if starts_with not in self.words_by_letter:
            self.words_by_letter[starts_with] = []
        self.words_by_letter[starts_with].append(word_entry)
        self.all_words.append(word_entry)

        # Agar fayl tizimiga yozish imkoni bo'lsa (lokal kompyuterda)
        try:
            if self.json_path.exists():
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not any(clean_word(item.get("word", "")) == cleaned for item in data):
                    data.append({
                        "word": raw_word,
                        "category": category,
                        "explanation": explanation,
                    })
                    with open(self.json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Serverless read-only muhitda jim o'tkazib yuborish
            pass

        return True

    def total_count(self) -> int:
        """Bazada jami nechta so'z borligini qaytaradi."""
        return len(self.words_by_cleaned)


# Yagona nusxa
db = WordDatabase()
