"""
Tests for podcast file upload functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi import UploadFile
from io import BytesIO

from app.services.file_upload import FileUploadService
from app.core.exceptions import FileTypeError, FileSizeError


class TestPodcastFileUpload:
    """Test podcast-specific file upload functionality"""
    
    @pytest.fixture
    def upload_service(self):
        """Create file upload service with temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = FileUploadService(upload_dir=temp_dir)
            yield service
    
    @pytest.fixture
    def mock_audio_file(self):
        """Create mock audio file"""
        # Create a minimal MP3-like file (just headers for testing)
        audio_content = b'ID3\x03\x00\x00\x00\x00\x00\x00' + b'\x00' * 100
        
        file_obj = BytesIO(audio_content)
        upload_file = UploadFile(
            filename="test_podcast.mp3",
            file=file_obj,
            content_type="audio/mpeg"
        )
        return upload_file
    
    @pytest.fixture
    def mock_large_audio_file(self):
        """Create mock large audio file that exceeds size limit"""
        # Create a file larger than 100MB
        large_content = b'\x00' * (101 * 1024 * 1024)
        
        file_obj = BytesIO(large_content)
        upload_file = UploadFile(
            filename="large_podcast.mp3",
            file=file_obj,
            content_type="audio/mpeg"
        )
        return upload_file
    
    @pytest.fixture
    def mock_invalid_audio_file(self):
        """Create mock invalid audio file"""
        # Create a text file with audio extension
        invalid_content = b'This is not an audio file'
        
        file_obj = BytesIO(invalid_content)
        upload_file = UploadFile(
            filename="fake_audio.mp3",
            file=file_obj,
            content_type="audio/mpeg"
        )
        return upload_file
    
    def test_audio_file_category_detection(self, upload_service):
        """Test that audio files are correctly categorized"""
        # Test various audio MIME types
        audio_types = [
            "audio/mpeg",
            "audio/mp3", 
            "audio/wav",
            "audio/ogg",
            "audio/m4a"
        ]
        
        for mime_type in audio_types:
            category = upload_service._get_file_category(mime_type)
            assert category == "audio", f"MIME type {mime_type} should be categorized as audio"
    
    def test_audio_file_size_limits(self, upload_service):
        """Test audio file size limits"""
        max_size = upload_service._get_max_size("audio")
        assert max_size == 100 * 1024 * 1024, "Audio file size limit should be 100MB"
    
    @pytest.mark.asyncio
    async def test_valid_audio_upload(self, upload_service, mock_audio_file):
        """Test uploading a valid audio file"""
        with patch.object(upload_service, '_validate_audio_file', return_value=True):
            with patch.object(upload_service, '_extract_audio_metadata', return_value={
                "duration": 180.5,
                "bitrate": 128,
                "title": "Test Podcast",
                "artist": "Test Host"
            }):
                result = await upload_service.upload_file(mock_audio_file, validate_content=True)
                
                assert result["upload_success"] is True
                assert result["category"] == "audio"
                assert result["mime_type"] == "audio/mpeg"
                assert result["original_filename"] == "test_podcast.mp3"
                assert "audio_metadata" in result
                assert result["duration"] == 180.5
    
    @pytest.mark.asyncio
    async def test_audio_file_too_large(self, upload_service, mock_large_audio_file):
        """Test that large audio files are rejected"""
        with pytest.raises(FileSizeError):
            await upload_service.upload_file(mock_large_audio_file)
    
    @pytest.mark.asyncio
    async def test_invalid_audio_file_type(self, upload_service):
        """Test that non-audio files with audio MIME type are rejected"""
        # Create a text file claiming to be audio
        text_content = b'This is not an audio file'
        file_obj = BytesIO(text_content)
        upload_file = UploadFile(
            filename="fake.mp3",
            file=file_obj,
            content_type="text/plain"  # Wrong MIME type
        )
        
        with pytest.raises(FileTypeError):
            await upload_service.upload_file(upload_file)
    
    def test_audio_metadata_extraction_no_mutagen(self, upload_service):
        """Test audio metadata extraction when mutagen is not available"""
        with patch('app.services.file_upload.HAS_MUTAGEN', False):
            temp_file = Path(upload_service.upload_dir) / "test.mp3"
            temp_file.touch()
            
            metadata = upload_service._extract_audio_metadata(temp_file)
            
            # Should return empty metadata structure
            expected_keys = ["duration", "bitrate", "sample_rate", "channels", 
                           "title", "artist", "album", "genre", "year", "track_number"]
            for key in expected_keys:
                assert key in metadata
                assert metadata[key] is None
    
    def test_audio_validation_no_mutagen(self, upload_service):
        """Test audio validation when mutagen is not available"""
        with patch('app.services.file_upload.HAS_MUTAGEN', False):
            temp_file = Path(upload_service.upload_dir) / "test.mp3"
            temp_file.touch()
            
            # Should fall back to extension-based validation
            is_valid = upload_service._validate_audio_file(temp_file, "audio/mpeg")
            assert is_valid is True
            
            # Test invalid extension
            temp_file_invalid = Path(upload_service.upload_dir) / "test.txt"
            temp_file_invalid.touch()
            
            is_valid = upload_service._validate_audio_file(temp_file_invalid, "audio/mpeg")
            assert is_valid is False
    
    def test_secure_filename_generation_audio(self, upload_service):
        """Test secure filename generation for audio files"""
        filename = upload_service._generate_secure_filename("My Podcast Episode.mp3", "audio/mpeg")
        
        # Should have .mp3 extension
        assert filename.endswith(".mp3")
        # Should be a UUID-based filename
        assert len(filename) == 40  # 36 chars for UUID + 4 chars for .mp3
        # Should not contain original filename
        assert "My Podcast Episode" not in filename
    
    def test_audio_thumbnail_creation(self, upload_service):
        """Test audio thumbnail creation (currently returns None)"""
        temp_file = Path(upload_service.upload_dir) / "test.mp3"
        temp_file.touch()
        
        metadata = {"duration": 180, "title": "Test"}
        thumbnail = upload_service._create_audio_thumbnail(temp_file, metadata)
        
        # Currently should return None (placeholder implementation)
        assert thumbnail is None
    
    @pytest.mark.asyncio
    async def test_get_audio_metadata_method(self, upload_service):
        """Test the get_audio_metadata method"""
        # Create a test audio file
        audio_dir = Path(upload_service.upload_dir) / "audio"
        audio_dir.mkdir(exist_ok=True)
        test_file = audio_dir / "test.mp3"
        test_file.touch()
        
        with patch.object(upload_service, '_extract_audio_metadata', return_value={
            "duration": 120.0,
            "title": "Test Audio"
        }):
            metadata = upload_service.get_audio_metadata("audio/test.mp3")
            
            assert metadata is not None
            assert metadata["duration"] == 120.0
            assert metadata["title"] == "Test Audio"
    
    def test_get_audio_metadata_non_audio_file(self, upload_service):
        """Test get_audio_metadata with non-audio file"""
        # Create a test image file
        image_dir = Path(upload_service.upload_dir) / "images"
        image_dir.mkdir(exist_ok=True)
        test_file = image_dir / "test.jpg"
        test_file.touch()
        
        metadata = upload_service.get_audio_metadata("images/test.jpg")
        assert metadata is None
    
    def test_get_file_info_with_audio_metadata(self, upload_service):
        """Test get_file_info includes audio metadata for audio files"""
        # Create a test audio file
        audio_dir = Path(upload_service.upload_dir) / "audio"
        audio_dir.mkdir(exist_ok=True)
        test_file = audio_dir / "test.mp3"
        test_file.write_bytes(b"test content")
        
        with patch.object(upload_service, '_extract_audio_metadata', return_value={
            "duration": 90.0,
            "bitrate": 128
        }):
            info = upload_service.get_file_info("audio/test.mp3")
            
            assert info is not None
            assert "audio_metadata" in info
            assert info["duration"] == 90.0
            assert info["audio_metadata"]["bitrate"] == 128