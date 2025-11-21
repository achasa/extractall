"""Archive detection and analysis."""

import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import re
import logging

from .interfaces import ArchiveInfo


class ArchiveDetector:
    """Detects and analyzes archive files."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # MIME type mappings
        self._mime_mappings = {
            'application/zip': 'zip',
            'application/x-rar': 'rar',
            'application/x-7z-compressed': '7z',
            'application/x-tar': 'tar',
            'application/gzip': 'gz',
            'application/x-bzip2': 'bz2',
            'application/x-xz': 'xz',
        }
        
        # Extension mappings
        self._extension_mappings = {
            '.zip': 'zip',
            '.rar': 'rar',
            '.7z': '7z',
            '.tar': 'tar',
            '.gz': 'gz',
            '.bz2': 'bz2',
            '.xz': 'xz',
        }
        
        # Multipart patterns
        self._multipart_patterns = [
            r'^(.+)\.7z\.(\d{3})$',           # archive.7z.001
            r'^(.+)\.part(\d+)\.7z$',         # archive.part1.7z  
            r'^(.+)\.(\d{3})\.7z$',           # archive.001.7z
            r'^(.+)\.r(\d{2})$',              # archive.r01 (RAR)
            r'^(.+)\.rar\.(\d{3})$',          # archive.rar.001
            r'^(.+)\.z(\d{2})$',              # archive.z01 (ZIP)
            r'^(.+)\.(\d{3})$',               # archive.001 (generic)
        ]
    
    def detect_archive_type(self, file_path: Path) -> Optional[str]:
        """Detect archive type using multiple methods."""
        
        # Try extension first
        archive_type = self._detect_by_extension(file_path)
        if archive_type:
            return archive_type
        
        # Try compound extensions
        archive_type = self._detect_compound_extensions(file_path)
        if archive_type:
            return archive_type
        
        # Try MIME type detection
        archive_type = self._detect_by_mime_type(file_path)
        if archive_type:
            return archive_type
        
        # Try magic numbers
        archive_type = self._detect_by_magic_numbers(file_path)
        if archive_type:
            return archive_type
        
        return None
    
    def analyze_archive(self, file_path: Path) -> ArchiveInfo:
        """Analyze archive and return detailed information."""
        
        archive_type = self.detect_archive_type(file_path)
        size = file_path.stat().st_size if file_path.exists() else 0
        
        # Check if multipart
        is_multipart, part_number = self._analyze_multipart(file_path)
        
        return ArchiveInfoImpl(
            path=file_path,
            type=archive_type or 'unknown',
            size=size,
            is_multipart=is_multipart,
            part_number=part_number
        )
    
    def _detect_by_extension(self, file_path: Path) -> Optional[str]:
        """Detect by file extension."""
        ext = file_path.suffix.lower()
        return self._extension_mappings.get(ext)
    
    def _detect_compound_extensions(self, file_path: Path) -> Optional[str]:
        """Detect compound extensions like .tar.gz."""
        name = file_path.name.lower()
        
        compound_extensions = {
            '.tar.gz': 'tar',
            '.tar.bz2': 'tar',
            '.tar.xz': 'tar',
        }
        
        for ext, archive_type in compound_extensions.items():
            if name.endswith(ext):
                return archive_type
        
        return None
    
    def _detect_by_mime_type(self, file_path: Path) -> Optional[str]:
        """Detect using file command MIME type."""
        try:
            result = subprocess.run(
                ['file', '--mime-type', str(file_path)], 
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                mime_type = result.stdout.split(':')[1].strip()
                return self._mime_mappings.get(mime_type)
                
        except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
            pass
        
        return None
    
    def _detect_by_magic_numbers(self, file_path: Path) -> Optional[str]:
        """Detect using magic numbers/file signatures."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
            
            # Common magic numbers
            magic_signatures = {
                b'PK\x03\x04': 'zip',
                b'PK\x05\x06': 'zip',
                b'Rar!\x1a\x07\x00': 'rar',
                b'Rar!\x1a\x07\x01\x00': 'rar',
                b'7z\xbc\xaf\x27\x1c': '7z',
                b'\x1f\x8b': 'gz',
                b'BZh': 'bz2',
                b'\xfd7zXZ\x00': 'xz',
            }
            
            for signature, archive_type in magic_signatures.items():
                if header.startswith(signature):
                    return archive_type
                    
        except (IOError, OSError):
            pass
        
        return None
    
    def _analyze_multipart(self, file_path: Path) -> Tuple[bool, Optional[int]]:
        """Analyze if file is part of multipart archive."""
        name = file_path.name
        
        for pattern in self._multipart_patterns:
            match = re.match(pattern, name, re.IGNORECASE)
            if match:
                try:
                    part_number = int(match.group(2))
                    return True, part_number
                except (ValueError, IndexError):
                    continue
        
        return False, None
    
    def find_related_parts(self, file_path: Path, all_files: List[Path]) -> List[Path]:
        """Find all parts related to a multipart archive."""
        is_multipart, _ = self._analyze_multipart(file_path)
        
        if not is_multipart:
            return [file_path]
        
        # Extract base name pattern
        name = file_path.name
        for pattern in self._multipart_patterns:
            match = re.match(pattern, name, re.IGNORECASE)
            if match:
                base_name = match.group(1)
                
                # Find all files with same base name
                related_parts = []
                for other_file in all_files:
                    other_match = re.match(pattern, other_file.name, re.IGNORECASE)
                    if other_match and other_match.group(1) == base_name:
                        related_parts.append(other_file)
                
                return sorted(related_parts, key=lambda p: p.name)
        
        return [file_path]


class ArchiveInfoImpl:
    """Implementation of ArchiveInfo protocol."""
    
    def __init__(self, path: Path, type: str, size: int, 
                 is_multipart: bool, part_number: Optional[int]):
        self.path = path
        self.type = type
        self.size = size
        self.is_multipart = is_multipart
        self.part_number = part_number
    
    def __repr__(self) -> str:
        return (f"ArchiveInfo(path={self.path.name}, type={self.type}, "
                f"size={self.size}, multipart={self.is_multipart})")
