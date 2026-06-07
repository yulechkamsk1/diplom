from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Callable

from auth.jwt_manager import jwt_manager
from ui.dashboard import Dashboard
from ui.payments import Payments
from ui.history import History
from ui.accounts import Accounts
from ui.analytics import Analytics
from ui.settings import Settings
from ui.banker_queue import BankerQueue
from ui.banker_clients import BankerClients
from ui.admin_users import AdminUsers
from ui.admin_audit import AdminAudit
from ui.admin_stats import AdminStats


NAV_CLIENT = [
    ("dashboard", "Главная"),
    ("payments",  "Платежи"),
    ("history",   "История"),
    ("accounts",  "Счета"),
    ("analytics", "Аналитика"),
    ("settings",  "Настройки"),
]

NAV_BANKER = [
    ("dashboard", "Главная"),
    ("queue",     "Очередь платежей"),
    ("clients",   "Клиенты"),
    ("history",   "История"),
    ("analytics", "Аналитика"),
    ("settings",  "Настройки"),
]

NAV_ADMIN = [
    ("dashboard", "Главная"),
    ("stats",     "Статистика"),
    ("users",     "Пользователи"),
    ("audit",     "Аудит"),
    ("settings",  "Настройки"),
]

PAGE_META = {
    "dashboard": ("Панель управления",    "Обзор финансовой активности"),
    "payments":  ("Платежи",              "Создание платёжного поручения"),
    "queue":     ("Очередь платежей",     "Проверка и одобрение платежей"),
    "clients":   ("Клиенты",              "Поиск и карточки клиентов"),
    "history":   ("История транзакций",   "Просмотр и фильтрация операций"),
    "accounts":  ("Счета",                "Управление банковскими счетами"),
    "analytics": ("Аналитика",            "Финансовая статистика"),
    "settings":  ("Настройки",            "Профиль и параметры"),
    "users":     ("Пользователи",         "Управление учётными записями"),
    "stats":     ("Статистика",           "Решения банкиров и статусы платежей"),
    "audit":     ("Журнал аудита",        "История действий в системе"),
}


