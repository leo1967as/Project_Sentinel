"""
===============================================================================
PROJECT SENTINEL - CONFIGURATION SETUP WIZARD
===============================================================================
Interactive setup wizard for secure configuration.

Features:
- Guides user through credential entry
- Validates MT5 connection before saving
- Creates encrypted backup with password
- Never stores sensitive data in source code

Author: Project Sentinel
===============================================================================
"""

import os
import sys
import getpass
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False

from config import ConfigLoader, ConfigEncryption, HAS_CRYPTO

# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"
BACKUP_FILE = PROJECT_ROOT / "config_backup.enc"

# =============================================================================
# WIZARD
# =============================================================================

class SetupWizard:
    """Interactive configuration setup"""
    
    def __init__(self):
        self.config_values = {}
    
    def print_header(self):
        """Print welcome header"""
        print()
        print("=" * 60)
        print("  🛡️ PROJECT SENTINEL - CONFIGURATION WIZARD")
        print("=" * 60)
        print()
        print("  This wizard will help you set up your trading bot securely.")
        print("  Your credentials will NEVER be stored in source code.")
        print()
        print("=" * 60)
        print()
    
    def print_section(self, title: str):
        """Print section header"""
        print()
        print(f"━━━ {title} ━━━")
        print()
    
    def get_input(self, prompt: str, default: str = "", 
                  secret: bool = False, required: bool = True) -> str:
        """Get user input with default value support"""
        if default:
            display = f"{prompt} [{default}]: "
        else:
            display = f"{prompt}: "
        
        while True:
            if secret:
                value = getpass.getpass(display)
            else:
                value = input(display)
            
            value = value.strip() or default
            
            if required and not value:
                print("  ⚠️ This field is required")
                continue
            
            return value
    
    def get_bool(self, prompt: str, default: bool = True) -> bool:
        """Get boolean input"""
        default_str = "Y/n" if default else "y/N"
        value = input(f"{prompt} [{default_str}]: ").strip().lower()
        
        if not value:
            return default
        return value in ('y', 'yes', 'true', '1')
    
    def validate_mt5_connection(self, login: int, password: str, 
                                server: str) -> bool:
        """Validate MT5 credentials"""
        if not HAS_MT5:
            print("  ⚠️ MetaTrader5 not installed, skipping validation")
            return True
        
        print("  Testing MT5 connection...")
        
        if mt5.initialize(login=login, password=password, server=server):
            account = mt5.account_info()
            if account:
                print(f"  ✅ Connected to Account: {account.login}")
                print(f"     Server: {account.server}")
                print(f"     Balance: {account.balance:.2f} {account.currency}")
                mt5.shutdown()
                return True
        
        error = mt5.last_error()
        print(f"  ❌ Connection failed: {error}")
        mt5.shutdown()
        return False
    
    def run_mt5_setup(self):
        """Setup MT5 credentials"""
        self.print_section("MT5 Credentials")
        
        while True:
            login = self.get_input("MT5 Account Login (number)")
            
            try:
                login_int = int(login)
            except ValueError:
                print("  ⚠️ Login must be a number")
                continue
            
            password = self.get_input("MT5 Password", secret=True)
            server = self.get_input("MT5 Server", default="Exness-MT5Real")
            terminal_path = self.get_input("MT5 Terminal Path (optional)", required=False)
            
            # Validate
            if self.validate_mt5_connection(login_int, password, server):
                self.config_values['MT5_LOGIN'] = login
                self.config_values['MT5_PASSWORD'] = password
                self.config_values['MT5_SERVER'] = server
                if terminal_path:
                    self.config_values['MT5_TERMINAL_PATH'] = terminal_path
                break
            else:
                retry = self.get_bool("Try again?")
                if not retry:
                    print("  Skipping MT5 validation...")
                    self.config_values['MT5_LOGIN'] = login
                    self.config_values['MT5_PASSWORD'] = password
                    self.config_values['MT5_SERVER'] = server
                    break
    
    def run_risk_setup(self):
        """Setup risk parameters"""
        self.print_section("Risk Settings")
        
        test_mode = self.get_bool("Enable TEST MODE? (recommended for initial setup)")
        self.config_values['TEST_MODE'] = 'true' if test_mode else 'false'
        
        max_loss = self.get_input("Max Loss PRODUCTION (cents)", default="-300")
        self.config_values['MAX_LOSS_PRODUCTION'] = max_loss
        
        max_loss_test = self.get_input("Max Loss TEST (cents)", default="-10")
        self.config_values['MAX_LOSS_TEST'] = max_loss_test
        
        reset_hour = self.get_input("Daily Reset Hour (0-23)", default="4")
        self.config_values['RESET_HOUR'] = reset_hour
        
        symbol = self.get_input("Trading Symbol", default="XAUUSDm")
        self.config_values['SYMBOL'] = symbol
    
    def run_api_setup(self):
        """Setup API keys"""
        self.print_section("API Keys (Optional)")
        
        print("  These keys are optional. Press Enter to skip.")
        print()
        
        openrouter = self.get_input("OpenRouter API Key", required=False, secret=True)
        if openrouter:
            self.config_values['OPENROUTER_API_KEY'] = openrouter
        
        line = self.get_input("Line Notify Token", required=False, secret=True)
        if line:
            self.config_values['LINE_NOTIFY_TOKEN'] = line
        
        gemini = self.get_input("Gemini API Key (backup)", required=False, secret=True)
        if gemini:
            self.config_values['GEMINI_API_KEY'] = gemini
    
    def run_alert_setup(self):
        """Setup alerts"""
        self.print_section("Alerts (Optional)")
        
        email = self.get_input("Alert Email", required=False)
        if email:
            self.config_values['ALERT_EMAIL'] = email
        
        cost = self.get_input("Cost Alert Threshold (USD)", default="1.0")
        self.config_values['COST_ALERT_THRESHOLD'] = cost
    
    def save_env_file(self):
        """Save configuration to .env file"""
        self.print_section("Saving Configuration")
        
        # Add defaults for optional values
        defaults = {
            'NORMAL_CHECK_INTERVAL': '5.0',
            'BLOCK_CHECK_INTERVAL': '0.5',
            'OPENROUTER_MODEL': 'google/gemini-2.0-flash-001',
            'OPENROUTER_FALLBACK_MODEL': 'openai/gpt-4o-mini',
            'AI_MAX_TOKENS': '2000',
            'AI_TEMPERATURE': '0.7',
        }
        
        for key, value in defaults.items():
            if key not in self.config_values:
                self.config_values[key] = value
        
        # Write .env file
        content = f"""# ===============================================================================
# PROJECT SENTINEL - ENVIRONMENT CONFIGURATION
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ===============================================================================
# WARNING: NEVER COMMIT THIS FILE TO GIT!
# ===============================================================================

"""
        for key, value in sorted(self.config_values.items()):
            content += f"{key}={value}\n"
        
        with open(ENV_FILE, 'w') as f:
            f.write(content)
        
        print(f"  ✅ Configuration saved to: {ENV_FILE}")
    
    def create_backup(self):
        """Create encrypted backup"""
        if not HAS_CRYPTO:
            print("  ⚠️ cryptography not installed, skipping backup")
            print("     Install with: pip install cryptography")
            return
        
        self.print_section("Encrypted Backup")
        
        create = self.get_bool("Create encrypted backup?")
        if not create:
            return
        
        print()
        print("  Enter a strong password for the backup.")
        print("  ⚠️ If you forget this password, data cannot be recovered!")
        print()
        
        while True:
            password = getpass.getpass("  Backup Password: ")
            confirm = getpass.getpass("  Confirm Password: ")
            
            if password != confirm:
                print("  ❌ Passwords don't match")
                continue
            
            if len(password) < 8:
                print("  ⚠️ Password should be at least 8 characters")
                if not self.get_bool("Continue anyway?", default=False):
                    continue
            
            break
        
        # Create backup (exclude sensitive keys from main backup)
        backup_data = {k: v for k, v in self.config_values.items() 
                       if 'PASSWORD' not in k and 'KEY' not in k and 'TOKEN' not in k}
        backup_data['_backup_time'] = datetime.now().isoformat()
        
        encrypted = ConfigEncryption.encrypt(backup_data, password)
        
        with open(BACKUP_FILE, 'wb') as f:
            f.write(encrypted)
        
        print(f"  ✅ Backup saved to: {BACKUP_FILE}")
    
    def run(self):
        """Run the full setup wizard"""
        self.print_header()
        
        # Check if .env already exists
        if ENV_FILE.exists():
            overwrite = self.get_bool("Configuration already exists. Overwrite?")
            if not overwrite:
                print("  Setup cancelled.")
                return
        
        # Run setup steps
        self.run_mt5_setup()
        self.run_risk_setup()
        self.run_api_setup()
        self.run_alert_setup()
        
        # Save
        self.save_env_file()
        self.create_backup()
        
        # Final message
        print()
        print("=" * 60)
        print("  ✅ SETUP COMPLETE!")
        print("=" * 60)
        print()
        print("  Next steps:")
        print("  1. Run: python main_guardian.py")
        print("  2. Or use: run_guardian.bat")
        print()
        print("  Remember:")
        print("  - NEVER commit .env to Git")
        print("  - Keep your backup password safe")
        print()

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    wizard = SetupWizard()
    wizard.run()
