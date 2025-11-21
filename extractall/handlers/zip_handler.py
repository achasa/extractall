"""ZIP archive handler."""

from pathlib import Path
from typing import List
import logging

from .base_handler import BaseArchiveHandler
from ..config.settings import ExtractionConfig


class ZipHandler(BaseArchiveHandler):
    """Handler for ZIP archives."""
    
    @property
    def supported_formats(self) -> List[str]:
        """List of supported archive formats."""
        return ['zip', 'jar', 'war', 'ear']
    
    def _get_extraction_commands(self) -> List[List[str]]:
        """Get ZIP extraction commands in order of preference."""
        return [
            # unzip (most compatible)
            ['unzip', '-q', '-o', '{file}', '-d', '{output}'],
            
            # 7z (good fallback)
            ['7z', 'x', '{file}', '-o{output}', '-y'],
            
            # Python zipfile (last resort)
            ['python3', '-m', 'zipfile', '-e', '{file}', '{output}'],
        ]
    
    def _get_test_commands(self) -> List[List[str]]:
        """Get ZIP test commands."""
        return [
            ['unzip', '-t', '{file}'],
            ['7z', 't', '{file}'],
        ]
    
    def _get_list_commands(self) -> List[List[str]]:
        """Get ZIP list commands."""
        return [
            ['unzip', '-l', '{file}'],
            ['7z', 'l', '{file}'],
        ]
    
    def _get_magic_numbers(self) -> List[bytes]:
        """Get ZIP magic numbers."""
        return [
            b'PK\x03\x04',  # Local file header
            b'PK\x05\x06',  # End of central directory
            b'PK\x07\x08',  # Data descriptor
        ]
    
    def _get_output_flag(self, extract_to: Path) -> List[str]:
        """Get output directory flag for ZIP tools."""
        return ['-d', str(extract_to)]
    
    def _parse_file_list(self, output: str) -> List[str]:
        """Parse file list from unzip -l output."""
        files = []
        lines = output.split('\n')
        
        # Skip header and footer lines
        in_file_list = False
        for line in lines:
            line = line.strip()
            
            if 'Length' in line and 'Name' in line:
                in_file_list = True
                continue
            
            if in_file_list and line.startswith('---'):
                break
            
            if in_file_list and line:
                # Extract filename (last column)
                parts = line.split()
                if len(parts) >= 4:
                    filename = parts[-1]
                    if filename and not filename.endswith('/'):
                        files.append(filename)
        
        return files
