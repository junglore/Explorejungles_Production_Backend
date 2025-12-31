"""
Comprehensive tests for Podcast API endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4, UUID
from unittest.mock import patch, AsyncMock
import tempfile
import os
from pathlib import Path
from io import BytesIO

from app.models.media import Media
from app.models.category import Category
from app.models.user import User


class TestPodcastAPI:
    """Test class for Podcast API endpoints"""

    @pytest.fixture
    async def test_podcast(self, test_db: AsyncSession, test_category: Category) -> Media:
        """Create a test podcast"""
        podcast = Media(
            media_type="PODCAST",
            title="Test Podcast Episode",
            description="This is a test podcast episode about wildlife",
            file_url="/uploads/audio/test-podcast.mp3",
            thumbnail_url="/uploads/images/test-podcast-thumb.jpg",
            photographer="Test Host",
            national_park="Test Show",
            category_id=test_category.id,
            file_size=25000000,
            filename="test-podcast.mp3",
            original_filename="Test Podcast Episode.mp3",
            mime_type="audio/mpeg",
            duration=1800,  # 30 minutes
            file_metadata={
                "episode_number": 1,
                "season_number": 1,
                "guest_names": ["Guest One", "Guest Two"],
                "show_notes": "Episode show notes content"
            }
        )
        test_db.add(podcast)
        await test_db.commit()
        await test_db.refresh(podcast)
        return podcast

    @pytest.fixture
    async def multiple_podcasts(self, test_db: AsyncSession, test_category: Category) -> list[Media]:
        """Create multiple test podcasts"""
        podcasts = []
        for i in range(5):
            podcast = Media(
                media_type="PODCAST",
                title=f"Podcast Episode {i+1}",
                description=f"Description for episode {i+1}",
                file_url=f"/uploads/audio/podcast-{i+1}.mp3",
                thumbnail_url=f"/uploads/images/podcast-{i+1}-thumb.jpg",
                photographer=f"Host {i+1}",
                national_park="Test Show",
                category_id=test_category.id,
                file_size=20000000 + (i * 1000000),
                filename=f"podcast-{i+1}.mp3",
                original_filename=f"Podcast Episode {i+1}.mp3",
                mime_type="audio/mpeg",
                duration=1500 + (i * 300)
            )
            test_db.add(podcast)
            podcasts.append(podcast)
        
        await test_db.commit()
        for podcast in podcasts:
            await test_db.refresh(podcast)
        return podcasts

    @pytest.mark.asyncio
    async def test_get_podcasts_list(self, client: AsyncClient, test_podcast: Media):
        """Test getting paginated list of podcasts"""
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check podcast structure
        podcast_item = data[0]
        assert "id" in podcast_item
        assert "title" in podcast_item
        assert "description" in podcast_item
        assert "file_url" in podcast_item
        assert "thumbnail_url" in podcast_item
        assert "photographer" in podcast_item
        assert "national_park" in podcast_item
        assert "duration" in podcast_item
        assert "created_at" in podcast_item
        assert "media_type" in podcast_item
        assert podcast_item["media_type"] == "PODCAST"

    @pytest.mark.asyncio
    async def test_get_podcasts_with_pagination(self, client: AsyncClient, multiple_podcasts: list[Media]):
        """Test podcast pagination"""
        # Test first page
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=0&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # Test second page
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=3&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Remaining podcasts

    @pytest.mark.asyncio
    async def test_get_podcasts_with_search(self, client: AsyncClient, multiple_podcasts: list[Media]):
        """Test podcast search functionality"""
        # Search by title
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Episode 1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert "Episode 1" in data[0]["title"]
        
        # Search by host (photographer)
        response = await client.get("/api/v1/media/?media_type=PODCAST&photographer=Host 2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["photographer"] == "Host 2"

    @pytest.mark.asyncio
    async def test_get_podcast_by_id(self, client: AsyncClient, test_podcast: Media):
        """Test getting specific podcast by ID"""
        response = await client.get(f"/api/v1/media/{test_podcast.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_podcast.id)
        assert data["title"] == test_podcast.title
        assert data["description"] == test_podcast.description
        assert data["file_url"] == test_podcast.file_url
        assert data["thumbnail_url"] == test_podcast.thumbnail_url
        assert data["photographer"] == test_podcast.photographer
        assert data["national_park"] == test_podcast.national_park
        assert data["duration"] == test_podcast.duration
        assert data["media_type"] == "PODCAST"
        assert data["file_metadata"] == test_podcast.file_metadata

    @pytest.mark.asyncio
    async def test_get_podcast_not_found(self, client: AsyncClient):
        """Test getting non-existent podcast"""
        non_existent_id = uuid4()
        response = await client.get(f"/api/v1/media/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_podcasts_by_category(self, client: AsyncClient, test_db: AsyncSession):
        """Test filtering podcasts by category"""
        # Create two categories
        category1 = Category(name="Wildlife", slug="wildlife")
        category2 = Category(name="Conservation", slug="conservation")
        test_db.add_all([category1, category2])
        await test_db.commit()
        await test_db.refresh(category1)
        await test_db.refresh(category2)
        
        # Create podcasts in different categories
        podcast1 = Media(
            media_type="PODCAST",
            title="Wildlife Podcast",
            file_url="/uploads/audio/wildlife.mp3",
            category_id=category1.id
        )
        podcast2 = Media(
            media_type="PODCAST",
            title="Conservation Podcast",
            file_url="/uploads/audio/conservation.mp3",
            category_id=category2.id
        )
        test_db.add_all([podcast1, podcast2])
        await test_db.commit()
        
        # Filter by category 1
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={category1.id}")
        assert response.status_code == 200
        data = response.json()
        
        # Should only return podcasts from category 1
        for item in data:
            assert item["category_id"] == str(category1.id)

    @pytest.mark.asyncio
    async def test_get_podcasts_by_host(self, client: AsyncClient, multiple_podcasts: list[Media]):
        """Test filtering podcasts by host (photographer)"""
        response = await client.get("/api/v1/media/?media_type=PODCAST&photographer=Host 1")
        assert response.status_code == 200
        data = response.json()
        
        # Should only return podcasts from Host 1
        for item in data:
            assert item["photographer"] == "Host 1"

    @pytest.mark.asyncio
    async def test_get_podcasts_by_show(self, client: AsyncClient, multiple_podcasts: list[Media]):
        """Test filtering podcasts by show (national_park)"""
        response = await client.get("/api/v1/media/?media_type=PODCAST&national_park=Test Show")
        assert response.status_code == 200
        data = response.json()
        
        # Should return all podcasts from Test Show
        assert len(data) >= 5
        for item in data:
            assert item["national_park"] == "Test Show"

    @pytest.mark.asyncio
    async def test_create_podcast_unauthorized(self, client: AsyncClient):
        """Test that podcast creation requires authentication"""
        podcast_data = {
            "title": "Unauthorized Podcast",
            "description": "This should fail",
            "media_type": "PODCAST"
        }
        
        response = await client.post("/api/v1/media/", json=podcast_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_podcast_unauthorized(self, client: AsyncClient, test_podcast: Media):
        """Test that podcast update requires authentication"""
        update_data = {"title": "Should not update"}
        
        response = await client.put(f"/api/v1/media/{test_podcast.id}", json=update_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_podcast_unauthorized(self, client: AsyncClient, test_podcast: Media):
        """Test that podcast deletion requires authentication"""
        response = await client.delete(f"/api/v1/media/{test_podcast.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_podcast_metadata_structure(self, client: AsyncClient, test_podcast: Media):
        """Test that podcast metadata is properly structured"""
        response = await client.get(f"/api/v1/media/{test_podcast.id}")
        assert response.status_code == 200
        data = response.json()
        
        # Check file_metadata structure
        metadata = data["file_metadata"]
        assert "episode_number" in metadata
        assert "season_number" in metadata
        assert "guest_names" in metadata
        assert "show_notes" in metadata
        assert metadata["episode_number"] == 1
        assert metadata["season_number"] == 1
        assert isinstance(metadata["guest_names"], list)
        assert len(metadata["guest_names"]) == 2

    @pytest.mark.asyncio
    async def test_podcast_duration_formatting(self, client: AsyncClient, test_podcast: Media):
        """Test that podcast duration is properly returned"""
        response = await client.get(f"/api/v1/media/{test_podcast.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["duration"] == 1800  # 30 minutes in seconds
        assert isinstance(data["duration"], int)

    @pytest.mark.asyncio
    async def test_podcast_file_size_information(self, client: AsyncClient, test_podcast: Media):
        """Test that podcast file size is properly returned"""
        response = await client.get(f"/api/v1/media/{test_podcast.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["file_size"] == 25000000  # 25MB
        assert isinstance(data["file_size"], int)

    @pytest.mark.asyncio
    async def test_podcast_ordering(self, client: AsyncClient, multiple_podcasts: list[Media]):
        """Test that podcasts are ordered by creation date (newest first)"""
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        data = response.json()
        
        # Should be ordered by created_at descending
        if len(data) > 1:
            for i in range(len(data) - 1):
                current_date = data[i]["created_at"]
                next_date = data[i + 1]["created_at"]
                assert current_date >= next_date

    @pytest.mark.asyncio
    async def test_podcast_with_missing_thumbnail(self, client: AsyncClient, test_db: AsyncSession, test_category: Category):
        """Test podcast without thumbnail URL"""
        podcast = Media(
            media_type="PODCAST",
            title="No Thumbnail Podcast",
            file_url="/uploads/audio/no-thumb.mp3",
            thumbnail_url=None,
            category_id=test_category.id
        )
        test_db.add(podcast)
        await test_db.commit()
        await test_db.refresh(podcast)
        
        response = await client.get(f"/api/v1/media/{podcast.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["thumbnail_url"] is None

    @pytest.mark.asyncio
    async def test_podcast_with_missing_metadata(self, client: AsyncClient, test_db: AsyncSession, test_category: Category):
        """Test podcast with minimal metadata"""
        podcast = Media(
            media_type="PODCAST",
            title="Minimal Podcast",
            file_url="/uploads/audio/minimal.mp3",
            photographer=None,
            national_park=None,
            description=None,
            duration=None,
            file_metadata=None,
            category_id=test_category.id
        )
        test_db.add(podcast)
        await test_db.commit()
        await test_db.refresh(podcast)
        
        response = await client.get(f"/api/v1/media/{podcast.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["photographer"] is None
        assert data["national_park"] is None
        assert data["description"] is None
        assert data["duration"] is None
        assert data["file_metadata"] is None

    @pytest.mark.asyncio
    async def test_invalid_media_type_filter(self, client: AsyncClient):
        """Test filtering with invalid media type"""
        response = await client.get("/api/v1/media/?media_type=INVALID")
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty list for invalid media type
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_podcast_search_case_insensitive(self, client: AsyncClient, test_podcast: Media):
        """Test that podcast search is case insensitive"""
        # Search with different cases
        test_cases = ["test podcast", "TEST PODCAST", "Test Podcast", "tEsT pOdCaSt"]
        
        for search_term in test_cases:
            response = await client.get(f"/api/v1/media/?media_type=PODCAST&search={search_term}")
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_podcast_search_partial_match(self, client: AsyncClient, test_podcast: Media):
        """Test that podcast search supports partial matches"""
        # Search with partial title
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # Search with partial host name
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Host")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_podcast_empty_search(self, client: AsyncClient, test_podcast: Media):
        """Test podcast search with empty query"""
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=")
        assert response.status_code == 200
        data = response.json()
        
        # Empty search should return all podcasts
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_podcast_search_no_results(self, client: AsyncClient):
        """Test podcast search with no matching results"""
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=nonexistent")
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty list
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_podcast_limit_validation(self, client: AsyncClient):
        """Test podcast list limit validation"""
        # Test valid limits
        response = await client.get("/api/v1/media/?media_type=PODCAST&limit=5")
        assert response.status_code == 200
        
        response = await client.get("/api/v1/media/?media_type=PODCAST&limit=50")
        assert response.status_code == 200
        
        # Test invalid limits (should use default)
        response = await client.get("/api/v1/media/?media_type=PODCAST&limit=0")
        assert response.status_code == 200
        
        response = await client.get("/api/v1/media/?media_type=PODCAST&limit=1000")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_podcast_skip_validation(self, client: AsyncClient):
        """Test podcast list skip validation"""
        # Test valid skip values
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=0")
        assert response.status_code == 200
        
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=10")
        assert response.status_code == 200
        
        # Test negative skip (should use default)
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=-1")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_database_error_handling(self, client: AsyncClient):
        """Test graceful handling of database errors"""
        with patch('app.api.endpoints.media.select') as mock_select:
            mock_select.side_effect = Exception("Database connection failed")
            
            response = await client.get("/api/v1/media/?media_type=PODCAST")
            
            # Should return 500 error for database issues
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_invalid_uuid_parameters(self, client: AsyncClient):
        """Test handling of invalid UUID parameters"""
        # Invalid UUID in path
        response = await client.get("/api/v1/media/invalid-uuid")
        assert response.status_code == 422
        
        # Invalid UUID in query parameter
        response = await client.get("/api/v1/media/?media_type=PODCAST&category_id=invalid-uuid")
        # Should still work, just ignore the invalid filter
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_podcast_content_type_validation(self, client: AsyncClient, test_podcast: Media):
        """Test that only PODCAST media type is returned"""
        # Create non-podcast media
        test_db = client.app.dependency_overrides[get_db_session]()
        
        image_media = Media(
            media_type="IMAGE",
            title="Test Image",
            file_url="/uploads/images/test.jpg"
        )
        test_db.add(image_media)
        await test_db.commit()
        
        # Get podcasts only
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        data = response.json()
        
        # All returned items should be podcasts
        for item in data:
            assert item["media_type"] == "PODCAST"

    @pytest.mark.asyncio
    async def test_podcast_response_performance(self, client: AsyncClient, multiple_podcasts: list[Media]):
        """Test that podcast API responses are reasonably fast"""
        import time
        
        start_time = time.time()
        response = await client.get("/api/v1/media/?media_type=PODCAST&limit=50")
        end_time = time.time()
        
        assert response.status_code == 200
        # Response should be under 1 second for reasonable dataset
        assert (end_time - start_time) < 1.0