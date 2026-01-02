"""
===============================================================================
PROJECT SENTINEL - SECURE CONFIGURATION MANAGEMENT
===============================================================================
Configuration loader with environment variables and encryption support.
NEVER stores sensitive data in source code.

Author: Project Sentinel
===============================================================================
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from functools import lru_cache

# Try to import encryption libraries (optional)
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Try to import dotenv
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"
CONFIG_BACKUP_FILE = PROJECT_ROOT / "config_backup.enc"
AUDIT_LOG_FILE = PROJECT_ROOT / "logs" / "config_audit.log"

# =============================================================================
# AUDIT LOGGER
# =============================================================================

class AuditLogger:
    """Logs ALL configuration access attempts"""
    
    def __init__(self, log_file: Path = AUDIT_LOG_FILE):
        self.log_file = log_file
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Setup file handler
        self.logger = logging.getLogger("config_audit")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s'
            ))
            self.logger.addHandler(handler)
    
    def log_access(self, key: str, action: str, success: bool, details: str = ""):
        """Log configuration access attempt"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"{action} | {key} | {status} | {details}")
    
    def log_warning(self, message: str):
        """Log security warning"""
        self.logger.warning(f"SECURITY | {message}")

# =============================================================================
# ENCRYPTION HELPER
# =============================================================================

class ConfigEncryption:
    """AES-256 encryption for config backup"""
    
    @staticmethod
    def derive_key(password: str, salt: bytes = None) -> tuple:
        """Derive encryption key from password"""
        if not HAS_CRYPTO:
            raise ImportError("cryptography library required for encryption")
        
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @staticmethod
    def encrypt(data: dict, password: str) -> bytes:
        """Encrypt dictionary with AES-256"""
        key, salt = ConfigEncryption.derive_key(password)
        f = Fernet(key)
        encrypted = f.encrypt(json.dumps(data).encode())
        return salt + encrypted  # Prepend salt
    
    @staticmethod
    def decrypt(encrypted_data: bytes, password: str) -> dict:
        """Decrypt data with password"""
        salt = encrypted_data[:16]
        data = encrypted_data[16:]
        key, _ = ConfigEncryption.derive_key(password, salt)
        f = Fernet(key)
        decrypted = f.decrypt(data)
        return json.loads(decrypted.decode())

# =============================================================================
# CONFIGURATION DATACLASS
# =============================================================================

@dataclass
class SentinelConfig:
    """All configuration values for Project Sentinel"""
    
    # ---- MT5 Settings ----
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = "Exness-MT5Real"
    mt5_terminal_path: str = ""
    
    # ---- Risk Guardian Settings ----
    max_loss_production: float = -300  # Cents
    reset_hour: int = 4                # 04:00 AM
    reset_minute: int = 0              # 00
    symbol: str = "XAUUSDm"
    
    # ---- Monitoring Intervals ----
    normal_check_interval: float = 5.0
    block_check_interval: float = 0.5
    
    # ---- API Keys (NEVER commit these!) ----
    openrouter_api_key: str = ""
    line_notify_token: str = ""
    gemini_api_key: str = ""
    
    # ---- OpenRouter Settings ----
    openrouter_model: str = "google/gemini-2.0-flash-001"
    openrouter_fallback_model: str = "openai/gpt-4o-mini"
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.7
    
    # ---- Alerts (Discord) ----
    alert_email: str = ""
    discord_webhook_url: str = ""
    discord_bot_token: str = ""
    discord_guild_id: str = ""
    discord_channel_id: str = ""
    cost_alert_threshold: float = 1.0  # USD
    
    # ---- IP Whitelist (for API security) ----
    ip_whitelist: list = field(default_factory=list)
    
    def validate(self) -> tuple:
        """Validate configuration values. Returns (is_valid, errors_list)"""
        errors = []
        
        if self.mt5_login <= 0:
            errors.append("MT5 login must be a positive integer")
        
        if not self.mt5_password:
            errors.append("MT5 password is required")
        
        if not self.mt5_server:
            errors.append("MT5 server is required")
        
        if self.max_loss_production >= 0:
            errors.append("max_loss_production should be negative")
        
        if self.reset_hour < 0 or self.reset_hour > 23:
            errors.append("reset_hour must be 0-23")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> dict:
        """Convert to dictionary (for backup)"""
        return {
            'mt5_login': self.mt5_login,
            'mt5_server': self.mt5_server,
            'mt5_terminal_path': self.mt5_terminal_path,
            'max_loss_production': self.max_loss_production,
            'reset_hour': self.reset_hour,
            'reset_minute': self.reset_minute,
            'symbol': self.symbol,
            'normal_check_interval': self.normal_check_interval,
            'block_check_interval': self.block_check_interval,
            'openrouter_model': self.openrouter_model,
            'openrouter_fallback_model': self.openrouter_fallback_model,
            'ai_max_tokens': self.ai_max_tokens,
            'ai_temperature': self.ai_temperature,
            'alert_email': self.alert_email,
            'cost_alert_threshold': self.cost_alert_threshold,
            # NOTE: Sensitive keys are NOT included in backup by default
        }

# =============================================================================
# CONFIGURATION LOADER
# =============================================================================

