"""
Enhanced file upload service with comprehensive validation and security
"""

import os
import aiofiles
import hashlib
from pathlib import Path
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.wav import WAVE
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
from uuid import uuid4
from typing import Optional, List, Dict, Any
from fastapi import UploadFile
from PIL import Image
import structlog
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import (
    FileUploadError,
    FileSizeError,
    FileTypeError
)

logger = structlog.get_logger()

class FileUploadService:
    """Enhanced file upload service with security and validation"""
    
    # File size limits (in bytes)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200MB
    MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB for podcasts
    MAX_DOCUMENT_SIZE = 25 * 1024 * 1024  # 25MB
    
    # Allowed MIME types
    ALLOWED_IMAGE_TYPES = {
        "image/jpeg", "image/jpg", "image/png", "image/gif", 
        "image/webp", "image/bmp", "image/tiff", "image/avif"
    }
    
    ALLOWED_VIDEO_TYPES = {
        "video/mp4", "video/avi", "video/mov", "video/wmv", 
        "video/webm", "video/mkv", "video/flv"
    }
    
    ALLOWED_AUDIO_TYPES = {
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", 
        "audio/m4a", "audio/aac", "audio/flac", "audio/webm"
    }
    
    ALLOWED_DOCUMENT_TYPES = {
        "application/pdf", "text/plain", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    
    # File extensions mapping
    EXTENSION_MAPPING = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg", 
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/avif": ".avif",
        "video/mp4": ".mp4",
        "video/avi": ".avi",
        "video/mov": ".mov",
        "video/wmv": ".wmv",
        "video/webm": ".webm",
        "video/mkv": ".mkv",
        "video/flv": ".flv",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/m4a": ".m4a",
        "audio/aac": ".aac",
        "audio/flac": ".flac",
        "audio/webm": ".webm",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"
    }
    
    def __init__(self, upload_dir: str = "uploads"):
        """
        Initialize file upload service
        
        Args:
            upload_dir: Base directory for file uploads
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        for subdir in ["images", "videos", "audio", "documents", "temp", "thumbnails"]:
            (self.upload_dir / subdir).mkdir(exist_ok=True)
        
        # R2 storage configuration
        self.use_r2 = settings.USE_R2_STORAGE.lower() == 'true'
        self.r2_bucket = settings.R2_BUCKET_NAME
        self.r2_endpoint = settings.R2_ENDPOINT_URL
        self.r2_access_key = settings.R2_ACCESS_KEY_ID
        self.r2_secret_key = settings.R2_SECRET_ACCESS_KEY
    
    def _get_r2_client(self):
        """Initialize R2 client using boto3 S3-compatible API"""
        if not all([self.r2_endpoint, self.r2_access_key, self.r2_secret_key]):
            raise FileUploadError("R2 credentials not configured")
        
        return boto3.client(
            's3',
            endpoint_url=self.r2_endpoint,
            aws_access_key_id=self.r2_access_key,
            aws_secret_access_key=self.r2_secret_key,
            region_name='auto'
        )
    
    async def _upload_to_r2(self, file_content: bytes, file_key: str, mime_type: str) -> str:
        """
        Upload file directly to R2
        
        Args:
            file_content: File bytes
            file_key: Object key (path) in R2 bucket
            mime_type: File MIME type
            
        Returns:
            File key (path) in R2
        """
        try:
            r2_client = self._get_r2_client()
            r2_client.put_object(
                Bucket=self.r2_bucket,
                Key=file_key,
                Body=file_content,
                ContentType=mime_type
            )
            logger.info("File uploaded to R2", file_key=file_key, bucket=self.r2_bucket)
            return file_key
        except ClientError as e:
            logger.error("R2 upload failed", error=str(e), file_key=file_key)
            raise FileUploadError(f"R2 upload failed: {str(e)}")
    
    async def generate_presigned_upload_url(self, filename: str, file_size: int, mime_type: str) -> Dict[str, Any]:
        """
        Generate presigned URL for direct frontend upload to R2
        
        Args:
            filename: Original filename
            file_size: File size in bytes
            mime_type: File MIME type
            
        Returns:
            Dictionary with upload_url, file_key, and expires_in
        """
        try:
            # Validate file size and type
            category = self._get_file_category(mime_type)
            max_size = self._get_max_size(category)
            
            if file_size > max_size:
                raise FileSizeError(category, file_size, max_size)
            
            # Generate secure filename and file key
            extension = self.EXTENSION_MAPPING.get(mime_type, Path(filename).suffix)
            secure_filename = f"{uuid4().hex}{extension}"
            file_key = f"{category}/{secure_filename}"
            
            # Generate presigned URL (valid for 1 hour)
            r2_client = self._get_r2_client()
            presigned_url = r2_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.r2_bucket,
                    'Key': file_key,
                    'ContentType': mime_type
                },
                ExpiresIn=3600  # 1 hour
            )
            
            logger.info("Presigned URL generated", file_key=file_key, expires_in=3600)
            
            return {
                "upload_url": presigned_url,
                "file_key": file_key,
                "expires_in": 3600,
                "mime_type": mime_type,
                "category": category
            }
            
        except (FileTypeError, FileSizeError) as e:
            raise e
        except Exception as e:
            logger.error("Presigned URL generation failed", error=str(e))
            raise FileUploadError(f"Failed to generate presigned URL: {str(e)}")
    
    def _get_file_category(self, mime_type: str) -> str:
        """
        Determine file category based on MIME type
        
        Args:
            mime_type: File MIME type
            
        Returns:
            File category (images, videos, documents)
        """
        if mime_type in self.ALLOWED_IMAGE_TYPES:
            return "images"
        elif mime_type in self.ALLOWED_VIDEO_TYPES:
            return "videos"
        elif mime_type in self.ALLOWED_AUDIO_TYPES:
            return "audio"
        elif mime_type in self.ALLOWED_DOCUMENT_TYPES:
            return "documents"
        else:
            raise FileTypeError("unknown", mime_type, list(
                self.ALLOWED_IMAGE_TYPES | 
                self.ALLOWED_VIDEO_TYPES | 
                self.ALLOWED_AUDIO_TYPES |
                self.ALLOWED_DOCUMENT_TYPES
            ))
    
    def _get_max_size(self, file_category: str) -> int:
        """
        Get maximum file size for category
        
        Args:
            file_category: File category
            
        Returns:
            Maximum file size in bytes
        """
        size_limits = {
            "images": self.MAX_IMAGE_SIZE,
            "videos": self.MAX_VIDEO_SIZE,
            "audio": self.MAX_AUDIO_SIZE,
            "documents": self.MAX_DOCUMENT_SIZE
        }
        return size_limits.get(file_category, self.MAX_DOCUMENT_SIZE)
    
    async def _validate_file_content(self, file_path: Path, mime_type: str) -> bool:
        """
        Validate file content matches declared MIME type
        
        Args:
            file_path: Path to uploaded file
            mime_type: Declared MIME type
            
        Returns:
            True if content is valid
        """
        try:
            # Use python-magic to detect actual file type if available
            if HAS_MAGIC:
                actual_mime = magic.from_file(str(file_path), mime=True)
            else:
                # Fallback: basic validation without magic
                actual_mime = mime_type
            
            # For images, also validate with PIL (except WebP and AVIF)
            if mime_type in self.ALLOWED_IMAGE_TYPES:
                try:
                    # Skip PIL validation for WebP and AVIF files since PIL doesn't support them well
                    if mime_type in ["image/webp", "image/avif"]:
                        if HAS_MAGIC:
                            return actual_mime in self.ALLOWED_IMAGE_TYPES
                        else:
                            return True  # Trust the MIME type for WebP and AVIF
                    
                    with Image.open(file_path) as img:
                        img.verify()  # Verify it's a valid image
                    if HAS_MAGIC:
                        return actual_mime in self.ALLOWED_IMAGE_TYPES
                    else:
                        return True  # PIL validation passed
                except Exception:
                    return False
            
            # For other files, check if detected type matches allowed types
            if HAS_MAGIC:
                return actual_mime == mime_type or actual_mime in (
                    self.ALLOWED_IMAGE_TYPES | 
                    self.ALLOWED_VIDEO_TYPES | 
                    self.ALLOWED_AUDIO_TYPES |
                    self.ALLOWED_DOCUMENT_TYPES
                )
            else:
                # Basic validation: check file extension matches mime type
                return mime_type in (
                    self.ALLOWED_IMAGE_TYPES | 
                    self.ALLOWED_VIDEO_TYPES | 
                    self.ALLOWED_AUDIO_TYPES |
                    self.ALLOWED_DOCUMENT_TYPES
                )
            
        except Exception as e:
            logger.warning("File content validation failed", error=str(e))
            return False
    
    def _extract_audio_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from audio files
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio metadata
        """
        metadata = {
            "duration": None,
            "bitrate": None,
            "sample_rate": None,
            "channels": None,
            "title": None,
            "artist": None,
            "album": None,
            "genre": None,
            "year": None,
            "track_number": None
        }
        
        if not HAS_MUTAGEN:
            logger.warning("Mutagen not available for audio metadata extraction")
            return metadata
        
        try:
            audio_file = MutagenFile(str(file_path))
            if audio_file is None:
                return metadata
            
            # Extract basic audio properties
            if hasattr(audio_file, 'info'):
                info = audio_file.info
                metadata["duration"] = getattr(info, 'length', None)
                metadata["bitrate"] = getattr(info, 'bitrate', None)
                metadata["sample_rate"] = getattr(info, 'sample_rate', None)
                metadata["channels"] = getattr(info, 'channels', None)
            
            # Extract tags
            if hasattr(audio_file, 'tags') and audio_file.tags:
                tags = audio_file.tags
                
                # Common tag mappings
                tag_mappings = {
                    'title': ['TIT2', 'TITLE', '\xa9nam'],
                    'artist': ['TPE1', 'ARTIST', '\xa9ART'],
                    'album': ['TALB', 'ALBUM', '\xa9alb'],
                    'genre': ['TCON', 'GENRE', '\xa9gen'],
                    'year': ['TDRC', 'DATE', '\xa9day'],
                    'track_number': ['TRCK', 'TRACKNUMBER', 'trkn']
                }
                
                for field, tag_keys in tag_mappings.items():
                    for tag_key in tag_keys:
                        if tag_key in tags:
                            value = tags[tag_key]
                            if isinstance(value, list) and value:
                                value = value[0]
                            if hasattr(value, 'text') and value.text:
                                value = value.text[0] if isinstance(value.text, list) else value.text
                            metadata[field] = str(value) if value else None
                            break
            
            logger.info("Audio metadata extracted successfully", 
                       duration=metadata["duration"], 
                       bitrate=metadata["bitrate"])
            
        except Exception as e:
            logger.warning("Failed to extract audio metadata", error=str(e))
        
        return metadata
    
    def _validate_audio_file(self, file_path: Path, mime_type: str) -> bool:
        """
        Enhanced validation for audio files
        
        Args:
            file_path: Path to audio file
            mime_type: Declared MIME type
            
        Returns:
            True if audio file is valid
        """
        try:
            # Basic MIME type check
            if mime_type not in self.ALLOWED_AUDIO_TYPES:
                return False
            
            # Use mutagen for deeper validation if available
            if HAS_MUTAGEN:
                audio_file = MutagenFile(str(file_path))
                if audio_file is None:
                    return False
                
                # Check if file has valid audio info
                if hasattr(audio_file, 'info'):
                    info = audio_file.info
                    # Validate duration (should be positive)
                    duration = getattr(info, 'length', 0)
                    if duration <= 0:
                        return False
                    
                    # Validate bitrate (should be reasonable for audio)
                    bitrate = getattr(info, 'bitrate', 0)
                    if bitrate > 0 and (bitrate < 8 or bitrate > 2000):  # 8 kbps to 2000 kbps
                        logger.warning("Unusual bitrate detected", bitrate=bitrate)
                    
                    # Validate sample rate (should be reasonable for audio)
                    sample_rate = getattr(info, 'sample_rate', 0)
                    if sample_rate > 0 and (sample_rate < 8000 or sample_rate > 192000):
                        logger.warning("Unusual sample rate detected", sample_rate=sample_rate)
                
                return True
            else:
                # Fallback: basic file extension check
                extension = file_path.suffix.lower()
                valid_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac']
                return extension in valid_extensions
                
        except Exception as e:
            logger.warning("Audio file validation failed", error=str(e))
            return False
    
    def _create_audio_thumbnail(self, file_path: Path, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Create thumbnail for audio files (placeholder image with metadata)
        
        Args:
            file_path: Path to audio file
            metadata: Audio metadata
            
        Returns:
            Thumbnail URL or None
        """
        try:
            # For now, we'll return None as audio thumbnails would require
            # extracting embedded album art or generating waveform images
            # This can be enhanced later with libraries like librosa or pydub
            return None
            
        except Exception as e:
            logger.warning("Failed to create audio thumbnail", error=str(e))
            return None
    
    def _generate_secure_filename(self, original_filename: str, mime_type: str) -> str:
        """
        Generate secure filename with proper extension
        
        Args:
            original_filename: Original filename
            mime_type: File MIME type
            
        Returns:
            Secure filename
        """
        # Get proper extension from MIME type
        extension = self.EXTENSION_MAPPING.get(mime_type, "")
        
        # If no extension mapping, try to extract from original filename
        if not extension and original_filename:
            original_ext = Path(original_filename).suffix.lower()
            if original_ext:
                extension = original_ext
        
        # Generate unique filename
        unique_id = str(uuid4())
        return f"{unique_id}{extension}"
    
    def _calculate_file_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content
        
        Args:
            content: File content bytes
            
        Returns:
            SHA-256 hash string
        """
        return hashlib.sha256(content).hexdigest()
    
    async def upload_file(
        self, 
        file: UploadFile, 
        file_category: Optional[str] = None,
        validate_content: bool = True
    ) -> Dict[str, Any]:
        """
        Upload and validate file with comprehensive security checks
        
        Args:
            file: FastAPI UploadFile object
            file_category: Optional file category override
            validate_content: Whether to validate file content
            
        Returns:
            Dictionary with file information
            
        Raises:
            FileUploadError: If upload fails
            FileSizeError: If file is too large
            FileTypeError: If file type is not allowed
        """
        if not file or not file.filename:
            raise FileUploadError("No file provided")
        
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Detect MIME type
            declared_mime = file.content_type
            if not declared_mime:
                raise FileTypeError(file.filename, "unknown", list(
                    self.ALLOWED_IMAGE_TYPES | 
                    self.ALLOWED_VIDEO_TYPES | 
                    self.ALLOWED_AUDIO_TYPES |
                    self.ALLOWED_DOCUMENT_TYPES
                ))
            
            # Determine file category
            if not file_category:
                file_category = self._get_file_category(declared_mime)
            
            # Validate file size
            max_size = self._get_max_size(file_category)
            if file_size > max_size:
                raise FileSizeError(file.filename, file_size, max_size)
            
            # Generate secure filename
            secure_filename = self._generate_secure_filename(file.filename, declared_mime)
            
            # Create file key for storage (works for both local and R2)
            file_key = f"{file_category}/{secure_filename}"
            file_path = self.upload_dir / file_category / secure_filename
            
            # Ensure temp directory exists
            temp_dir = self.upload_dir / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file temporarily for content validation
            temp_path = temp_dir / secure_filename
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(content)
            
            # Validate file content if requested
            if validate_content:
                # Use enhanced audio validation for audio files
                if file_category == "audio":
                    is_valid = self._validate_audio_file(temp_path, declared_mime)
                else:
                    is_valid = await self._validate_file_content(temp_path, declared_mime)
                
                if not is_valid:
                    # Clean up temp file
                    temp_path.unlink(missing_ok=True)
                    raise FileTypeError(
                        file.filename, 
                        declared_mime, 
                        list(self.ALLOWED_IMAGE_TYPES | self.ALLOWED_VIDEO_TYPES | self.ALLOWED_AUDIO_TYPES | self.ALLOWED_DOCUMENT_TYPES)
                    )
            
            # Upload to R2 or save locally based on configuration
            if self.use_r2:
                # Upload to R2
                await self._upload_to_r2(content, file_key, declared_mime)
                # Clean up temp file
                temp_path.unlink(missing_ok=True)
                logger.info("File uploaded to R2", file_key=file_key)
            else:
                # Move file to final location on local disk
                file_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.rename(file_path)
                logger.info("File uploaded locally", file_path=str(file_path))
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(content)
            
            # Extract metadata for audio files (from temp file if R2, or final file if local)
            audio_metadata = None
            audio_thumbnail = None
            if file_category == "audio":
                # For R2, use temp file (we'll clean it up after). For local, use final file
                metadata_path = temp_path if self.use_r2 else file_path
                if metadata_path.exists():
                    audio_metadata = self._extract_audio_metadata(metadata_path)
                    audio_thumbnail = self._create_audio_thumbnail(metadata_path, audio_metadata)
                    # Clean up temp file if using R2
                    if self.use_r2:
                        temp_path.unlink(missing_ok=True)
            
            # Generate file URL (relative path - works for both local and R2)
            file_url = file_key  # e.g., "images/abc123.jpg"
            
            # Log successful upload
            logger.info(
                "File uploaded successfully",
                filename=file.filename,
                secure_filename=secure_filename,
                file_size=file_size,
                mime_type=declared_mime,
                category=file_category,
                duration=audio_metadata.get("duration") if audio_metadata else None
            )
            
            # Build return dictionary
            result = {
                "filename": secure_filename,
                "original_filename": file.filename,
                "file_path": str(file_path),
                "file_url": file_url,
                "file_size": file_size,
                "mime_type": declared_mime,
                "category": file_category,
                "file_hash": file_hash,
                "upload_success": True
            }
            
            # Add audio-specific metadata
            if audio_metadata:
                result["audio_metadata"] = audio_metadata
                result["duration"] = audio_metadata.get("duration")
                
            if audio_thumbnail:
                result["thumbnail_url"] = audio_thumbnail
            
            return result
            
        except (FileUploadError, FileSizeError, FileTypeError):
            raise
        except Exception as e:
            logger.error("File upload failed", error=str(e), filename=file.filename)
            raise FileUploadError(f"Upload failed: {str(e)}", file.filename)
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete uploaded file
        
        Args:
            file_path: Relative file path
            
        Returns:
            True if file was deleted successfully
        """
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists() and full_path.is_file():
                full_path.unlink()
                logger.info("File deleted successfully", file_path=file_path)
                return True
            return False
        except Exception as e:
            logger.error("File deletion failed", error=str(e), file_path=file_path)
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about uploaded file
        
        Args:
            file_path: Relative file path
            
        Returns:
            File information dictionary or None if file doesn't exist
        """
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            info = {
                "file_path": file_path,
                "file_size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "exists": True
            }
            
            # Add audio metadata if it's an audio file
            if file_path.startswith("audio/"):
                audio_metadata = self._extract_audio_metadata(full_path)
                if audio_metadata:
                    info["audio_metadata"] = audio_metadata
                    info["duration"] = audio_metadata.get("duration")
            
            return info
        except Exception:
            return None
    
    def get_audio_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get audio metadata for a specific audio file
        
        Args:
            file_path: Relative path to audio file
            
        Returns:
            Audio metadata dictionary or None if file doesn't exist or isn't audio
        """
        try:
            full_path = self.upload_dir / file_path
            if not full_path.exists() or not file_path.startswith("audio/"):
                return None
            
            return self._extract_audio_metadata(full_path)
        except Exception:
            return None
    
    def list_files(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List uploaded files
        
        Args:
            category: Optional category filter
            
        Returns:
            List of file information dictionaries
        """
        files = []
        
        try:
            if category:
                search_dirs = [self.upload_dir / category]
            else:
                search_dirs = [
                    self.upload_dir / "images",
                    self.upload_dir / "videos", 
                    self.upload_dir / "audio",
                    self.upload_dir / "documents"
                ]
            
            for search_dir in search_dirs:
                if search_dir.exists():
                    for file_path in search_dir.iterdir():
                        if file_path.is_file():
                            relative_path = file_path.relative_to(self.upload_dir)
                            file_info = self.get_file_info(str(relative_path))
                            if file_info:
                                files.append(file_info)
            
            return files
            
        except Exception as e:
            logger.error("Failed to list files", error=str(e))
            return []


# Global file upload service instance
file_upload_service = FileUploadService()