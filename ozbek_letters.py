"""
O'zbek tili harflari va imlosini tahlil qilish moduli.

O'zbek lotin alifbosining o'ziga xos xususiyatlari:
- Sh, Ch, O', G', Ng harflari va birikmalari
- Apostroflarning turli variantlarini (', ’, ‘, ʻ, `, ´) yagona standartga keltirish
- So'zning boshlang'ich va oxirgi harfini aniq belgilash
"""

import re
from typing import Tuple

# Turli apostrof belgilarini yagona standart '‘' ga almashtirish uchun regex
APOSTROPHE_VARIANTS = ["'", "’", "ʻ", "ʼ", "`", "´", "‘"]
APOSTROPHE_PATTERN = re.compile(r"['’ʻʼ`´‘]")
STANDARD_APOSTROPHE = "‘"

# Ikki belgili o'zbek harflari
COMPOUND_LETTERS_LOWER = ["sh", "ch", "o‘", "g‘", "ng"]


def normalize_apostrophes(text: str) -> str:
    """Barcha turli apostrof belgilarini yagona standart belgi '‘' ga aylantiradi."""
    if not text:
        return ""
    return APOSTROPHE_PATTERN.sub(STANDARD_APOSTROPHE, text)


def clean_word(word: str) -> str:
    """
    So'zni tozalash:
    - Boshidagi va oxiridagi bo'sh joylarni olib tashlash
    - Ortiqcha tinish belgilarini tozalash
    - Apostroflarni normallashtirish
    - Kichik harflarga o'tkazish
    """
    if not word:
        return ""
    # Bo'sh joylar va chekka belgilarni tozalash
    word = word.strip()
    word = normalize_apostrophes(word)
    # So'z ichidagi ko'p bo'shliqlarni bitta bo'shliqqa keltirish
    word = re.sub(r"\s+", " ", word)
    return word.lower()


def get_first_letter(word: str) -> str:
    """
    So'zning boshlang'ich harfini o'zbek imlosiga binoan aniqlaydi.
    Misollar:
      - 'shahar' -> 'sh'
      - 'chop' -> 'ch'
      - 'o‘quvchi' -> 'o‘'
      - 'g‘oya' -> 'g‘'
      - 'kitob' -> 'k'
    """
    normalized = clean_word(word)
    if not normalized:
        return ""

    # 2 belgili birikmalarni tekshirish (o‘, g‘, sh, ch)
    if len(normalized) >= 2:
        prefix_2 = normalized[:2]
        if prefix_2 in ["sh", "ch", "o‘", "g‘"]:
            return prefix_2

    return normalized[0]


def get_last_letter(word: str) -> str:
    """
    So'zning tugash harfini o'zbek imlosiga binoan aniqlaydi.
    Misollar:
      - 'kutubxona' -> 'a'
      - 'kitob' -> 'b'
      - 'quyosh' -> 'sh'
      - 'qiziqish' -> 'sh'
      - 'tinch' -> 'ch'
      - 'kulg‘i' emas, 'cho‘g‘' -> 'g‘'
      - 'tong' -> 'ng'
    """
    normalized = clean_word(word)
    if not normalized:
        return ""

    if len(normalized) >= 2:
        suffix_2 = normalized[-2:]
        if suffix_2 in ["sh", "ch", "o‘", "g‘", "ng"]:
            return suffix_2

    return normalized[-1]


def letters_match(previous_last_letter: str, current_first_letter: str) -> bool:
    """
    Oldingi so'zning oxirgi harfi bilan yangi so'zning birinchi harfi
    mos kelishini o'zbek tili qoidalari va o'yin adolatliligi asosida tekshiradi.

    Maxsus holat:
    O'zbek tilida 'ng' harfi bilan so'zlar deyarli boshlanmaydi.
    Shuning uchun so'z 'ng' bilan tugasa, o'yinchi 'ng' yoki 'g' harfi
    bilan boshlanadigan so'z aytishiga ruxsat beriladi.
    """
    p_last = clean_word(previous_last_letter)
    c_first = clean_word(current_first_letter)

    if not p_last or not c_first:
        return False

    # To'g'ridan-to'g'ri tenglik
    if p_last == c_first:
        return True

    # 'ng' istisnosi: 'tong' -> 'g' harfiga ham ruxsat
    if p_last == "ng" and c_first == "g":
        return True

    # Apostroflar tufayli vujudga kelishi mumkin bo'lgan farqlar
    p_clean = normalize_apostrophes(p_last)
    c_clean = normalize_apostrophes(c_first)
    if p_clean == c_clean:
        return True

    return False


def display_letter(letter: str) -> str:
    """Harfni chiroyli bosh harf ko'rinishida formatlash (masalan 'Sh', 'O‘', 'B')."""
    cleaned = clean_word(letter)
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned.upper()
    if cleaned in ["sh", "ch", "ng"]:
        return cleaned[0].upper() + cleaned[1]
    if cleaned in ["o‘", "g‘"]:
        return cleaned[0].upper() + STANDARD_APOSTROPHE
    return cleaned.capitalize()
