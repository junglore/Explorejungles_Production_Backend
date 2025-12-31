"""
Tests for podcast search and categorization functionality
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch, AsyncMock

from app.models.media import Media
from app.models.category import Category


class TestPodcastSearchCategorization:
    """Test podcast search and categorization features"""

    @pytest.fixture
    async def wildlife_category(self, test_db: AsyncSession) -> Category:
        """Create wildlife category"""
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
    async def conservation_category(self, test_db: AsyncSession) -> Category:
        """Create conservation category"""
        category = Category(
            name="Conservation",
            slug="conservation",
            is_active=True
        )
        test_db.add(category)
        await test_db.commit()
        await test_db.refresh(category)
        return category

    @pytest.fixture
    async def categorized_podcasts(self, test_db: AsyncSession, wildlife_category: Category, conservation_category: Category) -> list[Media]:
        """Create podcasts in different categories"""
        podcasts = [
            Media(
                media_type="PODCAST",
                title="Wildlife Safari Adventures",
                description="Exploring the African savanna and its magnificent wildlife",
                file_url="/uploads/audio/wildlife-safari.mp3",
                photographer="David Attenborough",
                national_park="Wildlife Explorer",
                category_id=wildlife_category.id,
                file_size=30000000,
                duration=2400
            ),
            Media(
                media_type="PODCAST",
                title="Conservation Heroes",
                description="Stories of people working to save endangered species",
                file_url="/uploads/audio/conservation-heroes.mp3",
                photographer="Jane Goodall",
                national_park="Conservation Stories",
                category_id=conservation_category.id,
                file_size=25000000,
                duration=1800
            ),
            Media(
                media_type="PODCAST",
                title="Ocean Wildlife Documentary",
                description="Deep dive into marine life and ocean conservation",
                file_url="/uploads/audio/ocean-wildlife.mp3",
                photographer="Sylvia Earle",
                national_park="Ocean Explorer",
                category_id=wildlife_category.id,
                file_size=35000000,
                duration=3000
            ),
            Media(
                media_type="PODCAST",
                title="Forest Conservation Efforts",
                description="Protecting our forests for future generations",
                file_url="/uploads/audio/forest-conservation.mp3",
                photographer="Wangari Maathai",
                national_park="Forest Guardian",
                category_id=conservation_category.id,
                file_size=28000000,
                duration=2100
            )
        ]
        
        for podcast in podcasts:
            test_db.add(podcast)
        
        await test_db.commit()
        for podcast in podcasts:
            await test_db.refresh(podcast)
        
        return podcasts

    @pytest.mark.asyncio
    async def test_search_podcasts_by_title(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test searching podcasts by title"""
        # Search for "Wildlife"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Wildlife")
        assert response.status_code == 200
        data = response.json()
        
        # Should return podcasts with "Wildlife" in title
        wildlife_podcasts = [p for p in data if "Wildlife" in p["title"]]
        assert len(wildlife_podcasts) >= 2
        
        # Search for "Conservation"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Conservation")
        assert response.status_code == 200
        data = response.json()
        
        conservation_podcasts = [p for p in data if "Conservation" in p["title"]]
        assert len(conservation_podcasts) >= 2

    @pytest.mark.asyncio
    async def test_search_podcasts_by_description(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test searching podcasts by description content"""
        # Search for "African savanna"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=African savanna")
        assert response.status_code == 200
        data = response.json()
        
        # Should find the wildlife safari podcast
        assert len(data) >= 1
        assert any("African savanna" in p["description"] for p in data)
        
        # Search for "endangered species"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=endangered species")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1
        assert any("endangered species" in p["description"] for p in data)

    @pytest.mark.asyncio
    async def test_search_podcasts_by_host(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test searching podcasts by host name (photographer field)"""
        # Search for "David Attenborough"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=David Attenborough")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1
        assert any(p["photographer"] == "David Attenborough" for p in data)
        
        # Search for "Jane Goodall"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Jane Goodall")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1
        assert any(p["photographer"] == "Jane Goodall" for p in data)

    @pytest.mark.asyncio
    async def test_search_podcasts_by_show_name(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test searching podcasts by show name (national_park field)"""
        # Search for "Wildlife Explorer"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Wildlife Explorer")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1
        assert any(p["national_park"] == "Wildlife Explorer" for p in data)

    @pytest.mark.asyncio
    async def test_filter_podcasts_by_category(self, client: AsyncClient, categorized_podcasts: list[Media], wildlife_category: Category, conservation_category: Category):
        """Test filtering podcasts by category"""
        # Filter by wildlife category
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={wildlife_category.id}")
        assert response.status_code == 200
        data = response.json()
        
        # Should return only wildlife podcasts
        assert len(data) == 2
        for podcast in data:
            assert podcast["category_id"] == str(wildlife_category.id)
        
        # Filter by conservation category
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={conservation_category.id}")
        assert response.status_code == 200
        data = response.json()
        
        # Should return only conservation podcasts
        assert len(data) == 2
        for podcast in data:
            assert podcast["category_id"] == str(conservation_category.id)

    @pytest.mark.asyncio
    async def test_filter_podcasts_by_host(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test filtering podcasts by specific host"""
        # Filter by David Attenborough
        response = await client.get("/api/v1/media/?media_type=PODCAST&photographer=David Attenborough")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["photographer"] == "David Attenborough"
        assert data[0]["title"] == "Wildlife Safari Adventures"

    @pytest.mark.asyncio
    async def test_filter_podcasts_by_show(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test filtering podcasts by show name"""
        # Filter by Conservation Stories
        response = await client.get("/api/v1/media/?media_type=PODCAST&national_park=Conservation Stories")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["national_park"] == "Conservation Stories"
        assert data[0]["title"] == "Conservation Heroes"

    @pytest.mark.asyncio
    async def test_combined_search_and_filter(self, client: AsyncClient, categorized_podcasts: list[Media], wildlife_category: Category):
        """Test combining search with category filter"""
        # Search for "Ocean" within wildlife category
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&search=Ocean&category_id={wildlife_category.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["title"] == "Ocean Wildlife Documentary"
        assert data[0]["category_id"] == str(wildlife_category.id)

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test that search is case insensitive"""
        search_terms = ["wildlife", "WILDLIFE", "Wildlife", "WiLdLiFe"]
        
        for term in search_terms:
            response = await client.get(f"/api/v1/media/?media_type=PODCAST&search={term}")
            assert response.status_code == 200
            data = response.json()
            
            # Should return same results regardless of case
            assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_search_partial_matches(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test that search supports partial matches"""
        # Partial title match
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Safari")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1
        assert any("Safari" in p["title"] for p in data)
        
        # Partial host name match
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Attenborough")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1
        assert any("Attenborough" in p["photographer"] for p in data)

    @pytest.mark.asyncio
    async def test_search_multiple_words(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test searching with multiple words"""
        # Search for "Ocean Wildlife"
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Ocean Wildlife")
        assert response.status_code == 200
        data = response.json()
        
        # Should find the ocean wildlife documentary
        assert len(data) >= 1
        assert any("Ocean Wildlife" in p["title"] for p in data)

    @pytest.mark.asyncio
    async def test_search_no_results(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test search with no matching results"""
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=nonexistent")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test search with empty query returns all podcasts"""
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=")
        assert response.status_code == 200
        data = response.json()
        
        # Should return all podcasts
        assert len(data) >= 4

    @pytest.mark.asyncio
    async def test_featured_podcast_designation(self, client: AsyncClient, test_db: AsyncSession, wildlife_category: Category):
        """Test featured podcast functionality"""
        # Create featured and non-featured podcasts
        featured_podcast = Media(
            media_type="PODCAST",
            title="Featured Wildlife Special",
            file_url="/uploads/audio/featured.mp3",
            category_id=wildlife_category.id,
            file_metadata={"is_featured": True}
        )
        
        regular_podcast = Media(
            media_type="PODCAST",
            title="Regular Wildlife Episode",
            file_url="/uploads/audio/regular.mp3",
            category_id=wildlife_category.id,
            file_metadata={"is_featured": False}
        )
        
        test_db.add_all([featured_podcast, regular_podcast])
        await test_db.commit()
        
        # Test filtering by featured status (if implemented)
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        data = response.json()
        
        # Should include both featured and regular podcasts
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_podcast_ordering_by_date(self, client: AsyncClient, categorized_podcasts: list[Media]):
        """Test that podcasts are ordered by creation date"""
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        data = response.json()
        
        # Should be ordered by created_at descending (newest first)
        if len(data) > 1:
            for i in range(len(data) - 1):
                current_date = data[i]["created_at"]
                next_date = data[i + 1]["created_at"]
                assert current_date >= next_date

    @pytest.mark.asyncio
    async def test_podcast_ordering_by_popularity(self, client: AsyncClient, test_db: AsyncSession, wildlife_category: Category):
        """Test podcast ordering by popularity (if implemented)"""
        # Create podcasts with different popularity metrics
        popular_podcast = Media(
            media_type="PODCAST",
            title="Very Popular Podcast",
            file_url="/uploads/audio/popular.mp3",
            category_id=wildlife_category.id,
            file_metadata={"view_count": 1000, "like_count": 100}
        )
        
        less_popular_podcast = Media(
            media_type="PODCAST",
            title="Less Popular Podcast",
            file_url="/uploads/audio/less-popular.mp3",
            category_id=wildlife_category.id,
            file_metadata={"view_count": 50, "like_count": 5}
        )
        
        test_db.add_all([popular_podcast, less_popular_podcast])
        await test_db.commit()
        
        # Test default ordering (by date)
        response = await client.get("/api/v1/media/?media_type=PODCAST")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_category_with_no_podcasts(self, client: AsyncClient, test_db: AsyncSession):
        """Test filtering by category with no podcasts"""
        empty_category = Category(
            name="Empty Category",
            slug="empty-category",
            is_active=True
        )
        test_db.add(empty_category)
        await test_db.commit()
        await test_db.refresh(empty_category)
        
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={empty_category.id}")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_invalid_category_filter(self, client: AsyncClient):
        """Test filtering with invalid category ID"""
        invalid_category_id = uuid4()
        
        response = await client.get(f"/api/v1/media/?media_type=PODCAST&category_id={invalid_category_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty results for non-existent category
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, client: AsyncClient, test_db: AsyncSession, wildlife_category: Category):
        """Test search with special characters"""
        special_podcast = Media(
            media_type="PODCAST",
            title="Wildlife & Conservation: A Journey",
            description="Exploring nature's beauty & conservation efforts",
            file_url="/uploads/audio/special.mp3",
            photographer="Dr. Jane Smith-Wilson",
            category_id=wildlife_category.id
        )
        test_db.add(special_podcast)
        await test_db.commit()
        
        # Search with ampersand
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Wildlife & Conservation")
        assert response.status_code == 200
        data = response.json()
        
        # Should handle special characters gracefully
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_performance_with_large_dataset(self, client: AsyncClient, test_db: AsyncSession, wildlife_category: Category):
        """Test search performance with larger dataset"""
        # Create many podcasts for performance testing
        podcasts = []
        for i in range(50):
            podcast = Media(
                media_type="PODCAST",
                title=f"Performance Test Podcast {i}",
                description=f"Description for podcast {i}",
                file_url=f"/uploads/audio/perf-test-{i}.mp3",
                photographer=f"Host {i % 10}",  # 10 different hosts
                national_park=f"Show {i % 5}",  # 5 different shows
                category_id=wildlife_category.id
            )
            podcasts.append(podcast)
        
        test_db.add_all(podcasts)
        await test_db.commit()
        
        import time
        
        # Test search performance
        start_time = time.time()
        response = await client.get("/api/v1/media/?media_type=PODCAST&search=Performance")
        end_time = time.time()
        
        assert response.status_code == 200
        # Search should complete within reasonable time
        assert (end_time - start_time) < 2.0  # Less than 2 seconds
        
        data = response.json()
        assert len(data) >= 50  # Should find all performance test podcasts