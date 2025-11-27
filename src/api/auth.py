"""Authentication and authorization module for the Orchestration Service."""

import hashlib
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.infrastructure.database.connection import get_db
from src.infrastructure.secrets import get_global_credential_manager

logger = structlog.get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme - auto_error=False allows optional authentication
security = HTTPBearer(auto_error=False)

# Base for auth models
AuthBase = declarative_base()


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class APIKey(AuthBase):
    """Database model for API keys."""
    
    __tablename__ = "api_keys"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    encrypted_key = Column(Text, nullable=False)  # Store encrypted version for rotation
    user_id = Column(String(255), nullable=True)  # Optional user association
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class User(AuthBase):
    """Database model for users (for JWT authentication)."""
    
    __tablename__ = "users"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


# Pydantic models
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
    auth_method: str  # "api_key" or "jwt"


# Use global credential manager for encryption
credential_manager = get_global_credential_manager()


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
    # Use SHA256 for API keys since they're already random
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return hashlib.sha256(plain_key.encode()).hexdigest() == hashed_key


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


async def get_api_key_from_db(db: Session, key_hash: str) -> Optional[APIKey]:
    """Get API key from database by hash."""
    return db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.active == True
    ).first()


async def get_user_from_db(db: Session, user_id: UUID) -> Optional[User]:
    """Get user from database by ID."""
    return db.query(User).filter(
        User.id == user_id,
        User.active == True
    ).first()


async def authenticate_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """Authenticate using API key."""
    if not credentials.credentials.startswith("orc_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Hash the provided key to compare with stored hash
    key_hash = hash_api_key(credentials.credentials)
    
    # Find matching API key in database
    api_key = await get_api_key_from_db(db, key_hash)
    if not api_key:
        logger.warning("api_key_authentication_failed", key_prefix=credentials.credentials[:10])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if key is expired
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        logger.warning("api_key_expired", api_key_id=str(api_key.id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last used timestamp
    api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    logger.info("api_key_authentication_successful", 
               api_key_id=str(api_key.id), 
               role=api_key.role.value)
    
    return CurrentUser(
        api_key_id=api_key.id,
        user_id=UUID(api_key.user_id) if api_key.user_id else None,
        role=api_key.role,
        auth_method="api_key"
    )


async def authenticate_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """Authenticate using JWT token."""
    token_data = verify_token(credentials.credentials)
    
    if not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user_from_db(db, token_data.user_id)
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
    db: Optional[Session] = Depends(get_db)
) -> CurrentUser:
    """Get current authenticated user (supports both API key and JWT)."""
    # In development mode, allow access without authentication
    settings = get_settings()
    if settings.app.environment == "development" and credentials is None:
        logger.warning("Development mode: allowing unauthenticated access")
        return CurrentUser(
            user_id="00000000-0000-0000-0000-000000000000",  # Valid UUID for dev mode
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
    
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )
    
    # Try API key authentication first
    if credentials.credentials.startswith("orc_"):
        return await authenticate_api_key(credentials, db)
    else:
        # Try JWT authentication
        return await authenticate_jwt(credentials, db)


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""
    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
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
    """Manager class for API key operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_api_key(self, api_key_data: APIKeyCreate) -> APIKeyResponse:
        """Create a new API key."""
        # Generate the actual key
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        
        # Calculate expiration
        expires_at = None
        if api_key_data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=api_key_data.expires_in_days)
        
        # Encrypt the key for storage (for rotation purposes)
        encrypted_key = credential_manager.encrypt_credential(api_key)
        
        # Create database record
        db_api_key = APIKey(
            name=api_key_data.name,
            key_hash=key_hash,
            encrypted_key=encrypted_key,
            user_id=api_key_data.user_id,
            role=api_key_data.role,
            expires_at=expires_at
        )
        
        self.db.add(db_api_key)
        self.db.commit()
        self.db.refresh(db_api_key)
        
        logger.info("api_key_created", 
                   api_key_id=str(db_api_key.id),
                   name=api_key_data.name,
                   role=api_key_data.role.value)
        
        return APIKeyResponse(
            id=db_api_key.id,
            name=db_api_key.name,
            key=api_key,  # Only returned on creation
            user_id=db_api_key.user_id,
            role=db_api_key.role,
            active=db_api_key.active,
            created_at=db_api_key.created_at,
            expires_at=db_api_key.expires_at
        )
    
    def list_api_keys(self, user_id: Optional[str] = None) -> list[APIKeyInfo]:
        """List API keys (without the actual keys)."""
        query = self.db.query(APIKey)
        if user_id:
            query = query.filter(APIKey.user_id == user_id)
        
        api_keys = query.all()
        return [
            APIKeyInfo(
                id=key.id,
                name=key.name,
                user_id=key.user_id,
                role=key.role,
                active=key.active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at
            )
            for key in api_keys
        ]
    
    def revoke_api_key(self, api_key_id: UUID) -> bool:
        """Revoke (deactivate) an API key."""
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if not api_key:
            return False
        
        api_key.active = False
        self.db.commit()
        
        logger.info("api_key_revoked", api_key_id=str(api_key_id))
        return True
    
    def rotate_api_key(self, api_key_id: UUID) -> Optional[APIKeyResponse]:
        """Rotate an API key (generate new key, keep same metadata)."""
        api_key = self.db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if not api_key:
            return None
        
        # Generate new key
        new_key = generate_api_key()
        new_key_hash = hash_api_key(new_key)
        new_encrypted_key = credential_manager.encrypt_credential(new_key)
        
        # Update database record
        api_key.key_hash = new_key_hash
        api_key.encrypted_key = new_encrypted_key
        self.db.commit()
        
        logger.info("api_key_rotated", api_key_id=str(api_key_id))
        
        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key=new_key,  # Return new key
            user_id=api_key.user_id,
            role=api_key.role,
            active=api_key.active,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at
        )


class UserManager:
    """Manager class for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user."""
        # Check if username or email already exists
        existing_user = self.db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Create database record
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info("user_created", 
                   user_id=str(db_user.id),
                   username=user_data.username,
                   role=user_data.role.value)
        
        return UserResponse(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            role=db_user.role,
            active=db_user.active,
            created_at=db_user.created_at,
            last_login_at=db_user.last_login_at
        )
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        user = self.db.query(User).filter(
            User.username == username,
            User.active == True
        ).first()
        
        if not user or not verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            active=user.active,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )