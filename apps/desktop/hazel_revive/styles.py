"""Global Qt stylesheets — proportional mobile layout."""

from __future__ import annotations

from hazel_revive import theme as T


def app_stylesheet() -> str:
    return f"""
QMainWindow {{
    background-color: {T.BG};
    color: {T.TEXT};
}}

QWidget#root {{
    background-color: {T.BG};
}}

QLabel {{
    color: {T.TEXT};
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    font-size: 15px;
}}

QLabel#heading {{
    font-size: 22px;
    font-weight: bold;
    margin-bottom: 4px;
}}

QLabel#subheading {{
    font-size: 18px;
    font-weight: bold;
}}

QLabel#muted {{
    color: {T.MUTED};
    font-size: 13px;
}}

QLabel#accent {{
    color: {T.ACCENT};
    font-size: 15px;
}}

QLabel#statusBar {{
    color: {T.MUTED};
    font-size: 13px;
    padding: 8px 12px;
    background-color: {T.SURFACE};
    border-top: 1px solid {T.BORDER_SOLID};
}}

QPlainTextEdit#logPanel {{
    color: {T.MUTED};
    font-family: monospace;
    font-size: 11px;
    background-color: {T.SURFACE};
    border-top: 1px solid {T.BORDER_SOLID};
    padding: 6px;
}}

QPushButton {{
    background-color: {T.SURFACE};
    color: {T.TEXT};
    border: 1px solid {T.BORDER_SOLID};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 15px;
    min-height: 24px;
}}

QPushButton:hover {{
    border-color: {T.ACCENT};
}}

QPushButton:disabled {{
    color: {T.MUTED};
}}

QFrame#dashboardRow {{
    background-color: {T.SURFACE};
    border: 1px solid {T.BORDER_SOLID};
    border-radius: 8px;
}}

QFrame#dashboardRow:hover {{
    border-color: {T.ACCENT};
}}

QPushButton#btnPrimary {{
    background-color: {T.ACCENT};
    color: #0a0a0a;
    border: none;
    font-weight: bold;
}}

QPushButton#btnPrimary:hover {{
    background-color: #52e838;
}}

QListWidget {{
    background-color: {T.SURFACE};
    color: {T.TEXT};
    border: 1px solid {T.BORDER_SOLID};
    border-radius: 8px;
    padding: 4px;
    font-size: 15px;
}}

QListWidget::item {{
    padding: 12px 14px;
    border-radius: 6px;
    margin-bottom: 2px;
}}

QListWidget::item:selected {{
    background-color: rgba(68, 214, 44, 0.12);
    border: 1px solid {T.ACCENT};
}}
"""
