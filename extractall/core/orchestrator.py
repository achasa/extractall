"""Main extraction orchestrator."""

from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import tempfile

from .interfaces import ExtractionResult, ArchiveInfo
from .detection import ArchiveDetector
from .file_manager import DefaultFileManager
from .state_manager import JsonStateManager
from ..handlers.registry import create_handler_registry
from ..strategies.registry import create_strategy_registry
from ..config.settings import ExtractionConfig


class ExtractionOrchestrator:
    """Main orchestrator for archive extraction."""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.logger = self._setup_logging()
        
        # Initialize components
        self.detector = ArchiveDetector(self.logger)
        self.file_manager = DefaultFileManager(config, self.logger)
        self.state_manager = JsonStateManager(config, self.logger)
        self.handler_registry = create_handler_registry(config, self.logger)
        self.strategy_registry = create_strategy_registry(config, self.logger)
        
        self.logger.info(f"Initialized ExtractAll with mode: {config.mode.value}")
    
    def run(self) -> Dict[str, Any]:
        """Run the extraction process."""
        self.logger.info("Starting archive extraction...")
        
        # Load previous results from state if it exists
        previous_results = self._load_previous_results()
        
        results = {
            'success': list(previous_results.get('success', [])),
            'failed': list(previous_results.get('failed', [])),
            'locked': list(previous_results.get('locked', [])),
            'partial': list(previous_results.get('partial', [])),
            'skipped': list(previous_results.get('skipped', []))
        }
        
        # Keep processing until no new archives are found
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            # Find all files to process
            files = self._discover_files()
            
            if not files:
                break
                
            self.logger.info(f"Found {len(files)} files to process")
            
            # Group multipart archives if enabled
            if self.config.enable_multipart:
                file_groups = self._group_multipart_files(files)
            else:
                file_groups = [[f] for f in files]
            
            # Process each group
            files_processed_this_iteration = 0
            for group in file_groups:
                result = self._process_file_group(group)
                files_processed_this_iteration += len(group)
                for item in group:
                    file_path = item.path if hasattr(item, 'path') else item
                    file_path_str = str(file_path)
                    # Only add if not already in results
                    if file_path_str not in results[result.value]:
                        results[result.value].append(file_path_str)
            
            if files_processed_this_iteration == 0:
                break
                
            iteration += 1
        
        # Save current results to state
        self._save_current_results(results)
        
        # Generate final report
        report = self._generate_report(results)
        self.logger.info("Extraction complete!")
        self._log_summary(report)
        
        return report
    
    def _load_previous_results(self) -> Dict[str, List[str]]:
        """Load previous extraction results from state."""
        try:
            state = self.state_manager.load_state()
            return state.get('results', {})
        except Exception:
            return {}
    
    def _save_current_results(self, results: Dict[str, List[str]]) -> None:
        """Save current results to state."""
        try:
            self.state_manager.save_state({'results': results})
        except Exception as e:
            self.logger.warning(f"Failed to save state: {e}")
    
    def _discover_files(self) -> List[Path]:
        """Discover all files in input directory."""
        files = []
        
        for item in self.config.input_dir.iterdir():
            if item.is_file() and not self._is_system_file(item):
                files.append(item)
        
        # Also check extracted directory for nested archives if enabled
        if self.config.mode.value == "aggressive":
            extracted_dir = self.config.input_dir / "extracted"
            if extracted_dir.exists():
                for item in extracted_dir.iterdir():
                    if item.is_file() and not self._is_system_file(item):
                        # Check if this is an archive that hasn't been processed
                        archive_info = self.detector.analyze_archive(item)
                        if archive_info.type != "unknown" and not self.state_manager.is_processed(item):
                            files.append(item)
        
        return files
    
    def _is_system_file(self, file_path: Path) -> bool:
        """Check if file is a system file to skip."""
        system_files = {
            self.config.state_file,
            self.config.log_file,
            '.DS_Store',
            'Thumbs.db',
        }
        
        return file_path.name in system_files
    
    def _group_multipart_files(self, files: List[Path]) -> List[List[ArchiveInfo]]:
        """Group related multipart files."""
        groups = []
        processed_files = set()
        
        for file_path in files:
            if file_path in processed_files:
                continue
            
            archive_info = self.detector.analyze_archive(file_path)
            
            if archive_info.is_multipart:
                # Find all related parts
                related_parts = self.detector.find_related_parts(file_path, files)
                group = [self.detector.analyze_archive(f) for f in related_parts]
                groups.append(group)
                processed_files.update(related_parts)
            else:
                groups.append([archive_info])
                processed_files.add(file_path)
        
        return groups
    
    def _process_file_group(self, group: List[ArchiveInfo]) -> ExtractionResult:
        """Process a group of related files."""
        if len(group) == 1:
            return self._process_single_file(group[0])
        else:
            return self._process_multipart_group(group)
    
    def _process_single_file(self, archive_info: ArchiveInfo) -> ExtractionResult:
        """Process a single archive file."""
        file_path = archive_info.path
        
        # Check if already processed
        if self.state_manager.is_processed(file_path):
            self.logger.info(f"Skipping already processed: {file_path.name}")
            return ExtractionResult.SUCCESS
        
        self.logger.info(f"Processing: {file_path.name}")
        
        # Try extraction strategies
        result = self._attempt_extraction(archive_info)
        
        # Handle result
        self._handle_extraction_result(archive_info, result)
        
        return result
    
    def _process_multipart_group(self, group: List[ArchiveInfo]) -> ExtractionResult:
        """Process a multipart archive group."""
        self.logger.info(f"Processing multipart group: {len(group)} parts")
        
        # Check completeness and decide whether to attempt extraction
        if not self._should_attempt_multipart_extraction(group):
            self.logger.warning("Multipart group incomplete, moving to failed")
            for archive_info in group:
                self.file_manager.move_to_failed(archive_info.path)
                self.state_manager.mark_processed(archive_info.path, ExtractionResult.FAILED)
            return ExtractionResult.FAILED
        
        # Try to extract the first part (which should handle all parts)
        primary_archive = group[0]
        result = self._attempt_extraction(primary_archive)
        
        # Handle all parts based on result
        for archive_info in group:
            self._handle_extraction_result(archive_info, result)
        
        return result
    
    def _should_attempt_multipart_extraction(self, group: List[ArchiveInfo]) -> bool:
        """Decide if multipart extraction should be attempted."""
        # Simple heuristic: if we have at least 70% of expected parts
        if len(group) < 2:
            return True
        
        # Check for sequential part numbers
        part_numbers = [info.part_number for info in group if info.part_number is not None]
        if not part_numbers:
            return True
        
        part_numbers.sort()
        expected_parts = part_numbers[-1] - part_numbers[0] + 1
        actual_parts = len(part_numbers)
        
        completeness_ratio = actual_parts / expected_parts
        return completeness_ratio >= 0.7
    
    def _attempt_extraction(self, archive_info: ArchiveInfo) -> ExtractionResult:
        """Attempt to extract an archive using available strategies."""
        
        # Get compatible strategies
        strategies = self.strategy_registry.get_compatible_strategies(archive_info)
        
        if not strategies:
            self.logger.warning(f"No compatible strategies for {archive_info.path.name}")
            return ExtractionResult.FAILED
        
        # Create temporary extraction directory
        temp_dir = self.file_manager.get_temp_directory(archive_info.path.stem)
        
        try:
            # Try each strategy in order of priority
            for strategy in strategies:
                self.logger.debug(f"Trying strategy: {strategy.__class__.__name__}")
                
                result = strategy.extract(archive_info, temp_dir)
                
                if result == ExtractionResult.SUCCESS:
                    # Copy extracted files to output
                    files_copied = self.file_manager.copy_extracted_files(temp_dir)
                    
                    if files_copied > 0:
                        self.logger.info(f"Successfully extracted {files_copied} files")
                        # Check for nested archives in aggressive mode
                        if self.config.mode.value == "aggressive":
                            self._process_nested_archives(temp_dir)
                        return ExtractionResult.SUCCESS
                    else:
                        self.logger.warning("No files were extracted")
                        # Empty archive is still considered successful
                        return ExtractionResult.SUCCESS
                
                elif result == ExtractionResult.PARTIAL:
                    # Partial success - copy what we can
                    files_copied = self.file_manager.copy_extracted_files(temp_dir)
                    
                    if files_copied > 0:
                        self.logger.info(f"Partially extracted {files_copied} files")
                        return ExtractionResult.PARTIAL
                
                elif result == ExtractionResult.LOCKED:
                    self.logger.info("Archive is password protected")
                    return ExtractionResult.LOCKED
            
            # All strategies failed
            return ExtractionResult.FAILED
            
        finally:
            # Clean up temporary directory
            self.file_manager.cleanup_temp_directory(temp_dir)
    
    def _handle_extraction_result(self, archive_info: ArchiveInfo, result: ExtractionResult) -> None:
        """Handle the result of extraction."""
        file_path = archive_info.path
        
        try:
            if result == ExtractionResult.SUCCESS:
                self.file_manager.move_to_extracted(file_path)
            elif result == ExtractionResult.LOCKED:
                self.file_manager.move_to_locked(file_path)
            else:  # FAILED or PARTIAL
                self.file_manager.move_to_failed(file_path)
            
            # Update state
            self.state_manager.mark_processed(file_path, result)
            
        except Exception as e:
            self.logger.error(f"Error handling result for {file_path.name}: {e}")
    
    def _generate_report(self, results: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate extraction report."""
        total_files = sum(len(files) for files in results.values())
        
        return {
            'summary': {
                'total_files': total_files,
                'successful': len(results['success']),
                'failed': len(results['failed']),
                'locked': len(results['locked']),
                'partial': len(results['partial']),
                'skipped': len(results['skipped']),
                'success_rate': (len(results['success']) / total_files * 100) if total_files > 0 else 0,
            },
            'details': results,
            'statistics': self.state_manager.get_statistics(),
        }
    
    def _log_summary(self, report: Dict[str, Any]) -> None:
        """Log extraction summary."""
        summary = report['summary']
        
        self.logger.info(f"Extracted: {summary['successful']}")
        self.logger.info(f"Failed: {summary['failed']}")
        self.logger.info(f"Locked: {summary['locked']}")
        self.logger.info(f"Partial: {summary['partial']}")
        self.logger.info(f"Success rate: {summary['success_rate']:.1f}%")
    
    def _process_nested_archives(self, temp_dir: Path) -> None:
        """Process any nested archives found in extracted content."""
        for item in temp_dir.rglob("*"):
            if item.is_file():
                archive_info = self.detector.analyze_archive(item)
                if archive_info.type != "unknown":
                    self.logger.info(f"Found nested archive: {item.name}")
                    # Move to input directory for processing
                    target_path = self.config.input_dir / item.name
                    if not target_path.exists():
                        item.rename(target_path)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('extractall')
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Set level
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logger.setLevel(level)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        log_file = self.config.input_dir / self.config.log_file
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
