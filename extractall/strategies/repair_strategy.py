"""Archive repair and recovery strategy."""

from pathlib import Path
from typing import Optional
import logging
import subprocess
import tempfile

from ..core.interfaces import ExtractionStrategy, ArchiveInfo, ExtractionResult
from ..config.settings import ExtractionConfig
from .multi_tool_strategy import MultiToolStrategy


class RepairStrategy(ExtractionStrategy):
    """Attempt to repair corrupted archives before extraction."""
    
    def __init__(self, config: ExtractionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.multi_tool = MultiToolStrategy(config, logger)
    
    def can_handle(self, archive_info: ArchiveInfo) -> bool:
        """Can attempt repair on ZIP and RAR files."""
        return (archive_info.type in ['zip', 'rar'] and 
                self.config.enable_repair)
    
    def extract(self, archive_info: ArchiveInfo, extract_to: Path) -> ExtractionResult:
        """Try to repair and then extract."""
        if archive_info.type == 'zip':
            return self._repair_zip(archive_info, extract_to)
        elif archive_info.type == 'rar':
            return self._repair_rar(archive_info, extract_to)
        
        return ExtractionResult.FAILED
    
    def _repair_zip(self, archive_info: ArchiveInfo, extract_to: Path) -> ExtractionResult:
        """Repair ZIP file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repaired_file = temp_path / f"repaired_{archive_info.path.name}"
            
            # Try zip -F (simple fix)
            if self._try_zip_repair(['-F'], archive_info.path, repaired_file):
                from ..core.detection import ArchiveInfoImpl
                repaired_info = ArchiveInfoImpl(
                    path=repaired_file,
                    type='zip',
                    size=repaired_file.stat().st_size,
                    is_multipart=False,
                    part_number=None
                )
                result = self.multi_tool.extract(repaired_info, extract_to)
                if result == ExtractionResult.SUCCESS:
                    return result
            
            # Try zip -FF (aggressive fix)
            if self._try_zip_repair(['-FF'], archive_info.path, repaired_file):
                from ..core.detection import ArchiveInfoImpl
                repaired_info = ArchiveInfoImpl(
                    path=repaired_file,
                    type='zip', 
                    size=repaired_file.stat().st_size,
                    is_multipart=False,
                    part_number=None
                )
                return self.multi_tool.extract(repaired_info, extract_to)
        
        return ExtractionResult.FAILED
    
    def _try_zip_repair(self, flags: list, source: Path, output: Path) -> bool:
        """Try ZIP repair with given flags."""
        try:
            cmd = ['zip'] + flags + [str(source), '--out', str(output)]
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=self.config.repair_timeout
            )
            
            success = result.returncode == 0 and output.exists()
            if success:
                self.logger.info(f"ZIP repair successful with {flags}")
            
            return success
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _repair_rar(self, archive_info: ArchiveInfo, extract_to: Path) -> ExtractionResult:
        """Repair RAR file."""
        try:
            # RAR repair in place
            cmd = ['rar', 'r', str(archive_info.path)]
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=self.config.repair_timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"RAR repair successful")
                return self.multi_tool.extract(archive_info, extract_to)
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return ExtractionResult.FAILED
    
    @property
    def priority(self) -> int:
        """Lower priority - try after basic methods."""
        return 60
