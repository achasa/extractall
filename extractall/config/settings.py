"""Configuration management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any
from enum import Enum


class ExtractionMode(Enum):
    """Extraction aggressiveness modes."""
    CONSERVATIVE = "conservative"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


@dataclass
class ExtractionConfig:
    """Extraction configuration."""
    
    # Directories
    input_dir: Path
    extracted_dir: str = "extracted"
    output_dir: str = "output"
    failed_dir: str = "failed"
    locked_dir: str = "locked"
    stuck_dir: str = "stuck"
    
    # Extraction settings
    mode: ExtractionMode = ExtractionMode.STANDARD
    max_extraction_time: int = 300  # seconds
    max_file_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    
    # Strategy settings
    enable_multipart: bool = True
    enable_repair: bool = True
    enable_partial_extraction: bool = True
    enable_alternative_formats: bool = True
    enable_encoding_variants: bool = True
    
    # Timeouts
    strategy_timeout: int = 30
    repair_timeout: int = 60
    stuck_timeout: int = 300  # 5 minutes without progress
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "extraction.log"
    
    # State management
    state_file: str = "extraction_state.json"
    
    # Tool preferences
    preferred_tools: Dict[str, List[str]] = field(default_factory=lambda: {
        'zip': ['unzip', '7z', 'python'],
        'rar': ['unrar', '7z'],
        '7z': ['7z'],
        'tar': ['tar', '7z'],
    })
    
    def get_directory_paths(self) -> Dict[str, Path]:
        """Get all directory paths."""
        return {
            'input': self.input_dir,
            'extracted': self.input_dir / self.extracted_dir,
            'output': self.input_dir / self.output_dir,
            'failed': self.input_dir / self.failed_dir,
            'locked': self.input_dir / self.locked_dir,
            'stuck': self.input_dir / self.stuck_dir,
        }
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy-specific configuration."""
        return {
            'multipart': self.enable_multipart,
            'repair': self.enable_repair,
            'partial': self.enable_partial_extraction,
            'alternative_formats': self.enable_alternative_formats,
            'encoding_variants': self.enable_encoding_variants,
            'timeouts': {
                'strategy': self.strategy_timeout,
                'repair': self.repair_timeout,
            }
        }


@dataclass
class ToolConfig:
    """Tool-specific configuration."""
    
    # Available tools
    zip_tools: List[str] = field(default_factory=lambda: ['unzip', '7z'])
    rar_tools: List[str] = field(default_factory=lambda: ['unrar', '7z'])
    sevenz_tools: List[str] = field(default_factory=lambda: ['7z'])
    tar_tools: List[str] = field(default_factory=lambda: ['tar', '7z'])
    
    # Tool paths (auto-detected if None)
    tool_paths: Dict[str, str] = field(default_factory=dict)
    
    def get_tools_for_format(self, format_type: str) -> List[str]:
        """Get available tools for a format."""
        tool_map = {
            'zip': self.zip_tools,
            'rar': self.rar_tools,
            '7z': self.sevenz_tools,
            'tar': self.tar_tools,
        }
        return tool_map.get(format_type, [])


def create_default_config(input_dir: Path) -> ExtractionConfig:
    """Create default configuration."""
    return ExtractionConfig(input_dir=input_dir)


def create_conservative_config(input_dir: Path) -> ExtractionConfig:
    """Create conservative configuration."""
    return ExtractionConfig(
        input_dir=input_dir,
        mode=ExtractionMode.CONSERVATIVE,
        enable_repair=False,
        enable_partial_extraction=False,
        enable_alternative_formats=False,
        strategy_timeout=15,
    )


def create_aggressive_config(input_dir: Path) -> ExtractionConfig:
    """Create aggressive configuration."""
    return ExtractionConfig(
        input_dir=input_dir,
        mode=ExtractionMode.AGGRESSIVE,
        enable_multipart=True,
        enable_repair=True,
        enable_partial_extraction=True,
        enable_alternative_formats=True,
        enable_encoding_variants=True,
        strategy_timeout=60,
        repair_timeout=120,
    )
