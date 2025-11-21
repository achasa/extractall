"""Strategy registry for extraction strategies."""

from typing import List, Optional
import logging

from ..core.interfaces import ExtractionStrategy, ArchiveInfo
from ..config.settings import ExtractionConfig


class StrategyRegistry:
    """Registry for extraction strategies."""
    
    def __init__(self, config: ExtractionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.strategies: List[ExtractionStrategy] = []
    
    def register_strategy(self, strategy: ExtractionStrategy) -> None:
        """Register an extraction strategy."""
        self.strategies.append(strategy)
        self.logger.debug(f"Registered strategy: {strategy.__class__.__name__}")
    
    def get_compatible_strategies(self, archive_info: ArchiveInfo) -> List[ExtractionStrategy]:
        """Get strategies compatible with the archive, sorted by priority."""
        compatible = [s for s in self.strategies if s.can_handle(archive_info)]
        return sorted(compatible, key=lambda s: s.priority)


def create_strategy_registry(config: ExtractionConfig, 
                           logger: Optional[logging.Logger] = None) -> StrategyRegistry:
    """Create and configure strategy registry."""
    registry = StrategyRegistry(config, logger)
    
    # Register strategies based on configuration
    from .basic_strategy import BasicExtractionStrategy
    from .multi_tool_strategy import MultiToolStrategy
    
    # Always register basic and multi-tool strategies
    registry.register_strategy(BasicExtractionStrategy(config, logger))
    registry.register_strategy(MultiToolStrategy(config, logger))
    
    # Register advanced strategies based on config
    if config.enable_multipart:
        from .multipart_strategy import MultipartStrategy
        registry.register_strategy(MultipartStrategy(config, logger))
    
    if config.enable_alternative_formats:
        from .alternative_format_strategy import AlternativeFormatStrategy
        registry.register_strategy(AlternativeFormatStrategy(config, logger))
    
    if config.enable_repair:
        from .repair_strategy import RepairStrategy
        registry.register_strategy(RepairStrategy(config, logger))
    
    if config.enable_encoding_variants:
        from .encoding_strategy import EncodingStrategy
        registry.register_strategy(EncodingStrategy(config, logger))
    
    if config.enable_partial_extraction:
        from .partial_strategy import PartialExtractionStrategy
        registry.register_strategy(PartialExtractionStrategy(config, logger))
    
    logger.info(f"Registered {len(registry.strategies)} extraction strategies")
    return registry
