"""End-to-end integration tests."""

import pytest
import subprocess
from pathlib import Path

from extractall import ArchiveExtractor


class TestEndToEndExtraction:
    """Test complete extraction workflows."""

    def test_extracts_multiple_archive_types(self, temp_dir):
        """Should extract various archive types successfully."""
        # Create test content
        content_dir = temp_dir / "content"
        content_dir.mkdir()
        (content_dir / "file1.txt").write_text("content 1")
        (content_dir / "file2.txt").write_text("content 2")
        
        # Create different archive types
        archives_created = 0
        
        # ZIP
        if subprocess.run(["which", "zip"], capture_output=True).returncode == 0:
            subprocess.run(["zip", "-r", str(temp_dir / "test.zip"), str(content_dir)], 
                          capture_output=True)
            archives_created += 1
        
        # TAR.GZ
        if subprocess.run(["which", "tar"], capture_output=True).returncode == 0:
            subprocess.run(["tar", "-czf", str(temp_dir / "test.tar.gz"), 
                           "-C", str(content_dir.parent), content_dir.name], 
                          capture_output=True)
            archives_created += 1
        
        # 7Z
        if subprocess.run(["which", "7z"], capture_output=True).returncode == 0:
            subprocess.run(["7z", "a", str(temp_dir / "test.7z"), str(content_dir)], 
                          capture_output=True)
            archives_created += 1
        
        if archives_created == 0:
            pytest.skip("No archive tools available")
        
        # Run extraction
        extractor = ArchiveExtractor(str(temp_dir), mode="aggressive")
        report = extractor.run()
        
        # Verify results
        assert report['summary']['successful'] >= 1
        assert report['summary']['success_rate'] > 0
        
        # Check output files exist
        output_files = list((temp_dir / "output").rglob("*.txt"))
        assert len(output_files) >= 2  # At least 2 files extracted

    def test_handles_corrupted_archives_gracefully(self, temp_dir):
        """Should handle corrupted archives without crashing."""
        # Create corrupted files
        (temp_dir / "corrupted.zip").write_bytes(b"not a zip file")
        (temp_dir / "truncated.rar").write_bytes(b"Rar!\x1a\x07\x00incomplete")
        
        # Run extraction
        extractor = ArchiveExtractor(str(temp_dir), mode="conservative")
        report = extractor.run()
        
        # Should complete without errors
        assert report['summary']['failed'] >= 2
        assert (temp_dir / "failed").exists()

    def test_resume_capability_works(self, temp_dir):
        """Should resume extraction after interruption."""
        # Create test archive
        content_dir = temp_dir / "content"
        content_dir.mkdir()
        (content_dir / "test.txt").write_text("test content")
        
        subprocess.run(["zip", "-r", str(temp_dir / "test.zip"), str(content_dir)], 
                      capture_output=True)
        
        # First run
        extractor1 = ArchiveExtractor(str(temp_dir))
        report1 = extractor1.run()
        
        # Verify state file exists
        assert (temp_dir / "extraction_state.json").exists()
        
        # Second run (should skip processed files)
        extractor2 = ArchiveExtractor(str(temp_dir))
        report2 = extractor2.run()
        
        # Should have same results
        assert report2['summary']['successful'] == report1['summary']['successful']

    def test_directory_organization(self, temp_dir):
        """Should organize files into correct directories."""
        # Create mixed content
        content_dir = temp_dir / "content"
        content_dir.mkdir()
        (content_dir / "test.txt").write_text("test content")
        
        # Create good archive
        subprocess.run(["zip", "-r", str(temp_dir / "good.zip"), str(content_dir)], 
                      capture_output=True)
        
        # Create corrupted file
        (temp_dir / "bad.zip").write_bytes(b"corrupted")
        
        # Run extraction
        extractor = ArchiveExtractor(str(temp_dir))
        extractor.run()
        
        # Check directory organization
        assert (temp_dir / "extracted").exists()
        assert (temp_dir / "output").exists()
        assert (temp_dir / "failed").exists()
        
        # Check files are in correct places
        assert len(list((temp_dir / "extracted").glob("*.zip"))) >= 1
        assert len(list((temp_dir / "failed").glob("*.zip"))) >= 1
        assert len(list((temp_dir / "output").rglob("*.txt"))) >= 1
