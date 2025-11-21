"""RAR archive handler."""

from pathlib import Path
from typing import List

from .base_handler import BaseArchiveHandler


class RarHandler(BaseArchiveHandler):
    """Handler for RAR archives."""
    
    @property
    def supported_formats(self) -> List[str]:
        return ['rar']
    
    def _get_extraction_commands(self) -> List[List[str]]:
        return [
            ['unrar', 'x', '-y', '{file}', '{output}'],
            ['7z', 'x', '{file}', '-o{output}', '-y'],
        ]
    
    def _get_magic_numbers(self) -> List[bytes]:
        return [b'Rar!\x1a\x07\x00', b'Rar!\x1a\x07\x01\x00']
