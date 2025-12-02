#!/usr/bin/env python3
"""
MongoDB initialization script for Orchestration Service.

This script creates the database, collections, and indexes for MongoDB persistence.
It can be run as a standalone script or imported and called programmatically.

Usage:
    python scripts/init_mongodb.py [--connection-string MONGODB_URL] [--database orchestration]
"""

import argparse
import logging
import sys
from typing import Optional

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, OperationFailure

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_user(client: MongoClient, database_name: str, username: str, password: str) -> bool:
    """
    Create MongoDB user with read/write permissions.
    
    Args:
        client: MongoDB client
        database_name: Name of the database
        username: Username to create
        password: Password for the user
        
    Returns:
        True if user was created, False if already exists
    """
    try:
        db = client[database_name]
        db.command(
            "createUser",
            username,
            pwd=password,
            roles=[{"role": "readWrite", "db": database_name}]
        )
        logger.info(f"Created user: {username}")
        return True
    except OperationFailure as e:
        if "already exists" in str(e):
            logger.warning(f"User {username} already exists")
            return False
        else:
            logger.error(f"Failed to create user: {e}")
            raise


def create_collections(client: MongoClient, database_name: str) -> None:
    """
    Create MongoDB collections.
    
    Args:
        client: MongoDB client
        database_name: Name of the database
    """
    db = client[database_name]
    
    collections = ['sessions', 'messages', 'transcripts']
    
    logger.info("\nCreating collections...")
    
    for collection_name in collections:
        try:
            db.create_collection(collection_name)
            logger.info(f"Created {collection_name} collection")
        except CollectionInvalid:
            logger.warning(f"{collection_name} collection already exists")


def create_indexes(client: MongoClient, database_name: str) -> None:
    """
    Create MongoDB indexes including TTL indexes.
    
    Args:
        client: MongoDB client
        database_name: Name of the database
    """
    db = client[database_name]
    
    logger.info("\nCreating indexes...")
    
    # Sessions collection indexes
    logger.info("Creating indexes for sessions collection...")
    
    sessions = db['sessions']
    
    # TTL index: expire sessions after 24 hours of inactivity
    try:
        sessions.create_index(
            [("updated_at", ASCENDING)],
            name="ttl_updated_at",
            expireAfterSeconds=86400
        )
        logger.info("Created TTL index on sessions.updated_at (24 hour expiration)")
    except Exception as e:
        logger.warning(f"TTL index on sessions.updated_at: {e}")
    
    # Compound index for active sessions query
    try:
        sessions.create_index(
            [("active", ASCENDING), ("updated_at", DESCENDING)],
            name="active_updated_idx"
        )
        logger.info("Created compound index on sessions (active, updated_at)")
    except Exception as e:
        logger.warning(f"Compound index on sessions: {e}")
    
    # Messages collection indexes
    logger.info("\nCreating indexes for messages collection...")
    
    messages = db['messages']
    
    # TTL index: expire messages after 7 days
    try:
        messages.create_index(
            [("created_at", ASCENDING)],
            name="ttl_created_at",
            expireAfterSeconds=604800
        )
        logger.info("Created TTL index on messages.created_at (7 day expiration)")
    except Exception as e:
        logger.warning(f"TTL index on messages.created_at: {e}")
    
    # Compound index for session queries
    try:
        messages.create_index(
            [("session_id", ASCENDING), ("timestamp", ASCENDING)],
            name="session_timestamp_idx"
        )
        logger.info("Created compound index on messages (session_id, timestamp)")
    except Exception as e:
        logger.warning(f"Compound index on messages: {e}")
    
    # Index for agent notes queries
    try:
        messages.create_index(
            [("session_id", ASCENDING), ("is_agent_note", ASCENDING)],
            name="session_agent_note_idx"
        )
        logger.info("Created compound index on messages (session_id, is_agent_note)")
    except Exception as e:
        logger.warning(f"Compound index on messages (agent notes): {e}")
    
    # Transcripts collection indexes
    logger.info("\nCreating indexes for transcripts collection...")
    
    transcripts = db['transcripts']
    
    # TTL index: expire transcripts after 30 days
    try:
        transcripts.create_index(
            [("created_at", ASCENDING)],
            name="ttl_created_at",
            expireAfterSeconds=2592000
        )
        logger.info("Created TTL index on transcripts.created_at (30 day expiration)")
    except Exception as e:
        logger.warning(f"TTL index on transcripts.created_at: {e}")
    
    # Index for session lookup
    try:
        transcripts.create_index(
            [("session_id", ASCENDING)],
            name="session_id_idx"
        )
        logger.info("Created index on transcripts.session_id")
    except Exception as e:
        logger.warning(f"Index on transcripts.session_id: {e}")


