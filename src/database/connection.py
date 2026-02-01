"""
Database connection module for SQLite.
"""
from functools import lru_cache
from langchain_community.utilities import SQLDatabase
from src.config import Config


@lru_cache(maxsize=1)
def get_database() -> SQLDatabase:
    """
    Get a cached SQLDatabase connection.
    
    Uses LangChain's SQLDatabase utility for seamless integration
    with SQL agents.
    
    Returns:
        SQLDatabase: Connected database instance.
    """
    db_uri = Config.get_database_uri()
    return SQLDatabase.from_uri(db_uri)


def get_db_info() -> dict:
    """
    Get database metadata and information.
    
    Returns:
        dict: Dictionary containing:
            - dialect: Database dialect (sqlite)
            - tables: List of table names
            - schema: Full schema information
    """
    db = get_database()
    tables = db.get_usable_table_names()
    
    return {
        "dialect": db.dialect,
        "tables": tables,
        "schema": db.get_table_info(table_names=tables),
    }


def run_query(query: str) -> str:
    """
    Execute a SQL query against the database.
    
    Args:
        query: SQL query string to execute.
        
    Returns:
        str: Query results as a string.
        
    Raises:
        Exception: If the query fails.
    """
    db = get_database()
    return db.run(query)
