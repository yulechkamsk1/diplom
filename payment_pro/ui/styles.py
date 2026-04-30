MAIN_STYLE = """
QWidget {
    font-family: "Inter", "Segoe UI", "Ubuntu", sans-serif;
    font-size: 14px;
    color: #1E293B;
}

QMainWindow, #centralWidget {
    background-color: #F0F4F8;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
}

#logoTitle {
    font-size: 18px;
    font-weight: 700;
    color: #1E293B;
}

#logoSubtitle {
    font-size: 11px;
    color: #94A3B8;
}

#navButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    color: #64748B;
    font-size: 14px;
}

#navButton:hover {
    background-color: #F1F5F9;
    color: #1E293B;
}

#navButton[active="true"] {
    background-color: #3B82F6;
    color: #FFFFFF;
    font-weight: 600;
}

#logoutButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    text-align: left;
    color: #EF4444;
    font-size: 14px;
}

#logoutButton:hover {
    background-color: #FEF2F2;
}

/* ── Header ── */
#header {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}

#pageTitle {
    font-size: 22px;
    font-weight: 700;
    color: #1E293B;
}

#pageSubtitle {
    font-size: 13px;
    color: #94A3B8;
}

#notifButton {
    background: #F1F5F9;
    border: none;
    border-radius: 8px;
    padding: 8px;
    font-size: 18px;
    color: #64748B;
}

#notifButton:hover {
    background: #E2E8F0;
}

#userAvatar {
    background-color: #3B82F6;
    border-radius: 18px;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 15px;
}

#userName {
    font-weight: 600;
    color: #1E293B;
    font-size: 14px;
}

#userRole {
    font-size: 12px;
    color: #94A3B8;
}

/* ── Stat cards ── */
#statCard {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
}

#statValue {
    font-size: 24px;
    font-weight: 700;
    color: #1E293B;
}

#statLabel {
    font-size: 13px;
    color: #64748B;
}

#statChange {
    font-size: 12px;
    font-weight: 600;
}

#statIconBox {
    border-radius: 10px;
    font-size: 20px;
}

/* ── Quick action buttons ── */
#btnNewPayment {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
}
#btnNewPayment:hover { background-color: #2563EB; }

#btnTransfer {
    background-color: #10B981;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
}
#btnTransfer:hover { background-color: #059669; }

#btnHistory {
    background-color: #8B5CF6;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
}
#btnHistory:hover { background-color: #7C3AED; }

/* ── Tables ── */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    gridline-color: transparent;
    outline: none;
}

QTableWidget::item {
    padding: 10px 12px;
    border: none;
    color: #1E293B;
}

QTableWidget::item:alternate {
    background-color: #F9FAFB;
}

QTableWidget::item:selected {
    background-color: #EFF6FF;
    color: #1E293B;
}

QHeaderView::section {
    background-color: #F8FAFC;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    padding: 10px 12px;
    font-weight: 600;
    color: #64748B;
    font-size: 13px;
}

/* ── Cards / Frames ── */
#sectionCard {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
}

#sectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #1E293B;
}

#showAllLink {
    background: transparent;
    border: none;
    color: #3B82F6;
    font-size: 13px;
    font-weight: 600;
    text-decoration: underline;
}
#showAllLink:hover { color: #2563EB; }

/* ── Login ── */
#loginCard {
    background-color: #FFFFFF;
    border-radius: 16px;
    border: 1px solid #E2E8F0;
}

#loginTitle {
    font-size: 26px;
    font-weight: 700;
    color: #1E293B;
}

#loginSubtitle {
    font-size: 14px;
    color: #94A3B8;
}

QLineEdit {
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    background: #FFFFFF;
    color: #1E293B;
}

QLineEdit:focus {
    border-color: #3B82F6;
}

QLineEdit[error="true"] {
    border-color: #EF4444;
}

#loginButton {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 15px;
    font-weight: 600;
}
#loginButton:hover { background-color: #2563EB; }
#loginButton:pressed { background-color: #1D4ED8; }

#errorLabel {
    color: #EF4444;
    font-size: 13px;
}

/* ── Payments form ── */
QComboBox {
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    background: #FFFFFF;
    color: #1E293B;
}

QComboBox:focus { border-color: #3B82F6; }

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background: #FFFFFF;
    selection-background-color: #EFF6FF;
}

QTextEdit {
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    background: #FFFFFF;
    color: #1E293B;
}

QTextEdit:focus { border-color: #3B82F6; }

#submitButton {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 13px 32px;
    font-size: 15px;
    font-weight: 600;
}
#submitButton:hover { background-color: #2563EB; }
#submitButton:pressed { background-color: #1D4ED8; }

#fieldLabel {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 4px;
}

/* ── History filters ── */
QDateEdit {
    border: 1.5px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    background: #FFFFFF;
    color: #1E293B;
}

QDateEdit:focus { border-color: #3B82F6; }

#filterButton {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
}
#filterButton:hover { background-color: #2563EB; }

#exportButton {
    background-color: #10B981;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
}
#exportButton:hover { background-color: #059669; }

/* ── Accounts ── */
#accountCard {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
}

#accountName {
    font-size: 15px;
    font-weight: 700;
    color: #1E293B;
}

#accountNumber {
    font-size: 12px;
    color: #94A3B8;
    font-family: "Courier New", monospace;
}

#accountBalance {
    font-size: 20px;
    font-weight: 700;
    color: #1E293B;
}

#accountCurrency {
    font-size: 13px;
    color: #64748B;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #F1F5F9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollArea {
    border: none;
    background: transparent;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}
"""


def badge_style(status: str) -> str:
    mapping = {
        "completed": ("background:#D1FAE5; color:#065F46;", "Завершён"),
        "processing": ("background:#FEF3C7; color:#92400E;", "Обработка"),
        "failed": ("background:#FEE2E2; color:#991B1B;", "Ошибка"),
        "pending": ("background:#E0E7FF; color:#3730A3;", "Ожидание"),
    }
    style, label = mapping.get(status, ("background:#F1F5F9; color:#64748B;", status))
    return style, label
