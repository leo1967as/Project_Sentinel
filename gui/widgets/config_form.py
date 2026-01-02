"""
Config Form Widget - Settings form with validation (placeholder)
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ConfigFormWidget(QWidget):
    """Configuration form widget (placeholder)"""
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings form - TODO"))
        layout.addStretch()
