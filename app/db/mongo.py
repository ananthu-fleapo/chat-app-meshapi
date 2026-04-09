"""
MongoDB client — Motor (async) driver.

Collections
-----------
request_logs    Every HTTP request + response captured by RequestLoggingMiddleware.
                TTL index on `ts` recommended (e.g. 30 days) — create in Atlas UI
                or via: db.request_logs.createIndex({"ts":1},{expireAfterSeconds:2592000})

usage_events    Dual-write alongside Postgres usage_events table.
                Immune to schema migrations — stores arbitrary provider fields.
                Postgres remains source of truth until migration is confirmed stable.

balance_failures  Failed balance deductions with full context for manual recovery.
                  These must be reviewed and replayed — they represent unbilled usage.
"""

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = structlog.get_logger()

_client: AsyncIOMotorClient | None = None
_db_name: str = "routersvc"


async def init_mongo(url: str, database: str = "routersvc") -> None:
    """
    Connect to MongoDB Atlas and verify reachability.
    Called once from app lifespan. Raises on connection failure.
    """
    global _client, _db_name
    _db_name = database
    _client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5_000)
    # Ping to verify credentials + network before serving traffic
    await _client.admin.command("ping")
    logger.info("mongo_ready", database=database)


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Return the application database. Raises if init_mongo() was not called."""
    if _client is None:
        raise RuntimeError("MongoDB not initialized — call init_mongo() first")
    return _client[_db_name]


def is_mongo_available() -> bool:
    """True when MongoDB has been successfully initialized."""
    return _client is not None


async def close_mongo() -> None:
    """Close the Motor connection pool. Called from app lifespan shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("mongo_closed")
