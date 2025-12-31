"""
Tests for Blog API endpoints
"""

import pytest
from httpx import AsyncClient
from io import BytesIO
from uuid import uuid4
from app.models.content import ContentTypeEnum, ContentStatusEnum


class TestBlogAPI:
    """Test blog-specific API endpoints"""

    async def test_fetch_all_blogs(self, client: AsyncClient, test_content):
        """Test fetching all blogs"""
        response = await client.get("/api/v1/blogs/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert "data" in data
        assert "result" in data["data"]

    async def test_fetch_blogs_with_pagination(self, client: AsyncClient, test_content):
        """Test blog pagination"""
        response = await client.get("/api/v1/blogs/?page=1&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["currentPage"] == 1
        assert data["data"]["limit"] <= 5

    async def test_fetch_blogs_with_search(self, client: AsyncClient, test_content):
        """Test blog search functionality"""
        response = await client.get("/api/v1/blogs/?search=Test")
        
        assert response.status_code == 200
        data = response.json()
        # Should find the test content
        assert len(data["data"]["result"]) > 0

    async def test_fetch_blogs_by_category(self, client: AsyncClient, test_content):
        """Test filtering blogs by category"""
        response = await client.get(f"/api/v1/blogs/?category_id={test_content.category_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["result"]) > 0

    async def test_fetch_single_blog(self, client: AsyncClient, test_content):
        """Test fetching single blog by ID"""
        response = await client.get(f"/api/v1/blogs/{test_content.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert str(data["data"]["id"]) == str(test_content.id)

    async def test_fetch_nonexistent_blog(self, client: AsyncClient):
        """Test fetching non-existent blog"""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/blogs/{fake_id}")
        
        assert response.status_code == 404

    async def test_create_blog_with_form_data(self, client: AsyncClient, auth_headers, test_category):
        """Test creating blog with form data"""
        blog_data = {
            "title": "New Blog Post",
            "content": "This is the content of the new blog post.",
            "description": "Blog description",
            "category_id": str(test_category.id)
        }
        
        response = await client.post(
            "/api/v1/blogs/",
            data=blog_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["data"]["title"] == blog_data["title"]

    async def test_create_blog_with_image_upload(self, client: AsyncClient, auth_headers, test_category, sample_image_file):
        """Test creating blog with image upload"""
        blog_data = {
            "title": "Blog with Image",
            "content": "This blog has an image.",
            "category_id": str(test_category.id)
        }
        
        with open(sample_image_file, "rb") as f:
            files = {"image": ("test.jpg", f, "image/jpeg")}
            
            response = await client.post(
                "/api/v1/blogs/",
                data=blog_data,
                files=files,
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["image"] is not None

    async def test_create_blog_unauthorized(self, client: AsyncClient):
        """Test creating blog without authentication"""
        blog_data = {
            "title": "Unauthorized Blog",
            "content": "This should fail."
        }
        
        response = await client.post("/api/v1/blogs/", data=blog_data)
        assert response.status_code == 401

    async def test_update_blog(self, client: AsyncClient, auth_headers, test_content):
        """Test updating blog"""
        update_data = {
            "title": "Updated Blog Title",
            "content": "Updated blog content."
        }
        
        response = await client.patch(
            f"/api/v1/blogs/{test_content.id}",
            data=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == update_data["title"]

    async def test_update_blog_with_image(self, client: AsyncClient, auth_headers, test_content, sample_image_file):
        """Test updating blog with new image"""
        update_data = {
            "title": "Updated with Image"
        }
        
        with open(sample_image_file, "rb") as f:
            files = {"image": ("updated.jpg", f, "image/jpeg")}
            
            response = await client.patch(
                f"/api/v1/blogs/{test_content.id}",
                data=update_data,
                files=files,
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["image"] is not None

    async def test_feature_blog(self, client: AsyncClient, auth_headers, test_content):
        """Test featuring a blog"""
        feature_data = {"place": 1}
        
        response = await client.patch(
            f"/api/v1/blogs/feature/{test_content.id}",
            data=feature_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["featured"] is True
        assert data["data"]["feature_place"] == 1

    async def test_feature_blog_invalid_place(self, client: AsyncClient, auth_headers, test_content):
        """Test featuring blog with invalid place"""
        feature_data = {"place": 5}  # Invalid place (should be 1-3)
        
        response = await client.patch(
            f"/api/v1/blogs/feature/{test_content.id}",
            data=feature_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_delete_blog(self, client: AsyncClient, auth_headers, test_content):
        """Test deleting blog"""
        response = await client.delete(
            f"/api/v1/blogs/{test_content.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify blog is deleted
        get_response = await client.get(f"/api/v1/blogs/{test_content.id}")
        assert get_response.status_code == 404

    async def test_delete_blog_unauthorized(self, client: AsyncClient, test_content):
        """Test deleting blog without authentication"""
        response = await client.delete(f"/api/v1/blogs/{test_content.id}")
        assert response.status_code == 401


class TestBlogCategoryAPI:
    """Test blog category API endpoints"""

    async def test_fetch_all_categories(self, client: AsyncClient, test_category):
        """Test fetching all blog categories"""
        response = await client.get("/api/v1/blogs/category")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert "result" in data["data"]

    async def test_fetch_categories_with_pagination(self, client: AsyncClient, test_category):
        """Test category pagination"""
        response = await client.get("/api/v1/blogs/category?page=1&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["currentPage"] == 1

    async def test_fetch_categories_with_search(self, client: AsyncClient, test_category):
        """Test category search"""
        response = await client.get("/api/v1/blogs/category?search=Test")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["result"]) > 0

    async def test_fetch_single_category(self, client: AsyncClient, test_category):
        """Test fetching single category"""
        response = await client.get(f"/api/v1/blogs/category/{test_category.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert str(data["data"]["id"]) == str(test_category.id)

    async def test_create_category(self, client: AsyncClient, auth_headers):
        """Test creating new category"""
        category_data = {
            "name": "New Category",
            "slug": "new-category"
        }
        
        response = await client.post(
            "/api/v1/blogs/category",
            data=category_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == category_data["name"]
        assert data["data"]["slug"] == category_data["slug"]

    async def test_create_category_auto_slug(self, client: AsyncClient, auth_headers):
        """Test creating category with auto-generated slug"""
        category_data = {"name": "Auto Slug Category"}
        
        response = await client.post(
            "/api/v1/blogs/category",
            data=category_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["slug"] is not None
        assert "auto-slug" in data["data"]["slug"]

    async def test_update_category(self, client: AsyncClient, auth_headers, test_category):
        """Test updating category"""
        update_data = {
            "name": "Updated Category Name",
            "slug": "updated-category"
        }
        
        response = await client.patch(
            f"/api/v1/blogs/category/{test_category.id}",
            data=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == update_data["name"]
        assert data["data"]["slug"] == update_data["slug"]

    async def test_delete_category(self, client: AsyncClient, auth_headers, test_db):
        """Test deleting category"""
        # Create a category to delete
        from app.models.category import Category
        
        category = Category(name="Delete Me", slug="delete-me")
        test_db.add(category)
        await test_db.commit()
        await test_db.refresh(category)
        
        response = await client.delete(
            f"/api/v1/blogs/category/{category.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestBlogFileUpload:
    """Test blog file upload functionality"""

    async def test_upload_valid_image(self, client: AsyncClient, auth_headers, test_category, sample_image_file):
        """Test uploading valid image file"""
        blog_data = {
            "title": "Blog with Valid Image",
            "content": "Content with image.",
            "category_id": str(test_category.id)
        }
        
        with open(sample_image_file, "rb") as f:
            files = {"image": ("valid.jpg", f, "image/jpeg")}
            
            response = await client.post(
                "/api/v1/blogs/",
                data=blog_data,
                files=files,
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["image"] is not None

    async def test_upload_multiple_files(self, client: AsyncClient, auth_headers, test_category, sample_image_file):
        """Test uploading multiple files (image, banner, video)"""
        blog_data = {
            "title": "Blog with Multiple Files",
            "content": "Content with multiple files.",
            "category_id": str(test_category.id)
        }
        
        with open(sample_image_file, "rb") as f:
            files = {
                "image": ("image.jpg", f, "image/jpeg"),
                "banner": ("banner.jpg", f, "image/jpeg")
            }
            
            response = await client.post(
                "/api/v1/blogs/",
                data=blog_data,
                files=files,
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["image"] is not None
        assert data["data"]["banner"] is not None

    async def test_upload_invalid_file_type(self, client: AsyncClient, auth_headers, test_category):
        """Test uploading invalid file type"""
        blog_data = {
            "title": "Blog with Invalid File",
            "content": "Content with invalid file.",
            "category_id": str(test_category.id)
        }
        
        # Create a text file
        text_content = b"This is not an image"
        files = {"image": ("invalid.txt", BytesIO(text_content), "text/plain")}
        
        response = await client.post(
            "/api/v1/blogs/",
            data=blog_data,
            files=files,
            headers=auth_headers
        )
        
        # Should either reject the file or handle gracefully
        assert response.status_code in [200, 400, 422]

    async def test_upload_oversized_file(self, client: AsyncClient, auth_headers, test_category):
        """Test uploading oversized file"""
        blog_data = {
            "title": "Blog with Large File",
            "content": "Content with large file.",
            "category_id": str(test_category.id)
        }
        
        # Create a large file (simulate)
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB (exceeds 50MB limit)
        files = {"image": ("large.jpg", BytesIO(large_content), "image/jpeg")}
        
        response = await client.post(
            "/api/v1/blogs/",
            data=blog_data,
            files=files,
            headers=auth_headers
        )
        
        # Should reject oversized file
        assert response.status_code in [400, 413, 422]

    async def test_upload_empty_file(self, client: AsyncClient, auth_headers, test_category):
        """Test uploading empty file"""
        blog_data = {
            "title": "Blog with Empty File",
            "content": "Content with empty file.",
            "category_id": str(test_category.id)
        }
        
        files = {"image": ("empty.jpg", BytesIO(b""), "image/jpeg")}
        
        response = await client.post(
            "/api/v1/blogs/",
            data=blog_data,
            files=files,
            headers=auth_headers
        )
        
        # Should handle empty file gracefully
        assert response.status_code in [200, 400, 422]


class TestBlogErrorHandling:
    """Test blog API error handling"""

    async def test_invalid_blog_id_format(self, client: AsyncClient):
        """Test handling invalid blog ID format"""
        response = await client.get("/api/v1/blogs/invalid-id")
        assert response.status_code == 422

    async def test_missing_required_fields(self, client: AsyncClient, auth_headers):
        """Test creating blog with missing required fields"""
        # Missing title
        blog_data = {"content": "Content without title"}
        
        response = await client.post(
            "/api/v1/blogs/",
            data=blog_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_invalid_category_id(self, client: AsyncClient, auth_headers):
        """Test creating blog with invalid category ID"""
        blog_data = {
            "title": "Blog with Invalid Category",
            "content": "Content with invalid category.",
            "category_id": "invalid-uuid"
        }
        
        response = await client.post(
            "/api/v1/blogs/",
            data=blog_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    async def test_nonexistent_category_id(self, client: AsyncClient, auth_headers):
        """Test creating blog with non-existent category ID"""
        fake_category_id = uuid4()
        blog_data = {
            "title": "Blog with Nonexistent Category",
            "content": "Content with nonexistent category.",
            "category_id": str(fake_category_id)
        }
        
        response = await client.post(
            "/api/v1/blogs/",
            data=blog_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400

    async def test_duplicate_category_slug(self, client: AsyncClient, auth_headers, test_category):
        """Test creating category with duplicate slug"""
        category_data = {
            "name": "Duplicate Slug Category",
            "slug": test_category.slug  # Use existing slug
        }
        
        response = await client.post(
            "/api/v1/blogs/category",
            data=category_data,
            headers=auth_headers
        )
        
        # Should handle duplicate slug (either reject or auto-modify)
        if response.status_code == 200:
            data = response.json()
            # Slug should be modified to be unique
            assert data["data"]["slug"] != test_category.slug
        else:
            assert response.status_code in [400, 422]

    async def test_feature_limit_exceeded(self, client: AsyncClient, auth_headers, test_db, test_user, test_category):
        """Test featuring more than 3 blogs"""
        # Create 3 featured blogs first
        from app.models.content import Content
        
        for i in range(3):
            blog = Content(
                title=f"Featured Blog {i+1}",
                content=f"Content for featured blog {i+1}",
                type=ContentTypeEnum.BLOG,
                status=ContentStatusEnum.PUBLISHED,
                author_id=test_user.id,
                category_id=test_category.id,
                slug=f"featured-blog-{i+1}",
                featured=True,
                feature_place=i+1
            )
            test_db.add(blog)
        
        await test_db.commit()
        
        # Create another blog to feature (should exceed limit)
        new_blog = Content(
            title="Fourth Blog",
            content="This should not be featurable.",
            type=ContentTypeEnum.BLOG,
            status=ContentStatusEnum.PUBLISHED,
            author_id=test_user.id,
            category_id=test_category.id,
            slug="fourth-blog"
        )
        test_db.add(new_blog)
        await test_db.commit()
        await test_db.refresh(new_blog)
        
        feature_data = {"place": 1}
        
        response = await client.patch(
            f"/api/v1/blogs/feature/{new_blog.id}",
            data=feature_data,
            headers=auth_headers
        )
        
        # Should reject featuring when limit is exceeded
        assert response.status_code == 400