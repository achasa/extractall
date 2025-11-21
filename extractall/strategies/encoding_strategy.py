"""Encoding variants strategy for international filenames."""

from pathlib import Path
from typing import Optional, List
import logging
import subprocess
import os

from ..core.interfaces import ExtractionStrategy, ArchiveInfo, ExtractionResult
from ..config.settings import ExtractionConfig


class EncodingStrategy(ExtractionStrategy):
    """Try different character encodings for filenames."""
    
    def __init__(self, config: ExtractionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        self.encodings = ['utf-8', 'cp437', 'cp850', 'iso-8859-1', 'windows-1252']
    
    def can_handle(self, archive_info: ArchiveInfo) -> bool:
        """Can try encoding variants for ZIP files if enabled."""
        return (self.config.enable_encoding_variants and 
                archive_info.type == 'zip')
    
    def extract(self, archive_info: ArchiveInfo, extract_to: Path) -> ExtractionResult:
        """Try different encodings for ZIP extraction."""
        extract_to.mkdir(parents=True, exist_ok=True)
        
        for encoding in self.encodings:
            if self._try_encoding(archive_info, extract_to, encoding):
                self.logger.info(f"Success with encoding {encoding}")
                return ExtractionResult.SUCCESS
        
        return ExtractionResult.FAILED
    
    def _try_encoding(self, archive_info: ArchiveInfo, extract_to: Path, encoding: str) -> bool:
        """Try extraction with specific encoding."""
        try:
            # Set environment variable for unzip
            env = os.environ.copy()
            env['UNZIP'] = f'-O {encoding}'
            
            result = subprocess.run(
                ['unzip', '-q', '-o', str(archive_info.path), '-d', str(extract_to)], 
                capture_output=True, text=True, 
                timeout=15, env=env
            )
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @property
    def priority(self) -> int:
        """Medium-low priority."""
        return 70
