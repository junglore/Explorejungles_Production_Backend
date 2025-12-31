"""
Comprehensive tests for Podcast Admin routes
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4, UUID
from unittest.mock import patch, AsyncMock, MagicMock
import tempfile
import os
from pathlib import Path
from io import BytesIO

from app.models.media import Media
from app.models.category import Category
from app.models.user import User


class TestPodcastAdmin:
    """Test class for Podcast Admin routes"""

    @pytest.fixture
    async def authenticated_session(self, client: AsyncClient):
        """Create authenticated admin session"""
        # Simulate admin login
        async with client as ac:
            # Mock session authentication
            with patch.object(ac, 'cookies') as mock_cookies:
                mock_cookies.get.return_value = "authenticated_session"
                yield ac

    @pytest.fixture
    async def test_podcast(self, test_db: AsyncSession, test_category: Category) -> Media:
        """Create a test podcast for admin operations"""
        podcast = Media(
            media_type="PODCAST",
            title="Admin Test Podcast",
            description="Test podcast for admin operations",
            file_url="/uploads/audio/admin-test.mp3",
            thumbnail_url="/uploads/images/admin-test-thumb.jpg",
            photographer="Admin Test Host",
            national_park="Admin Test Show",
            category_id=test_category.id,
            file_size=30000000,
            filename="admin-test.mp3",
            original_filename="Admin Test Podcast.mp3",
            mime_type="audio/mpeg",
            duration=2100,
            file_metadata={
                "episode_number": 1,
                "season_number": 1,
                "uploaded_by": "admin"
            }
        )
        test_db.add(podcast)
        await test_db.commit()
        await test_db.refresh(podcast)
        return podcast

    @pytest.fixture
    def mock_audio_file(self):
        """Create mock audio file for upload tests"""
        audio_content = b'ID3\x03\x00\x00\x00\x00\x00\x00' + b'\x00' * 1000
        return ("test_podcast.mp3", BytesIO(audio_content), "audio/mpeg")

    @pytest.fixture
    def mock_image_file(self):
        """Create mock image file for cover upload tests"""
        # Minimal JPEG header
        jpeg_content = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46
        ]) + b'\x00' * 100
        return ("cover.jpg", BytesIO(jpeg_content), "image/jpeg")

    @pytest.mark.asyncio
    async def test_podcast_dashboard_unauthenticated(self, client: AsyncClient):
        """Test that dashboard redirects when not authenticated"""
        response = await client.get("/admin/podcasts/")
        
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_podcast_dashboard_authenticated(self, client: AsyncClient, test_podcast: Media):
        """Test podcast dashboard with authentication"""
        # Mock authentication
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock database queries
                mock_session.execute.return_value.scalar.side_effect = [3, 75000000]  # 3 podcasts, 75MB total
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_podcast
                
                response = await client.get("/admin/podcasts/")
                
                assert response.status_code == 200
                assert "Podcast Management Dashboard" in response.text
                assert "3" in response.text  # Total podcasts count
                assert "71.5 MB" in response.text  # Formatted file size

    @pytest.mark.asyncio
    async def test_podcast_dashboard_database_error(self, client: AsyncClient):
        """Test dashboard handles database errors gracefully"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_db.side_effect = Exception("Database connection failed")
                
                response = await client.get("/admin/podcasts/")
                
                assert response.status_code == 200
                assert "Error loading dashboard" in response.text

    @pytest.mark.asyncio
    async def test_create_podcast_form_unauthenticated(self, client: AsyncClient):
        """Test create form redirects when not authenticated"""
        response = await client.get("/admin/podcasts/create")
        
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_create_podcast_form_authenticated(self, client: AsyncClient, test_category: Category):
        """Test create podcast form loads correctly"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock categories query
                mock_session.execute.return_value.scalars.return_value.all.return_value = [test_category]
                
                response = await client.get("/admin/podcasts/create")
                
                assert response.status_code == 200
                assert "Create New Podcast" in response.text
                assert test_category.name in response.text

    @pytest.mark.asyncio
    async def test_create_podcast_success(self, client: AsyncClient, test_category: Category, mock_audio_file, mock_image_file):
        """Test successful podcast creation"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock category validation
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_category
                
                # Mock file upload service
                with patch('app.admin.routes.podcasts.file_upload_service') as mock_upload:
                    mock_upload.upload_file.side_effect = [
                        {  # Audio file upload result
                            "category": "audio",
                            "file_url": "audio/test-podcast.mp3",
                            "file_size": 25000000,
                            "filename": "test-podcast.mp3",
                            "original_filename": "test_podcast.mp3",
                            "mime_type": "audio/mpeg",
                            "file_hash": "abc123"
                        },
                        {  # Cover image upload result
                            "category": "images",
                            "file_url": "images/cover.jpg"
                        }
                    ]
                    
                    # Mock database operations
                    mock_podcast = Media(id=uuid4())
                    mock_session.add = MagicMock()
                    mock_session.commit = AsyncMock()
                    mock_session.refresh = AsyncMock()
                    
                    form_data = {
                        "title": "New Test Podcast",
                        "description": "Test description",
                        "photographer": "Test Host",
                        "national_park": "Test Show",
                        "category_id": str(test_category.id)
                    }
                    
                    files = {
                        "audio_file": mock_audio_file,
                        "cover_image": mock_image_file
                    }
                    
                    response = await client.post("/admin/podcasts/create", data=form_data, files=files)
                    
                    assert response.status_code == 302
                    assert "/admin/podcasts/list" in response.headers["location"]
                    assert "upload_success=true" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_create_podcast_unauthenticated(self, client: AsyncClient):
        """Test create podcast fails without authentication"""
        form_data = {"title": "Should Fail"}
        
        response = await client.post("/admin/podcasts/create", data=form_data)
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_podcast_invalid_category(self, client: AsyncClient, mock_audio_file):
        """Test create podcast with invalid category"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock category not found
                mock_session.execute.return_value.scalar_one_or_none.return_value = None
                
                form_data = {
                    "title": "Test Podcast",
                    "category_id": str(uuid4())  # Non-existent category
                }
                
                files = {"audio_file": mock_audio_file}
                
                response = await client.post("/admin/podcasts/create", data=form_data, files=files)
                
                assert response.status_code == 400
                assert "Invalid category ID" in response.text

    @pytest.mark.asyncio
    async def test_create_podcast_invalid_audio_file(self, client: AsyncClient):
        """Test create podcast with invalid audio file"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.file_upload_service') as mock_upload:
                # Mock invalid audio file
                mock_upload.upload_file.return_value = {
                    "category": "images",  # Wrong category
                    "file_url": "images/not-audio.jpg"
                }
                
                form_data = {"title": "Test Podcast"}
                files = {"audio_file": ("fake.mp3", BytesIO(b"not audio"), "audio/mpeg")}
                
                response = await client.post("/admin/podcasts/create", data=form_data, files=files)
                
                assert response.status_code == 400
                assert "Invalid audio file type" in response.text

    @pytest.mark.asyncio
    async def test_edit_podcast_form_unauthenticated(self, client: AsyncClient, test_podcast: Media):
        """Test edit form redirects when not authenticated"""
        response = await client.get(f"/admin/podcasts/edit/{test_podcast.id}")
        
        assert response.status_code == 302
        assert "/admin/login" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_edit_podcast_form_authenticated(self, client: AsyncClient, test_podcast: Media, test_category: Category):
        """Test edit podcast form loads correctly"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcast and categories queries
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_podcast
                mock_session.execute.return_value.scalars.return_value.all.return_value = [test_category]
                
                response = await client.get(f"/admin/podcasts/edit/{test_podcast.id}")
                
                assert response.status_code == 200
                assert "Edit Podcast" in response.text
                assert test_podcast.title in response.text

    @pytest.mark.asyncio
    async def test_edit_podcast_not_found(self, client: AsyncClient):
        """Test edit form with non-existent podcast"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcast not found
                mock_session.execute.return_value.scalar_one_or_none.return_value = None
                
                non_existent_id = uuid4()
                response = await client.get(f"/admin/podcasts/edit/{non_existent_id}")
                
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_edit_podcast_invalid_uuid(self, client: AsyncClient):
        """Test edit form with invalid UUID"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            response = await client.get("/admin/podcasts/edit/invalid-uuid")
            
            assert response.status_code == 400
            assert "Invalid podcast ID" in response.text

    @pytest.mark.asyncio
    async def test_update_podcast_success(self, client: AsyncClient, test_podcast: Media, test_category: Category):
        """Test successful podcast update"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcast and category queries
                mock_session.execute.return_value.scalar_one_or_none.side_effect = [test_podcast, test_category]
                
                form_data = {
                    "title": "Updated Podcast Title",
                    "description": "Updated description",
                    "photographer": "Updated Host",
                    "national_park": "Updated Show",
                    "category_id": str(test_category.id)
                }
                
                response = await client.post(f"/admin/podcasts/edit/{test_podcast.id}", data=form_data)
                
                assert response.status_code == 302
                assert "/admin/podcasts/list" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_update_podcast_with_new_audio(self, client: AsyncClient, test_podcast: Media, mock_audio_file):
        """Test updating podcast with new audio file"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcast query
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_podcast
                
                # Mock file upload service
                with patch('app.admin.routes.podcasts.file_upload_service') as mock_upload:
                    mock_upload.upload_file.return_value = {
                        "category": "audio",
                        "file_url": "audio/updated-podcast.mp3",
                        "file_size": 30000000,
                        "filename": "updated-podcast.mp3",
                        "original_filename": "updated_podcast.mp3",
                        "mime_type": "audio/mpeg",
                        "file_hash": "def456"
                    }
                    
                    form_data = {"title": "Updated with New Audio"}
                    files = {"audio_file": mock_audio_file}
                    
                    response = await client.post(f"/admin/podcasts/edit/{test_podcast.id}", data=form_data, files=files)
                    
                    assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_update_podcast_unauthenticated(self, client: AsyncClient, test_podcast: Media):
        """Test update podcast fails without authentication"""
        form_data = {"title": "Should Fail"}
        
        response = await client.post(f"/admin/podcasts/edit/{test_podcast.id}", data=form_data)
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_podcast_not_found(self, client: AsyncClient):
        """Test update non-existent podcast"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcast not found
                mock_session.execute.return_value.scalar_one_or_none.return_value = None
                
                non_existent_id = uuid4()
                form_data = {"title": "Should Not Work"}
                
                response = await client.post(f"/admin/podcasts/edit/{non_existent_id}", data=form_data)
                
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_podcast_success(self, client: AsyncClient, test_podcast: Media):
        """Test successful podcast deletion"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcast query
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_podcast
                
                response = await client.delete(f"/admin/podcasts/delete/{test_podcast.id}")
                
                assert response.status_code == 302
                assert "/admin/podcasts/list" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_delete_podcast_unauthenticated(self, client: AsyncClient, test_podcast: Media):
        """Test delete podcast fails without authentication"""
        response = await client.delete(f"/admin/podcasts/delete/{test_podcast.id}")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_podcast_not_found(self, client: AsyncClient):
        """Test delete non-existent podcast"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcast not found
                mock_session.execute.return_value.scalar_one_or_none.return_value = None
                
                non_existent_id = uuid4()
                response = await client.delete(f"/admin/podcasts/delete/{non_existent_id}")
                
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_podcast_list_page(self, client: AsyncClient, test_podcast: Media):
        """Test podcast list page"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock podcasts query
                mock_session.execute.return_value.scalars.return_value.all.return_value = [test_podcast]
                mock_session.execute.return_value.scalar.return_value = 1  # Total count
                
                response = await client.get("/admin/podcasts/list")
                
                assert response.status_code == 200
                assert "Podcast List" in response.text
                assert test_podcast.title in response.text

    @pytest.mark.asyncio
    async def test_podcast_list_with_pagination(self, client: AsyncClient):
        """Test podcast list with pagination"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock empty results for pagination test
                mock_session.execute.return_value.scalars.return_value.all.return_value = []
                mock_session.execute.return_value.scalar.return_value = 0
                
                response = await client.get("/admin/podcasts/list?page=2&limit=10")
                
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_podcast_list_with_search(self, client: AsyncClient, test_podcast: Media):
        """Test podcast list with search functionality"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock search results
                mock_session.execute.return_value.scalars.return_value.all.return_value = [test_podcast]
                mock_session.execute.return_value.scalar.return_value = 1
                
                response = await client.get("/admin/podcasts/list?search=test")
                
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_file_size_formatting(self, client: AsyncClient):
        """Test file size formatting in dashboard"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Test different file sizes
                test_cases = [
                    (0, "0.0 B"),
                    (1024, "1.0 KB"),
                    (1048576, "1.0 MB"),
                    (1073741824, "1.0 GB")
                ]
                
                for size_bytes, expected in test_cases:
                    mock_session.execute.return_value.scalar.side_effect = [1, size_bytes]
                    mock_session.execute.return_value.scalar_one_or_none.return_value = None
                    
                    response = await client.get("/admin/podcasts/")
                    
                    assert response.status_code == 200
                    assert expected in response.text

    @pytest.mark.asyncio
    async def test_form_validation_errors(self, client: AsyncClient):
        """Test form validation error handling"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            # Test missing required fields
            form_data = {}  # Missing title and audio file
            
            response = await client.post("/admin/podcasts/create", data=form_data)
            
            # Should handle validation errors gracefully
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_cover_image_upload_failure(self, client: AsyncClient, test_category: Category, mock_audio_file):
        """Test podcast creation continues when cover image upload fails"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock category validation
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_category
                
                # Mock file upload service
                with patch('app.admin.routes.podcasts.file_upload_service') as mock_upload:
                    # Audio upload succeeds, image upload fails
                    mock_upload.upload_file.side_effect = [
                        {  # Audio file success
                            "category": "audio",
                            "file_url": "audio/test.mp3",
                            "file_size": 25000000,
                            "filename": "test.mp3",
                            "original_filename": "test.mp3",
                            "mime_type": "audio/mpeg",
                            "file_hash": "abc123"
                        },
                        Exception("Image upload failed")  # Image upload failure
                    ]
                    
                    form_data = {"title": "Test Podcast"}
                    files = {
                        "audio_file": mock_audio_file,
                        "cover_image": ("cover.jpg", BytesIO(b"fake image"), "image/jpeg")
                    }
                    
                    response = await client.post("/admin/podcasts/create", data=form_data, files=files)
                    
                    # Should still succeed without cover image
                    assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, client: AsyncClient, mock_audio_file):
        """Test database transaction rollback on error"""
        with patch('app.admin.routes.podcasts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.podcasts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock file upload success but database commit failure
                with patch('app.admin.routes.podcasts.file_upload_service') as mock_upload:
                    mock_upload.upload_file.return_value = {
                        "category": "audio",
                        "file_url": "audio/test.mp3",
                        "file_size": 25000000,
                        "filename": "test.mp3",
                        "original_filename": "test.mp3",
                        "mime_type": "audio/mpeg",
                        "file_hash": "abc123"
                    }
                    
                    # Mock database commit failure
                    mock_session.commit.side_effect = Exception("Database error")
                    
                    form_data = {"title": "Test Podcast"}
                    files = {"audio_file": mock_audio_file}
                    
                    response = await client.post("/admin/podcasts/create", data=form_data, files=files)
                    
                    assert response.status_code == 500