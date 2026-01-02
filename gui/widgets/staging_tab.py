
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, 
    QListWidgetItem, QLabel, QPushButton, QTextEdit, QComboBox, 
    QGroupBox, QCheckBox, QScrollArea, QFrame, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Slot, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QColor, QFont

from daily_report import JournalManager

class StagingTab(QWidget):
    """
    Staging Area for Trade Analysis (Trading Journal)
    Allows users to:
    1. Select battle (cluster of trades)
    2. Add context (Strategy, Notes, Emotion)
    3. Send to AI for analysis
    """
    
    def __init__(self):
        super().__init__()
        self.journal_manager = JournalManager()
        self.current_battle_id: Optional[str] = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header / Toolbar
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Refresh Battles")
        self.refresh_btn.clicked.connect(self.refresh_battles)
        self.refresh_btn.setStyleSheet("background-color: #2196F3;")
        
        self.analyze_btn = QPushButton("🚀 Analyze Selected")
        self.analyze_btn.clicked.connect(self.analyze_current)
        self.analyze_btn.setStyleSheet("background-color: #9C27B0; font-weight: bold;")
        self.analyze_btn.setEnabled(False)
        
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.analyze_btn)
        
        layout.addLayout(toolbar)
        
        # Main Content (3 Columns)
        splitter = QSplitter(Qt.Horizontal)
        
        # --- LEFT: Battle List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_label = QLabel("⚔️ Battle List")
        left_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.battle_list = QListWidget()
        self.battle_list.itemClicked.connect(self._on_battle_selected)
        
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.battle_list)
        
        # --- MIDDLE: Preview & Context ---
        mid_panel = QScrollArea()
        mid_panel.setWidgetResizable(True)
        mid_widget = QWidget()
        mid_layout = QVBoxLayout(mid_widget)
        
        # Chart Preview
        self.chart_label = QLabel("Select a battle to preview")
        self.chart_label.setAlignment(Qt.AlignCenter)
        self.chart_label.setMinimumHeight(300)
        self.chart_label.setStyleSheet("border: 2px dashed #444; border-radius: 8px;")
        self.chart_label.setScaledContents(True)
        
        # Context Inputs
        context_group = QGroupBox("📝 Trader Context")
        context_layout = QVBoxLayout()
        
        # Strategy
        strat_layout = QHBoxLayout()
        strat_layout.addWidget(QLabel("Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Select Strategy...",
            "SMC - FVG", "SMC - Order Block", "SMC - BOS/CHoCH", "SMC - Liquidity Sweep",
            "Breakout", "Reversal", "Trend Following", "News Trade", 
            "Scalping", "Mouth Lun (มือลั่น)", "Test/Experiment"
        ])
        strat_layout.addWidget(self.strategy_combo)
        
        # Emotion
        emo_layout = QHBoxLayout()
        emo_layout.addWidget(QLabel("Emotion:"))
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems(["1 - Calm/Zen", "2 - Focused", "3 - Neutral", "4 - Frustrated", "5 - Tilted/Angry"])
        self.emotion_combo.setCurrentIndex(2) # Default Neutral
        emo_layout.addWidget(self.emotion_combo)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Why did you take this trade? What were you thinking?")
        self.notes_input.setMaximumHeight(100)
        
        # Save Context Button
        self.save_context_btn = QPushButton("💾 Save Context")
        self.save_context_btn.clicked.connect(self.save_current_context)
        
        context_layout.addLayout(strat_layout)
        context_layout.addLayout(emo_layout)
        context_layout.addWidget(QLabel("Notes:"))
        context_layout.addWidget(self.notes_input)
        context_layout.addWidget(self.save_context_btn)
        context_group.setLayout(context_layout)
        
        mid_layout.addWidget(QLabel("📸 Chart Preview"))
        mid_layout.addWidget(self.chart_label)
        mid_layout.addWidget(context_group)
        mid_layout.addStretch()
        
        mid_panel.setWidget(mid_widget)
        
        # --- RIGHT: AI Analysis ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("🤖 AI Coach Analysis"))
        self.ai_response_view = QTextEdit()
        self.ai_response_view.setReadOnly(True)
        self.ai_response_view.setPlaceholderText("Analysis will appear here...")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0) # Indeterminate
        
        right_layout.addWidget(self.ai_response_view)
        right_layout.addWidget(self.progress_bar)
        
        # Add to Splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(mid_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        
        layout.addWidget(splitter)
        
        # Initial Load
        self.refresh_battles()

    def refresh_battles(self):
        """Load battles from JournalManager"""
        self.battle_list.clear()
        try:
            self.battles = self.journal_manager.sync_battles()
            
            # Sort by start time desc (handle both str and datetime just in case)
            def get_time(item):
                t = item.get('start_time', '')
                return str(t)
                
            self.battles.sort(key=get_time, reverse=True)
            
            for b in self.battles:
                try:
                    start_t = b.get('start_time')
                    if isinstance(start_t, datetime):
                        time_str = start_t.strftime("%H:%M")
                    else:
                        # Assume ISO string
                        time_str = datetime.fromisoformat(str(start_t)).strftime("%H:%M")
                except Exception:
                    time_str = "??"

                pnl = b.get('pnl', 0.0)
                count = b.get('trade_count', 0)
                status = b.get('status', 'pending')
                
                # Format Item Text
                status_icon = "✅" if status == 'analyzed' else "⏳"
                text = f"{status_icon} {time_str} | ${pnl:+.2f} | {count} Runs"
                
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, b['battle_id'])
                
                # Color coding
                if pnl > 0:
                    item.setForeground(QColor('#00ff88'))
                else:
                    item.setForeground(QColor('#ff4757'))
                    
                self.battle_list.addItem(item)
                
        except Exception as e:
            logging.error(f"Error refreshing battles: {e}")
            self.battle_list.addItem(f"Error: {e}")
            
    def _on_battle_selected(self, item):
        battle_id = item.data(Qt.UserRole)
        self.current_battle_id = battle_id
        self.analyze_btn.setEnabled(True)
        
        # Find data
        battle_data = next((b for b in self.battles if b['battle_id'] == battle_id), None)
        if not battle_data:
            return
            
        # 1. Load Context
        self.notes_input.setText(battle_data.get('user_notes', ''))
        
        strat = battle_data.get('strategy_tag', '')
        index = self.strategy_combo.findText(strat)
        if index >= 0:
            self.strategy_combo.setCurrentIndex(index)
        else:
            self.strategy_combo.setCurrentIndex(0)
            
        emo = battle_data.get('emotion_score', 0)
        # simplistic mapping 1-5 to index 0-4
        if emo > 0:
            self.emotion_combo.setCurrentIndex(emo - 1)
        else:
            self.emotion_combo.setCurrentIndex(2) # Default
            
        # 2. Load Analysis
        analysis = battle_data.get('ai_analysis', '')
        if analysis:
            self.ai_response_view.setMarkdown(analysis)
        else:
            self.ai_response_view.clear()
            
        # 3. Load Chart (Preview) NOT GENERATED YET?
        # We need to ask manager to generate preview if not exists?
        # Or maybe just show placeholder until analyzed?
        # Better: Try to find if chart exists.
        # Actually daily_report generates charts during analysis. 
        # But for 'preview', we might want to generate it NOW.
        # Let's add a `generate_preview` method to manager later if needed.
        self.chart_label.setText("Click 'Analyze' to generate chart & analysis")

    def save_current_context(self):
        if not self.current_battle_id:
            return
            
        strat = self.strategy_combo.currentText()
        if strat == "Select Strategy...":
            strat = ""
            
        notes = self.notes_input.toPlainText()
        
        # Map emotion combo index 0..4 to score 1..5
        emo = self.emotion_combo.currentIndex() + 1
        
        success = self.journal_manager.update_context(
            self.current_battle_id, strat, notes, emo
        )
        
        if success:
            # Update local cache
            for b in self.battles:
                if b['battle_id'] == self.current_battle_id:
                    b['strategy_tag'] = strat
                    b['user_notes'] = notes
                    b['emotion_score'] = emo
                    break
            QMessageBox.information(self, "Saved", "Context saved successfully!")
        else:
            QMessageBox.warning(self, "Error", "Failed to save context")

    def analyze_current(self):
        if not self.current_battle_id:
            return
            
        # Auto-save context first
        self.save_current_context()
        
        self.progress_bar.setVisible(True)
        self.analyze_btn.setEnabled(False)
        self.ai_response_view.setText("Analyzing... This may take a minute...")
        
        # Run in background? Ideally yes. But for now, simple blocking or simple threading.
        # Since we are in GUI, blocking is bad.
        # But to be quick, let's use QTimer.singleShot to allow UI update then run.
        # OR use a Worker.
        
        # Using a simple delayed call to let UI show 'Analyzing...'
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._run_analysis_task)
        
    def _run_analysis_task(self):
        try:
            success = self.journal_manager.analyze_staged_battle(self.current_battle_id)
            if success:
                # Reload data
                battle_data = self.journal_manager.db.get_journal_entry(self.current_battle_id)
                self.ai_response_view.setMarkdown(battle_data.get('ai_analysis', 'Error displaying analysis'))
                self.refresh_battles() # Update icon
            else:
                self.ai_response_view.setText("Analysis Failed. Check logs.")
        except Exception as e:
            self.ai_response_view.setText(f"Error: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
            self.analyze_btn.setEnabled(True)
