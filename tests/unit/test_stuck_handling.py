"""Tests for stuck extraction handling."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from extractall.core.interfaces import ExtractionResult
from extractall.strategies.basic_strategy import BasicExtractionStrategy
from extractall.config.settings import create_default_config


def test_basic_strategy_handles_stuck():
    """Test that basic strategy returns STUCK on timeout."""
    config = create_default_config(Path("/tmp"))
    strategy = BasicExtractionStrategy(config)
    
    # Mock archive info
    archive_info = Mock()
    archive_info.type = "zip"
    archive_info.path = Path("/tmp/test.zip")
    
    # Mock handler that raises TimeoutExpired
    with patch.object(strategy.handler_registry, 'get_handler') as mock_get_handler:
        mock_handler = Mock()
        mock_handler.extract.side_effect = subprocess.TimeoutExpired("cmd", 300)
        mock_get_handler.return_value = mock_handler
        
        result = strategy.extract(archive_info, Path("/tmp/output"))
        assert result == ExtractionResult.STUCK
