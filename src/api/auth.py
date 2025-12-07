"""Authentication and authorization module for the Orchestration Service."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.config.settings import get_settings
from src.infrastructure.secrets import get_global_credential_manager

logger = structlog.get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme - auto_error=False allows optional authentication
security = HTTPBearer(auto_error=False)


# Import MongoDB auth store types
from src.infrastructure.database.mongo_auth_store import (
    APIKeyCreate,
    APIKeyInfo,
    APIKeyResponse,
    MongoAuthStore,
    UserCreate,
    UserDocument,
    UserResponse,
    UserRole,
    generate_api_key,
    get_mongo_auth_store,
    hash_api_key,
    init_mongo_auth_store,
)


class Token(BaseModel):
    """Model for JWT tokens."""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Model for token data."""
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None


class CurrentUser(BaseModel):
    """Model for current authenticated user."""
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    api_key_id: Optional[UUID] = None
    role: UserRole
    auth_method: str  # "api_key", "jwt", or "development"


# Re-export for backwards compatibility
__all__ = [
    "APIKeyCreate",
    "APIKeyInfo", 
    "APIKeyResponse",
    "CurrentUser",
    "Token",
    "TokenData",
    "UserCreate",
    "UserResponse",
    "UserRole",
    "create_access_token",
    "get_current_user",
    "require_admin",
    "require_readonly",
    "require_user",
    "verify_token",
    "APIKeyManager",
    "UserManager",
]


# Use global credential manager for encryption
credential_manager = get_global_credential_manager()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.security.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.security.secret_key, 
        algorithm=settings.security.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, 
            settings.security.secret_key, 
            algorithms=[settings.security.algorithm]
        )
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(
            user_id=UUID(user_id) if user_id else None,
            username=username,
            role=UserRole(role) if role else None
        )
        return token_data
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _get_auth_store() -> Optional[MongoAuthStore]:
    """Get or initialize the MongoDB auth store."""
    store = get_mongo_auth_store()
    if store is None:
        settings = get_settings()
        if settings.memory.mongodb_url:
            try:
                store = init_mongo_auth_store(
                    settings.memory.mongodb_url,
                    settings.memory.mongodb_database
                )
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB auth store: {e}")
                return None
    return store


async def authenticate_api_key(
    credentials: HTTPAuthorizationCredentials,
) -> CurrentUser:
    """Authenticate using API key."""
    if not credentials.credentials.startswith("orc_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    store = _get_auth_store()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available (MongoDB not configured)",
        )
    
    # Hash the provided key to compare with stored hash
    key_hash = hash_api_key(credentials.credentials)
    
    # Find matching API key in database
    api_key_doc = store.get_api_key_by_hash(key_hash)
    if not api_key_doc:
        logger.warning("api_key_authentication_failed", key_prefix=credentials.credentials[:10])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if key is expired
    if api_key_doc.get("expires_at") and api_key_doc["expires_at"] < datetime.utcnow():
        logger.warning("api_key_expired", api_key_id=api_key_doc["_id"])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last used timestamp
    store.update_api_key_last_used(api_key_doc["_id"])
    
    logger.info("api_key_authentication_successful", 
               api_key_id=api_key_doc["_id"], 
               role=api_key_doc["role"])
    
    return CurrentUser(
        api_key_id=UUID(api_key_doc["_id"]),
        user_id=UUID(api_key_doc["user_id"]) if api_key_doc.get("user_id") else None,
        role=UserRole(api_key_doc["role"]),
        auth_method="api_key"
    )


async def authenticate_jwt(
    credentials: HTTPAuthorizationCredentials,
) -> CurrentUser:
    """Authenticate using JWT token."""
    token_data = verify_token(credentials.credentials)
    
    if not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    store = _get_auth_store()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available (MongoDB not configured)",
        )
    
    user = store.get_active_user(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("jwt_authentication_successful", 
               user_id=str(user.id), 
               username=user.username,
               role=user.role.value)
    
    return CurrentUser(
        user_id=user.id,
        username=user.username,
        role=user.role,
        auth_method="jwt"
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Get current authenticated user (supports both API key and JWT)."""
    # In development mode, allow access without authentication
    settings = get_settings()
    if settings.app.environment == "development" and credentials is None:
        logger.warning("Development mode: allowing unauthenticated access")
        return CurrentUser(
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            username="development",
            role=UserRole.ADMIN,
            auth_method="development"
        )
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Try API key authentication first
    if credentials.credentials.startswith("orc_"):
        return await authenticate_api_key(credentials)
    else:
        # Try JWT authentication
        return await authenticate_jwt(credentials)


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        # Admin can access everything
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Check specific role requirements
        if required_role == UserRole.ADMIN and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        elif required_role == UserRole.USER and current_user.role == UserRole.READONLY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User access required"
            )
        
        return current_user
    
    return role_checker


# Convenience dependencies
require_admin = require_role(UserRole.ADMIN)
require_user = require_role(UserRole.USER)
require_readonly = require_role(UserRole.READONLY)


class APIKeyManager:
    """Manager class for API key operations using MongoDB."""
    
    def __init__(self, store: Optional[MongoAuthStore] = None):
        self.store = store or _get_auth_store()
        if not self.store:
            raise ValueError("MongoDB auth store not available")
    
    def create_api_key(self, api_key_data: APIKeyCreate) -> APIKeyResponse:
        """Create a new API key."""
        api_key = generate_api_key()
        encrypted_key = credential_manager.encrypt_credential(api_key)
        
        # Create the key (store will generate its own key)
        response = self.store.create_api_key(api_key_data, encrypted_key)
        
        # Override with the generated key for return
        return APIKeyResponse(
            id=response.id,
            name=response.name,
            key=api_key,
            user_id=response.user_id,
            role=response.role,
            active=response.active,
            created_at=response.created_at,
            expires_at=response.expires_at,
        )
    
    def list_api_keys(self, user_id: Optional[str] = None) -> list[APIKeyInfo]:
        """List API keys (without the actual keys)."""
        return self.store.list_api_keys(user_id)
    
    def revoke_api_key(self, api_key_id: UUID) -> bool:
        """Revoke (deactivate) an API key."""
        return self.store.revoke_api_key(api_key_id)
    
    def rotate_api_key(self, api_key_id: UUID) -> Optional[APIKeyResponse]:
        """Rotate an API key (generate new key, keep same metadata)."""
        new_key = generate_api_key()
        new_encrypted_key = credential_manager.encrypt_credential(new_key)
        return self.store.rotate_api_key(api_key_id, new_encrypted_key)


class UserManager:
    """Manager class for user operations using MongoDB."""
    
    def __init__(self, store: Optional[MongoAuthStore] = None):
        self.store = store or _get_auth_store()
        if not self.store:
            raise ValueError("MongoDB auth store not available")
    
    def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user."""
        try:
            return self.store.create_user(user_data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    def authenticate_user(self, username: str, password: str) -> Optional[UserDocument]:
        """Authenticate a user with username and password."""
        return self.store.authenticate_user(username, password)
    
    def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID."""
        return self.store.get_user(user_id)
