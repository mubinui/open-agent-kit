"""MongoDB-based authentication store for users and API keys."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from passlib.context import CryptContext
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


# Pydantic models
class UserCreate(BaseModel):
    """Model for creating users."""
    username: str
    email: str
    password: str
    role: UserRole = UserRole.USER


class UserResponse(BaseModel):
    """Model for user responses."""
    id: UUID
    username: str
    email: str
    role: UserRole
    active: bool
    created_at: datetime
    last_login_at: Optional[datetime]


class UserDocument(BaseModel):
    """Internal model for user documents."""
    id: UUID
    username: str
    email: str
    password_hash: str
    role: UserRole
    active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class APIKeyCreate(BaseModel):
    """Model for creating API keys."""
    name: str
    user_id: Optional[str] = None
    role: UserRole = UserRole.USER
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """Model for API key responses."""
    id: UUID
    name: str
    key: str  # Only returned on creation
    user_id: Optional[str]
    role: UserRole
    active: bool
    created_at: datetime
    expires_at: Optional[datetime]


class APIKeyInfo(BaseModel):
    """Model for API key info (without the actual key)."""
    id: UUID
    name: str
    user_id: Optional[str]
    role: UserRole
    active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"orc_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage using SHA256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key_hash(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return hashlib.sha256(plain_key.encode()).hexdigest() == hashed_key


class MongoAuthStore:
    """MongoDB-based store for users and API keys."""
    
    _instance: Optional["MongoAuthStore"] = None
    
    def __init__(
        self,
        connection_string: str,
        database_name: str = "orchestration",
    ):
        """Initialize MongoDB auth store.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        self.connection_string = connection_string
        self.database_name = database_name
        
        # Initialize MongoDB client
        self.client: MongoClient = MongoClient(
            connection_string,
            maxPoolSize=10,
            serverSelectionTimeoutMS=5000,
            retryWrites=True,
        )
        
        self.db: Database = self.client[database_name]
        self.users_collection: Collection = self.db["users"]
        self.api_keys_collection: Collection = self.db["api_keys"]
        
        # Create indexes
        self._create_indexes()
        
        logger.info(f"MongoDB auth store initialized for database: {database_name}")
    
    def _create_indexes(self):
        """Create necessary indexes for users and api_keys collections."""
        try:
            # Users indexes
            self.users_collection.create_index("username", unique=True)
            self.users_collection.create_index("email", unique=True)
            self.users_collection.create_index("active")
            
            # API keys indexes
            self.api_keys_collection.create_index("key_hash", unique=True)
            self.api_keys_collection.create_index("active")
            self.api_keys_collection.create_index("user_id")
            self.api_keys_collection.create_index("expires_at")
            
            logger.debug("MongoDB auth indexes created")
        except PyMongoError as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    # User operations
    def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user."""
        user_id = uuid4()
        current_time = datetime.utcnow()
        password_hash = hash_password(user_data.password)
        
        user_doc = {
            "_id": str(user_id),
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "role": user_data.role.value,
            "active": True,
            "created_at": current_time,
            "last_login_at": None,
        }
        
        try:
            self.users_collection.insert_one(user_doc)
            logger.info(f"User created: {user_data.username}")
            
            return UserResponse(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                role=user_data.role,
                active=True,
                created_at=current_time,
                last_login_at=None,
            )
        except DuplicateKeyError:
            raise ValueError("Username or email already exists")
        except PyMongoError as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[UserDocument]:
        """Authenticate a user with username and password."""
        user_doc = self.users_collection.find_one({
            "username": username,
            "active": True,
        })
        
        if not user_doc:
            return None
        
        if not verify_password(password, user_doc["password_hash"]):
            return None
        
        # Update last login
        self.users_collection.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"last_login_at": datetime.utcnow()}}
        )
        
        return UserDocument(
            id=UUID(user_doc["_id"]),
            username=user_doc["username"],
            email=user_doc["email"],
            password_hash=user_doc["password_hash"],
            role=UserRole(user_doc["role"]),
            active=user_doc["active"],
            created_at=user_doc["created_at"],
            last_login_at=user_doc.get("last_login_at"),
        )
    
    def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID."""
        user_doc = self.users_collection.find_one({"_id": str(user_id)})
        
        if not user_doc:
            return None
        
        return UserResponse(
            id=UUID(user_doc["_id"]),
            username=user_doc["username"],
            email=user_doc["email"],
            role=UserRole(user_doc["role"]),
            active=user_doc["active"],
            created_at=user_doc["created_at"],
            last_login_at=user_doc.get("last_login_at"),
        )
    
    def get_active_user(self, user_id: UUID) -> Optional[UserDocument]:
        """Get active user by ID."""
        user_doc = self.users_collection.find_one({
            "_id": str(user_id),
            "active": True,
        })
        
        if not user_doc:
            return None
        
        return UserDocument(
            id=UUID(user_doc["_id"]),
            username=user_doc["username"],
            email=user_doc["email"],
            password_hash=user_doc["password_hash"],
            role=UserRole(user_doc["role"]),
            active=user_doc["active"],
            created_at=user_doc["created_at"],
            last_login_at=user_doc.get("last_login_at"),
        )
    
    # API Key operations
    def create_api_key(self, api_key_data: APIKeyCreate, encrypted_key: str) -> APIKeyResponse:
        """Create a new API key."""
        key_id = uuid4()
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        current_time = datetime.utcnow()
        
        expires_at = None
        if api_key_data.expires_in_days:
            expires_at = current_time + timedelta(days=api_key_data.expires_in_days)
        
        key_doc = {
            "_id": str(key_id),
            "name": api_key_data.name,
            "key_hash": key_hash,
            "encrypted_key": encrypted_key,
            "user_id": api_key_data.user_id,
            "role": api_key_data.role.value,
            "active": True,
            "created_at": current_time,
            "last_used_at": None,
            "expires_at": expires_at,
        }
        
        try:
            self.api_keys_collection.insert_one(key_doc)
            logger.info(f"API key created: {api_key_data.name}")
            
            return APIKeyResponse(
                id=key_id,
                name=api_key_data.name,
                key=api_key,
                user_id=api_key_data.user_id,
                role=api_key_data.role,
                active=True,
                created_at=current_time,
                expires_at=expires_at,
            )
        except PyMongoError as e:
            logger.error(f"Failed to create API key: {e}")
            raise
    
    def get_api_key_by_hash(self, key_hash: str) -> Optional[dict]:
        """Get API key document by hash."""
        key_doc = self.api_keys_collection.find_one({
            "key_hash": key_hash,
            "active": True,
        })
        return key_doc
    
    def update_api_key_last_used(self, key_id: str):
        """Update the last_used_at timestamp for an API key."""
        self.api_keys_collection.update_one(
            {"_id": key_id},
            {"$set": {"last_used_at": datetime.utcnow()}}
        )
    
    def list_api_keys(self, user_id: Optional[str] = None) -> list[APIKeyInfo]:
        """List API keys (without the actual keys)."""
        query = {}
        if user_id:
            query["user_id"] = user_id
        
        keys = list(self.api_keys_collection.find(query))
        
        return [
            APIKeyInfo(
                id=UUID(key["_id"]),
                name=key["name"],
                user_id=key.get("user_id"),
                role=UserRole(key["role"]),
                active=key["active"],
                created_at=key["created_at"],
                last_used_at=key.get("last_used_at"),
                expires_at=key.get("expires_at"),
            )
            for key in keys
        ]
    
    def revoke_api_key(self, api_key_id: UUID) -> bool:
        """Revoke (deactivate) an API key."""
        result = self.api_keys_collection.update_one(
            {"_id": str(api_key_id)},
            {"$set": {"active": False}}
        )
        
        if result.modified_count > 0:
            logger.info(f"API key revoked: {api_key_id}")
            return True
        return False
    
    def rotate_api_key(self, api_key_id: UUID, new_encrypted_key: str) -> Optional[APIKeyResponse]:
        """Rotate an API key (generate new key, keep same metadata)."""
        key_doc = self.api_keys_collection.find_one({"_id": str(api_key_id)})
        
        if not key_doc:
            return None
        
        # Generate new key
        new_api_key = generate_api_key()
        new_key_hash = hash_api_key(new_api_key)
        
        self.api_keys_collection.update_one(
            {"_id": str(api_key_id)},
            {"$set": {
                "key_hash": new_key_hash,
                "encrypted_key": new_encrypted_key,
            }}
        )
        
        logger.info(f"API key rotated: {api_key_id}")
        
        return APIKeyResponse(
            id=api_key_id,
            name=key_doc["name"],
            key=new_api_key,
            user_id=key_doc.get("user_id"),
            role=UserRole(key_doc["role"]),
            active=key_doc["active"],
            created_at=key_doc["created_at"],
            expires_at=key_doc.get("expires_at"),
        )
    
    def health_check(self) -> bool:
        """Check if MongoDB connection is healthy."""
        try:
            self.client.admin.command("ping")
            return True
        except PyMongoError:
            return False


# Global instance management
_mongo_auth_store: Optional[MongoAuthStore] = None


def get_mongo_auth_store() -> Optional[MongoAuthStore]:
    """Get the global MongoDB auth store instance."""
    return _mongo_auth_store


def init_mongo_auth_store(connection_string: str, database_name: str = "orchestration") -> MongoAuthStore:
    """Initialize the global MongoDB auth store."""
    global _mongo_auth_store
    _mongo_auth_store = MongoAuthStore(connection_string, database_name)
    return _mongo_auth_store


def close_mongo_auth_store():
    """Close the MongoDB auth store connection."""
    global _mongo_auth_store
    if _mongo_auth_store:
        _mongo_auth_store.client.close()
        _mongo_auth_store = None
