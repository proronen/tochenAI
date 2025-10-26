import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, delete, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    # dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    if not current_user.is_superuser:
        statement = select(User).where(User.email == current_user.email).offset(skip).limit(limit)
        users = session.exec(statement).all()
        return UsersPublic(data=users)
    else:
        statement = select(User).offset(skip).limit(limit)
        users = session.exec(statement).all()
        return UsersPublic(data=users, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    return user


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")


@router.get("/me/quota")
def get_my_quota_info(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get current user's quota information.
    """
    quota_info = crud.get_user_quota_info(session=session, user_id=current_user.id)
    if not quota_info:
        raise HTTPException(status_code=404, detail="User not found")
    return quota_info


@router.get("/{user_id}/quota", dependencies=[Depends(get_current_active_superuser)])
def get_user_quota_info(
    session: SessionDep, user_id: uuid.UUID, current_user: CurrentUser
) -> Any:
    """
    Get a specific user's quota information (superuser only).
    """
    quota_info = crud.get_user_quota_info(session=session, user_id=user_id)
    if not quota_info:
        raise HTTPException(status_code=404, detail="User not found")
    return quota_info


@router.patch("/{user_id}/client-specifics")
def update_user_client_specifics(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user's client-specific information (quota, business description, avatars).
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    
    # Only allow updating quota-related fields
    allowed_fields = ["quota", "business_description", "client_avatars"]
    update_data = {}
    for field in allowed_fields:
        if hasattr(user_in, field) and getattr(user_in, field) is not None:
            update_data[field] = getattr(user_in, field)
    
    if update_data:
        for key, value in update_data.items():
            setattr(db_user, key, value)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    
    return {"message": "Client specifics updated successfully", "user": db_user}


@router.post("/me/increment-usage")
def increment_my_usage(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Increment current user's usage count (for LLM requests).
    """
    success = crud.increment_user_usage(session=session, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Usage incremented successfully"}


@router.post("/{user_id}/increment-usage", dependencies=[Depends(get_current_active_superuser)])
def increment_user_usage(
    session: SessionDep, user_id: uuid.UUID, current_user: CurrentUser
) -> Any:
    """
    Increment a specific user's usage count (superuser only).
    """
    success = crud.increment_user_usage(session=session, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Usage incremented successfully"}


@router.get("/me/llm-usage-summary")
def get_my_llm_usage_summary(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get current user's LLM usage summary.
    """
    usage_summary = crud.get_user_llm_usage_summary(session=session, user_id=current_user.id)
    if not usage_summary:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "requests_by_provider": {},
            "requests_by_type": {}
        }
    return usage_summary


@router.get("/{user_id}/llm-usage-summary")
def get_user_llm_usage_summary(
    session: SessionDep, user_id: uuid.UUID, current_user: CurrentUser
) -> Any:
    """
    Get a specific user's LLM usage summary.
    Users can only access their own data unless they are superusers.
    """
    # Security check: users can only access their own data unless they are superusers
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own LLM usage summary"
        )
    
    usage_summary = crud.get_user_llm_usage_summary(session=session, user_id=user_id)
    if not usage_summary:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "requests_by_provider": {},
            "requests_by_type": {}
        }
    return usage_summary
