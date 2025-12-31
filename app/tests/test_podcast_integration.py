"""
Integration tests for complete podcast workflow
Tests end-to-end functionality from creation to API consumption
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch, AsyncMock
import tempfile
import os
from pathlib import Path
from io import BytesIO

from app.models.media import Media
from app.models.category import Category
from app.models.user import User


class TestPodcastIntegration:
    """Integration tests for complete podcast workflow"""

    @pytest.fixture
    async def wildlife_category(self, test_db: AsyncSession) -> Category:
        """Create wildlife category for testing"""
        category = Category(
            name="Wildlife",
            slug="wildlife",
            is_active=True
        )
        test_db.add(category)
        await test_db.commit()
        await test_db.refresh(category)
        return category

    @pytest.fixture
    def mock_audio_file_content(self):
        """Create mock audio file content"""
        # Create a minimal MP3-like file for testing
        return b'ID3\x03\x00\x00\x00\x00\x00\x00' + b'\x00' * 1000

    @pytest.fixture
    def mock_image_file_content(self):
        """Create mock image file content"""
        # Minimal JPEG header for testing
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46
        ]) + b'\x00' * 100

    @pytest.mark.asyncio
    async def test_complete_podcast_creation_workflow(
        self, 
        client: AsyncClient, 
        admin_headers: dict, 
        wildlife_category: Category,
        mock_audio_file_content: bytes,
        mock_image_file_content: bytes
    ):
        """Test complete podcast creation from upload to API retrieval"""
        
        # Step 1: Create podcast via admin API (simulating admin panel)
        with patch('app.services.file_upload.file_upload_service') as mock_upload:
            # Mock successful file uploads
            mock_upload.upload_file.side_effect = [
                {  # Audio file upload
                    "upload_success": True,
                    "category": "audio",
                    "file_url": "audio/integration-test-podcast.mp3",
                    "file_size": 25000000,
                    "filename": "integration-test-podcast.mp3",
                    "original_filename": "Integration Test Podcast.mp3",
                    "mime_type": "audio/mpeg",
                    "file_hash": "abc123def456",
                    "duration": 1800
                },
                {  # Cover image upload
                    "upload_success": True,
                    "category": "images",
                    "file_url": "images/integration-test-cover.jpg",
                    "file_size": 500000,
                    "filename": "integration-test-cover.jpg",
                    "original_filename": "Integration Test Cover.jpg",
                    "mime_type": "image/jpeg",
                    "file_hash": "def456ghi789"
                }
            ]
            
            # Create podcast data
            podcast_data = {
                "title": "Integration Test Wildlife Podcast",
                "description": "This is a comprehensive integration test podcast that verifies the complete workflow from creation to consumption.",
                "photographer": "Integration Test Host",
                "national_park": "Integration Test Show",
                "category_id": str(wildlife_category.id),
                "media_type": "PODCAST"
            }
            
            # Simulate file uploads
            files = {
                "audio_file": ("test-audio.mp3", BytesIO(mock_audio_file_content), "audio/mpeg"),
                "cover_image": ("test-cover.jpg", BytesIO(mock_image_file_content), "image/jpeg")
            }
            
            # Create podcast via media upload endpoint
            response = await client.post(
                "/api/v1/media/upload",
                data=podcast_data,
                files=files,
                headers=admin_headers
            )
            
            assert response.status_code == 201
            created_podcast = response.json()
            podcast_id = created_podcast["id"]

        # Step 2: Verify podcast appears in podcast list API
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        podcasts = response.json()
        
        # Find our created podcast
        created_podcast_in_list = None
        for podcast in podcasts:
            if podcast["id"] == podcast_id:
                created_podcast_in_list = podcast
                break
        
        assert created_podcast_in_list is not None
        assert created_podcast_in_list["title"] == "Integration Test Wildlife Podcast"
        assert created_podcast_in_list["photographer"] == "Integration Test Host"
        assert created_podcast_in_list["national_park"] == "Integration Test Show"
        assert created_podcast_in_list["media_type"] == "PODCAST"

        # Step 3: Verify podcast detail API
        response = await client.get(f"/api/v1/media/{podcast_id}")
        assert response.status_code == 200
        podcast_detail = response.json()
        
        assert podcast_detail["id"] == podcast_id
        assert podcast_detail["title"] == "Integration Test Wildlife Podcast"
        assert podcast_detail["description"] == podcast_data["description"]
        assert podcast_detail["file_url"].endswith("integration-test-podcast.mp3")
        assert podcast_detail["thumbnail_url"].endswith("integration-test-cover.jpg")
        assert podcast_detail["duration"] == 1800
        assert podcast_detail["file_size"] == 25000000

        # Step 4: Verify podcast can be searched
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Integration Test")
        assert response.status_code == 200
        search_results = response.json()
        
        assert len(search_results) >= 1
        assert any(p["id"] == podcast_id for p in search_results)

        # Step 5: Verify podcast can be filtered by category
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={wildlife_category.id}")
        assert response.status_code == 200
        category_results = response.json()
        
        assert len(category_results) >= 1
        assert any(p["id"] == podcast_id for p in category_results)

        # Step 6: Verify podcast can be filtered by host
        response = await client.get("/api/v1/media/?media_type=PODCAST&photographer=Integration Test Host")
        assert response.status_code == 200
        host_results = response.json()
        
        assert len(host_results) >= 1
        assert any(p["id"] == podcast_id for p in host_results)

    @pytest.mark.asyncio
    async def test_podcast_update_workflow(
        self, 
        client: AsyncClient, 
        admin_headers: dict,
        test_db: AsyncSession,
        wildlife_category: Category
    ):
        """Test complete podcast update workflow"""
        
        # Step 1: Create initial podcast
        podcast = Media(
            media_type="PODCAST",
            title="Original Podcast Title",
            description="Original description",
            file_url="/uploads/audio/original.mp3",
            photographer="Original Host",
            national_park="Original Show",
            category_id=wildlife_category.id,
            file_size=20000000,
            duration=1500
        )
        test_db.add(podcast)
        await test_db.commit()
        await test_db.refresh(podcast)

        # Step 2: Update podcast via API
        update_data = {
            "title": "Updated Podcast Title",
            "description": "Updated description with more details",
            "photographer": "Updated Host Name",
            "national_park": "Updated Show Name"
        }
        
        response = await client.put(
            f"/api/v1/media/{podcast.id}",
            json=update_data,
            headers=admin_headers
        )
        
        assert response.status_code == 200

        # Step 3: Verify updates appear in list API
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        podcasts = response.json()
        
        updated_podcast = None
        for p in podcasts:
            if p["id"] == str(podcast.id):
                updated_podcast = p
                break
        
        assert updated_podcast is not None
        assert updated_podcast["title"] == "Updated Podcast Title"
        assert updated_podcast["photographer"] == "Updated Host Name"
        assert updated_podcast["national_park"] == "Updated Show Name"

        # Step 4: Verify updates appear in detail API
        response = await client.get(f"/api/v1/media/{podcast.id}")
        assert response.status_code == 200
        podcast_detail = response.json()
        
        assert podcast_detail["title"] == "Updated Podcast Title"
        assert podcast_detail["description"] == "Updated description with more details"

        # Step 5: Verify search works with updated data
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Updated")
        assert response.status_code == 200
        search_results = response.json()
        
        assert len(search_results) >= 1
        assert any(p["id"] == str(podcast.id) for p in search_results)

    @pytest.mark.asyncio
    async def test_podcast_deletion_workflow(
        self, 
        client: AsyncClient, 
        admin_headers: dict,
        test_db: AsyncSession,
        wildlife_category: Category
    ):
        """Test complete podcast deletion workflow"""
        
        # Step 1: Create podcast to delete
        podcast = Media(
            media_type="PODCAST",
            title="Podcast to Delete",
            file_url="/uploads/audio/to-delete.mp3",
            category_id=wildlife_category.id
        )
        test_db.add(podcast)
        await test_db.commit()
        await test_db.refresh(podcast)
        podcast_id = str(podcast.id)

        # Step 2: Verify podcast exists in list
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        podcasts_before = response.json()
        
        assert any(p["id"] == podcast_id for p in podcasts_before)

        # Step 3: Delete podcast
        response = await client.delete(
            f"/api/v1/media/{podcast_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200

        # Step 4: Verify podcast no longer appears in list
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        podcasts_after = response.json()
        
        assert not any(p["id"] == podcast_id for p in podcasts_after)

        # Step 5: Verify podcast detail returns 404
        response = await client.get(f"/api/v1/media/{podcast_id}")
        assert response.status_code == 404

        # Step 6: Verify search no longer finds deleted podcast
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Delete")
        assert response.status_code == 200
        search_results = response.json()
        
        assert not any(p["id"] == podcast_id for p in search_results)

    @pytest.mark.asyncio
    async def test_podcast_category_integration(
        self, 
        client: AsyncClient,
        test_db: AsyncSession
    ):
        """Test podcast integration with category system"""
        
        # Step 1: Create multiple categories
        wildlife_cat = Category(name="Wildlife", slug="wildlife", is_active=True)
        conservation_cat = Category(name="Conservation", slug="conservation", is_active=True)
        education_cat = Category(name="Education", slug="education", is_active=True)
        
        test_db.add_all([wildlife_cat, conservation_cat, education_cat])
        await test_db.commit()
        for cat in [wildlife_cat, conservation_cat, education_cat]:
            await test_db.refresh(cat)

        # Step 2: Create podcasts in different categories
        podcasts = [
            Media(
                media_type="PODCAST",
                title="Wildlife Safari",
                file_url="/uploads/audio/safari.mp3",
                category_id=wildlife_cat.id
            ),
            Media(
                media_type="PODCAST",
                title="Conservation Heroes",
                file_url="/uploads/audio/heroes.mp3",
                category_id=conservation_cat.id
            ),
            Media(
                media_type="PODCAST",
                title="Educational Series",
                file_url="/uploads/audio/education.mp3",
                category_id=education_cat.id
            ),
            Media(
                media_type="PODCAST",
                title="Uncategorized Podcast",
                file_url="/uploads/audio/uncategorized.mp3",
                category_id=None
            )
        ]
        
        test_db.add_all(podcasts)
        await test_db.commit()

        # Step 3: Test category filtering
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={wildlife_cat.id}")
        assert response.status_code == 200
        wildlife_podcasts = response.json()
        
        assert len(wildlife_podcasts) == 1
        assert wildlife_podcasts[0]["title"] == "Wildlife Safari"

        # Step 4: Test multiple category filtering
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={conservation_cat.id}")
        assert response.status_code == 200
        conservation_podcasts = response.json()
        
        assert len(conservation_podcasts) == 1
        assert conservation_podcasts[0]["title"] == "Conservation Heroes"

        # Step 5: Test uncategorized podcasts
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        all_podcasts = response.json()
        
        uncategorized = [p for p in all_podcasts if p["category_id"] is None]
        assert len(uncategorized) == 1
        assert uncategorized[0]["title"] == "Uncategorized Podcast"

    @pytest.mark.asyncio
    async def test_podcast_search_integration(
        self, 
        client: AsyncClient,
        test_db: AsyncSession,
        wildlife_category: Category
    ):
        """Test comprehensive podcast search functionality"""
        
        # Step 1: Create podcasts with varied content for search testing
        podcasts = [
            Media(
                media_type="PODCAST",
                title="African Wildlife Safari Adventure",
                description="Explore the magnificent wildlife of the African savanna",
                photographer="David Attenborough",
                national_park="Wildlife Explorer Show",
                category_id=wildlife_category.id,
                file_url="/uploads/audio/african-safari.mp3"
            ),
            Media(
                media_type="PODCAST",
                title="Ocean Conservation Efforts",
                description="Deep dive into marine conservation and ocean protection",
                photographer="Sylvia Earle",
                national_park="Ocean Guardian Podcast",
                category_id=wildlife_category.id,
                file_url="/uploads/audio/ocean-conservation.mp3"
            ),
            Media(
                media_type="PODCAST",
                title="Forest Preservation Stories",
                description="Stories from the frontlines of forest conservation",
                photographer="Jane Goodall",
                national_park="Forest Protector Series",
                category_id=wildlife_category.id,
                file_url="/uploads/audio/forest-preservation.mp3"
            )
        ]
        
        test_db.add_all(podcasts)
        await test_db.commit()

        # Step 2: Test title search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Safari")
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) == 1
        assert "Safari" in results[0]["title"]

        # Step 3: Test description search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=ocean protection")
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) >= 1
        assert any("Ocean" in p["title"] for p in results)

        # Step 4: Test host search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=David Attenborough")
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) == 1
        assert results[0]["photographer"] == "David Attenborough"

        # Step 5: Test show name search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Ocean Guardian")
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) == 1
        assert "Ocean Guardian" in results[0]["national_park"]

        # Step 6: Test case-insensitive search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=WILDLIFE")
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) >= 1

        # Step 7: Test partial word search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Conserv")
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) >= 2  # Should match "Conservation" and "conservation"

        # Step 8: Test multi-word search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Forest Stories")
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) >= 1
        assert any("Forest" in p["title"] and "Stories" in p["title"] for p in results)

    @pytest.mark.asyncio
    async def test_podcast_pagination_integration(
        self, 
        client: AsyncClient,
        test_db: AsyncSession,
        wildlife_category: Category
    ):
        """Test podcast pagination across large datasets"""
        
        # Step 1: Create many podcasts for pagination testing
        podcasts = []
        for i in range(25):
            podcast = Media(
                media_type="PODCAST",
                title=f"Pagination Test Podcast {i+1:02d}",
                description=f"Description for podcast number {i+1}",
                photographer=f"Host {(i % 5) + 1}",
                national_park=f"Show {(i % 3) + 1}",
                category_id=wildlife_category.id,
                file_url=f"/uploads/audio/pagination-test-{i+1:02d}.mp3",
                duration=1800 + (i * 60)  # Varying durations
            )
            podcasts.append(podcast)
        
        test_db.add_all(podcasts)
        await test_db.commit()

        # Step 2: Test first page
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=0&limit=10")
        assert response.status_code == 200
        page1_results = response.json()
        
        assert len(page1_results) == 10

        # Step 3: Test second page
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=10&limit=10")
        assert response.status_code == 200
        page2_results = response.json()
        
        assert len(page2_results) == 10

        # Step 4: Test third page (partial)
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=20&limit=10")
        assert response.status_code == 200
        page3_results = response.json()
        
        assert len(page3_results) == 5  # Only 5 remaining

        # Step 5: Verify no duplicate results across pages
        all_ids = set()
        for results in [page1_results, page2_results, page3_results]:
            for podcast in results:
                assert podcast["id"] not in all_ids, "Duplicate podcast found across pages"
                all_ids.add(podcast["id"])

        # Step 6: Test pagination with search
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Pagination&skip=0&limit=5")
        assert response.status_code == 200
        search_page1 = response.json()
        
        assert len(search_page1) == 5

        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Pagination&skip=5&limit=5")
        assert response.status_code == 200
        search_page2 = response.json()
        
        assert len(search_page2) == 5

    @pytest.mark.asyncio
    async def test_podcast_error_handling_integration(
        self, 
        client: AsyncClient,
        admin_headers: dict
    ):
        """Test error handling across the podcast system"""
        
        # Step 1: Test invalid podcast ID
        response = await client.get("/api/v1/media/invalid-uuid")
        assert response.status_code == 422

        # Step 2: Test non-existent podcast
        non_existent_id = uuid4()
        response = await client.get(f"/api/v1/media/{non_existent_id}")
        assert response.status_code == 404

        # Step 3: Test invalid category filter
        invalid_category_id = uuid4()
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={invalid_category_id}")
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 0  # Should return empty results

        # Step 4: Test invalid pagination parameters
        response = await client.get("/api/v1/media/?media_type=PODCAST&skip=-1")
        assert response.status_code == 200  # Should handle gracefully

        response = await client.get("/api/v1/media/?media_type=PODCAST&limit=0")
        assert response.status_code == 200  # Should handle gracefully

        # Step 5: Test unauthorized operations
        response = await client.post("/api/v1/media/", json={"title": "Unauthorized"})
        assert response.status_code == 401

        response = await client.put(f"/api/v1/media/{uuid4()}", json={"title": "Unauthorized"})
        assert response.status_code == 401

        response = await client.delete(f"/api/v1/media/{uuid4()}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_podcast_performance_integration(
        self, 
        client: AsyncClient,
        test_db: AsyncSession,
        wildlife_category: Category
    ):
        """Test podcast system performance with realistic data volumes"""
        
        # Step 1: Create a realistic number of podcasts
        podcasts = []
        for i in range(100):
            podcast = Media(
                media_type="PODCAST",
                title=f"Performance Test Podcast Episode {i+1}",
                description=f"This is episode {i+1} of our performance test series. " * 10,  # Longer descriptions
                photographer=f"Host {(i % 10) + 1}",
                national_park=f"Show Series {(i % 5) + 1}",
                category_id=wildlife_category.id,
                file_url=f"/uploads/audio/perf-test-{i+1:03d}.mp3",
                duration=1800 + (i * 30),
                file_size=25000000 + (i * 100000)
            )
            podcasts.append(podcast)
        
        test_db.add_all(podcasts)
        await test_db.commit()

        # Step 2: Test list performance
        import time
        
        start_time = time.time()
        response = await client.get("/api/v1/media/?media_type=PODCAST&limit=50")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should complete within 2 seconds
        
        results = response.json()
        assert len(results) == 50

        # Step 3: Test search performance
        start_time = time.time()
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Performance")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Search should be fast
        
        results = response.json()
        assert len(results) == 100  # Should find all performance test podcasts

        # Step 4: Test category filter performance
        start_time = time.time()
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={wildlife_category.id}")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.5  # Category filter should be reasonably fast

        # Step 5: Test combined filter performance
        start_time = time.time()
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&search=Episode&category_id={wildlife_category.id}&limit=20")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Combined filters should still be fast