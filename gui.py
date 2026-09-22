"""
«So'nggi harf» intellektual o'yini uchun zamonaviy PyQt6 grafik interfeysi.

Xususiyatlari:
- Chiroyli zamonaviy dizayn (kutubxona uslubidagi quyuq zamonaviy tema)
- Katta 7 soniyalik rangli taymer (yashil -> to'q sariq -> qizil)
- Oxirgi harfi ajratib ko'rsatilgan so'z kartochkasi
- AI tekshiruvi davomida interfeys qotib qolmasligi uchun QThread oqimlari
- Ishlatilgan so'zlar ro'yxati va real vaqt hisobi
- To'liq o'zbek tilidagi qulay foydalanuvchi tajribasi
"""

import sys
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QDialog,
    QInputDialog,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from config import TURN_TIME_LIMIT, is_api_configured, update_api_key
from ozbek_letters import display_letter, get_last_letter
from game import LastLetterGame, GameStatus
from word_validator import ValidationResult


class AIWorkerThread(QThread):
    """AI va so'zlarni tekshirishni orqa fonda bajaruvchi oqim (UI qotib qolmasligi uchun)."""
    validation_done = pyqtSignal(bool, object)  # success, ValidationResult
    computer_turn_done = pyqtSignal(dict)  # computer result dict

    def __init__(self, game: LastLetterGame, mode: str, word_to_check: str = ""):
        super().__init__()
        self.game = game
        self.mode = mode
        self.word_to_check = word_to_check

    def run(self):
        if self.mode == "validate_player":
            success, result = self.game.process_player_word(self.word_to_check)
            self.validation_done.emit(success, result)
        elif self.mode == "computer_turn":
            comp_res = self.game.play_computer_turn()
            self.computer_turn_done.emit(comp_res)


