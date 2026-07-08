from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# For SQLite, we need connect_args={"check_same_thread": False}
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    """Dependency for getting async database session"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initializes schema and tables if they do not exist"""
    async with engine.begin() as conn:
        # Create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)
