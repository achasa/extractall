"""7Z archive handler."""

from pathlib import Path
from typing import List

from .base_handler import BaseArchiveHandler


class SevenZHandler(BaseArchiveHandler):
    """Handler for 7Z archives."""
    
    @property
    def supported_formats(self) -> List[str]:
        return ['7z']
    
    def _get_extraction_commands(self) -> List[List[str]]:
        return [
            ['7z', 'x', '{file}', '-o{output}', '-y'],
        ]
    
    def _get_magic_numbers(self) -> List[bytes]:
        return [b'7z\xbc\xaf\x27\x1c']
