"""
Tests for Content API endpoints
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from app.models.content import ContentTypeEnum, ContentStatusEnum


class TestContentAPI:
    """Test content API endpoints"""

    async def test_get_content_list(self, client: AsyncClient, test_content):
        """Test getting content list"""
        response = await client.get("/api/v1/content/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert "data" in data
        assert "result" in data["data"]
        assert len(data["data"]["result"]) > 0

    async def test_get_content_with_pagination(self, client: AsyncClient, test_content):
        """Test content pagination"""
        response = await client.get("/api/v1/content/?page=1&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["currentPage"] == 1
        assert data["data"]["limit"] <= 5

    async def test_get_content_with_filters(self, client: AsyncClient, test_content):
        """Test content filtering"""
        # Test type filter
        response = await client.get(f"/api/v1/content/?type={ContentTypeEnum.BLOG}")
        assert response.status_code == 200
        
        # Test category filter
        response = await client.get(f"/api/v1/content/?category_id={test_content.category_id}")
        assert response.status_code == 200
        
        # Test search
        response = await client.get("/api/v1/content/?search=Test")
        assert response.status_code == 200

    async def test_get_content_by_id(self, client: AsyncClient, test_content):
        """Test getting content by ID"""
        response = await client.get(f"/api/v1/content/{test_content.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(test_content.id)
        assert data["title"] == test_content.title

    async def test_get_content_by_slug(self, client: AsyncClient, test_content):
        """Test getting content by slug"""
        response = await client.get(f"/api/v1/content/slug/{test_content.slug}")
        
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(test_content.id)
        assert data["slug"] == test_content.slug

    async def test_get_nonexistent_content(self, client: AsyncClient):
        """Test getting non-existent content"""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/content/{fake_id}")
        
        assert response.status_code == 404

    async def test_create_content(self, client: AsyncClient, auth_headers, test_category):
        """Test creating new content"""
        content_data = {
            "title": "New Test Content",
            "content": "This is new test content.",
            "type": ContentTypeEnum.BLOG,
            "category_id": str(test_category.id),
            "excerpt": "New test excerpt",
            "status": ContentStatusEnum.PUBLISHED
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == content_data["title"]
        assert data["content"] == content_data["content"]

    async def test_create_content_unauthorized(self, client: AsyncClient):
        """Test creating content without authentication"""
        content_data = {
            "title": "Unauthorized Content",
            "content": "This should fail.",
            "type": ContentTypeEnum.BLOG
        }
        
        response = await client.post("/api/v1/content/", json=content_data)
        assert response.status_code == 401

    async def test_update_content(self, client: AsyncClient, auth_headers, test_content):
        """Test updating content"""
        update_data = {
            "title": "Updated Test Content",
            "content": "This content has been updated."
        }
        
        response = await client.put(
            f"/api/v1/content/{test_content.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["content"] == update_data["content"]

    async def test_update_content_permission_denied(self, client: AsyncClient, test_content, test_db):
        """Test updating content without permission"""
        # Create another user
        from app.models.user import User
        from app.core.security import get_password_hash, create_access_token
        
        other_user = User(
            email="other@example.com",
            hashed_password=get_password_hash("password"),
            username="otheruser",
            is_active=True,
            is_superuser=False
        )
        test_db.add(other_user)
        await test_db.commit()
        
        other_token = create_access_token(
            data={"sub": str(other_user.id), "email": other_user.email}
        )
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        update_data = {"title": "Unauthorized Update"}
        
        response = await client.put(
            f"/api/v1/content/{test_content.id}",
            json=update_data,
            headers=other_headers
        )
        
        assert response.status_code == 403

    async def test_delete_content(self, client: AsyncClient, auth_headers, test_content):
        """Test deleting content"""
        response = await client.delete(
            f"/api/v1/content/{test_content.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify content is deleted
        get_response = await client.get(f"/api/v1/content/{test_content.id}")
        assert get_response.status_code == 404

    async def test_delete_content_unauthorized(self, client: AsyncClient, test_content):
        """Test deleting content without authentication"""
        response = await client.delete(f"/api/v1/content/{test_content.id}")
        assert response.status_code == 401

    async def test_content_view_count_increment(self, client: AsyncClient, test_content):
        """Test that view count increments when content is accessed"""
        initial_views = test_content.view_count or 0
        
        response = await client.get(f"/api/v1/content/{test_content.id}")
        assert response.status_code == 200
        
        # Check view count increased
        response = await client.get(f"/api/v1/content/{test_content.id}")
        data = response.json()
        assert data["view_count"] > initial_views

    async def test_content_slug_generation(self, client: AsyncClient, auth_headers, test_category):
        """Test automatic slug generation"""
        content_data = {
            "title": "Test Content With Special Characters!@#",
            "content": "Testing slug generation.",
            "type": ContentTypeEnum.BLOG,
            "category_id": str(test_category.id)
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] is not None
        assert "special" in data["slug"].lower()

    async def test_content_status_filtering(self, client: AsyncClient, admin_headers, test_db, test_user, test_category):
        """Test content status filtering for admin users"""
        # Create draft content
        from app.models.content import Content
        
        draft_content = Content(
            title="Draft Content",
            content="This is draft content.",
            type=ContentTypeEnum.BLOG,
            status=ContentStatusEnum.DRAFT,
            author_id=test_user.id,
            category_id=test_category.id,
            slug="draft-content"
        )
        test_db.add(draft_content)
        await test_db.commit()
        
        # Admin should see draft content
        response = await client.get(
            f"/api/v1/content/?status={ContentStatusEnum.DRAFT}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["result"]) > 0

    async def test_invalid_content_type(self, client: AsyncClient, auth_headers):
        """Test creating content with invalid type"""
        content_data = {
            "title": "Invalid Type Content",
            "content": "This has invalid type.",
            "type": "invalid_type"
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_content_metadata_handling(self, client: AsyncClient, auth_headers, test_category):
        """Test content metadata storage and retrieval"""
        metadata = {
            "tags": ["wildlife", "conservation"],
            "reading_time": 5,
            "custom_field": "custom_value"
        }
        
        content_data = {
            "title": "Content with Metadata",
            "content": "This content has metadata.",
            "type": ContentTypeEnum.BLOG,
            "category_id": str(test_category.id),
            "content_metadata": metadata
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content_metadata"] == metadata


class TestContentTypeSpecificEndpoints:
    """Test content type-specific endpoints"""

    async def test_get_blogs_endpoint(self, client: AsyncClient, test_content):
        """Test blogs-specific endpoint"""
        response = await client.get("/api/v1/content/resources/blogs")
        
        assert response.status_code == 200
        data = response.json()
        assert "blogs" in data
        assert "pagination" in data

    async def test_get_case_studies_endpoint(self, client: AsyncClient, test_db, test_user, test_category):
        """Test case studies endpoint"""
        # Create case study content
        from app.models.content import Content
        
        case_study = Content(
            title="Test Case Study",
            content="This is a case study.",
            type=ContentTypeEnum.CASE_STUDY,
            status=ContentStatusEnum.PUBLISHED,
            author_id=test_user.id,
            category_id=test_category.id,
            slug="test-case-study"
        )
        test_db.add(case_study)
        await test_db.commit()
        
        response = await client.get("/api/v1/content/resources/casestudies")
        
        assert response.status_code == 200
        data = response.json()
        assert "casestudies" in data

    async def test_get_conservation_efforts_endpoint(self, client: AsyncClient, test_db, test_user, test_category):
        """Test conservation efforts endpoint"""
        # Create conservation effort content
        from app.models.content import Content
        
        conservation = Content(
            title="Test Conservation Effort",
            content="This is a conservation effort.",
            type=ContentTypeEnum.CONSERVATION_EFFORT,
            status=ContentStatusEnum.PUBLISHED,
            author_id=test_user.id,
            category_id=test_category.id,
            slug="test-conservation"
        )
        test_db.add(conservation)
        await test_db.commit()
        
        response = await client.get("/api/v1/content/resources/conservation")
        
        assert response.status_code == 200
        data = response.json()
        assert "conservation" in data

    async def test_get_daily_updates_endpoint(self, client: AsyncClient, test_db, test_user, test_category):
        """Test daily updates endpoint"""
        # Create daily update content
        from app.models.content import Content
        
        daily_update = Content(
            title="Test Daily Update",
            content="This is a daily update.",
            type=ContentTypeEnum.DAILY_UPDATE,
            status=ContentStatusEnum.PUBLISHED,
            author_id=test_user.id,
            category_id=test_category.id,
            slug="test-daily-update"
        )
        test_db.add(daily_update)
        await test_db.commit()
        
        response = await client.get("/api/v1/content/resources/dailyupdates")
        
        assert response.status_code == 200
        data = response.json()
        assert "dailyupdates" in data or "daily_updates" in data


class TestContentErrorHandling:
    """Test content API error handling"""

    async def test_invalid_uuid_format(self, client: AsyncClient):
        """Test handling of invalid UUID format"""
        response = await client.get("/api/v1/content/invalid-uuid")
        assert response.status_code == 422

    async def test_invalid_pagination_params(self, client: AsyncClient):
        """Test handling of invalid pagination parameters"""
        # Negative page
        response = await client.get("/api/v1/content/?page=-1")
        assert response.status_code == 422
        
        # Zero limit
        response = await client.get("/api/v1/content/?limit=0")
        assert response.status_code == 422
        
        # Excessive limit
        response = await client.get("/api/v1/content/?limit=1000")
        assert response.status_code == 422

    async def test_invalid_category_id(self, client: AsyncClient, auth_headers):
        """Test creating content with invalid category ID"""
        fake_category_id = uuid4()
        content_data = {
            "title": "Content with Invalid Category",
            "content": "This has invalid category.",
            "type": ContentTypeEnum.BLOG,
            "category_id": str(fake_category_id)
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400

    async def test_missing_required_fields(self, client: AsyncClient, auth_headers):
        """Test creating content with missing required fields"""
        # Missing title
        content_data = {
            "content": "Content without title.",
            "type": ContentTypeEnum.BLOG
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        
        # Missing content
        content_data = {
            "title": "Title without content",
            "type": ContentTypeEnum.BLOG
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_content_length_limits(self, client: AsyncClient, auth_headers, test_category):
        """Test content field length limits"""
        # Title too long
        long_title = "x" * 600  # Exceeds 500 char limit
        content_data = {
            "title": long_title,
            "content": "Valid content.",
            "type": ContentTypeEnum.BLOG,
            "category_id": str(test_category.id)
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_duplicate_slug_handling(self, client: AsyncClient, auth_headers, test_category, test_content):
        """Test handling of duplicate slugs"""
        # Create content with same title (should generate unique slug)
        content_data = {
            "title": test_content.title,  # Same title as existing content
            "content": "Different content with same title.",
            "type": ContentTypeEnum.BLOG,
            "category_id": str(test_category.id)
        }
        
        response = await client.post(
            "/api/v1/content/",
            json=content_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Slug should be different (with suffix)
        assert data["slug"] != test_content.slug
        assert test_content.slug in data["slug"]  # Should contain original slug as base