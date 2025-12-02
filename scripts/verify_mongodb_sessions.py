#!/usr/bin/env python3
"""Verify MongoDB session storage and debug session creation."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from src.config.settings import get_settings


def verify_mongodb_connection():
    """Verify MongoDB connection and list collections."""
    settings = get_settings()
    
    print(f"\n{'='*60}")
    print("MongoDB Configuration Check")
    print(f"{'='*60}")
    print(f"MONGODB_URL: {settings.memory.mongodb_url[:40]}..." if settings.memory.mongodb_url else "MONGODB_URL: NOT SET")
    print(f"MONGODB_DATABASE: {settings.memory.mongodb_database}")
    print(f"MEMORY_BACKEND: {settings.memory.backend}")
    
    if not settings.memory.mongodb_url:
        print("\nERROR: MONGODB_URL is not configured in .env")
        print("Please set MONGODB_URL in your .env file")
        return False
    
    try:
        client = MongoClient(
            settings.memory.mongodb_url,
            serverSelectionTimeoutMS=5000
        )
        db = client[settings.memory.mongodb_database]
        
        # Test connection
        client.admin.command('ping')
        print("\nMongoDB connection successful")
        
        # List collections
        collections = db.list_collection_names()
        print(f"\nCollections in '{settings.memory.mongodb_database}' database:")
        if collections:
            for coll in collections:
                count = db[coll].count_documents({})
                print(f"   - {coll}: {count} documents")
        else:
            print("   (no collections found)")
        
        # Check sessions collection
        if "sessions" in collections:
            session_count = db.sessions.count_documents({})
            print(f"\nSessions collection: {session_count} documents")
            
            if session_count > 0:
                print("\nSample sessions:")
                sessions = list(db.sessions.find().limit(5))
                for i, session in enumerate(sessions, 1):
                    print(f"   {i}. ID: {session.get('_id')}")
                    print(f"      Active: {session.get('active')}")
                    print(f"      Created: {session.get('created_at')}")
                    print(f"      Metadata: {session.get('metadata', {})}")
            else:
                print("\nNo sessions found in database")
                print("\nTesting write permissions...")
                
                # Test write
                test_doc = {
                    "_id": "test-session-verify",
                    "turn_count": 0,
                    "active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "metadata": {"test": True}
                }
                result = db.sessions.insert_one(test_doc)
                print(f"Write test successful: inserted {result.inserted_id}")
                
                # Clean up
                db.sessions.delete_one({"_id": "test-session-verify"})
                print("Test document cleaned up")
        else:
            print("\nERROR: 'sessions' collection not found!")
            print("Run: python scripts/init_mongodb.py to create collections")
            return False
            
        # Check indexes
        print("\nIndexes on sessions collection:")
        indexes = list(db.sessions.list_indexes())
        for idx in indexes:
            print(f"   - {idx['name']}: {idx.get('key', {})}")
            if 'expireAfterSeconds' in idx:
                print(f"     TTL: {idx['expireAfterSeconds']} seconds")
        
        client.close()
        return True
        
    except ConnectionFailure as e:
        print(f"\nMongoDB connection failed: {e}")
        return False
    except Exception as e:
        print(f"\nMongoDB verification error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_store():
    """Test the MongoDBConversationStore directly."""
    from src.infrastructure.database.mongo_store import MongoDBConversationStore
    from src.api.session_manager import SessionManager
    from uuid import uuid4
    
    settings = get_settings()
    
    print(f"\n{'='*60}")
    print("SessionManager Test")
    print(f"{'='*60}")
    
    try:
        # Initialize session manager
        print("\nInitializing SessionManager...")
        session_manager = SessionManager()
        
        print(f"   - MongoDB store: {'configured' if session_manager._mongo_store else 'not available'}")
        print(f"   - PostgreSQL store: {'configured' if session_manager._postgres_store else 'not available'}")
        print(f"   - Default store: {type(session_manager.default_conversation_store).__name__}")
        
        if not session_manager._mongo_store:
            print("\nERROR: MongoDB store not initialized!")
            print("Check MONGODB_URL in .env and restart")
            return False
        
        # Create a test session via SessionManager
        print("\nTesting session creation via SessionManager...")
        
        session_state = await session_manager.create_session(
            workflow_id="simple_assistant",
            user_id="test-user-verify",
            metadata={"test": True, "purpose": "verification"}
        )
        
        session_id = session_state.session_id
        print(f"Session created: {session_id}")
        print(f"   - Active: {session_state.active}")
        print(f"   - Turn count: {session_state.turn_count}")
        print(f"   - Metadata: {session_state.metadata}")
        
        # Retrieve the session
        print(f"\nRetrieving session {session_id}...")
        retrieved = await session_manager.get_session(session_id)
        
        if retrieved:
            print(f"Session retrieved successfully")
            print(f"   - Active: {retrieved.active}")
            print(f"   - Metadata: {retrieved.metadata}")
        else:
            print(f"Failed to retrieve session!")
            return False
        
        # Verify in MongoDB directly
        print(f"\nVerifying in MongoDB directly...")
        client = MongoClient(settings.memory.mongodb_url)
        db = client[settings.memory.mongodb_database]
        
        mongo_doc = db.sessions.find_one({"_id": str(session_id)})
        if mongo_doc:
            print(f"Session found in MongoDB")
            print(f"   - Document ID: {mongo_doc.get('_id')}")
            print(f"   - Turn count: {mongo_doc.get('turn_count')}")
            print(f"   - Active: {mongo_doc.get('active')}")
        else:
            print(f"Session NOT found in MongoDB!")
            print(f"   - This indicates sessions are not persisting to MongoDB")
            client.close()
            return False
        
        # Clean up
        print(f"\nCleaning up test session...")
        await session_manager.delete_session(session_id)
        print(f"Test session deleted")
        
        # Verify deletion
        deleted_doc = db.sessions.find_one({"_id": str(session_id)})
        if deleted_doc:
            print(f"Warning: Session still exists in MongoDB after deletion")
        else:
            print(f"Session successfully removed from MongoDB")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\nSession store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run MongoDB verification checks."""
    print(f"\n{'='*60}")
    print("MongoDB Session Storage Verification")
    print(f"{'='*60}\n")
    
    # Check connection and collections
    print("Step 1: Verifying MongoDB connection...")
    conn_ok = verify_mongodb_connection()
    
    if not conn_ok:
        print("\nMongoDB connection verification failed")
        print("\nTroubleshooting steps:")
        print("1. Ensure MongoDB is running: docker ps | grep mongodb")
        print("2. Check .env file has MONGODB_URL set")
        print("3. Run: export $(cat .env | grep -v '^#' | xargs)")
        print("4. Verify connection: mongosh 'mongodb://orchestrator:orchestrator_pass@localhost:27017/orchestration'")
        return 1
    
    # Test session store
    print("\nStep 2: Testing SessionManager and session storage...")
    store_ok = await test_session_store()
    
    if store_ok:
        print(f"\n{'='*60}")
        print("ALL TESTS PASSED")
        print(f"{'='*60}")
        print("\nMongoDB session storage is working correctly!")
        print("\nNext steps:")
        print("1. Create sessions via API: POST /api/v1/sessions")
        print("2. Check sessions in MongoDB: mongosh and run 'db.sessions.find()'")
        print("3. Sessions will auto-expire after 24 hours (TTL index)")
        return 0
    else:
        print(f"\n{'='*60}")
        print("SESSION STORAGE TEST FAILED")
        print(f"{'='*60}")
        print("\nPlease check the errors above and:")
        print("1. Ensure .env has MEMORY_BACKEND=mongodb")
        print("2. Restart the application after fixing configuration")
        print("3. Check application logs for MongoDB initialization errors")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
