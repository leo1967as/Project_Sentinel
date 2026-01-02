
import pytest
from PySide6.QtWidgets import QApplication
from gui.main_window import SentinelMainWindow
from gui.widgets.pnl_gauge import PnLGaugeWidget

@pytest.fixture
def app(qtbot):
    return qtbot

@pytest.fixture
def main_window(qtbot, mocker):
    """Fixture to create MainWindow with mocked dependencies"""
    # Mock ConfigLoader to return predictable config
    mock_config = mocker.Mock()
    mock_config.max_loss_production = -300
    mock_config.reset_hour = 4
    mock_config.reset_minute = 0
    # ensure it DOES NOT have test_mode
    del mock_config.test_mode 
    del mock_config.max_loss_test
    
    mocker.patch('gui.main_window.get_config', return_value=mock_config)
    
    window = SentinelMainWindow()
    qtbot.addWidget(window)
    return window

def test_main_window_init(main_window):
    """Test that main window initializes correctly"""
    assert "Sentinel" in main_window.windowTitle()
    assert isinstance(main_window.pnl_gauge, PnLGaugeWidget)

def test_settings_saved_handler(main_window, mocker):
    """Test _on_settings_saved handles config items correctly"""
    # Mock a new config returning different values
    new_config = mocker.Mock()
    new_config.max_loss_production = -500.0
    # Again, ensure NO test_mode
    del new_config.test_mode
    
    mocker.patch('gui.main_window.get_config', return_value=new_config)
    
    # Trigger the slot
    main_window._on_settings_saved()
    
    # Verify threshold was updated (this would crash if test_mode was accessed)
    # Access private attribute for verification if needed or check gauge
    # Assuming set_threshold accesses valid logic
    assert main_window._config.max_loss_production == -500.0
