"""
Log Viewer Widget - Scrolling colored log output
"""

from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Slot
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor


class LogViewerWidget(QPlainTextEdit):
    """Scrolling log viewer with colored output"""
    
    COLORS = {
        'DEBUG': '#a4b0be',
        'INFO': '#00d4ff',
        'WARNING': '#ffd32a',
        'ERROR': '#ff4757',
        'CRITICAL': '#ff4757',
    }
    
    def __init__(self, max_lines: int = 1000, parent=None) -> None:
        super().__init__(parent)
        self._max_lines = max_lines
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setReadOnly(True)
        self.setMaximumBlockCount(self._max_lines)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    
    @Slot(str, str)
    def append_log(self, level: str, message: str) -> None:
        """Append a log message with timestamp and color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        
        # Get color for level
        color = self.COLORS.get(level.upper(), '#ffffff')
        
        # Create colored format
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        
        # Append with color
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(formatted + "\n", fmt)
        
        # Scroll to bottom
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        )
    
    def clear_logs(self) -> None:
        """Clear all logs"""
        self.clear()
    
    def export_logs(self, filepath: Path) -> None:
        """Export logs to file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.toPlainText())