class MainWindow(QMainWindow):
    def __init__(self, on_logout):
        super().__init__()
        self._on_logout = on_logout
        self._nav_buttons: dict[str, QPushButton] = {}
        self._pages: dict[str, QWidget] = {}
        self._page_factories: dict[str, Callable[[], QWidget]] = {}

        role = jwt_manager.get_role_key()
        if role == "BANKER":
            self._nav_items = NAV_BANKER
        elif role == "ADMIN":
            self._nav_items = NAV_ADMIN
        else:
            self._nav_items = NAV_CLIENT

        self.setWindowTitle("PaymentPro — Платёжная система")
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._navigate("dashboard")

    def _build_ui(self):
        role = jwt_manager.get_role_key()

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.header = self._build_header()
        right_layout.addWidget(self.header)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")
        # Pages are created lazily. This keeps login fast and avoids loading
        # heavy tables until the user opens the relevant section.
        self._register_page("dashboard", self._build_dashboard)
        self._register_page("history", History)
        self._register_page("analytics", Analytics)
        self._register_page("settings", Settings)

        # Role-specific pages
        if role == "BANKER":
            self._register_page("queue", BankerQueue)
            self._register_page("clients", BankerClients)
        elif role == "ADMIN":
            self._register_page("stats", AdminStats)
            self._register_page("users", AdminUsers)
            self._register_page("audit", AdminAudit)
        else:
            self._register_page("payments", Payments)
            self._register_page("accounts", Accounts)

        right_layout.addWidget(self.stack, stretch=1)
        root.addWidget(right, stretch=1)

    # ── Sidebar ──────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(180)
        sidebar.setMaximumWidth(220)
        sidebar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        logo_area = QWidget()
        logo_area.setMinimumHeight(72)
        logo_area.setMaximumHeight(84)
        logo_layout = QHBoxLayout(logo_area)
        logo_layout.setContentsMargins(20, 16, 20, 16)
        logo_layout.setSpacing(12)

        icon = QLabel("PP")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "background: #3B82F6; border-radius: 8px; color: #FFFFFF; "
            "font-size: 13px; font-weight: 700;"
        )
        logo_layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        title = QLabel("PaymentPro")
        title.setObjectName("logoTitle")
        sub = QLabel("Платёжная система")
        sub.setObjectName("logoSubtitle")
        text_col.addWidget(title)
        text_col.addWidget(sub)
        logo_layout.addLayout(text_col)
        logo_layout.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #E2E8F0;")

        layout.addWidget(logo_area)
        layout.addWidget(divider)
        layout.addSpacing(8)

        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(4)

        for page_id, label in self._nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navButton")
            btn.setMinimumHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, pid=page_id: self._navigate(pid))
            nav_layout.addWidget(btn)
            self._nav_buttons[page_id] = btn

        nav_layout.addStretch()
        layout.addWidget(nav_widget, stretch=1)

        bottom_div = QFrame()
        bottom_div.setFrameShape(QFrame.Shape.HLine)
        bottom_div.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(bottom_div)

        logout_widget = QWidget()
        logout_widget.setMinimumHeight(56)
        logout_widget.setMaximumHeight(66)
        logout_layout = QHBoxLayout(logout_widget)
        logout_layout.setContentsMargins(12, 8, 12, 8)

        logout_btn = QPushButton("Выйти")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setMinimumHeight(42)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self._logout)
        logout_layout.addWidget(logout_btn)
        layout.addWidget(logout_widget)

        return sidebar

    # ── Header ───────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setMinimumHeight(70)
        header.setMaximumHeight(88)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 0, 24, 0)
        layout.setSpacing(16)

        self.page_title = QLabel("Панель управления")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("Обзор финансовой активности")
        self.page_subtitle.setObjectName("pageSubtitle")
        self.page_subtitle.setWordWrap(True)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(self.page_title)
        title_col.addWidget(self.page_subtitle)
        layout.addLayout(title_col)
        layout.addStretch()

        notif_btn = QPushButton("Уведомления")
        notif_btn.setObjectName("notifButton")
        notif_btn.setFixedHeight(36)
        notif_btn.setMaximumWidth(150)
        notif_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(notif_btn)

        username = jwt_manager.get_username()
        role = jwt_manager.get_role()
        initials = "".join(p[0].upper() for p in username.split()[:2]) or "U"

        avatar = QLabel(initials)
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        user_col = QVBoxLayout()
        user_col.setSpacing(1)
        user_name_lbl = QLabel(username)
        user_name_lbl.setObjectName("userName")
        user_name_lbl.setMaximumWidth(180)
        user_role_lbl = QLabel(role)
        user_role_lbl.setObjectName("userRole")
        user_col.addWidget(user_name_lbl)
        user_col.addWidget(user_role_lbl)

        layout.addWidget(avatar)
        layout.addLayout(user_col)

        return header

    # ── Navigation ────────────────────────────────────────────────

    def _add_page(self, page_id: str, widget: QWidget):
        self._pages[page_id] = widget
        self.stack.addWidget(widget)

    def _register_page(self, page_id: str, factory: Callable[[], QWidget]):
        self._page_factories[page_id] = factory

    def _build_dashboard(self) -> QWidget:
        dash = Dashboard()
        dash.navigate.connect(self._navigate)
        return dash

    def _get_or_create_page(self, page_id: str) -> QWidget | None:
        if page_id in self._pages:
            return self._pages[page_id]
        factory = self._page_factories.get(page_id)
        if not factory:
            return None
        widget = factory()
        self._add_page(page_id, widget)
        return widget

    def _navigate(self, page_id: str):
        switch_email_tab = page_id == "payments_email"
        actual_id = "payments" if switch_email_tab else page_id

        widget = self._get_or_create_page(actual_id)
        if widget is None:
            return

        if switch_email_tab and hasattr(widget, "switch_to_email_tab"):
            widget.switch_to_email_tab()
        elif page_id == "payments" and hasattr(widget, "switch_to_account_tab"):
            widget.switch_to_account_tab()

        for pid, btn in self._nav_buttons.items():
            btn.setProperty("active", pid == actual_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        title, subtitle = PAGE_META.get(actual_id, (actual_id.capitalize(), ""))
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)

        self.stack.setCurrentWidget(widget)

    def _logout(self):
        jwt_manager.clear()
        self._on_logout()
