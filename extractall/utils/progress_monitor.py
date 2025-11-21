"""Progress monitoring for stuck extraction detection."""

import time
import threading
from pathlib import Path
from typing import Optional, Callable


class ProgressMonitor:
    """Monitor extraction progress to detect stuck operations."""
    
    def __init__(self, output_dir: Path, stuck_timeout: int = 300):
        self.output_dir = output_dir
        self.stuck_timeout = stuck_timeout
        self.last_activity = time.time()
        self.initial_size = 0
        self.monitoring = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    def start_monitoring(self) -> None:
        """Start monitoring for progress."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.last_activity = time.time()
        self.initial_size = self._get_dir_size()
        self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.monitoring = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
    
    def is_stuck(self) -> bool:
        """Check if extraction appears stuck."""
        if not self.monitoring:
            return False
        return time.time() - self.last_activity > self.stuck_timeout
    
    def _monitor_loop(self) -> None:
        """Monitor loop running in background thread."""
        while not self._stop_event.wait(5):  # Check every 5 seconds
            current_size = self._get_dir_size()
            
            if current_size > self.initial_size:
                self.last_activity = time.time()
                self.initial_size = current_size
    
    def _get_dir_size(self) -> int:
        """Get total size of output directory."""
        try:
            if not self.output_dir.exists():
                return 0
            return sum(f.stat().st_size for f in self.output_dir.rglob('*') if f.is_file())
        except (OSError, PermissionError):
            return 0
