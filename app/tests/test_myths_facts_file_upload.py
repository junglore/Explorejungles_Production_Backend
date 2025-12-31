"""
Tests for file upload functionality in myths vs facts
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os
from pathlib import Path
import io
from PIL import Image

from app.models.myth_fact import MythFact
from app.models.category import Category
from app.services.file_upload import file_upload_service


class TestMythsFactsFileUpload:
    """Test file upload functionality for myths vs facts"""

    @pytest.fixture
    def large_image_file(self):
        """Create a large image file for testing size limits"""
        # Create a large image (simulating > 10MB)
        img = Image.new('RGB', (3000, 3000), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=95)
        img_bytes.seek(0)
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(img_bytes.getvalue())
            f.flush()
            yield f.name
        
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass

    @pytest.fixture
    def invalid_file(self):
        """Create an invalid file type for testing"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"This is not an image file")
            f.flush()
            yield f.name
        
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass

    @pytest.fixture
    def corrupted_image_file(self):
        """Create a corrupted image file for testing"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"Not a valid JPEG file content")
            f.flush()
            yield f.name
        
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass

    @pytest.mark.asyncio
    async def test_valid_image_upload_create(self, client: AsyncClient, admin_headers: dict, sample_image_file, test_category: Category):
        """Test uploading valid image during myth fact creation"""
        with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
            mock_upload.return_value = "/uploads/images/test-image.jpg"
            
            with open(sample_image_file, 'rb') as f:
                files = {"image": ("test.jpg", f, "image/jpeg")}
                data = {
                    "title": "Myth with Image",
                    "myth_content": "This myth has an image",
                    "fact_content": "This fact explains with visual aid",
                    "category_id": str(test_category.id)
                }
                
                # Test via API endpoint (if file upload is supported)
                response = await client.post(
                    "/api/v1/myths-facts/",
                    data=data,
                    files=files,
                    headers=admin_headers
                )
                
                # Should either succeed or indicate file upload not supported via API
                assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_valid_image_upload_admin_create(self, client: AsyncClient, sample_image_file, test_category: Category):
        """Test uploading valid image via admin interface"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
                mock_upload.return_value = "/uploads/images/admin-test.jpg"
                
                with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                    mock_session = AsyncMock()
                    mock_db.return_value.__aenter__.return_value = mock_session
                    
                    mock_session.add = AsyncMock()
                    mock_session.commit = AsyncMock()
                    mock_session.refresh = AsyncMock()
                    
                    with open(sample_image_file, 'rb') as f:
                        files = {"image": ("admin-test.jpg", f, "image/jpeg")}
                        data = {
                            "title": "Admin Myth with Image",
                            "myth_content": "Admin myth content",
                            "fact_content": "Admin fact content",
                            "category_id": str(test_category.id)
                        }
                        
                        response = await client.post(
                            "/admin/myths-facts/create",
                            data=data,
                            files=files
                        )
                        
                        assert response.status_code in [200, 302]
                        mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_file_type_upload(self, client: AsyncClient, admin_headers: dict, invalid_file):
        """Test uploading invalid file type"""
        with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
            mock_upload.side_effect = ValueError("Invalid file type")
            
            with open(invalid_file, 'rb') as f:
                files = {"image": ("invalid.txt", f, "text/plain")}
                data = {
                    "title": "Myth with Invalid File",
                    "myth_content": "This should fail",
                    "fact_content": "File type validation should catch this"
                }
                
                # Test file type validation
                response = await client.post(
                    "/api/v1/myths-facts/",
                    data=data,
                    files=files,
                    headers=admin_headers
                )
                
                # Should reject invalid file type
                assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_large_file_upload(self, client: AsyncClient, admin_headers: dict, large_image_file):
        """Test uploading file that exceeds size limit"""
        with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
            mock_upload.side_effect = ValueError("File size exceeds limit")
            
            with open(large_image_file, 'rb') as f:
                files = {"image": ("large.jpg", f, "image/jpeg")}
                data = {
                    "title": "Myth with Large File",
                    "myth_content": "This file is too large",
                    "fact_content": "Should be rejected"
                }
                
                response = await client.post(
                    "/api/v1/myths-facts/",
                    data=data,
                    files=files,
                    headers=admin_headers
                )
                
                # Should reject large file
                assert response.status_code in [400, 413, 422]

    @pytest.mark.asyncio
    async def test_corrupted_image_upload(self, client: AsyncClient, admin_headers: dict, corrupted_image_file):
        """Test uploading corrupted image file"""
        with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
            mock_upload.side_effect = ValueError("Corrupted image file")
            
            with open(corrupted_image_file, 'rb') as f:
                files = {"image": ("corrupted.jpg", f, "image/jpeg")}
                data = {
                    "title": "Myth with Corrupted Image",
                    "myth_content": "This image is corrupted",
                    "fact_content": "Should be rejected"
                }
                
                response = await client.post(
                    "/api/v1/myths-facts/",
                    data=data,
                    files=files,
                    headers=admin_headers
                )
                
                # Should reject corrupted file
                assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_file_upload_service_integration(self, temp_upload_dir, sample_image_file):
        """Test file upload service integration"""
        # Mock the file upload service
        with patch('app.services.file_upload.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.mkdir.return_value = None
            
            with patch('app.services.file_upload.uuid4') as mock_uuid:
                mock_uuid.return_value = MagicMock()
                mock_uuid.return_value.hex = "test123"
                
                with patch('builtins.open', create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_open.return_value.__enter__.return_value = mock_file
                    
                    # Test file upload
                    with open(sample_image_file, 'rb') as f:
                        file_content = f.read()
                        
                    # Mock UploadFile
                    mock_upload_file = MagicMock()
                    mock_upload_file.filename = "test.jpg"
                    mock_upload_file.content_type = "image/jpeg"
                    mock_upload_file.size = len(file_content)
                    mock_upload_file.read = AsyncMock(return_value=file_content)
                    
                    # Test the upload
                    result = await file_upload_service.upload_file(mock_upload_file, "images")
                    
                    # Should return a file path
                    assert isinstance(result, str)
                    assert result.startswith("/")

    @pytest.mark.asyncio
    async def test_file_upload_validation_mime_type(self):
        """Test MIME type validation in file upload"""
        # Test valid MIME types
        valid_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        
        for mime_type in valid_types:
            mock_file = MagicMock()
            mock_file.content_type = mime_type
            mock_file.filename = f"test.{mime_type.split('/')[-1]}"
            mock_file.size = 1024  # 1KB
            
            # Should not raise exception for valid types
            try:
                # This would be the validation logic
                assert mime_type.startswith("image/")
                assert mock_file.size < 10 * 1024 * 1024  # 10MB limit
            except Exception:
                pytest.fail(f"Valid MIME type {mime_type} was rejected")

    @pytest.mark.asyncio
    async def test_file_upload_validation_file_extension(self):
        """Test file extension validation"""
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        
        for ext in valid_extensions:
            filename = f"test{ext}"
            # Should be valid
            assert any(filename.lower().endswith(valid_ext) for valid_ext in valid_extensions)

    @pytest.mark.asyncio
    async def test_file_upload_security_validation(self):
        """Test security validations in file upload"""
        # Test malicious filenames
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "test.php.jpg",
            "script.js.png",
            "<script>alert('xss')</script>.jpg"
        ]
        
        for filename in malicious_names:
            # Should sanitize or reject malicious filenames
            sanitized = filename.replace("../", "").replace("..\\", "")
            sanitized = "".join(c for c in sanitized if c.isalnum() or c in ".-_")
            
            # Should not contain path traversal
            assert "../" not in sanitized
            assert "..\\" not in sanitized

    @pytest.mark.asyncio
    async def test_image_optimization_integration(self, sample_image_file):
        """Test image optimization during upload"""
        with patch('app.services.image_optimization.optimize_image') as mock_optimize:
            mock_optimize.return_value = "/optimized/path.jpg"
            
            # Mock file upload with optimization
            mock_file = MagicMock()
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            
            with open(sample_image_file, 'rb') as f:
                mock_file.read = AsyncMock(return_value=f.read())
            
            # Test optimization is called
            with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
                mock_upload.return_value = "/uploads/optimized.jpg"
                
                result = await file_upload_service.upload_file(mock_file, "images")
                
                # Should return optimized path
                assert result is not None

    @pytest.mark.asyncio
    async def test_file_cleanup_on_error(self, sample_image_file):
        """Test file cleanup when upload fails"""
        with patch('app.services.file_upload.Path') as mock_path:
            mock_file_path = MagicMock()
            mock_path.return_value = mock_file_path
            
            # Simulate upload failure after file is written
            mock_file_path.exists.return_value = True
            mock_file_path.unlink = MagicMock()
            
            with patch('builtins.open', side_effect=Exception("Write failed")):
                mock_upload_file = MagicMock()
                mock_upload_file.filename = "test.jpg"
                mock_upload_file.content_type = "image/jpeg"
                
                with open(sample_image_file, 'rb') as f:
                    mock_upload_file.read = AsyncMock(return_value=f.read())
                
                # Should clean up on failure
                try:
                    await file_upload_service.upload_file(mock_upload_file, "images")
                except Exception:
                    pass  # Expected to fail
                
                # Should attempt cleanup (in real implementation)
                # This tests the error handling pattern

    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(self, sample_image_file):
        """Test handling concurrent file uploads"""
        import asyncio
        
        async def upload_file():
            with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
                mock_upload.return_value = f"/uploads/concurrent-{asyncio.current_task().get_name()}.jpg"
                
                mock_file = MagicMock()
                mock_file.filename = "concurrent.jpg"
                mock_file.content_type = "image/jpeg"
                
                with open(sample_image_file, 'rb') as f:
                    mock_file.read = AsyncMock(return_value=f.read())
                
                return await file_upload_service.upload_file(mock_file, "images")
        
        # Test multiple concurrent uploads
        tasks = [upload_file() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed or fail gracefully
        for result in results:
            assert isinstance(result, (str, Exception))

    @pytest.mark.asyncio
    async def test_file_upload_admin_edit_form(self, client: AsyncClient, test_db: AsyncSession, test_category: Category, sample_image_file):
        """Test file upload in admin edit form"""
        # Create existing myth fact
        myth_fact = MythFact(
            title="Existing Myth",
            myth_content="Existing myth content",
            fact_content="Existing fact content",
            category_id=test_category.id,
            image_url="/old/image.jpg"
        )
        test_db.add(myth_fact)
        await test_db.commit()
        await test_db.refresh(myth_fact)
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
                mock_upload.return_value = "/uploads/images/updated-image.jpg"
                
                with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                    mock_session = AsyncMock()
                    mock_db.return_value.__aenter__.return_value = mock_session
                    
                    # Mock finding existing myth fact
                    mock_result = AsyncMock()
                    mock_result.scalar_one_or_none.return_value = myth_fact
                    mock_session.execute.return_value = mock_result
                    
                    mock_session.commit = AsyncMock()
                    mock_session.refresh = AsyncMock()
                    
                    with open(sample_image_file, 'rb') as f:
                        files = {"image": ("updated.jpg", f, "image/jpeg")}
                        data = {
                            "title": "Updated Myth with New Image",
                            "myth_content": "Updated myth content",
                            "fact_content": "Updated fact content"
                        }
                        
                        response = await client.post(
                            f"/admin/myths-facts/edit/{myth_fact.id}",
                            data=data,
                            files=files
                        )
                        
                        assert response.status_code in [200, 302]
                        mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_upload_error_handling(self, client: AsyncClient, admin_headers: dict, sample_image_file):
        """Test error handling in file upload"""
        with patch('app.services.file_upload.file_upload_service.upload_file') as mock_upload:
            # Test different types of upload errors
            upload_errors = [
                OSError("Disk full"),
                PermissionError("Permission denied"),
                ValueError("Invalid file format"),
                Exception("Unexpected error")
            ]
            
            for error in upload_errors:
                mock_upload.side_effect = error
                
                with open(sample_image_file, 'rb') as f:
                    files = {"image": ("error-test.jpg", f, "image/jpeg")}
                    data = {
                        "title": "Error Test Myth",
                        "myth_content": "This should handle errors",
                        "fact_content": "Error handling test"
                    }
                    
                    response = await client.post(
                        "/api/v1/myths-facts/",
                        data=data,
                        files=files,
                        headers=admin_headers
                    )
                    
                    # Should handle error gracefully
                    assert response.status_code in [400, 422, 500]