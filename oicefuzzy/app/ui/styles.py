DARK_THEME = """
QWidget {
    font-family: "Bahnschrift";
    color: #E6EDF7;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0B111A, stop:0.5 #111827, stop:1 #0F172A);
}

QFrame#Card {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(24, 30, 42, 0.92), stop:1 rgba(18, 24, 34, 0.92));
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 16px;
}

QLabel#Title {
    font-size: 22px;
    font-weight: 700;
    color: #F8FAFC;
}

QLabel#Avatar {
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 24px;
    padding: 6px;
}

QLabel#StatusText {
    font-size: 13px;
    color: #A7B6D8;
}

QLabel#StatusDot {
    background: #64748B;
    border-radius: 6px;
    min-width: 12px;
    min-height: 12px;
    max-width: 12px;
    max-height: 12px;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

QLabel#StatusDot[status="listening"] { background: #2DD4BF; }
QLabel#StatusDot[status="executing"] { background: #F97316; }
QLabel#StatusDot[status="idle"] { background: #64748B; }

QPushButton {
    background: rgba(30, 41, 59, 0.9);
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 12px;
    padding: 10px 14px;
}

QPushButton:hover { background: rgba(51, 65, 85, 0.95); }
QPushButton:pressed { background: rgba(71, 85, 105, 0.95); }

QPushButton#PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #38BDF8, stop:1 #14B8A6);
    border: 1px solid rgba(125, 211, 252, 0.6);
    color: #0B1220;
    font-weight: 700;
}

QPushButton#PrimaryButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60A5FA, stop:1 #22D3EE); }
QPushButton#PrimaryButton:pressed { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D4ED8, stop:1 #0F766E); color: #E2E8F0; }

QPushButton#GhostButton {
    background: rgba(15, 23, 42, 0.6);
    border: 1px dashed rgba(148, 163, 184, 0.35);
    color: #C7D2FE;
}

QListWidget, QTableWidget {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 12px;
    padding: 6px;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background: rgba(56, 189, 248, 0.18);
    color: #E2E8F0;
}

QHeaderView::section {
    background: rgba(30, 41, 59, 0.9);
    color: #CBD5E1;
    border: none;
    padding: 8px;
}

QScrollBar:vertical {
    background: rgba(15, 23, 42, 0.6);
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(100, 116, 139, 0.6);
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QGroupBox {
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 12px;
    margin-top: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #94A3B8; }
"""

LIGHT_THEME = """
QWidget {
    font-family: "Bahnschrift";
    color: #0F172A;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #F8FAFF, stop:0.5 #EEF2F7, stop:1 #E6EDF6);
}

QFrame#Card {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 16px;
}

QLabel#Title {
    font-size: 22px;
    font-weight: 700;
    color: #0B1220;
}

QLabel#Avatar {
    background: rgba(14, 165, 233, 0.12);
    border: 1px solid rgba(14, 165, 233, 0.35);
    border-radius: 24px;
    padding: 6px;
}

QLabel#StatusText {
    font-size: 13px;
    color: #475569;
}

QLabel#StatusDot {
    background: #94A3B8;
    border-radius: 6px;
    min-width: 12px;
    min-height: 12px;
    max-width: 12px;
    max-height: 12px;
    border: 1px solid rgba(15, 23, 42, 0.2);
}

QLabel#StatusDot[status="listening"] { background: #0F766E; }
QLabel#StatusDot[status="executing"] { background: #EA580C; }
QLabel#StatusDot[status="idle"] { background: #94A3B8; }

QPushButton {
    background: rgba(241, 245, 249, 0.95);
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 12px;
    padding: 10px 14px;
}

QPushButton:hover { background: rgba(226, 232, 240, 0.95); }
QPushButton:pressed { background: rgba(203, 213, 225, 0.95); }

QPushButton#PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0EA5E9, stop:1 #14B8A6);
    border: 1px solid rgba(14, 165, 233, 0.35);
    color: #F8FAFC;
    font-weight: 700;
}

QPushButton#PrimaryButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #2DD4BF); }
QPushButton#PrimaryButton:pressed { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0F766E); }

QPushButton#GhostButton {
    background: rgba(248, 250, 252, 0.8);
    border: 1px dashed rgba(100, 116, 139, 0.5);
    color: #334155;
}

QListWidget, QTableWidget {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 12px;
    padding: 6px;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background: rgba(14, 165, 233, 0.15);
    color: #0B1220;
}

QHeaderView::section {
    background: rgba(226, 232, 240, 0.95);
    color: #475569;
    border: none;
    padding: 8px;
}

QScrollBar:vertical {
    background: rgba(226, 232, 240, 0.7);
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(100, 116, 139, 0.5);
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QGroupBox {
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 12px;
    margin-top: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #64748B; }
"""


def theme_styles(name: str) -> str:
    if name == "light":
        return LIGHT_THEME
    return DARK_THEME
