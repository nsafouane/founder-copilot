import pytest
from typer.testing import CliRunner
from copilot.cli.main import app
from copilot.core.config import ConfigManager
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

runner = CliRunner()

@pytest.fixture
def mock_registry():
    with patch("copilot.cli.main.get_registry") as mock:
        registry = MagicMock()
        mock.return_value = registry
        
        # Mock storage
        storage = MagicMock()
        storage.get_posts.return_value = []
        storage.get_leads.return_value = []
        registry.get_storage.return_value = storage
        
        # Mock LLM
        llm = MagicMock()
        registry.get_llm.return_value = llm
        
        # Mock Scraper
        scraper = MagicMock()
        registry.get_scraper.return_value = scraper
        
        yield registry

def test_config_command():
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Founder Co-Pilot Configuration" in result.stdout

def test_config_set_command(tmp_path):
    result = runner.invoke(app, ["config", "llm_provider", "openai"])
    assert result.exit_code == 0
    assert "Set llm_provider = openai" in result.stdout

def test_leads_command(mock_registry):
    result = runner.invoke(app, ["leads"])
    assert result.exit_code == 0
    # The new leads command prints a table or a "No leads found" message
    assert "leads" in result.stdout.lower() or "no leads found" in result.stdout.lower()

def test_monitor_command(mock_registry):
    # Mock modules to avoid real scraping/LLM
    with patch("copilot.cli.main.MonitorModule") as mock_mod:
        instance = mock_mod.return_value
        instance.monitor_competitors.return_value = 0
        instance.run_periodic_discovery.return_value = 0
        
        result = runner.invoke(app, ["monitor"])
        assert result.exit_code == 0
        assert "Monitoring Run Complete" in result.stdout

def test_validate_command(mock_registry):
    with patch("copilot.cli.main.ValidationModule") as mock_mod:
        instance = mock_mod.return_value
        instance.validate_idea.return_value = MagicMock()
        instance.format_report_markdown.return_value = "# Report"
        
        result = runner.invoke(app, ["validate", "test_id"])
        assert result.exit_code == 0
        assert "Report" in result.stdout
