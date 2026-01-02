"""
Settings Dialog - Edit and Save Configuration via GUI
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QPushButton, QTabWidget, QWidget, QLabel,
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Signal


class SettingsDialog(QDialog):
    """Settings dialog for editing .env configuration"""
    
    settings_saved = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings")
        self.setMinimumSize(500, 600)
        
        self._env_path = Path(__file__).parent.parent.parent / ".env"
        self._settings = {}
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # === Risk Tab ===
        risk_tab = QWidget()
        risk_layout = QVBoxLayout(risk_tab)
        

        # Thresholds
        threshold_group = QGroupBox("Loss Thresholds")
        threshold_layout = QFormLayout(threshold_group)
        
        self.max_loss_production = QDoubleSpinBox()
        self.max_loss_production.setRange(-10000, 0)
        self.max_loss_production.setPrefix("$")
        self.max_loss_production.setDecimals(0)
        threshold_layout.addRow("Max Daily Loss:", self.max_loss_production)
        
        risk_layout.addWidget(threshold_group)
        
        # Intervals
        interval_group = QGroupBox("Check Intervals")
        interval_layout = QFormLayout(interval_group)
        
        self.normal_interval = QDoubleSpinBox()
        self.normal_interval.setRange(1, 60)
        self.normal_interval.setSuffix(" seconds")
        interval_layout.addRow("Normal Mode:", self.normal_interval)
        
        self.block_interval = QDoubleSpinBox()
        self.block_interval.setRange(0.1, 10)
        self.block_interval.setSuffix(" seconds")
        interval_layout.addRow("Block Mode:", self.block_interval)
        
        risk_layout.addWidget(interval_group)
        
        # Reset Time (Hour and Minute)
        reset_group = QGroupBox("Daily Reset")
        reset_layout = QFormLayout(reset_group)
        
        # Hour
        self.reset_hour = QSpinBox()
        self.reset_hour.setRange(0, 23)
        reset_layout.addRow("Reset Hour:", self.reset_hour)
        
        # Minute
        self.reset_minute = QSpinBox()
        self.reset_minute.setRange(0, 59)
        reset_layout.addRow("Reset Minute:", self.reset_minute)
        
        self.symbol = QLineEdit()
        reset_layout.addRow("Symbol:", self.symbol)
        
        risk_layout.addWidget(reset_group)
        risk_layout.addStretch()
        
        tabs.addTab(risk_tab, "📊 Risk")
        
        # === MT5 Tab ===
        mt5_tab = QWidget()
        mt5_layout = QVBoxLayout(mt5_tab)
        
        mt5_group = QGroupBox("MT5 Connection")
        mt5_form = QFormLayout(mt5_group)
        
        self.mt5_login = QLineEdit()
        mt5_form.addRow("Login:", self.mt5_login)
        
        self.mt5_password = QLineEdit()
        self.mt5_password.setEchoMode(QLineEdit.EchoMode.Password)
        mt5_form.addRow("Password:", self.mt5_password)
        
        self.mt5_server = QLineEdit()
        mt5_form.addRow("Server:", self.mt5_server)
        
        self.mt5_terminal = QLineEdit()
        mt5_form.addRow("Terminal Path:", self.mt5_terminal)
        
        mt5_layout.addWidget(mt5_group)
        mt5_layout.addStretch()
        
        tabs.addTab(mt5_tab, "🔌 MT5")
        
        # === API Tab ===
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        
        api_group = QGroupBox("API Keys")
        api_form = QFormLayout(api_group)
        
        self.openrouter_key = QLineEdit()
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("OpenRouter:", self.openrouter_key)
        
        self.line_token = QLineEdit()
        self.line_token.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("Line Notify:", self.line_token)
        
        api_layout.addWidget(api_group)
        
        ai_group = QGroupBox("AI Settings")
        ai_form = QFormLayout(ai_group)
        
        self.ai_model = QLineEdit()
        ai_form.addRow("Model:", self.ai_model)
        
        self.ai_max_tokens = QSpinBox()
        self.ai_max_tokens.setRange(100, 10000)
        ai_form.addRow("Max Tokens:", self.ai_max_tokens)
        
        self.ai_temperature = QDoubleSpinBox()
        self.ai_temperature.setRange(0, 2)
        self.ai_temperature.setSingleStep(0.1)
        ai_form.addRow("Temperature:", self.ai_temperature)
        
        api_layout.addWidget(ai_group)
        api_layout.addStretch()
        
        tabs.addTab(api_tab, "🔑 API")
        
        # === Notifications Tab ===
        notify_tab = QWidget()
        notify_layout = QVBoxLayout(notify_tab)
        
        # Line Notify - REMOVED PER USER REQUEST
        # Discord Bot
        discord_group = QGroupBox("Discord Configuration")
        discord_form = QFormLayout(discord_group)
        
        self.discord_webhook = QLineEdit()
        self.discord_webhook.setEchoMode(QLineEdit.Password)
        discord_form.addRow("Webhook URL:", self.discord_webhook)
        
        self.discord_token = QLineEdit()
        self.discord_token.setEchoMode(QLineEdit.Password)
        discord_form.addRow("Bot Token:", self.discord_token)
        
        self.discord_guild = QLineEdit()
        discord_form.addRow("Guild ID:", self.discord_guild)
        
        self.discord_channel = QLineEdit()
        discord_form.addRow("Channel ID:", self.discord_channel)
        
        notify_layout.addWidget(discord_group)
        notify_layout.addStretch()
        
        tabs.addTab(notify_tab, "🔔 Notifications")
        
        # === Buttons ===
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_settings(self):
        """Load settings from .env file"""
        if not self._env_path.exists():
            return
        
        with open(self._env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    self._settings[key] = value
        
        # Populate fields
        self.max_loss_production.setValue(
            float(self._settings.get('MAX_LOSS_PRODUCTION', '-300'))
        )
        self.normal_interval.setValue(
            float(self._settings.get('NORMAL_CHECK_INTERVAL', '5.0'))
        )
        self.block_interval.setValue(
            float(self._settings.get('BLOCK_CHECK_INTERVAL', '0.5'))
        )
        self.reset_hour.setValue(
            int(self._settings.get('RESET_HOUR', '4'))
        )
        self.reset_minute.setValue(
            int(self._settings.get('RESET_MINUTE', '0'))
        )
        self.symbol.setText(self._settings.get('SYMBOL', 'XAUUSDm'))
        
        self.mt5_login.setText(self._settings.get('MT5_LOGIN', ''))
        self.mt5_password.setText(self._settings.get('MT5_PASSWORD', ''))
        self.mt5_server.setText(self._settings.get('MT5_SERVER', 'Exness-MT5Real'))
        self.mt5_terminal.setText(self._settings.get('MT5_TERMINAL_PATH', ''))
        
        self.openrouter_key.setText(self._settings.get('OPENROUTER_API_KEY', ''))
        self.ai_model.setText(
            self._settings.get('OPENROUTER_MODEL', 'google/gemini-2.0-flash-001')
        )
        self.ai_max_tokens.setValue(
            int(self._settings.get('AI_MAX_TOKENS', '2000'))
        )
        self.ai_temperature.setValue(
            float(self._settings.get('AI_TEMPERATURE', '0.7'))
        )
        
        # Notifications
        self.discord_webhook.setText(self._settings.get('DISCORD_WEBHOOK_URL', ''))
        self.discord_token.setText(self._settings.get('DISCORD_BOT_TOKEN', ''))
        self.discord_guild.setText(self._settings.get('DISCORD_GUILD_ID', ''))
        self.discord_channel.setText(self._settings.get('DISCORD_CHANNEL_ID', ''))
    
    def _save_settings(self):
        """Save settings to .env file"""
        # Update settings dict
        self._settings['MAX_LOSS_PRODUCTION'] = str(int(self.max_loss_production.value()))
        self._settings['NORMAL_CHECK_INTERVAL'] = str(self.normal_interval.value())
        self._settings['BLOCK_CHECK_INTERVAL'] = str(self.block_interval.value())
        self._settings['RESET_HOUR'] = str(self.reset_hour.value())
        self._settings['RESET_MINUTE'] = str(self.reset_minute.value())
        self._settings['SYMBOL'] = self.symbol.text()
        
        self._settings['MT5_LOGIN'] = self.mt5_login.text()
        self._settings['MT5_PASSWORD'] = self.mt5_password.text()
        self._settings['MT5_SERVER'] = self.mt5_server.text()
        self._settings['MT5_TERMINAL_PATH'] = self.mt5_terminal.text()
        
        self._settings['OPENROUTER_API_KEY'] = self.openrouter_key.text()
        self._settings['OPENROUTER_MODEL'] = self.ai_model.text()
        self._settings['AI_MAX_TOKENS'] = str(self.ai_max_tokens.value())
        self._settings['AI_TEMPERATURE'] = str(self.ai_temperature.value())
        
        # Notifications
        self._settings['DISCORD_WEBHOOK_URL'] = self.discord_webhook.text()
        self._settings['DISCORD_BOT_TOKEN'] = self.discord_token.text()
        self._settings['DISCORD_GUILD_ID'] = self.discord_guild.text()
        self._settings['DISCORD_CHANNEL_ID'] = self.discord_channel.text()
        
        # Write to file
        try:
            lines = [
                "# ===============================================================================",
                "# PROJECT SENTINEL - ENVIRONMENT CONFIGURATION",
                "# ===============================================================================",
                "",
                "# ---- MT5 Credentials ----",
                f"MT5_LOGIN={self._settings.get('MT5_LOGIN', '')}",
                f"MT5_PASSWORD={self._settings.get('MT5_PASSWORD', '')}",
                f"MT5_SERVER={self._settings.get('MT5_SERVER', 'Exness-MT5Real')}",
                f"MT5_TERMINAL_PATH={self._settings.get('MT5_TERMINAL_PATH', '')}",
                "",
                "# ---- Risk Guardian Settings ----",
                f"MAX_LOSS_PRODUCTION={self._settings.get('MAX_LOSS_PRODUCTION', '-300')}",
                f"RESET_HOUR={self._settings.get('RESET_HOUR', '4')}",
                f"RESET_MINUTE={self._settings.get('RESET_MINUTE', '0')}",
                f"SYMBOL={self._settings.get('SYMBOL', 'XAUUSDm')}",
                "",
                "# ---- Monitoring Intervals ----",
                f"NORMAL_CHECK_INTERVAL={self._settings.get('NORMAL_CHECK_INTERVAL', '5.0')}",
                f"BLOCK_CHECK_INTERVAL={self._settings.get('BLOCK_CHECK_INTERVAL', '0.5')}",
                "",
                "# ---- API Keys ----",
                f"OPENROUTER_API_KEY={self._settings.get('OPENROUTER_API_KEY', '')}",
                f"GEMINI_API_KEY={self._settings.get('GEMINI_API_KEY', '')}",
                "",
                "# ---- Discord Settings ----",
                f"DISCORD_WEBHOOK_URL={self._settings.get('DISCORD_WEBHOOK_URL', '')}",
                f"DISCORD_BOT_TOKEN={self._settings.get('DISCORD_BOT_TOKEN', '')}",
                f"DISCORD_GUILD_ID={self._settings.get('DISCORD_GUILD_ID', '')}",
                f"DISCORD_CHANNEL_ID={self._settings.get('DISCORD_CHANNEL_ID', '')}",
                "",
                "# ---- AI Settings ----",
                f"OPENROUTER_MODEL={self._settings.get('OPENROUTER_MODEL', 'google/gemini-2.0-flash-001')}",
                f"AI_MAX_TOKENS={self._settings.get('AI_MAX_TOKENS', '2000')}",
                f"AI_TEMPERATURE={self._settings.get('AI_TEMPERATURE', '0.7')}",
            ]
            
            with open(self._env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            # FORCE RELOAD CONFIG
            from config import ConfigLoader
            ConfigLoader().load()
            
            QMessageBox.information(self, "Saved", "Settings saved successfully!\n\nNew configuration active.")
            self.settings_saved.emit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
