"""Basic extraction strategy using handlers."""

from pathlib import Path
from typing import Optional
import logging

from ..core.interfaces import ExtractionStrategy, ArchiveInfo, ExtractionResult
from ..handlers.registry import create_handler_registry
from ..config.settings import ExtractionConfig


class BasicExtractionStrategy(ExtractionStrategy):
    """Basic extraction using format-specific handlers."""
    
    def __init__(self, config: ExtractionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.handler_registry = create_handler_registry(config, logger)
    
    def can_handle(self, archive_info: ArchiveInfo) -> bool:
        """Check if we have a handler for this archive type."""
        handler = self.handler_registry.get_handler(archive_info.type)
        return handler is not None
    
    def extract(self, archive_info: ArchiveInfo, extract_to: Path) -> ExtractionResult:
        """Extract using appropriate handler."""
        handler = self.handler_registry.get_handler(archive_info.type)
        
        if not handler:
            self.logger.warning(f"No handler for {archive_info.type}")
            return ExtractionResult.FAILED
        
        try:
            success = handler.extract(archive_info.path, extract_to)
            return ExtractionResult.SUCCESS if success else ExtractionResult.FAILED
            
        except Exception as e:
            self.logger.error(f"Handler extraction failed: {e}")
            return ExtractionResult.FAILED
    
    @property
    def priority(self) -> int:
        """Basic strategy has lowest priority."""
        return 100
