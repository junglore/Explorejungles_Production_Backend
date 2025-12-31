"""
Test configuration and fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os
from pathlib import Path

from app.main import app
from app.db.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.category import Category
from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
from app.models.myth_fact import MythFact
from app.core.security import get_password_hash, create_access_token


# Test database setup
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:admin123@localhost:5432/junglore_KE_db"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database dependency override"""
    from httpx import ASGITransport
    from app.db.database import get_db_session
    
    async def override_get_db():
        yield test_db
    
    # Override both database dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create test user"""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        username="testuser",
        is_active=True,
        is_superuser=False
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """Create admin user"""
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        username="admin",
        is_active=True,
        is_superuser=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user: User) -> str:
    """Create access token for test user"""
    return create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create access token for admin user"""
    return create_access_token(
        data={"sub": str(admin_user.id), "email": admin_user.email}
    )


@pytest.fixture
async def test_category(test_db: AsyncSession) -> Category:
    """Create test category"""
    category = Category(
        name="Test Category",
        slug="test-category"
    )
    test_db.add(category)
    await test_db.commit()
    await test_db.refresh(category)
    return category


@pytest.fixture
async def test_content(test_db: AsyncSession, test_user: User, test_category: Category) -> Content:
    """Create test content"""
    content = Content(
        title="Test Blog Post",
        content="This is test content for the blog post.",
        type=ContentTypeEnum.BLOG,
        status=ContentStatusEnum.PUBLISHED,
        author_id=test_user.id,
        category_id=test_category.id,
        slug="test-blog-post",
        excerpt="Test excerpt"
    )
    test_db.add(content)
    await test_db.commit()
    await test_db.refresh(content)
    return content


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory for file tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        upload_dir = Path(temp_dir) / "uploads"
        upload_dir.mkdir(exist_ok=True)
        yield upload_dir


@pytest.fixture
def sample_image_file():
    """Create a sample image file for testing"""
    # Create a minimal valid JPEG file (1x1 pixel)
    jpeg_data = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01,
        0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0xFF, 0xC4,
        0x00, 0x14, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xDA, 0x00, 0x0C,
        0x03, 0x01, 0x00, 0x02, 0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0xB2, 0xC0,
        0x07, 0xFF, 0xD9
    ])
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(jpeg_data)
        f.flush()
        yield f.name
    
    # Clean up
    try:
        os.unlink(f.name)
    except FileNotFoundError:
        pass


@pytest.fixture
def auth_headers(user_token: str):
    """Create authorization headers for authenticated requests"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str):
    """Create authorization headers for admin requests"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def test_myth_fact(test_db: AsyncSession, test_category: Category) -> MythFact:
    """Create a test myth fact entry"""
    myth_fact = MythFact(
        title="Test Myth vs Fact",
        myth_content="This is a test myth statement",
        fact_content="This is the corresponding fact explanation",
        category_id=test_category.id,
        is_featured=False,
        image_url="/test/image.jpg"
    )
    test_db.add(myth_fact)
    await test_db.commit()
    await test_db.refresh(myth_fact)
    return myth_fact


@pytest.fixture
async def featured_myth_fact(test_db: AsyncSession, test_category: Category) -> MythFact:
    """Create a featured myth fact entry"""
    myth_fact = MythFact(
        title="Featured Myth vs Fact",
        myth_content="This is a featured myth statement",
        fact_content="This is the featured fact explanation",
        category_id=test_category.id,
        is_featured=True,
        image_url="/featured/image.jpg"
    )
    test_db.add(myth_fact)
    await test_db.commit()
    await test_db.refresh(myth_fact)
    return myth_fact