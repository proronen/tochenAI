import uuid
from typing import Any
from datetime import datetime

from sqlmodel import Session, select, func

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate, Post, PostCreate, PostUpdate, LLMUsage, LLMUsageCreate, LLMUsageSummary


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def increment_user_usage(*, session: Session, user_id: uuid.UUID) -> bool:
    """Increment the usage count for a user"""
    db_user = session.get(User, user_id)
    if not db_user:
        return False
    db_user.usage_count += 1
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return True


def check_user_quota(*, session: Session, user_id: uuid.UUID) -> bool:
    """Check if user has quota remaining (superusers have unlimited quota)"""
    db_user = session.get(User, user_id)
    if not db_user:
        return False
    if db_user.is_superuser:
        return True
    return db_user.usage_count < db_user.quota


def get_user_quota_info(*, session: Session, user_id: uuid.UUID) -> dict[str, Any] | None:
    """Get user's quota information"""
    db_user = session.get(User, user_id)
    if not db_user:
        return None
    return {
        "quota": db_user.quota,
        "usage_count": db_user.usage_count,
        "remaining": db_user.quota - db_user.usage_count if not db_user.is_superuser else "unlimited",
        "is_superuser": db_user.is_superuser
    }


def create_llm_usage(*, session: Session, usage_create: LLMUsageCreate, user_id: uuid.UUID) -> LLMUsage:
    """Create a new LLM usage record"""
    db_obj = LLMUsage.model_validate(usage_create, update={"user_id": user_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_user_llm_usage_summary(*, session: Session, user_id: uuid.UUID) -> LLMUsageSummary | None:
    """Get LLM usage summary for a user"""
    # Get total counts
    total_requests = session.exec(
        select(func.count(LLMUsage.id)).where(LLMUsage.user_id == user_id)
    ).one()
    
    total_tokens = session.exec(
        select(func.sum(LLMUsage.total_tokens)).where(LLMUsage.user_id == user_id)
    ).one() or 0
    
    total_cost = session.exec(
        select(func.sum(LLMUsage.cost_usd)).where(LLMUsage.user_id == user_id)
    ).one() or 0.0
    
    # Get requests by provider
    provider_counts = session.exec(
        select(LLMUsage.provider, func.count(LLMUsage.id))
        .where(LLMUsage.user_id == user_id)
        .group_by(LLMUsage.provider)
    ).all()
    
    requests_by_provider = {provider: count for provider, count in provider_counts}
    
    # Get requests by type
    type_counts = session.exec(
        select(LLMUsage.request_type, func.count(LLMUsage.id))
        .where(LLMUsage.user_id == user_id)
        .group_by(LLMUsage.request_type)
    ).all()
    
    requests_by_type = {req_type: count for req_type, count in type_counts}
    
    return LLMUsageSummary(
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
        requests_by_provider=requests_by_provider,
        requests_by_type=requests_by_type
    )


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def create_post(*, session: Session, post_create: PostCreate, owner_id: uuid.UUID) -> Post:
    db_obj = Post.model_validate(post_create, update={"owner_id": owner_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_posts_for_user(*, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[Post]:
    return session.exec(select(Post).where(Post.owner_id == owner_id).offset(skip).limit(limit)).all()


def get_posts_by_status(*, session: Session, owner_id: uuid.UUID, status: str, skip: int = 0, limit: int = 100) -> list[Post]:
    return session.exec(select(Post).where(Post.owner_id == owner_id, Post.status == status).offset(skip).limit(limit)).all()


def get_scheduled_posts_ready_to_publish(*, session: Session) -> list[Post]:
    """Get posts that are scheduled and ready to be published"""
    now = datetime.utcnow()
    return session.exec(
        select(Post).where(
            Post.status == "scheduled",
            Post.scheduled_time <= now
        )
    ).all()


def update_post(*, session: Session, post_id: uuid.UUID, post_update: PostUpdate) -> Post | None:
    db_obj = session.get(Post, post_id)
    if not db_obj:
        return None
    post_data = post_update.model_dump(exclude_unset=True)
    for key, value in post_data.items():
        setattr(db_obj, key, value)
    db_obj.updated_at = datetime.utcnow()
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_post_performance(*, session: Session, post_id: uuid.UUID, performance_data: dict) -> Post | None:
    """Update post performance metrics"""
    db_obj = session.get(Post, post_id)
    if not db_obj:
        return None
    
    # Update performance fields
    for field in ['likes', 'comments', 'shares', 'views', 'engagement_rate']:
        if field in performance_data:
            setattr(db_obj, field, performance_data[field])
    
    db_obj.last_updated = datetime.utcnow()
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_post(*, session: Session, post_id: uuid.UUID) -> bool:
    db_obj = session.get(Post, post_id)
    if not db_obj:
        return False
    session.delete(db_obj)
    session.commit()
    return True
