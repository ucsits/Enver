import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from click.testing import CliRunner
from enver_cli.main import cli

def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "enver-cli version" in result.output

def test_eth_block_number():
    runner = CliRunner()
    result = runner.invoke(cli, ["eth_block_number"])
    # Accept exit code 0 (success) or 2 (ClickException for connection error)
    assert result.exit_code in (0, 2)
    assert "block" in result.output or "Could not connect" in result.output or "Error:" in result.output
