"""
Database connection and session management
"""
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from .models import Base


class Database:
    """Async database manager using SQLite"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "praxix_senate.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create async engine
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}",
            echo=False,
            poolclass=NullPool
        )

        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        return self.async_session()


# Global database instance
_db_instance = None


def get_database(db_path: str = None) -> Database:
    """Get or create global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance


async def init_database(db_path: str = None) -> Database:
    """Initialize the database"""
    db = get_database(db_path)
    await db.init_db()
    return db
