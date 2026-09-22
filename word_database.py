"""
So'zlar bazasini boshqarish moduli.
SQLite va JSON formatlarini qo'llab-quvvatlaydi, so'zlarni indekslaydi
va kompyuter uchun mos so'zlarni qidirishni ta'minlaydi.
"""

import json
import sqlite3
import random
from typing import Optional, Dict, List, Set
from pathlib import Path

from config import DB_PATH, JSON_WORDS_PATH
from ozbek_letters import clean_word, get_first_letter, get_last_letter


class WordDatabase:
    """Kutubxona atamalari bazasini boshqaruvchi sinf."""

    def __init__(self, db_path: Path = DB_PATH, json_path: Path = JSON_WORDS_PATH):
        self.db_path = db_path
        self.json_path = json_path
        self._init_db()
        self._sync_initial_words()

    def _get_connection(self) -> sqlite3.Connection:
        """SQLite ulanishini yaratish (Serverless read-only muhitlar uchun fallback bilan)."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            # Sinab ko'rish
            conn.execute("SELECT 1")
            return conn
        except Exception:
            # Agar fayl tizimi read-only bo'lsa (masalan Vercel)
            import tempfile
            temp_db = Path(tempfile.gettempdir()) / "library_words_temp.db"
            conn = sqlite3.connect(str(temp_db))
            conn.row_factory = sqlite3.Row
            return conn

    def _init_db(self):
        """Jadvallarni yaratish va indekslarni sozlash."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    cleaned_word TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    starts_with TEXT NOT NULL,
                    ends_with TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_starts_with ON words(starts_with);"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_cleaned_word ON words(cleaned_word);"
            )
            conn.commit()

    def _sync_initial_words(self):
        """Agar SQLite bo'sh bo'lsa, JSON fayldagi so'zlarni yuklash."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM words")
            count = cursor.fetchone()[0]

            if count == 0 and self.json_path.exists():
                try:
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        words_data = json.load(f)

                    for item in words_data:
                        raw_word = item.get("word", "").strip()
                        cleaned = clean_word(raw_word)
                        if not cleaned:
                            continue

                        category = item.get("category", "Kutubxonachilik")
                        explanation = item.get("explanation", "")
                        starts_with = get_first_letter(cleaned)
                        ends_with = get_last_letter(cleaned)

                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO words 
                            (word, cleaned_word, category, explanation, starts_with, ends_with, is_verified)
                            VALUES (?, ?, ?, ?, ?, ?, 1)
                            """,
                            (raw_word, cleaned, category, explanation, starts_with, ends_with),
                        )
                    conn.commit()
                except Exception as e:
                    print(f"Boshlang'ich so'zlarni yuklashda xatolik: {e}")

    def get_word_info(self, word: str) -> Optional[Dict]:
        """Berilgan so'z haqidagi ma'lumotni olish."""
        cleaned = clean_word(word)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT word, category, explanation, starts_with, ends_with FROM words WHERE cleaned_word = ?",
                (cleaned,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def is_word_in_database(self, word: str) -> bool:
        """So'z bazada mavjudligini tekshirish."""
        return self.get_word_info(word) is not None

    def find_words_starting_with(self, letter: str, excluded_words: Optional[Set[str]] = None) -> List[Dict]:
        """Berilgan harf bilan boshlanuvchi so'zlarni topish."""
        letter = clean_word(letter)
        excluded = {clean_word(w) for w in excluded_words} if excluded_words else set()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT word, category, explanation, starts_with, ends_with FROM words WHERE starts_with = ?",
                (letter,),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                c_word = clean_word(row["word"])
                if c_word not in excluded:
                    results.append(dict(row))
            return results

    def get_random_word_starting_with(self, letter: str, excluded_words: Optional[Set[str]] = None) -> Optional[Dict]:
        """Berilgan harf bilan boshlanadigan tasodifiy so'zni tanlash."""
        words = self.find_words_starting_with(letter, excluded_words)
        if words:
            return random.choice(words)
        return None

    def get_random_starting_word(self) -> Dict:
        """O'yin boshlanishi uchun mos boshlang'ich so'z tanlash."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Boshlang'ich so'z uchun qulay (a, b, k, m, s, t bilan boshlanadigan) so'zlarni afzal ko'rish
            cursor.execute(
                "SELECT word, category, explanation, starts_with, ends_with FROM words ORDER BY RANDOM() LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {
                "word": "kutubxona",
                "category": "Kutubxonachilik",
                "explanation": "Kitoblar saqlanadigan ma'rifat maskani.",
                "starts_with": "k",
                "ends_with": "a",
            }

    def add_verified_word(self, word: str, category: str, explanation: str) -> bool:
        """
        AI tomonidan tasdiqlangan yangi so'zni bazaga qo'shish.
        So'z avval mavjud bo'lmasa kiritiladi va JSON fayl ham yangilanadi.
        """
        raw_word = word.strip()
        cleaned = clean_word(raw_word)
        if not cleaned:
            return False

        starts_with = get_first_letter(cleaned)
        ends_with = get_last_letter(cleaned)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO words 
                    (word, cleaned_word, category, explanation, starts_with, ends_with, is_verified)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (raw_word, cleaned, category, explanation, starts_with, ends_with),
                )
                conn.commit()

            # Shuningdek JSON faylga ham qo'shib qo'yish (agar mavjud bo'lsa)
            if self.json_path.exists():
                try:
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # Takror emasligini tekshirish
                    if not any(clean_word(item.get("word", "")) == cleaned for item in data):
                        data.append({
                            "word": raw_word,
                            "category": category,
                            "explanation": explanation,
                        })
                        with open(self.json_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            return True
        except Exception as e:
            print(f"So'z qo'shishda xatolik: {e}")
            return False

    def total_count(self) -> int:
        """Bazada jami nechta so'z borligini qaytaradi."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM words")
            return cursor.fetchone()[0]


# Yagona nusxa (singleton sifatida)
db = WordDatabase()
