"""
===============================================================================
PROJECT SENTINEL - MAIN GUARDIAN CONTROLLER
===============================================================================
Master controller that orchestrates all Sentinel components.

Features:
- Initializes MT5 connection
- Runs Risk Guardian and Data Collector in parallel threads
- Monitors system health (CPU, memory, connection)
- Auto-restarts failed components
- Provides health check endpoint for remote monitoring

Author: Project Sentinel
Hardware: Intel N95 Mini PC (24/7 operation)
===============================================================================
"""

import sys
import time
import signal
import threading
import logging
import json
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config, SafeMode, AuditLogger
from utils.mt5_connect import get_mt5_manager

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Health check HTTP server
HEALTH_CHECK_PORT = 8765

# Component restart settings
MAX_RESTART_ATTEMPTS = 5
RESTART_COOLDOWN = 60  # seconds

# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("main_guardian")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler(LOG_DIR / "main_guardian.log", encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(fh)
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
    logger.addHandler(ch)

# =============================================================================
# COMPONENT STATE
# =============================================================================

@dataclass
class ComponentState:
    """Track state of a managed component"""
    name: str
    running: bool = False
    thread: Optional[threading.Thread] = None
    start_time: Optional[datetime] = None
    restart_count: int = 0
    last_error: str = ""
    last_activity: Optional[datetime] = None

# =============================================================================
# HEALTH CHECK HTTP SERVER
# =============================================================================

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks"""
    
    guardian: 'MainGuardian' = None  # Set by MainGuardian
    
    def do_GET(self):
        if self.path == '/health':
            self.send_health_response()
        elif self.path == '/status':
            self.send_status_response()
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_health_response(self):
        """Simple UP/DOWN health check"""
        if self.guardian and self.guardian.is_healthy():
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(503)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'UNHEALTHY')
    
    def send_status_response(self):
        """Detailed JSON status"""
        if self.guardian:
            status = self.guardian.get_status()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2, default=str).encode())
        else:
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress HTTP logs"""
        pass

# =============================================================================
# MAIN GUARDIAN
# =============================================================================

