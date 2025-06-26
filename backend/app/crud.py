import uuid
from typing import Any
from datetime import datetime

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate, UpcomingPost, UpcomingPostCreate, UpcomingPostUpdate


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


def create_upcoming_post(*, session: Session, post_create: UpcomingPostCreate, owner_id: uuid.UUID) -> UpcomingPost:
    db_obj = UpcomingPost.model_validate(post_create, update={"owner_id": owner_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_upcoming_posts_for_user(*, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[UpcomingPost]:
    return session.exec(select(UpcomingPost).where(UpcomingPost.owner_id == owner_id).offset(skip).limit(limit)).all()


def update_upcoming_post(*, session: Session, post_id: uuid.UUID, post_update: UpcomingPostUpdate) -> UpcomingPost | None:
    db_obj = session.get(UpcomingPost, post_id)
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


def delete_upcoming_post(*, session: Session, post_id: uuid.UUID) -> bool:
    db_obj = session.get(UpcomingPost, post_id)
    if not db_obj:
        return False
    session.delete(db_obj)
    session.commit()
    return True
