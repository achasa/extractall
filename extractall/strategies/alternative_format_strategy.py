"""Alternative format detection strategy."""

from pathlib import Path
from typing import Optional, List, Tuple
import logging

from ..core.interfaces import ExtractionStrategy, ArchiveInfo, ExtractionResult
from ..config.settings import ExtractionConfig
from .multi_tool_strategy import MultiToolStrategy


class AlternativeFormatStrategy(ExtractionStrategy):
    """Try treating archives as different formats."""
    
    def __init__(self, config: ExtractionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.multi_tool = MultiToolStrategy(config, logger)
        
        # Format alternatives to try
        self.alternatives = [
            ('zip', 'rar'),   # ZIP files sometimes have .rar extension
            ('rar', 'zip'),   # RAR files sometimes have .zip extension
            ('7z', 'zip'),    # 7z can handle ZIP files
            ('tar', '7z'),    # 7z can handle TAR files
            ('gz', 'zip'),    # Compressed files sometimes mislabeled
        ]
    
    def can_handle(self, archive_info: ArchiveInfo) -> bool:
        """Can try alternative formats if enabled."""
        return (self.config.enable_alternative_formats and 
                any(archive_info.type == from_type for from_type, _ in self.alternatives))
    
    def extract(self, archive_info: ArchiveInfo, extract_to: Path) -> ExtractionResult:
        """Try alternative formats."""
        original_type = archive_info.type
        
        for from_type, to_type in self.alternatives:
            if original_type == from_type:
                self.logger.info(f"Trying {archive_info.path.name} as {to_type} instead of {from_type}")
                
                # Create alternative archive info
                from ..core.detection import ArchiveInfoImpl
                alt_info = ArchiveInfoImpl(
                    path=archive_info.path,
                    type=to_type,
                    size=archive_info.size,
                    is_multipart=archive_info.is_multipart,
                    part_number=archive_info.part_number
                )
                
                if self.multi_tool.can_handle(alt_info):
                    result = self.multi_tool.extract(alt_info, extract_to)
                    if result == ExtractionResult.SUCCESS:
                        return result
        
        return ExtractionResult.FAILED
    
    @property
    def priority(self) -> int:
        """Medium priority."""
        return 40
