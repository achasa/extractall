"""TAR archive handler."""

from pathlib import Path
from typing import List

from .base_handler import BaseArchiveHandler


class TarHandler(BaseArchiveHandler):
    """Handler for TAR archives."""
    
    @property
    def supported_formats(self) -> List[str]:
        return ['tar', 'gz', 'bz2', 'xz']
    
    def _get_extraction_commands(self) -> List[List[str]]:
        return [
            ['tar', '-xf', '{file}', '-C', '{output}'],
            ['7z', 'x', '{file}', '-o{output}', '-y'],
        ]
    
    def _get_output_flag(self, extract_to: Path) -> List[str]:
        return ['-C', str(extract_to)]
