"""
«So‘nggi harf» o‘yini uchun to‘liq avtomatlashtirilgan testlar to‘plami.
"""

import unittest
import time
from ozbek_letters import (
    clean_word,
    get_first_letter,
    get_last_letter,
    letters_match,
    normalize_apostrophes,
    display_letter,
)
from word_database import WordDatabase
from word_validator import WordValidator, ValidationResult
from game import LastLetterGame, GameStatus
from timer import GameTimer


class TestOzbekLetters(unittest.TestCase):
    """O'zbek alifbosi va harflar tahlili testlari."""

    def test_first_letters(self):
        self.assertEqual(get_first_letter("kitob"), "k")
        self.assertEqual(get_first_letter("kutubxona"), "k")
        self.assertEqual(get_first_letter("shahar"), "sh")
        self.assertEqual(get_first_letter("chop"), "ch")
        self.assertEqual(get_first_letter("o‘quvchi"), "o‘")
        self.assertEqual(get_first_letter("o'quvchi"), "o‘")
        self.assertEqual(get_first_letter("oʻquvchi"), "o‘")
        self.assertEqual(get_first_letter("g‘oya"), "g‘")
        self.assertEqual(get_first_letter("g'azal"), "g‘")

    def test_last_letters(self):
        self.assertEqual(get_last_letter("kitob"), "b")
        self.assertEqual(get_last_letter("kutubxona"), "a")
        self.assertEqual(get_last_letter("quyosh"), "sh")
        self.assertEqual(get_last_letter("tinch"), "ch")
        self.assertEqual(get_last_letter("tong"), "ng")

    def test_letters_match(self):
        self.assertTrue(letters_match("b", "b"))
        self.assertTrue(letters_match("B", "b"))
        self.assertTrue(letters_match("sh", "sh"))
        self.assertTrue(letters_match("o‘", "o'"))
        # 'ng' bilan tugasa 'g' bilan ham boshlanishiga ruxsat berish:
        self.assertTrue(letters_match("ng", "g"))
        self.assertTrue(letters_match("ng", "ng"))
        # Mos kelmaslik
        self.assertFalse(letters_match("a", "b"))
        self.assertFalse(letters_match("sh", "s"))
        self.assertFalse(letters_match("ch", "c"))

    def test_apostrophe_normalization(self):
        w1 = clean_word("o'quvchi")
        w2 = clean_word("o‘quvchi")
        w3 = clean_word("oʻquvchi")
        self.assertEqual(w1, w2)
        self.assertEqual(w2, w3)


class TestWordDatabase(unittest.TestCase):
    """So'zlar bazasi testlari."""

    def setUp(self):
        self.db = WordDatabase()

    def test_database_populated(self):
        count = self.db.total_count()
        self.assertGreaterEqual(count, 100, "Bazada kamida 100 ta kutubxona so'zi bo'lishi kerak")

    def test_find_words(self):
        words = self.db.find_words_starting_with("k")
        self.assertGreater(len(words), 0)
        for w in words:
            self.assertEqual(w["starts_with"], "k")

    def test_duplicate_filtering(self):
        excluded = {"kutubxona", "kitob"}
        words = self.db.find_words_starting_with("k", excluded_words=excluded)
        word_names = {clean_word(w["word"]) for w in words}
        self.assertNotIn("kutubxona", word_names)
        self.assertNotIn("kitob", word_names)

    def test_random_starting_word(self):
        word_info = self.db.get_random_starting_word()
        self.assertIn("word", word_info)
        self.assertIn("starts_with", word_info)
        self.assertIn("ends_with", word_info)


class TestWordValidator(unittest.TestCase):
    """Validator testlari."""

    def setUp(self):
        self.validator = WordValidator()

    def test_empty_word(self):
        res = self.validator.validate("", "a", set())
        self.assertFalse(res.is_valid)

    def test_duplicate_word(self):
        res = self.validator.validate("kitob", "k", {"kitob", "kutubxona"})
        self.assertFalse(res.is_valid)
        self.assertTrue(res.is_duplicate)

    def test_wrong_letter(self):
        res = self.validator.validate("shahar", "k", set())
        self.assertFalse(res.is_valid)

    def test_valid_local_word(self):
        res = self.validator.validate("kutubxona", "k", set())
        self.assertTrue(res.is_valid)
        self.assertEqual(res.starts_with, "k")
        self.assertEqual(res.ends_with, "a")


class TestGameLogic(unittest.TestCase):
    """O'yin qoidalari va oqimi testlari."""

    def setUp(self):
        self.game = LastLetterGame()

    def test_game_start(self):
        data = self.game.start_game()
        self.assertEqual(self.game.status, GameStatus.PLAYER_TURN)
        self.assertTrue(len(self.game.current_word) > 0)
        self.assertTrue(len(self.game.expected_letter) > 0)
        self.assertIn(clean_word(self.game.current_word), self.game.used_words)

    def test_player_correct_turn(self):
        self.game.start_game()
        # Majburiy ravishda expected_letter ni 'k' ga moslaymiz
        self.game.expected_letter = "k"
        success, res = self.game.process_player_word("kutubxona")
        self.assertTrue(success)
        self.assertEqual(res.word, "kutubxona")
        self.assertGreater(self.game.score, 0)
        self.assertEqual(self.game.streak, 1)
        self.assertEqual(self.game.expected_letter, "a")

    def test_computer_turn(self):
        self.game.start_game()
        self.game.expected_letter = "k"
        self.game.process_player_word("kutubxona")
        # Kompyuter 'a' harfiga so'z aytishi kerak
        comp_res = self.game.play_computer_turn()
        self.assertTrue(comp_res["success"])
        self.assertEqual(self.game.status, GameStatus.PLAYER_TURN)
        self.assertIn(clean_word(comp_res["word"]), self.game.used_words)

    def test_player_timeout(self):
        self.game.start_game()
        data = self.game.handle_player_timeout()
        self.assertEqual(self.game.status, GameStatus.GAME_OVER)
        self.assertIn("Vaqt", data["reason"])


class TestGameTimer(unittest.TestCase):
    """7 soniyalik taymer mexanizmi testi."""

    def test_timer_runs_and_stops(self):
        ticks = []
        timer = GameTimer(duration=2)
        timer.start(on_tick=lambda s: ticks.append(s))
        time.sleep(0.5)
        self.assertTrue(timer.is_running)
        timer.stop()
        self.assertFalse(timer.is_running)
        self.assertGreater(len(ticks), 0)


if __name__ == "__main__":
    unittest.main()
