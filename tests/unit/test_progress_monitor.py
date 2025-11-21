"""Tests for progress monitoring."""

import time
import tempfile
from pathlib import Path
import pytest

from extractall.utils.progress_monitor import ProgressMonitor


def test_progress_monitor_detects_stuck():
    """Test that monitor detects stuck extraction."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        monitor = ProgressMonitor(output_dir, stuck_timeout=1)  # 1 second timeout
        
        monitor.start_monitoring()
        time.sleep(1.5)  # Wait longer than timeout
        
        assert monitor.is_stuck()
        monitor.stop_monitoring()


def test_progress_monitor_detects_progress():
    """Test that monitor detects ongoing progress."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        monitor = ProgressMonitor(output_dir, stuck_timeout=2)
        
        monitor.start_monitoring()
        time.sleep(0.5)
        
        # Create a file to simulate progress
        (output_dir / "test.txt").write_text("progress")
        time.sleep(1)
        
        assert not monitor.is_stuck()
        monitor.stop_monitoring()
