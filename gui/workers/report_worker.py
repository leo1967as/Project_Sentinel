"""
Report Worker - Run Daily Report Generation in Background
"""

from PySide6.QtCore import QThread, Signal
import traceback
import sys
from pathlib import Path

# Add project root to path if needed (though usually handled by main)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from daily_report import DailyReportGenerator

class ReportGenWorker(QThread):
    """Worker for generating AI reports"""
    
    # Signals
    log = Signal(str, str)  # level, message
    finished = Signal(bool) # success
    error = Signal(str)
    
    def __init__(self, mode="TODAY", parent=None):
        super().__init__(parent)
        self.mode = mode
    
    def run(self):
        """Run report generation"""
        self.log.emit("INFO", f"🚀 Starting AI Report Generation ({self.mode})...")
        
        try:
            generator = DailyReportGenerator()
            
            # Hook into logger if possible, or just rely on generator's internal logging
            # (Note: standard logging will go to console/file, we might want to capture it to GUI log eventually)
            
            success = generator.generate_report(mode=self.mode)
            
            if success:
                self.log.emit("INFO", "✅ AI Report generated and sent successfully!")
                self.finished.emit(True)
            else:
                self.log.emit("ERROR", "❌ Report generation finished with errors")
                self.finished.emit(False)
                
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(f"Report Error: {str(e)}")
            self.log.emit("ERROR", f"Traceback: {tb}")
            self.finished.emit(False)
