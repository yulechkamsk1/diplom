from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from api.client import api_client
from auth.jwt_manager import jwt_manager


class LoginWindow(QWidget):
    login_success = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("loginBg")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(420)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        # Logo row
        logo_row = QHBoxLayout()
        logo_icon = QLabel("PP")
        logo_icon.setFixedSize(36, 36)
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setStyleSheet(
            "background: #3B82F6; border-radius: 8px; color: #FFFFFF; "
            "font-size: 14px; font-weight: 700;"
        )
        logo_text = QLabel("PaymentPro")
        logo_text.setObjectName("logoTitle")
        logo_row.addWidget(logo_icon)
        logo_row.addSpacing(10)
        logo_row.addWidget(logo_text)
        logo_row.addStretch()
        layout.addLayout(logo_row)

        title = QLabel("Добро пожаловать")
        title.setObjectName("loginTitle")
        layout.addWidget(title)

        subtitle = QLabel("Войдите в систему управления платежами")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Username
        lbl_user = QLabel("Логин")
        lbl_user.setObjectName("fieldLabel")
        layout.addWidget(lbl_user)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Введите логин")
        self.username_edit.setMinimumHeight(44)
        layout.addWidget(self.username_edit)

        # Password
        lbl_pass = QLabel("Пароль")
        lbl_pass.setObjectName("fieldLabel")
        layout.addWidget(lbl_pass)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(0)
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Введите пароль")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setMinimumHeight(44)
        self.password_edit.returnPressed.connect(self._on_login)

        self.toggle_btn = QPushButton("Показать")
        self.toggle_btn.setFixedSize(72, 44)
        self.toggle_btn.setStyleSheet(
            "QPushButton { border: 1.5px solid #E2E8F0; border-left: none; "
            "border-radius: 0 8px 8px 0; background: #F8FAFC; font-size: 12px; color: #64748B; }"
            "QPushButton:hover { background: #F1F5F9; }"
        )
        self.toggle_btn.clicked.connect(self._toggle_password)
        self.password_edit.setStyleSheet(
            "QLineEdit { border-radius: 8px 0 0 8px; border: 1.5px solid #E2E8F0; "
            "padding: 10px 14px; font-size: 14px; }"
            "QLineEdit:focus { border-color: #3B82F6; }"
        )

        pass_row.addWidget(self.password_edit)
        pass_row.addWidget(self.toggle_btn)
        layout.addLayout(pass_row)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        layout.addSpacing(4)

        # Login button
        self.login_btn = QPushButton("Войти")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.setMinimumHeight(48)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

        layout.addSpacing(4)
        hint = QLabel("Тестовый режим: любой логин и пароль")
        hint.setStyleSheet("color: #94A3B8; font-size: 12px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _toggle_password(self):
        if self.password_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("Скрыть")
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("Показать")

    def _set_error(self, msg: str):
        self.error_label.setText(msg)
        self.error_label.setVisible(bool(msg))

    def _on_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username:
            self._set_error("Введите логин")
            return
        if not password:
            self._set_error("Введите пароль")
            return

        self._set_error("")
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Вход...")

        try:
            result = api_client.login(username, password)
            jwt_manager.set_token(result["access_token"])
            self.login_success.emit()
        except Exception as e:
            self._set_error(str(e))
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Войти")
