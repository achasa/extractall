"""Core interfaces and abstractions."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Protocol
from enum import Enum


class ExtractionResult(Enum):
    """Extraction result status."""
    SUCCESS = "success"
    FAILED = "failed"
    LOCKED = "locked"
    PARTIAL = "partial"
    STUCK = "stuck"


class ArchiveInfo(Protocol):
    """Archive information protocol."""
    path: Path
    type: str
    size: int
    is_multipart: bool
    part_number: Optional[int]


class ExtractionStrategy(ABC):
    """Base class for extraction strategies."""
    
    @abstractmethod
    def can_handle(self, archive_info: ArchiveInfo) -> bool:
        """Check if this strategy can handle the archive."""
        pass
    
    @abstractmethod
    def extract(self, archive_info: ArchiveInfo, extract_to: Path) -> ExtractionResult:
        """Extract the archive."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Strategy priority (lower = higher priority)."""
        pass


class ArchiveHandler(ABC):
    """Base class for archive format handlers."""
    
    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the file."""
        pass
    
    @abstractmethod
    def extract(self, file_path: Path, extract_to: Path) -> bool:
        """Extract the archive."""
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """List of supported archive formats."""
        pass


class StateManager(ABC):
    """Base class for state management."""
    
    @abstractmethod
    def save_state(self, state: Dict) -> None:
        """Save extraction state."""
        pass
    
    @abstractmethod
    def load_state(self) -> Dict:
        """Load extraction state."""
        pass
    
    @abstractmethod
    def is_processed(self, file_path: Path) -> bool:
        """Check if file was already processed."""
        pass


class FileManager(ABC):
    """Base class for file operations."""
    
    @abstractmethod
    def move_to_extracted(self, file_path: Path) -> Path:
        """Move file to extracted directory."""
        pass
    
    @abstractmethod
    def move_to_failed(self, file_path: Path) -> Path:
        """Move file to failed directory."""
        pass
    
    @abstractmethod
    def move_to_locked(self, file_path: Path) -> Path:
        """Move file to locked directory."""
        pass
    
    @abstractmethod
    def move_to_stuck(self, file_path: Path) -> Path:
        """Move file to stuck directory."""
        pass
    
    @abstractmethod
    def get_unique_output_path(self, base_path: Path) -> Path:
        """Get unique path for output file."""
        pass
