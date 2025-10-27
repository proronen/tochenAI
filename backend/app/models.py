import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    quota: int = Field(default=1000)  # LLM request quota
    usage_count: int = Field(default=0)  # Current usage count
    business_description: str | None = Field(default=None, max_length=2000)  # Client business description
    client_avatars: str | None = Field(default=None, max_length=2000)  # Client avatars description


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)
    quota: int | None = None
    usage_count: int | None = None
    business_description: str | None = None
    client_avatars: str | None = None


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    business_description: str | None = Field(default=None, max_length=2000)
    client_avatars: str | None = Field(default=None, max_length=2000)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    __tablename__ = "toc_users"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: Optional[int] = None


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="toc_users.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


class PostStatus(str, Enum):
    SCHEDULED = "scheduled"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"


class PostBase(SQLModel):
    media_url: str = Field(max_length=512)
    text: str = Field(max_length=1024)
    hashtags: str = Field(default="", max_length=512)  # comma-separated
    scheduled_time: datetime
    to_facebook: bool = Field(default=True)
    to_instagram: bool = Field(default=True)
    to_tiktok: bool = Field(default=True)
    
    # Status and timing
    status: PostStatus = Field(default=PostStatus.SCHEDULED)
    posted_at: datetime | None = None
    
    # Platform-specific IDs (for tracking)
    facebook_post_id: str | None = None
    instagram_post_id: str | None = None
    tiktok_post_id: str | None = None
    
    # Performance metrics (updated after posting)
    likes: int = Field(default=0)
    comments: int = Field(default=0)
    shares: int = Field(default=0)
    views: int = Field(default=0)
    engagement_rate: float = Field(default=0.0)
    last_updated: datetime | None = None


class PostCreate(PostBase):
    pass


class PostUpdate(SQLModel):
    media_url: str | None = None
    text: str | None = None
    hashtags: str | None = None
    scheduled_time: datetime | None = None
    to_facebook: bool | None = None
    to_instagram: bool | None = None
    to_tiktok: bool | None = None
    status: PostStatus | None = None
    posted_at: datetime | None = None
    facebook_post_id: str | None = None
    instagram_post_id: str | None = None
    tiktok_post_id: str | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    views: int | None = None
    engagement_rate: float | None = None
    last_updated: datetime | None = None


class Post(PostBase, table=True):
    __tablename__ = "posts"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="toc_users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    owner: User | None = Relationship(back_populates=None)


class PostPublic(PostBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PostsPublic(SQLModel):
    data: List[PostPublic]
    count: int


class SocialAccountBase(SQLModel):
    platform: str = Field(max_length=32)  # facebook, instagram, tiktok
    access_token: str = Field(max_length=1024)
    refresh_token: Optional[str] = Field(default=None, max_length=1024)
    expires_at: Optional[datetime] = None
    account_id: str = Field(max_length=128)
    account_name: Optional[str] = Field(default=None, max_length=255)


class SocialAccountCreate(SocialAccountBase):
    pass


class SocialAccountUpdate(SQLModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    account_name: Optional[str] = None


class SocialAccount(SocialAccountBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="toc_users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user: User | None = Relationship(back_populates=None)


class SocialAccountPublic(SocialAccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SocialAccountsPublic(SQLModel):
    data: List[SocialAccountPublic]
    count: int


class LLMUsageBase(SQLModel):
    provider: str = Field(max_length=32)  # openai, anthropic, etc.
    model: str = Field(max_length=64)  # gpt-4, claude-3, etc.
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    request_type: str = Field(max_length=64)  # post_generation, hashtag_generation, etc.
    success: bool = Field(default=True)
    error_message: str | None = Field(default=None, max_length=512)


class LLMUsageCreate(LLMUsageBase):
    pass


class LLMUsage(LLMUsageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="toc_users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user: User | None = Relationship(back_populates=None)


class LLMUsagePublic(LLMUsageBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class LLMUsageSummary(SQLModel):
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    requests_by_provider: dict[str, int]
    requests_by_type: dict[str, int]
