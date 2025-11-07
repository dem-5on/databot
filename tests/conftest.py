import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.user import User
from app.models.wallet import Wallet
from app.models.bundle import Bundle
from app.models.transaction import Transaction
from app.models.order import Order
from sqlalchemy.dialects.postgresql import UUID
import uuid


@pytest.fixture
async def test_db():
    """Create a test database session."""
    # Use SQLite in-memory for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_user(test_db: AsyncSession):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        telegram_id="123456789",
        name="Test User",
        phone="0551234567",
        provider="MTN"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_wallet(test_db: AsyncSession, test_user: User):
    """Create a test wallet."""
    wallet = Wallet(
        user_id=test_user.id,
        balance=100.00
    )
    test_db.add(wallet)
    await test_db.commit()
    await test_db.refresh(wallet)
    return wallet


@pytest.fixture
async def test_bundle(test_db: AsyncSession):
    """Create a test bundle."""
    bundle = Bundle(
        network="MTN",
        capacity="5",
        mb="5000",
        price=23.00,
        currency="GHS",
        active=True
    )
    test_db.add(bundle)
    await test_db.commit()
    await test_db.refresh(bundle)
    return bundle

