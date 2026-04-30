import sys
import os

# Allow imports from payment_pro/ directory
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QStackedWidget
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from ui.styles import MAIN_STYLE
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


class App(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("PaymentPro")
        self.setApplicationVersion("1.0.0")
        self.setStyleSheet(MAIN_STYLE)

        font = QFont("Inter", 10)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.setFont(font)

        self.root = QStackedWidget()
        self.root.setObjectName("centralWidget")
        self.root.setWindowTitle("PaymentPro — Платёжная система")
        self.root.setMinimumSize(1100, 700)
        self.root.resize(1280, 800)

        self.login_win = LoginWindow()
        self.login_win.login_success.connect(self._on_login)
        self.root.addWidget(self.login_win)

        self.main_win: MainWindow | None = None

        self.root.show()

    def _on_login(self):
        self.main_win = MainWindow(on_logout=self._on_logout)
        self.root.addWidget(self.main_win)
        self.root.setCurrentWidget(self.main_win)
        self.root.setWindowTitle("PaymentPro — Платёжная система")

    def _on_logout(self):
        if self.main_win:
            self.root.removeWidget(self.main_win)
            self.main_win.deleteLater()
            self.main_win = None
        self.root.setCurrentWidget(self.login_win)
        self.login_win.username_edit.clear()
        self.login_win.password_edit.clear()
        self.login_win.error_label.setVisible(False)


def main():
    app = App(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
