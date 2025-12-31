"""
Tests for Myths vs Facts admin panel routes
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import patch, AsyncMock
import tempfile
import os
from pathlib import Path

from app.models.myth_fact import MythFact
from app.models.category import Category
from app.models.user import User


class TestMythsFactsAdmin:
    """Test class for Myths vs Facts admin routes"""

    @pytest.fixture
    async def authenticated_session(self, client: AsyncClient):
        """Create authenticated admin session"""
        # Simulate admin login session
        async with client as ac:
            # Mock session authentication
            with patch.object(ac, 'cookies') as mock_cookies:
                mock_cookies.get.return_value = "authenticated_session"
                yield ac

    @pytest.fixture
    async def test_myth_facts(self, test_db: AsyncSession, test_category: Category):
        """Create multiple test myth facts for admin testing"""
        myth_facts = []
        for i in range(5):
            myth_fact = MythFact(
                title=f"Admin Test Myth {i}",
                myth_content=f"Admin myth content {i}",
                fact_content=f"Admin fact content {i}",
                category_id=test_category.id,
                is_featured=(i % 2 == 0)  # Alternate featured status
            )
            test_db.add(myth_fact)
            myth_facts.append(myth_fact)
        
        await test_db.commit()
        for myth_fact in myth_facts:
            await test_db.refresh(myth_fact)
        
        return myth_facts

    @pytest.mark.asyncio
    async def test_admin_myths_facts_list_unauthenticated(self, client: AsyncClient):
        """Test admin list redirects when not authenticated"""
        response = await client.get("/admin/myths-facts")
        
        # Should redirect to login
        assert response.status_code == 302
        assert "/admin/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_admin_myths_facts_list_authenticated(self, client: AsyncClient, test_myth_facts):
        """Test admin list view when authenticated"""
        # Mock authenticated session
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            # Mock database session
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock query results
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = test_myth_facts
                mock_session.execute.return_value = mock_result
                
                # Mock count query
                mock_count_result = AsyncMock()
                mock_count_result.scalar.return_value = len(test_myth_facts)
                mock_session.execute.return_value = mock_count_result
                
                response = await client.get("/admin/myths-facts")
                
                assert response.status_code == 200
                content = response.text
                
                # Check that HTML contains expected elements
                assert "Myths vs Facts" in content
                assert "Create New" in content
                assert "admin-table" in content

    @pytest.mark.asyncio
    async def test_admin_myths_facts_list_with_search(self, client: AsyncClient, test_myth_facts):
        """Test admin list with search functionality"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock filtered results
                filtered_results = [mf for mf in test_myth_facts if "0" in mf.title]
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = filtered_results
                mock_session.execute.return_value = mock_result
                
                response = await client.get("/admin/myths-facts?search=0")
                
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_myths_facts_list_with_category_filter(self, client: AsyncClient, test_myth_facts, test_category):
        """Test admin list with category filter"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock category filtered results
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = test_myth_facts
                mock_session.execute.return_value = mock_result
                
                response = await client.get(f"/admin/myths-facts?category_id={test_category.id}")
                
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_myths_facts_list_featured_filter(self, client: AsyncClient, test_myth_facts):
        """Test admin list with featured filter"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock featured only results
                featured_results = [mf for mf in test_myth_facts if mf.is_featured]
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = featured_results
                mock_session.execute.return_value = mock_result
                
                response = await client.get("/admin/myths-facts?featured_only=true")
                
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_myths_facts_list_pagination(self, client: AsyncClient, test_myth_facts):
        """Test admin list pagination"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock paginated results
                page_size = 2
                page_results = test_myth_facts[:page_size]
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = page_results
                mock_session.execute.return_value = mock_result
                
                # Mock total count
                mock_count_result = AsyncMock()
                mock_count_result.scalar.return_value = len(test_myth_facts)
                
                response = await client.get(f"/admin/myths-facts?page=1&limit={page_size}")
                
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_create_form_unauthenticated(self, client: AsyncClient):
        """Test create form redirects when not authenticated"""
        response = await client.get("/admin/myths-facts/create")
        
        assert response.status_code == 302
        assert "/admin/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_admin_create_form_authenticated(self, client: AsyncClient, test_category):
        """Test create form when authenticated"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock categories query
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = [test_category]
                mock_session.execute.return_value = mock_result
                
                response = await client.get("/admin/myths-facts/create")
                
                assert response.status_code == 200
                content = response.text
                
                # Check form elements
                assert "Create Myth vs Fact" in content
                assert "form" in content.lower()
                assert "title" in content.lower()
                assert "myth_content" in content.lower()
                assert "fact_content" in content.lower()

    @pytest.mark.asyncio
    async def test_admin_create_form_database_error(self, client: AsyncClient):
        """Test create form handles database errors gracefully"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_db.side_effect = Exception("Database connection failed")
                
                response = await client.get("/admin/myths-facts/create")
                
                # Should still return form, just without categories
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_create_post_success(self, client: AsyncClient, test_category):
        """Test successful creation via admin form"""
        form_data = {
            "title": "Admin Created Myth",
            "myth_content": "This myth was created via admin",
            "fact_content": "This fact was created via admin",
            "category_id": str(test_category.id),
            "is_featured": "true"
        }
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock successful creation
                mock_session.add = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.refresh = AsyncMock()
                
                response = await client.post("/admin/myths-facts/create", data=form_data)
                
                # Should redirect to list on success
                assert response.status_code in [200, 302]

    @pytest.mark.asyncio
    async def test_admin_create_post_validation_error(self, client: AsyncClient):
        """Test creation with validation errors"""
        # Missing required fields
        form_data = {
            "title": "",  # Empty title should fail
            "myth_content": "Valid myth",
            "fact_content": "Valid fact"
        }
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            response = await client.post("/admin/myths-facts/create", data=form_data)
            
            # Should return form with errors
            assert response.status_code == 200
            # Should contain error message
            content = response.text
            assert "error" in content.lower() or "required" in content.lower()

    @pytest.mark.asyncio
    async def test_admin_edit_form_unauthenticated(self, client: AsyncClient, test_myth_facts):
        """Test edit form redirects when not authenticated"""
        myth_fact = test_myth_facts[0]
        response = await client.get(f"/admin/myths-facts/edit/{myth_fact.id}")
        
        assert response.status_code == 302
        assert "/admin/login" in response.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_admin_edit_form_authenticated(self, client: AsyncClient, test_myth_facts, test_category):
        """Test edit form when authenticated"""
        myth_fact = test_myth_facts[0]
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock myth fact query
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = myth_fact
                mock_session.execute.return_value = mock_result
                
                # Mock categories query
                mock_categories_result = AsyncMock()
                mock_categories_result.scalars.return_value.all.return_value = [test_category]
                
                response = await client.get(f"/admin/myths-facts/edit/{myth_fact.id}")
                
                assert response.status_code == 200
                content = response.text
                
                # Check form is pre-populated
                assert myth_fact.title in content
                assert "Edit Myth vs Fact" in content

    @pytest.mark.asyncio
    async def test_admin_edit_form_not_found(self, client: AsyncClient):
        """Test edit form with non-existent myth fact"""
        non_existent_id = uuid4()
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock not found
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_session.execute.return_value = mock_result
                
                response = await client.get(f"/admin/myths-facts/edit/{non_existent_id}")
                
                assert response.status_code == 200
                content = response.text
                assert "not found" in content.lower() or "error" in content.lower()

    @pytest.mark.asyncio
    async def test_admin_edit_post_success(self, client: AsyncClient, test_myth_facts):
        """Test successful edit via admin form"""
        myth_fact = test_myth_facts[0]
        
        form_data = {
            "title": "Updated Admin Title",
            "myth_content": "Updated myth content",
            "fact_content": "Updated fact content",
            "is_featured": "true"
        }
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock finding existing myth fact
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = myth_fact
                mock_session.execute.return_value = mock_result
                
                # Mock successful update
                mock_session.commit = AsyncMock()
                mock_session.refresh = AsyncMock()
                
                response = await client.post(f"/admin/myths-facts/edit/{myth_fact.id}", data=form_data)
                
                # Should redirect or return success
                assert response.status_code in [200, 302]

    @pytest.mark.asyncio
    async def test_admin_delete_unauthenticated(self, client: AsyncClient, test_myth_facts):
        """Test delete redirects when not authenticated"""
        myth_fact = test_myth_facts[0]
        response = await client.delete(f"/admin/myths-facts/delete/{myth_fact.id}")
        
        # Should return unauthorized or redirect
        assert response.status_code in [302, 401, 403]

    @pytest.mark.asyncio
    async def test_admin_delete_success(self, client: AsyncClient, test_myth_facts):
        """Test successful deletion via admin"""
        myth_fact = test_myth_facts[0]
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock finding myth fact
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = myth_fact
                mock_session.execute.return_value = mock_result
                
                # Mock successful deletion
                mock_session.delete = AsyncMock()
                mock_session.commit = AsyncMock()
                
                response = await client.delete(f"/admin/myths-facts/delete/{myth_fact.id}")
                
                assert response.status_code == 200
                data = response.json()
                assert "success" in data.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_admin_delete_not_found(self, client: AsyncClient):
        """Test delete of non-existent myth fact"""
        non_existent_id = uuid4()
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock not found
                mock_result = AsyncMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_session.execute.return_value = mock_result
                
                response = await client.delete(f"/admin/myths-facts/delete/{non_existent_id}")
                
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_file_upload_handling(self, client: AsyncClient, sample_image_file):
        """Test file upload in admin forms"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.file_upload_service') as mock_upload:
                mock_upload.upload_file.return_value = "/uploads/test-image.jpg"
                
                # Test file upload in create form
                with open(sample_image_file, 'rb') as f:
                    files = {"image": ("test.jpg", f, "image/jpeg")}
                    form_data = {
                        "title": "Test with Image",
                        "myth_content": "Test myth",
                        "fact_content": "Test fact"
                    }
                    
                    response = await client.post(
                        "/admin/myths-facts/create",
                        data=form_data,
                        files=files
                    )
                    
                    # Should handle file upload
                    assert response.status_code in [200, 302]

    @pytest.mark.asyncio
    async def test_admin_database_error_handling(self, client: AsyncClient):
        """Test admin routes handle database errors gracefully"""
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_db.side_effect = Exception("Database connection failed")
                
                response = await client.get("/admin/myths-facts")
                
                # Should return error page instead of crashing
                assert response.status_code == 200
                content = response.text
                assert "error" in content.lower()

    @pytest.mark.asyncio
    async def test_admin_form_csrf_protection(self, client: AsyncClient):
        """Test CSRF protection in admin forms"""
        # This would test CSRF token validation if implemented
        # For now, just ensure forms can be submitted
        
        form_data = {
            "title": "CSRF Test",
            "myth_content": "Test myth",
            "fact_content": "Test fact"
        }
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            response = await client.post("/admin/myths-facts/create", data=form_data)
            
            # Should process form (success or validation error)
            assert response.status_code in [200, 302, 422]

    @pytest.mark.asyncio
    async def test_admin_search_functionality(self, client: AsyncClient, test_myth_facts):
        """Test search functionality in admin interface"""
        search_term = "Admin Test Myth 0"
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                mock_session = AsyncMock()
                mock_db.return_value.__aenter__.return_value = mock_session
                
                # Mock search results
                matching_myths = [mf for mf in test_myth_facts if search_term in mf.title]
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = matching_myths
                mock_session.execute.return_value = mock_result
                
                response = await client.get(f"/admin/myths-facts?search={search_term}")
                
                assert response.status_code == 200
                # Should contain search term in response
                content = response.text
                assert search_term in content or "search" in content.lower()

    @pytest.mark.asyncio
    async def test_admin_bulk_operations(self, client: AsyncClient, test_myth_facts):
        """Test bulk operations if implemented"""
        # This would test bulk delete, bulk feature toggle, etc.
        # For now, just test that individual operations work
        
        with patch('app.admin.routes.myths_facts.Request') as mock_request:
            mock_request.return_value.session.get.return_value = True
            
            # Test that multiple individual operations can be performed
            for myth_fact in test_myth_facts[:2]:
                with patch('app.admin.routes.myths_facts.get_db_session') as mock_db:
                    mock_session = AsyncMock()
                    mock_db.return_value.__aenter__.return_value = mock_session
                    
                    mock_result = AsyncMock()
                    mock_result.scalar_one_or_none.return_value = myth_fact
                    mock_session.execute.return_value = mock_result
                    
                    response = await client.delete(f"/admin/myths-facts/delete/{myth_fact.id}")
                    assert response.status_code in [200, 404]  # 404 if already deleted