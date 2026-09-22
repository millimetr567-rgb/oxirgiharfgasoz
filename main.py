"""
«So‘nggi harf» intellektual o‘yini — Asosiy ishga tushirish fayli.

Ishga tushirish variantlari:
1. python main.py            -> PyQt6 zamonaviy grafik interfeysida ochiladi.
2. python main.py --cli      -> Buyruqlar satri (Terminal) rejimida ishlaydi.
"""

import sys
import time
import argparse
from typing import Optional

from config import TURN_TIME_LIMIT, is_api_configured
from ozbek_letters import display_letter
from game import LastLetterGame, GameStatus


def run_cli_mode():
    """Terminal (CLI) orqali o'ynash rejimi."""
    print("=" * 60)
    print("📚 «SO‘NGGI HARF» — KUTUBXONA INTELLEKTUAL O‘YINI")
    print("Mavzu: Kutubxonachilik, Kitobxonlik, Adabiyot va Nashriyot")
    print(f"Har bir javob uchun qat'iy {TURN_TIME_LIMIT} soniya vaqt beriladi!")
    print("=" * 60)

    if not is_api_configured():
        print("⚠️ DIQQAT: GEMINI_API_KEY .env faylida topilmadi.")
        print("O'yin mahalliy tasdiqlangan kutubxona lug'ati asosida ishlaydi.\n")

    game = LastLetterGame()
    start_info = game.start_game()

    print(f"🤖 Kompyuter boshladi: «{start_info['current_word'].upper()}»")
    print(f"ℹ️ Izoh: {start_info['current_explanation']}")
    print(f"👉 Sizning navbatingiz: «{start_info['expected_letter_display']}» harfidan boshlang!\n")

    while game.status == GameStatus.PLAYER_TURN:
        print(f"⏳ Sizda {TURN_TIME_LIMIT} soniya bor...")
        start_time = time.monotonic()

        try:
            player_word = input(f"[{start_info['expected_letter_display']}] So'zni kiriting: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nO'yin to'xtatildi.")
            break

        elapsed = time.monotonic() - start_time
        if elapsed > TURN_TIME_LIMIT:
            print(f"\n❌ Vaqt tugadi! ({elapsed:.1f} soniya o'tdi). 7 soniya ichida yozishingiz kerak edi.")
            game.handle_player_timeout()
            break

        print("🔍 Tekshirilmoqda...")
        success, val_result = game.process_player_word(player_word)

        if not success:
            print(f"\n❌ Noto'g'ri javob: {val_result.error_message or val_result.explanation}")
            break

        print(f"✅ To'g'ri! {val_result.explanation}")
        print(f"⭐ Joriy ball: {game.score} | Ketma-ketlik: {game.streak} 🔥\n")

        # Kompyuter navbati
        print("🤖 Kompyuter so'z izlamoqda...")
        comp_res = game.play_computer_turn()

        if not comp_res.get("success"):
            print(f"\n🏆 {comp_res.get('reason')}")
            break

        print(f"🤖 Kompyuter aytdi: «{comp_res['word'].upper()}»")
        print(f"ℹ️ Izoh: {comp_res['explanation']}")
        print(f"👉 Endi siz «{comp_res['expected_letter_display']}» harfi bilan boshlanuvchi so'z aytasiz.\n")

    summary = game.get_summary()
    print("\n" + "=" * 60)
    print("🏁 O‘YIN YAKUNLANDI!")
    print(f"⭐ Yakuniy ball: {summary['score']}")
    print(f"🔥 Eng uzun ketma-ketlik: {summary['streak']}")
    print(f"📚 Ishlatilgan so'zlar: {summary['total_words']} ta")
    if summary["reason"]:
        print(f"📌 Sabab: {summary['reason']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="«So‘nggi harf» — Kutubxona intellektual o‘yini")
    parser.add_argument("--cli", action="store_true", help="O'yinni buyruqlar satrida (terminalda) ishga tushirish")
    args = parser.parse_args()

    if args.cli:
        run_cli_mode()
    else:
        try:
            from gui import run_gui
            run_gui()
        except ImportError as e:
            print(f"PyQt6 kutubxonasi yuklanmadi ({e}). Terminal rejimida boshlanmoqda...")
            run_cli_mode()


if __name__ == "__main__":
    main()
