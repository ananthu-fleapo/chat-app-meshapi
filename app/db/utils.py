import structlog
from sqlalchemy.dialects import postgresql

logger = structlog.get_logger()

def debug_query(query):
    """
    Log the compiled SQL of a SQLAlchemy query with literal binds.
    Useful for debugging issues with complex queries.
    """
    try:
        compiled = query.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        logger.info("sql_query", query=str(compiled))
    except Exception as e:
        logger.warning("query_compile_failed", error=str(e))
