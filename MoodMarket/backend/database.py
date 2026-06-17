# c:\Mood_Market\database.py
import os
import re
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from config import api_settings

logger = logging.getLogger("database")

db_uri = api_settings.timescaledb_uri
if db_uri.startswith("postgresql://"):
    db_uri = db_uri.replace("postgresql://", "postgresql+asyncpg://")

is_sqlite = False

try:
    engine = create_async_engine(
        db_uri,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30.0,
        pool_pre_ping=True
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.info(f"Initialized database engine using Postgres/TimescaleDB pool.")
except Exception as e:
    logger.warning(f"TimescaleDB connection pool init failed: {e}. Falling back to SQLite.")
    fallback_uri = "sqlite+aiosqlite:///moodmarket.db"
    engine = create_async_engine(fallback_uri, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    is_sqlite = True


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for retrieving database session context."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def translate_postgres_to_sqlite(sql: str) -> str:
    """Translates Postgres/TimescaleDB syntax into SQLite compatible statements."""
    # Remove TimescaleDB extension command (optional semicolon at the end)
    sql = re.sub(r"(?i)CREATE\s+EXTENSION\s+.*?(;|$)", "", sql)
    
    # Exclude TimescaleDB API calls
    sql = re.sub(r"(?i)SELECT\s+create_hypertable\([^)]*\)(;|$)", "", sql)
    sql = re.sub(r"(?i)SELECT\s+add_compression_policy\([^)]*\)(;|$)", "", sql)
    sql = re.sub(r"(?i)SELECT\s+add_retention_policy\([^)]*\)(;|$)", "", sql)
    sql = re.sub(r"(?i)ALTER\s+TABLE\s+\w+\s+SET\s+\([^)]*\)(;|$)", "", sql)
    
    # Convert Materialized Views to standard Views
    sql = re.sub(
        r"(?i)CREATE\s+MATERIALIZED\s+VIEW\s+(IF\s+NOT\s+EXISTS\s+)?(\w+)\s+WITH\s+\(timescaledb\.continuous\)\s+AS",
        r"CREATE VIEW \1\2 AS",
        sql
    )
    
    # Map aggregate functions
    sql = re.sub(r"(?i)FIRST\(\s*(\w+)\s*,\s*time\s*\)", r"MIN(\1)", sql)
    sql = re.sub(r"(?i)LAST\(\s*(\w+)\s*,\s*time\s*\)", r"MAX(\1)", sql)
    
    # Convert time_bucket expressions
    sql = re.sub(r"(?i)time_bucket\(\s*INTERVAL\s*'1\s+day'\s*,\s*time\s*\)", r"date(time)", sql)
    sql = re.sub(r"(?i)time_bucket\(\s*INTERVAL\s*'1\s+hour'\s*,\s*time\s*\)", r"strftime('%Y-%m-%d %H:00:00', time)", sql)
    sql = re.sub(r"(?i)time_bucket\(\s*INTERVAL\s*'7\s+days'\s*,\s*time\s*\)", r"strftime('%Y-%W', time)", sql)
    
    # Map types
    sql = sql.replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMP")
    sql = sql.replace("DOUBLE PRECISION", "FLOAT")
    sql = sql.replace("JSONB", "TEXT")
    
    # SQLite does not support IF NOT EXISTS in ALTER TABLE ADD COLUMN
    sql = re.sub(
        r"(?i)ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+(.*)",
        r"ALTER TABLE \1 ADD COLUMN \2",
        sql
    )
    sql = re.sub(
        r"(?i)ALTER\s+TABLE\s+(\w+)\s+ADD\s+IF\s+NOT\s+EXISTS\s+(.*)",
        r"ALTER TABLE \1 ADD COLUMN \2",
        sql
    )
    
    return sql


async def run_migration_file(filepath: str):
    """Parses a migration SQL file and executes individual statements sequentially."""
    if not os.path.exists(filepath):
        logger.warning(f"Migration file '{filepath}' not found. Skipping.")
        return

    logger.info(f"Executing migration file: {filepath}")
    with open(filepath, "r") as f:
        content = f.read()

    # Split by semicolon (ignoring comments)
    # Remove multi-line comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove single line comments
    lines = [line for line in content.splitlines() if not line.strip().startswith("--")]
    clean_content = "\n".join(lines)
    
    statements = clean_content.split(";")
    
    async with engine.begin() as conn:
        # Check if we are running on SQLite engine
        db_engine_name = conn.dialect.name
        is_conn_sqlite = (db_engine_name == "sqlite")
        
        for statement in statements:
            stmt = statement.strip()
            if not stmt:
                continue
                
            if is_conn_sqlite:
                stmt = translate_postgres_to_sqlite(stmt).strip()
                if not stmt:
                    continue
            
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                logger.error(f"Migration error executing:\n{stmt}\nError: {e}")
                # For SQLite column alters, ignore if column already exists
                if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                    continue
                raise


async def run_all_migrations():
    """Runs initial schema setup followed by incremental column additions."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 1. Run 001_initial_schema
        await run_migration_file(os.path.join(base_dir, "migrations", "001_initial_schema.sql"))
        # 2. Run 002_add_columns
        await run_migration_file(os.path.join(base_dir, "migrations", "002_add_columns.sql"))
        logger.info("✓ All database migrations executed successfully.")
    except Exception as e:
        logger.error(f"Database migrations failed: {e}")
        raise
