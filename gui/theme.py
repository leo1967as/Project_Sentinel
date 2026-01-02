"""
Theme Manager - Dark/Light theme support with QSS
"""

from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor


class ThemeManager:
    """Manages application theming"""
    
    RESOURCES_DIR = Path(__file__).parent / "resources"
    
    # Dark theme colors
    DARK_COLORS = {
        'background': '#1a1a2e',
        'surface': '#16213e',
        'surface_light': '#1f3460',
        'primary': '#00d4ff',
        'secondary': '#7f5af0',
        'success': '#00ff88',
        'danger': '#ff4757',
        'warning': '#ffd32a',
        'text': '#ffffff',
        'text_secondary': '#a4b0be',
        'border': '#2d3436',
    }
    
    def __init__(self) -> None:
        self.current_theme = 'dark'
    
    def apply_dark_theme(self, app: QApplication) -> None:
        """Apply dark theme to application"""
        self.current_theme = 'dark'
        
        # Try to load QSS file first
        qss_file = self.RESOURCES_DIR / "styles" / "dark.qss"
        if qss_file.exists():
            with open(qss_file, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
            return
        
        # Fallback: Generate stylesheet
        app.setStyleSheet(self._generate_dark_qss())
    
    def _generate_dark_qss(self) -> str:
        """Generate dark theme QSS"""
        c = self.DARK_COLORS
        return f"""
        /* Global */
        QWidget {{
            background-color: {c['background']};
            color: {c['text']};
            font-family: "Segoe UI", Arial, sans-serif;
        }}
        
        QMainWindow {{
            background-color: {c['background']};
        }}
        
        /* Frames & Cards */
        QFrame {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 8px;
        }}
        
        QGroupBox {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            margin-top: 16px;
            padding-top: 16px;
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
            color: {c['primary']};
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {c['surface_light']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px 16px;
            color: {c['text']};
            font-weight: 500;
        }}
        
        QPushButton:hover {{
            background-color: {c['primary']};
            color: {c['background']};
        }}
        
        QPushButton:pressed {{
            background-color: {c['secondary']};
        }}
        
        QPushButton:disabled {{
            background-color: {c['border']};
            color: {c['text_secondary']};
        }}
        
        QPushButton#emergency {{
            background-color: {c['danger']};
            color: white;
            font-weight: bold;
        }}
        
        QPushButton#emergency:hover {{
            background-color: #ff6b7a;
        }}
        
        /* Labels */
        QLabel {{
            border: none;
            background: transparent;
        }}
        
        QLabel#title {{
            font-size: 18px;
            font-weight: bold;
            color: {c['primary']};
        }}
        
        QLabel#subtitle {{
            font-size: 12px;
            color: {c['text_secondary']};
        }}
        
        /* Tables */
        QTableWidget {{
            background-color: {c['surface']};
            alternate-background-color: {c['surface_light']};
            gridline-color: {c['border']};
            border: 1px solid {c['border']};
            border-radius: 8px;
        }}
        
        QTableWidget::item {{
            padding: 8px;
        }}
        
        QTableWidget::item:selected {{
            background-color: {c['primary']};
            color: {c['background']};
        }}
        
        QHeaderView::section {{
            background-color: {c['surface_light']};
            padding: 8px;
            border: none;
            border-bottom: 2px solid {c['primary']};
            font-weight: bold;
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {c['border']};
            border-radius: 8px;
            background-color: {c['surface']};
        }}
        
        QTabBar::tab {{
            background-color: {c['surface_light']};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {c['surface']};
            border-bottom: 2px solid {c['primary']};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {c['border']};
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {c['surface']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c['border']};
            border-radius: 6px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c['primary']};
        }}
        
        /* Text Edit / Plain Text */
        QPlainTextEdit {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 8px;
            font-family: "Consolas", monospace;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {c['surface_light']};
            border-top: 1px solid {c['border']};
        }}
        
        QStatusBar::item {{
            border: none;
        }}
        
        /* Splitter */
        QSplitter::handle {{
            background-color: {c['border']};
        }}
        
        QSplitter::handle:hover {{
            background-color: {c['primary']};
        }}
        
        /* Menu */
        QMenuBar {{
            background-color: {c['surface']};
            border-bottom: 1px solid {c['border']};
        }}
        
        QMenuBar::item:selected {{
            background-color: {c['surface_light']};
        }}
        
        QMenu {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
        }}
        
        QMenu::item:selected {{
            background-color: {c['primary']};
            color: {c['background']};
        }}
        """
    
    def get_color(self, name: str) -> str:
        """Get color by name for current theme"""
        if self.current_theme == 'dark':
            return self.DARK_COLORS.get(name, '#ffffff')
        return '#000000'
