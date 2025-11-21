"""ExtractAll - Universal archive extraction tool."""

__version__ = "2.0.0"

from .core.orchestrator import ExtractionOrchestrator
from .config.settings import (
    ExtractionConfig, 
    ExtractionMode,
    create_default_config,
    create_conservative_config,
    create_aggressive_config
)

# Backward compatibility
class ArchiveExtractor:
    """Backward compatible interface."""
    
    def __init__(self, input_dir: str, mode: str = "standard"):
        from pathlib import Path
        
        input_path = Path(input_dir)
        
        if mode == "conservative":
            config = create_conservative_config(input_path)
        elif mode == "aggressive":
            config = create_aggressive_config(input_path)
        else:
            config = create_default_config(input_path)
        
        self.orchestrator = ExtractionOrchestrator(config)
        self.state = {"processed": [], "extracted": [], "failed": [], "locked": []}
    
    def run(self):
        """Run extraction process."""
        report = self.orchestrator.run()
        
        # Update state for backward compatibility
        self.state = {
            "processed": (report['details']['success'] + 
                         report['details']['failed'] + 
                         report['details']['locked'] + 
                         report['details']['partial']),
            "extracted": report['details']['success'],
            "failed": report['details']['failed'],
            "locked": report['details']['locked'],
        }
        
        return report


__all__ = [
    "ArchiveExtractor", 
    "ExtractionOrchestrator",
    "ExtractionConfig", 
    "ExtractionMode",
    "create_default_config",
    "create_conservative_config", 
    "create_aggressive_config"
]
