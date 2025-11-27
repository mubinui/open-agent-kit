#!/usr/bin/env python3
"""Script to create a test user for the Orchestration Service."""

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.auth import User, UserRole, AuthBase
import hashlib
from src.config.settings import get_settings
from uuid import uuid4
from datetime import datetime

async def create_test_user():
    """Create a test user in the database."""
    import os
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "postgresql://orchestrator:orchestrator_pass@localhost:5432/orchestration")
    
    print(f"Using database: {database_url}")
    
    # Create database engine
    engine = create_engine(database_url)
    
    # Create tables if they don't exist
    AuthBase.metadata.create_all(engine)
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("✓ Test user 'admin' already exists")
            print(f"  User ID: {existing_user.id}")
            print(f"  Email: {existing_user.email}")
            print(f"  Role: {existing_user.role.value}")
            return
        
        # Create test user
        password = "admin123"
        # Use a simple hash for testing (in production, use proper bcrypt)
        password_hash = "$2b$12$" + hashlib.sha256(password.encode()).hexdigest()[:50]
        
        user = User(
            id=uuid4(),
            username="admin",
            email="admin@example.com",
            password_hash=password_hash,
            role=UserRole.ADMIN,
            active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print("✓ Test user created successfully!")
        print(f"  Username: admin")
        print(f"  Password: admin123")
        print(f"  Email: admin@example.com")
        print(f"  Role: {user.role.value}")
        print(f"  User ID: {user.id}")
        print("\nYou can now get a token with:")
        print("  curl -X POST http://localhost:8000/api/v1/auth/token \\")
        print("    -H 'Content-Type: application/x-www-form-urlencoded' \\")
        print("    -d 'username=admin&password=admin123'")
        
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_test_user())
