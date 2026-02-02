import pytest
from typer.testing import CliRunner
from copilot.cli.main import app
from copilot.core.config import ConfigManager
import os
import shutil
from pathlib import Path

runner = CliRunner()

@pytest.fixture
def temp_config(tmp_path):
    config_file = tmp_path / "config.json"
    db_path = tmp_path / "test.db"
    manager = ConfigManager(config_path=config_file)
    manager.set("db_path", str(db_path))
    return manager

def test_config_command():
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Founder Co-Pilot Configuration" in result.stdout

def test_config_set_command(tmp_path):
    # We use a custom config path via env var if the app supported it, 
    # but for CLI testing we'll just check if it runs.
    result = runner.invoke(app, ["config", "llm_provider", "openai"])
    assert result.exit_code == 0
    assert "Set llm_provider = openai" in result.stdout

def test_leads_command():
    result = runner.invoke(app, ["leads"])
    assert result.exit_code == 0
    assert "Leads management" in result.stdout

def test_monitor_command():
    result = runner.invoke(app, ["monitor"])
    assert result.exit_code == 0
    assert "Monitoring subreddits" in result.stdout

def test_validate_command():
    result = runner.invoke(app, ["validate", "test_id"])
    assert result.exit_code == 0
    assert "Validation logic for post test_id" in result.stdout

# Discovery test would require mocks for Reddit and Groq
# which are handled in unit tests for modules/discovery.py
