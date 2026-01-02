
import pytest
import os
from PySide6.QtWidgets import QApplication, QDialog, QDoubleSpinBox, QCheckBox, QSpinBox
from PySide6.QtCore import Qt
from gui.dialogs.settings_dialog import SettingsDialog
from gui.main_window import SentinelMainWindow

@pytest.fixture
def app(qtbot):
    """Fixture to ensure QApplication exists"""
    # qtbot fixture from pytest-qt handles QApplication automatically
    return qtbot

@pytest.fixture
def settings_dialog(qtbot, mocker):
    """Fixture to create SettingsDialog with mocked parent"""
    # Mock parent to avoid side effects
    # PySide6 strict typing rejects Mock objects, so use None
    dialog = SettingsDialog(None)
    qtbot.addWidget(dialog)
    return dialog

def test_settings_dialog_init(settings_dialog):
    """Test that dialog initializes without error"""
    assert isinstance(settings_dialog, QDialog)
    assert settings_dialog.windowTitle() == "⚙️ Settings"

def test_settings_dialog_fields_exist(settings_dialog):
    """Test that all required fields exist"""
    assert isinstance(settings_dialog.max_loss_production, QDoubleSpinBox)
    assert isinstance(settings_dialog.reset_hour, QSpinBox)
    assert isinstance(settings_dialog.reset_minute, QSpinBox)

def test_load_settings(settings_dialog, mocker):
    """Test that settings are loaded correctly"""
    # Mock file content
    mock_content = "MAX_LOSS_PRODUCTION=-500\nRESET_HOUR=12\nRESET_MINUTE=30\nSYMBOL=EURUSD"
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    # Ensure exists return True so it doesn't return early
    # (Note: Path.exists is a property or method depending on python version/mocking, simple patch works usually)
    # But since we are patching open, we should also ensure exists is True for the path object
    # If using pathlib, mocking Path.exists is best.
    mocker.patch('pathlib.Path.exists', return_value=True)
    
    # Trigger load
    settings_dialog._load_settings()
    
    assert settings_dialog.max_loss_production.value() == -500.0
    assert settings_dialog.reset_hour.value() == 12 # From mock content 12
    assert settings_dialog.reset_minute.value() == 30 # From mock content 30
    assert settings_dialog.symbol.text() == 'EURUSD'

def test_save_settings(settings_dialog, mocker):
    """Test that settings are saved correctly"""
    # Set values
    settings_dialog.max_loss_production.setValue(-1000)
    settings_dialog.reset_hour.setValue(12)
    settings_dialog.reset_minute.setValue(15)
    settings_dialog.symbol.setText('BTCUSD')
    
    # Mock file writing to avoid touching real .env
    mocker.patch('builtins.open', mocker.mock_open())
    mocker.patch.object(settings_dialog, 'accept') # Prevent dialog closing
    mocker.patch('PySide6.QtWidgets.QMessageBox.information') # Suppress popup
    
    settings_dialog._save_settings()
    
    # Verify internal settings dict updated
    assert settings_dialog._settings['MAX_LOSS_PRODUCTION'] == '-1000'
    assert settings_dialog._settings['RESET_HOUR'] == '12' # QSpinBox returns int
    assert settings_dialog._settings['RESET_MINUTE'] == '15'
    assert settings_dialog._settings['SYMBOL'] == 'BTCUSD'