class ConfigLoader:
    """Loads configuration from environment variables"""
    
    _instance: Optional['ConfigLoader'] = None
    _config: Optional[SentinelConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.audit = AuditLogger()
        self._loaded = False

    def _get_int(self, key: str, default: int) -> int:
        """Safely parse int from env"""
        val = os.getenv(key, "")
        if not val:
            return default
        try:
            return int(float(val))
        except ValueError:
            return default
            
    def _get_float(self, key: str, default: float) -> float:
        """Safely parse float from env"""
        val = os.getenv(key, "")
        if not val:
            return default
        try:
            return float(val)
        except ValueError:
            return default
            
    def load(self, env_file: Path = ENV_FILE) -> SentinelConfig:
        """Load configuration from .env file"""
        
        # Load .env if available
        if HAS_DOTENV and env_file.exists():
            load_dotenv(env_file, override=True)
            self.audit.log_access(".env", "LOAD", True, f"Loaded from {env_file}")
        elif not env_file.exists():
            self.audit.log_warning(f".env file not found at {env_file}")
        
        # Build config from environment
        config = SentinelConfig(
            # MT5
            mt5_login=self._get_int("MT5_LOGIN", 0),
            mt5_password=os.getenv("MT5_PASSWORD", ""),
            mt5_server=os.getenv("MT5_SERVER", "Exness-MT5Real"),
            mt5_terminal_path=os.getenv("MT5_TERMINAL_PATH", ""),
            
            # Risk Settings
            max_loss_production=self._get_float("MAX_LOSS_PRODUCTION", -300.0),
            reset_hour=self._get_int("RESET_HOUR", 4),
            reset_minute=self._get_int("RESET_MINUTE", 0),
            symbol=os.getenv("SYMBOL", "XAUUSDm"),
            
            # Intervals
            normal_check_interval=self._get_float("NORMAL_CHECK_INTERVAL", 5.0),
            block_check_interval=self._get_float("BLOCK_CHECK_INTERVAL", 0.5),
            
            # API Keys
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            
            # AI Settings
            openrouter_model=os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001"),
            openrouter_fallback_model=os.getenv("OPENROUTER_FALLBACK_MODEL", "openai/gpt-4o-mini"),
            ai_max_tokens=self._get_int("AI_MAX_TOKENS", 2000),
            ai_temperature=self._get_float("AI_TEMPERATURE", 0.7),
            
            # Alerts
            alert_email=os.getenv("ALERT_EMAIL", ""),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
            discord_guild_id=os.getenv("DISCORD_GUILD_ID", ""),
            discord_channel_id=os.getenv("DISCORD_CHANNEL_ID", ""),
            cost_alert_threshold=self._get_float("COST_ALERT_THRESHOLD", 1.0),
            
            # IP Whitelist
            ip_whitelist=os.getenv("IP_WHITELIST", "").split(",") if os.getenv("IP_WHITELIST") else [],
        )
        
        self._config = config
        self._loaded = True
        
        # Validate
        is_valid, errors = config.validate()
        if not is_valid:
            self.audit.log_warning(f"Config validation failed: {errors}")
        
        return config
    
    @property
    def config(self) -> SentinelConfig:
        """Get loaded config (load if needed)"""
        if not self._loaded:
            self.load()
        return self._config
    
    def create_encrypted_backup(self, password: str, 
                                 output_file: Path = CONFIG_BACKUP_FILE) -> bool:
        """Create encrypted backup of non-sensitive config"""
        if not HAS_CRYPTO:
            self.audit.log_warning("Encryption not available (install cryptography)")
            return False
        
        try:
            data = self.config.to_dict()
            encrypted = ConfigEncryption.encrypt(data, password)
            
            with open(output_file, 'wb') as f:
                f.write(encrypted)
            
            self.audit.log_access("backup", "CREATE", True, str(output_file))
            return True
            
        except Exception as e:
            self.audit.log_access("backup", "CREATE", False, str(e))
            return False
    
    def restore_from_backup(self, password: str, 
                           input_file: Path = CONFIG_BACKUP_FILE) -> Optional[dict]:
        """Restore config from encrypted backup"""
        if not HAS_CRYPTO:
            return None
        
        try:
            with open(input_file, 'rb') as f:
                encrypted = f.read()
            
            data = ConfigEncryption.decrypt(encrypted, password)
            self.audit.log_access("backup", "RESTORE", True, str(input_file))
            return data
            
        except Exception as e:
            self.audit.log_access("backup", "RESTORE", False, str(e))
            return None

# =============================================================================
# SAFE MODE
# =============================================================================

class SafeMode:
    """Emergency safe mode when config is corrupted"""
    
    @staticmethod
    def check_config_health() -> bool:
        """Check if configuration is usable"""
        try:
            loader = ConfigLoader()
            config = loader.load()
            is_valid, _ = config.validate()
            return is_valid
        except Exception:
            return False
    
    @staticmethod
    def enter_safe_mode(reason: str):
        """Enter safe mode - disable trading, send alert"""
        print("=" * 60)
        print("  ⚠️  SAFE MODE ACTIVATED")
        print("=" * 60)
        print(f"  Reason: {reason}")
        print("  Trading is DISABLED")
        print("  Please run config_setup.py to reconfigure")
        print("=" * 60)
        
        # Log to audit
        audit = AuditLogger()
        audit.log_warning(f"SAFE MODE ACTIVATED: {reason}")
        
        # TODO: Send email alert if configured
        
        return {
            'safe_mode': True,
            'trading_allowed': False,
            'reason': reason
        }

# =============================================================================
# HELPER FUNCTION
# =============================================================================

@lru_cache(maxsize=1)
def get_config() -> SentinelConfig:
    """Get singleton config instance"""
    loader = ConfigLoader()
    return loader.load()

# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("Testing configuration loader...")
    
    config = get_config()
    print(f"\nLoaded configuration:")
    print(f"  MT5 Login: {config.mt5_login}")
    print(f"  MT5 Server: {config.mt5_server}")
    print(f"  Max Daily Loss: {config.max_loss_production}")
    print(f"  Symbol: {config.symbol}")
    print(f"  Reset Time: {config.reset_hour}:{config.reset_minute:02d}")
    
    is_valid, errors = config.validate()
    print(f"\n  Valid: {is_valid}")
    if errors:
        print(f"  Errors: {errors}")