class MainGuardian:
    """
    Master controller for Project Sentinel.
    Manages all components and ensures 24/7 operation.
    """
    
    def __init__(self):
        self.config = get_config()
        self.audit = AuditLogger()
        self.running = False
        self.safe_mode = False
        
        # Component states
        self.components: Dict[str, ComponentState] = {
            'risk_guardian': ComponentState(name='Risk Guardian'),
            'data_collector': ComponentState(name='Data Collector'),
        }
        
        # MT5 manager
        self.mt5 = get_mt5_manager()
        
        # Stop event for graceful shutdown
        self.stop_event = threading.Event()
        
        # Health check server
        self.health_server: Optional[HTTPServer] = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal")
        self.stop()
    
    # =========================================================================
    # SYSTEM HEALTH
    # =========================================================================
    
    def get_system_health(self) -> Dict:
        """Get system resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent if sys.platform != 'win32' else psutil.disk_usage('C:').percent,
            'uptime_seconds': time.time() - psutil.boot_time()
        }
    
    def get_mt5_health(self) -> Dict:
        """Get MT5 connection health"""
        return self.mt5.health_check()
    
    def is_healthy(self) -> bool:
        """Check if system is healthy overall"""
        # Check safe mode
        if self.safe_mode:
            return False
        
        # Check MT5 connection
        if not self.mt5.is_connected():
            return False
        
        # Check all components running
        for state in self.components.values():
            if not state.running:
                return False
        
        return True
    
    def get_status(self) -> Dict:
        """Get detailed system status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'healthy': self.is_healthy(),
            'safe_mode': self.safe_mode,
            'running': self.running,
            'system': self.get_system_health(),
            'mt5': self.get_mt5_health(),
            'components': {
                name: {
                    'running': state.running,
                    'restart_count': state.restart_count,
                    'last_error': state.last_error,
                    'uptime': str(datetime.now() - state.start_time) if state.start_time else None
                }
                for name, state in self.components.items()
            }
        }
    
    # =========================================================================
    # COMPONENT MANAGEMENT
    # =========================================================================
    
    def _run_risk_guardian(self):
        """Run Risk Guardian component"""
        from active_block_monitor import TradingGuardian
        
        state = self.components['risk_guardian']
        state.running = True
        state.start_time = datetime.now()
        
        try:
            # Pass stop_event to guardian so it can be stopped externally
            guardian = TradingGuardian(stop_event=self.stop_event)
            
            # Connect to MT5 (uses existing connection from mt5_connect)
            if not guardian.connect():
                raise Exception("Could not connect to MT5")
            
            guardian.running = True
            guardian.log_action("START", f"Guardian active (limit: {guardian.max_loss})", "MONITORING")
            
            # Main loop
            while not self.stop_event.is_set() and guardian.running:
                if guardian.state.is_trading_allowed:
                    guardian.run_normal_mode()
                    self.stop_event.wait(5.0)
                else:
                    guardian.run_block_mode()
                    self.stop_event.wait(0.5)
                
                state.last_activity = datetime.now()
            
            guardian.disconnect()
                
        except Exception as e:
            state.last_error = str(e)
            logger.error(f"Risk Guardian error: {e}")
        finally:
            state.running = False
    
    def _run_data_collector(self):
        """Run Data Collector component"""
        from data_collector import DataCollector
        
        state = self.components['data_collector']
        state.running = True
        state.start_time = datetime.now()
        
        try:
            collector = DataCollector()
            
            # Use our stop event
            collector.stop_event = self.stop_event
            
            # Start collection threads
            import threading
            
            tick_thread = threading.Thread(
                target=collector.tick_collector.run,
                args=(self.stop_event,)
            )
            tick_thread.daemon = True
            tick_thread.start()
            
            news_thread = threading.Thread(
                target=collector.news_scraper.run,
                args=(self.stop_event,)
            )
            news_thread.daemon = True
            news_thread.start()
            
            # Monitor threads
            while not self.stop_event.is_set():
                state.last_activity = datetime.now()
                self.stop_event.wait(60)
                
        except Exception as e:
            state.last_error = str(e)
            logger.error(f"Data Collector error: {e}")
        finally:
            state.running = False
    
    def _start_component(self, name: str, target: Callable):
        """Start a component in a new thread"""
        state = self.components[name]
        
        if state.running:
            logger.warning(f"{name} already running")
            return
        
        state.restart_count += 1
        state.thread = threading.Thread(target=target, name=name)
        state.thread.daemon = True
        state.thread.start()
        
        logger.info(f"Started {name} (attempt #{state.restart_count})")
    
    def _monitor_components(self):
        """Monitor and restart failed components"""
        for name, state in self.components.items():
            if not state.running and state.restart_count < MAX_RESTART_ATTEMPTS:
                # Check cooldown
                if state.start_time:
                    elapsed = (datetime.now() - state.start_time).total_seconds()
                    if elapsed < RESTART_COOLDOWN:
                        continue
                
                logger.warning(f"{name} not running, restarting...")
                
                if name == 'risk_guardian':
                    self._start_component(name, self._run_risk_guardian)
                elif name == 'data_collector':
                    self._start_component(name, self._run_data_collector)
            
            elif state.restart_count >= MAX_RESTART_ATTEMPTS:
                if not self.safe_mode:
                    logger.error(f"{name} exceeded max restarts, entering safe mode")
                    self.enter_safe_mode(f"{name} failed repeatedly")
    
    # =========================================================================
    # SAFE MODE
    # =========================================================================
    
    def enter_safe_mode(self, reason: str):
        """Enter safe mode - stop all trading"""
        self.safe_mode = True
        SafeMode.enter_safe_mode(reason)
        self.audit.log_warning(f"SAFE MODE: {reason}")
    
    # =========================================================================
    # MAIN CONTROL
    # =========================================================================
    
    def _start_health_server(self):
        """Start HTTP health check server"""
        try:
            HealthCheckHandler.guardian = self
            self.health_server = HTTPServer(('0.0.0.0', HEALTH_CHECK_PORT), HealthCheckHandler)
            
            thread = threading.Thread(target=self.health_server.serve_forever)
            thread.daemon = True
            thread.start()
            
            logger.info(f"Health check server started on port {HEALTH_CHECK_PORT}")
        except Exception as e:
            logger.warning(f"Could not start health server: {e}")
    
    def start(self):
        """Start the main guardian"""
        print("=" * 60)
        print("  PROJECT SENTINEL - MAIN GUARDIAN")
        print("=" * 60)
        print(f"  Mode: {'TEST' if self.config.test_mode else 'PRODUCTION'}")
        print(f"  Health Check: http://localhost:{HEALTH_CHECK_PORT}/health")
        print("=" * 60)
        print()
        
        # Check config health
        if not SafeMode.check_config_health():
            self.enter_safe_mode("Configuration validation failed")
            return
        
        # Connect to MT5
        logger.info("Connecting to MT5...")
        if not self.mt5.connect():
            logger.error("Failed to connect to MT5")
            self.enter_safe_mode("MT5 connection failed")
            return
        
        self.running = True
        self.audit.log_access("main_guardian", "START", True)
        
        # Start health check server
        self._start_health_server()
        
        # Start components
        self._start_component('risk_guardian', self._run_risk_guardian)
        time.sleep(2)  # Stagger startup
        self._start_component('data_collector', self._run_data_collector)
        
        logger.info("All components started. Entering monitoring loop.")
        
        # Main monitoring loop
        try:
            while self.running and not self.stop_event.is_set():
                self._monitor_components()
                
                # Log status periodically
                if datetime.now().minute % 5 == 0:  # Every 5 minutes
                    status = self.get_status()
                    logger.debug(f"Status: {json.dumps(status, default=str)}")
                
                self.stop_event.wait(30)  # Check every 30 seconds
                
        except Exception as e:
            logger.error(f"Main loop error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop all components gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping all components...")
        self.running = False
        self.stop_event.set()
        
        # Stop health server
        if self.health_server:
            self.health_server.shutdown()
        
        # Wait for threads
        for name, state in self.components.items():
            if state.thread and state.thread.is_alive():
                logger.info(f"Waiting for {name} to stop...")
                state.thread.join(timeout=10)
        
        # Disconnect MT5
        self.mt5.disconnect()
        
        self.audit.log_access("main_guardian", "STOP", True)
        logger.info("Main Guardian stopped")
        
        # Print final status
        print("\n" + "=" * 60)
        print("  SHUTDOWN COMPLETE")
        print("=" * 60)
        for name, state in self.components.items():
            print(f"  {name}: restarts={state.restart_count}")
        print("=" * 60)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    guardian = MainGuardian()
    guardian.start()