def display_statistics(client: MongoClient, database_name: str) -> None:
    """
    Display collection statistics and indexes.
    
    Args:
        client: MongoDB client
        database_name: Name of the database
    """
    db = client[database_name]
    
    logger.info("\n=== Collection Statistics ===")
    logger.info(f"Sessions: {db.sessions.count_documents({})}")
    logger.info(f"Messages: {db.messages.count_documents({})}")
    logger.info(f"Transcripts: {db.transcripts.count_documents({})}")
    
    logger.info("\n=== Indexes ===")
    
    logger.info("\nSessions indexes:")
    for idx in db.sessions.list_indexes():
        logger.info(f"  - {idx['name']}: {idx['key']}")
    
    logger.info("\nMessages indexes:")
    for idx in db.messages.list_indexes():
        logger.info(f"  - {idx['name']}: {idx['key']}")
    
    logger.info("\nTranscripts indexes:")
    for idx in db.transcripts.list_indexes():
        logger.info(f"  - {idx['name']}: {idx['key']}")


def initialize_mongodb(
    connection_string: str,
    database_name: str = "orchestration",
    create_user_account: bool = False,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> bool:
    """
    Initialize MongoDB for Orchestration Service.
    
    Args:
        connection_string: MongoDB connection string
        database_name: Name of the database to create
        create_user_account: Whether to create a user account
        username: Username for the user account
        password: Password for the user account
        
    Returns:
        True if initialization was successful
    """
    try:
        logger.info(f"Connecting to MongoDB: {connection_string.split('@')[-1]}")
        
        client = MongoClient(connection_string)
        
        # Test connection
        client.admin.command('ping')
        logger.info("Connected to MongoDB")
        
        # Create user if requested
        if create_user_account:
            if not username or not password:
                logger.error("Username and password required to create user")
                return False
            create_user(client, database_name, username, password)
        
        # Create collections
        create_collections(client, database_name)
        
        # Create indexes
        create_indexes(client, database_name)
        
        # Display statistics
        display_statistics(client, database_name)
        
        logger.info("\nMongoDB initialization complete!")
        logger.info("\nConnection string format:")
        logger.info(f"mongodb://username:password@host:port/{database_name}")
        logger.info("\nSet MONGODB_URL environment variable to use MongoDB persistence.")
        
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"MongoDB initialization failed: {e}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Initialize MongoDB for Orchestration Service"
    )
    parser.add_argument(
        "--connection-string",
        default="mongodb://localhost:27017",
        help="MongoDB connection string (default: mongodb://localhost:27017)"
    )
    parser.add_argument(
        "--database",
        default="orchestration",
        help="Database name (default: orchestration)"
    )
    parser.add_argument(
        "--create-user",
        action="store_true",
        help="Create a user account"
    )
    parser.add_argument(
        "--username",
        default="orchestrator",
        help="Username for the user account (default: orchestrator)"
    )
    parser.add_argument(
        "--password",
        help="Password for the user account"
    )
    
    args = parser.parse_args()
    
    # If creating user, password is required
    if args.create_user and not args.password:
        logger.error("--password is required when --create-user is specified")
        sys.exit(1)
    
    success = initialize_mongodb(
        connection_string=args.connection_string,
        database_name=args.database,
        create_user_account=args.create_user,
        username=args.username if args.create_user else None,
        password=args.password if args.create_user else None,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