class LastLetterGameWindow(QMainWindow):
    """Asosiy o'yin oynasi."""

    def __init__(self):
        super().__init__()
        self.game = LastLetterGame()
        self.time_left = TURN_TIME_LIMIT
        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # Har 1 soniyada
        self.timer.timeout.connect(self._on_timer_tick)

        self.worker_thread: Optional[AIWorkerThread] = None

        self.init_ui()
        self._update_api_status_badge()

    def init_ui(self):
        """Foydalanuvchi interfeysini qurish."""
        self.setWindowTitle("«So‘nggi harf» — Kutubxona intellektual o‘yini (Gemini AI)")
        self.resize(1000, 750)
        self.setMinimumSize(850, 650)

        # Markaziy vidjet va asosiy stil
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # CSS Stilizatsiya
        self.setStyleSheet("""
            QWidget#centralWidget {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame.card {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
            }
            QLabel {
                color: #f8fafc;
            }
            QPushButton.primary-btn {
                background-color: #3b82f6;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 15px;
                font-weight: bold;
                border: none;
            }
            QPushButton.primary-btn:hover {
                background-color: #2563eb;
            }
            QPushButton.primary-btn:disabled {
                background-color: #475569;
                color: #94a3b8;
            }
            QPushButton.secondary-btn {
                background-color: #334155;
                color: #f8fafc;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                border: 1px solid #475569;
            }
            QPushButton.secondary-btn:hover {
                background-color: #475569;
            }
            QLineEdit {
                background-color: #0f172a;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                color: #f8fafc;
                padding: 10px 15px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #60a5fa;
            }
            QListWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #e2e8f0;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #1e293b;
            }
        """)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Chap qism: Asosiy o'yin maydoni (70%)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)

        # 1. Sarlavha paneli
        header_frame = QFrame()
        header_frame.setProperty("class", "card")
        header_layout = QHBoxLayout(header_frame)

        title_box = QVBoxLayout()
        self.title_lbl = QLabel("📚 «So‘nggi harf» Intellektual O‘yini")
        self.title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        subtitle_lbl = QLabel("Kutubxona, bibliografiya va kitobxonlik olamiga sayohat")
        subtitle_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(self.title_lbl)
        title_box.addWidget(subtitle_lbl)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # API Kalit statusi va sozlash tugmasi
        self.api_badge = QLabel("API Holati")
        self.api_badge.setStyleSheet("padding: 4px 8px; border-radius: 4px; font-size: 12px;")
        self.api_btn = QPushButton("🔑 API Kaliti")
        self.api_btn.setProperty("class", "secondary-btn")
        self.api_btn.clicked.connect(self._prompt_api_key)

        header_layout.addWidget(self.api_badge)
        header_layout.addWidget(self.api_btn)
        left_layout.addWidget(header_frame)

        # 2. Hisob va Taymer paneli
        stats_frame = QFrame()
        stats_frame.setProperty("class", "card")
        stats_layout = QHBoxLayout(stats_frame)

        # Hisob
        score_box = QVBoxLayout()
        score_title = QLabel("JORIY HISOB")
        score_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.score_val = QLabel("0")
        self.score_val.setStyleSheet("color: #38bdf8; font-size: 26px; font-weight: bold;")
        score_box.addWidget(score_title)
        score_box.addWidget(self.score_val)
        stats_layout.addLayout(score_box)

        # Ketma-ketlik (Streak)
        streak_box = QVBoxLayout()
        streak_title = QLabel("KETMA-KETLIK")
        streak_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.streak_val = QLabel("0 🔥")
        self.streak_val.setStyleSheet("color: #f59e0b; font-size: 22px; font-weight: bold;")
        streak_box.addWidget(streak_title)
        streak_box.addWidget(self.streak_val)
        stats_layout.addLayout(streak_box)

        stats_layout.addStretch()

        # 7 Soniyalik Katta Taymer
        timer_box = QVBoxLayout()
        timer_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_title = QLabel("QOLGAN VAQT")
        timer_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        self.timer_val = QLabel("7s")
        self.timer_val.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.timer_val.setStyleSheet("color: #10b981; font-weight: 800;")
        timer_box.addWidget(timer_title, alignment=Qt.AlignmentFlag.AlignCenter)
        timer_box.addWidget(self.timer_val, alignment=Qt.AlignmentFlag.AlignCenter)
        stats_layout.addLayout(timer_box)

        left_layout.addWidget(stats_frame)

        # 3. Markaziy So'z Kartochkasi (Kompyuter aytgan so'z)
        self.word_card = QFrame()
        self.word_card.setProperty("class", "card")
        word_card_layout = QVBoxLayout(self.word_card)
        word_card_layout.setContentsMargins(20, 20, 20, 20)

        word_card_label = QLabel("KOMPYUTER AYTGAN SO‘Z:")
        word_card_label.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold;")
        word_card_layout.addWidget(word_card_label)

        self.word_display = QLabel("O‘yinni boshlang")
        self.word_display.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.word_display.setTextFormat(Qt.TextFormat.RichText)
        self.word_display.setStyleSheet("color: #f8fafc; padding: 5px 0;")
        word_card_layout.addWidget(self.word_display)

        # So'z izohi
        self.word_meaning = QLabel("O'yinni boshlash tugmasini bosing.")
        self.word_meaning.setWordWrap(True)
        self.word_meaning.setStyleSheet("color: #cbd5e1; font-size: 13px; font-style: italic;")
        word_card_layout.addWidget(self.word_meaning)

        # Kutilayotgan harf ko'rsatkichi
        self.target_letter_lbl = QLabel("")
        self.target_letter_lbl.setStyleSheet("color: #fbbf24; font-size: 15px; font-weight: bold; margin-top: 5px;")
        word_card_layout.addWidget(self.target_letter_lbl)

        left_layout.addWidget(self.word_card)

        # 4. Javob Kiritish Maydoni
        input_frame = QFrame()
        input_frame.setProperty("class", "card")
        input_layout = QVBoxLayout(input_frame)

        input_prompt = QLabel("Sizning javobingiz (oxirgi harf bilan boshlanuvchi so'z):")
        input_prompt.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold;")
        input_layout.addWidget(input_prompt)

        input_action_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Masalan: kutubxona...")
        self.word_input.setEnabled(False)
        self.word_input.returnPressed.connect(self._on_submit_word)
        input_action_layout.addWidget(self.word_input)

        self.submit_btn = QPushButton("🚀 Yuborish")
        self.submit_btn.setProperty("class", "primary-btn")
        self.submit_btn.setEnabled(False)
        self.submit_btn.clicked.connect(self._on_submit_word)
        input_action_layout.addWidget(self.submit_btn)

        input_layout.addLayout(input_action_layout)
        left_layout.addWidget(input_frame)

        # 5. AI Tekshiruv Natijasi va Xabarlar
        self.status_card = QFrame()
        self.status_card.setProperty("class", "card")
        status_card_layout = QVBoxLayout(self.status_card)
        self.status_msg = QLabel("Tayyor. O'yinni boshlash uchun pastdagi tugmani bosing.")
        self.status_msg.setWordWrap(True)
        self.status_msg.setStyleSheet("color: #94a3b8; font-size: 14px;")
        status_card_layout.addWidget(self.status_msg)
        left_layout.addWidget(self.status_card)

        # 6. Boshqaruv Tugmalari
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("🎮 O‘yinni boshlash")
        self.start_btn.setProperty("class", "primary-btn")
        self.start_btn.setStyleSheet("background-color: #10b981; font-size: 16px; padding: 12px 24px;")
        self.start_btn.clicked.connect(self._start_new_game)
        control_layout.addWidget(self.start_btn)

        self.restart_btn = QPushButton("🔄 Qayta o‘ynash")
        self.restart_btn.setProperty("class", "secondary-btn")
        self.restart_btn.setVisible(False)
        self.restart_btn.clicked.connect(self._start_new_game)
        control_layout.addWidget(self.restart_btn)

        left_layout.addLayout(control_layout)
        main_layout.addLayout(left_layout, 65)

        # O'ng qism: Ishlatilgan so'zlar ro'yxati (35%)
        right_frame = QFrame()
        right_frame.setProperty("class", "card")
        right_layout = QVBoxLayout(right_frame)

        history_title = QLabel("📜 Ishlatilgan so‘zlar tarixi")
        history_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        right_layout.addWidget(history_title)

        self.history_list = QListWidget()
        right_layout.addWidget(self.history_list)

        words_count_layout = QHBoxLayout()
        self.total_words_lbl = QLabel("Jami so'zlar: 0")
        self.total_words_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        words_count_layout.addWidget(self.total_words_lbl)
        words_count_layout.addStretch()

        right_layout.addLayout(words_count_layout)
        main_layout.addWidget(right_frame, 35)

    def _update_api_status_badge(self):
        """API holatini yangilash."""
        if is_api_configured():
            self.api_badge.setText("✅ Gemini AI Ulandi")
            self.api_badge.setStyleSheet("background-color: #065f46; color: #34d399; padding: 4px 8px; border-radius: 4px; font-size: 12px;")
        else:
            self.api_badge.setText("⚠️ Gemini Kalit yo'q (Lokal baza)")
            self.api_badge.setStyleSheet("background-color: #78350f; color: #fcd34d; padding: 4px 8px; border-radius: 4px; font-size: 12px;")

    def _prompt_api_key(self):
        """Foydalanuvchidan API kalitini kiritishni so'rash."""
        key, ok = QInputDialog.getText(
            self,
            "Gemini API Kaliti",
            "Google Gemini API kalitingizni kiriting:\n(Kalit xavfsiz holda faqat .env faylida saqlanadi)",
            text="",
        )
        if ok and key.strip():
            update_api_key(key.strip())
            self.game.ai.update_key(key.strip())
            self._update_api_status_badge()
            QMessageBox.information(
                self,
                "Muvaffaqiyatli",
                "Gemini API kaliti muvaffaqiyatli saqlandi va faollashtirildi!",
            )

    def _start_new_game(self):
        """O'yinni noldan boshlash."""
        self.start_btn.setVisible(False)
        self.restart_btn.setVisible(True)
        self.word_input.setEnabled(True)
        self.submit_btn.setEnabled(True)
        self.word_input.clear()
        self.history_list.clear()

        start_data = self.game.start_game()
        self._display_computer_word(
            start_data["current_word"],
            start_data["current_explanation"],
            start_data["expected_letter"],
        )

        self._add_to_history(
            author="Kompyuter",
            word=start_data["current_word"],
            explanation=start_data["current_explanation"],
        )

        self._update_score_ui()
        self._start_player_turn()

    def _display_computer_word(self, word: str, explanation: str, last_letter: str):
        """Kompyuter so'zini oxirgi harfini yorqin ajratib ko'rsatish."""
        # Oxirgi harfni ajratish
        if len(word) >= len(last_letter) and word.lower().endswith(last_letter.lower()):
            prefix = word[:-len(last_letter)]
            highlight = word[-len(last_letter):]
            formatted_word = f"{prefix}<span style='color: #f59e0b; background-color: #451a03; border-radius: 4px; padding: 2px 6px;'>{highlight}</span>"
        else:
            formatted_word = word

        self.word_display.setText(formatted_word)
        self.word_meaning.setText(explanation or "Izoh mavjud emas.")
        self.target_letter_lbl.setText(f"👉 Sizning so'zingiz «{display_letter(last_letter)}» harfidan boshlanishi shart!")

    def _start_player_turn(self):
        """O'yinchi uchun 7 soniyalik navbatni boshlash."""
        self.word_input.setEnabled(True)
        self.submit_btn.setEnabled(True)
        self.word_input.clear()
        self.word_input.setFocus()

        self.time_left = TURN_TIME_LIMIT
        self._update_timer_display(self.time_left)
        self.timer.start()

        self.status_msg.setText("⏳ Navbat sizda! 7 soniya ichida so'zni yozing va Yuborish tugmasini bosing.")
        self.status_msg.setStyleSheet("color: #38bdf8; font-size: 14px;")

    def _on_timer_tick(self):
        """Taymerning har soniyada kamayishi."""
        self.time_left -= 1
        self._update_timer_display(self.time_left)

        if self.time_left <= 0:
            self.timer.stop()
            self._handle_timeout()

    def _update_timer_display(self, seconds: int):
        """Taymer rangini vaqtga qarab o'zgartirish."""
        self.timer_val.setText(f"{seconds}s")
        if seconds > 4:
            self.timer_val.setStyleSheet("color: #10b981; font-weight: 800; font-size: 32px;")  # Yashil
        elif seconds > 2:
            self.timer_val.setStyleSheet("color: #f59e0b; font-weight: 800; font-size: 32px;")  # Sariq
        else:
            self.timer_val.setStyleSheet("color: #ef4444; font-weight: 800; font-size: 32px;")  # Qizil

    def _handle_timeout(self):
        """Vaqt tugaganda o'yinni to'xtatish."""
        self.word_input.setEnabled(False)
        self.submit_btn.setEnabled(False)
        timeout_data = self.game.handle_player_timeout()

        self.status_msg.setText(f"❌ {timeout_data['reason']}")
        self.status_msg.setStyleSheet("color: #ef4444; font-size: 14px; font-weight: bold;")

        self._show_game_over_dialog(
            title="Vaqt tugadi!",
            message="Afsus, 7 soniya ichida javob berilmadi.\nNavbat boy berildi!",
        )

    def _on_submit_word(self):
        """O'yinchi javob yuborganida."""
        player_word = self.word_input.text().strip()
        if not player_word:
            return

        # Taymer darhol to'xtatiladi (chunki javob 7 soniya ichida berildi!)
        self.timer.stop()
        self.word_input.setEnabled(False)
        self.submit_btn.setEnabled(False)

        self.status_msg.setText(f"🤖 Gemini AI «{player_word}» so'zini tekshirmoqda...")
        self.status_msg.setStyleSheet("color: #fbbf24; font-size: 14px;")

        # Alohida QThread orqali AI tekshiruvini boshlash
        self.worker_thread = AIWorkerThread(self.game, mode="validate_player", word_to_check=player_word)
        self.worker_thread.validation_done.connect(self._on_player_validation_done)
        self.worker_thread.start()

    def _on_player_validation_done(self, success: bool, result: ValidationResult):
        """O'yinchi so'zining tekshiruv natijasi qaytganida."""
        if not success:
            # Xato so'z!
            err = result.error_message or result.explanation
            self.status_msg.setText(f"❌ Noto'g'ri javob: {err}")
            self.status_msg.setStyleSheet("color: #ef4444; font-size: 14px; font-weight: bold;")

            self._show_game_over_dialog(
                title="O‘yin yakunlandi!",
                message=f"Kiritilgan so‘z qabul qilinmadi.\n\nSababi: {err}",
            )
            return

        # So'z to'g'ri qabul qilindi!
        self._add_to_history(
            author="O'yinchi",
            word=result.word,
            explanation=result.explanation,
        )
        self._update_score_ui()

        self.status_msg.setText(f"✅ To'g'ri! {result.explanation}")
        self.status_msg.setStyleSheet("color: #10b981; font-size: 14px;")

        # Endi kompyuter navbati (yana QThread da)
        self.status_msg.setText(f"✅ Ajoyib! Endi kompyuter «{display_letter(self.game.expected_letter)}» harfiga so'z qidirmoqda...")
        self.worker_thread = AIWorkerThread(self.game, mode="computer_turn")
        self.worker_thread.computer_turn_done.connect(self._on_computer_turn_done)
        self.worker_thread.start()

    def _on_computer_turn_done(self, comp_res: Dict[str, Any]):
        """Kompyuter o'z javobini topganida."""
        if not comp_res.get("success"):
            # Kompyuter so'z topa olmadi -> O'yinchi g'olib!
            reason = comp_res.get("reason", "Kompyuter so'z topa olmadi.")
            self.status_msg.setText(f"🏆 {reason}")
            self.status_msg.setStyleSheet("color: #10b981; font-size: 14px; font-weight: bold;")
            self._show_game_over_dialog(
                title="Tabriklaymiz, Siz G'olib Bo'ldingiz!",
                message=reason,
                is_win=True,
            )
            return

        # Kompyuter so'z aytdi
        comp_word = comp_res["word"]
        comp_expl = comp_res["explanation"]
        expected_next = comp_res["expected_letter"]

        self._display_computer_word(comp_word, comp_expl, expected_next)
        self._add_to_history(
            author="Kompyuter",
            word=comp_word,
            explanation=comp_expl,
        )

        # Navbatni yana o'yinchiga berish va 7 soniyani boshlash
        self._start_player_turn()

    def _add_to_history(self, author: str, word: str, explanation: str):
        """Ishlatilgan so'zlar ro'yxatiga qo'shish."""
        item = QListWidgetItem()
        if author == "O'yinchi":
            item.setText(f"👤 {word.upper()} (O'yinchi)\n   ℹ️ {explanation[:60]}...")
            item.setForeground(QColor("#38bdf8"))
        else:
            item.setText(f"🤖 {word.upper()} (Kompyuter)\n   ℹ️ {explanation[:60]}...")
            item.setForeground(QColor("#f59e0b"))

        self.history_list.insertItem(0, item)
        self.total_words_lbl.setText(f"Jami so'zlar: {len(self.game.history)}")

    def _update_score_ui(self):
        """Hisob va ketma-ketlikni ekranda yangilash."""
        self.score_val.setText(str(self.game.score))
        self.streak_val.setText(f"{self.game.streak} 🔥")

    def _show_game_over_dialog(self, title: str, message: str, is_win: bool = False):
        """O'yin yakuni modali."""
        summary = self.game.get_summary()

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(420, 320)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e293b;
                color: #f8fafc;
            }
            QLabel {
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        icon_lbl = QLabel("🏆" if is_win else "🏁")
        icon_lbl.setFont(QFont("Segoe UI", 36))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet("color: #10b981;" if is_win else "color: #ef4444;")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        layout.addWidget(msg_lbl)

        # Statistika
        stats_box = QFrame()
        stats_box.setStyleSheet("background-color: #0f172a; border-radius: 8px; padding: 10px;")
        stats_layout = QVBoxLayout(stats_box)
        stats_layout.addWidget(QLabel(f"⭐ To'plangan ball: <b>{summary['score']}</b>"))
        stats_layout.addWidget(QLabel(f"🔥 Eng uzun ketma-ketlik: <b>{summary['streak']} ta so'z</b>"))
        stats_layout.addWidget(QLabel(f"📚 O'yinda ishlatilgan so'zlar: <b>{summary['total_words']} ta</b>"))
        layout.addWidget(stats_box)

        # Qayta o'ynash tugmasi
        btn_layout = QHBoxLayout()
        restart_btn = QPushButton("🔄 Qayta o‘ynash")
        restart_btn.setProperty("class", "primary-btn")
        restart_btn.clicked.connect(lambda: (dialog.accept(), self._start_new_game()))
        btn_layout.addWidget(restart_btn)

        close_btn = QPushButton("Yopish")
        close_btn.setProperty("class", "secondary-btn")
        close_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        dialog.exec()


def run_gui():
    """Grafik interfeysni ishga tushirish."""
    app = QApplication(sys.argv)
    window = LastLetterGameWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
