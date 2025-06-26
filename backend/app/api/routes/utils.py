from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic.networks import EmailStr
from sqlmodel import Session
from fastapi.responses import JSONResponse
import os
import uuid

from app.api.deps import get_current_active_superuser, get_current_active_user
from app.models import Message, User, UpcomingPostCreate, UpcomingPostUpdate, UpcomingPostPublic, UpcomingPostsPublic
from app.utils import generate_test_email, send_email
from app.core.db import get_session
from app.crud import create_upcoming_post, get_upcoming_posts_for_user, update_upcoming_post, delete_upcoming_post

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    return True

@router.get("/postings", response_model=UpcomingPostsPublic)
def list_upcoming_posts(skip: int = 0, limit: int = 100, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    posts = get_upcoming_posts_for_user(session=session, owner_id=current_user.id, skip=skip, limit=limit)
    return {"data": posts, "count": len(posts)}

@router.post("/postings", response_model=UpcomingPostPublic)
def create_posting(post: UpcomingPostCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    return create_upcoming_post(session=session, post_create=post, owner_id=current_user.id)

@router.patch("/postings/{post_id}", response_model=UpcomingPostPublic)
def update_posting(post_id: uuid.UUID, post_update: UpcomingPostUpdate, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    post = update_upcoming_post(session=session, post_id=post_id, post_update=post_update)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.delete("/postings/{post_id}", response_model=dict)
def delete_posting(post_id: uuid.UUID, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    success = delete_upcoming_post(session=session, post_id=post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"success": True}

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../uploads')
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    url = f"/static/uploads/{file_name}"
    return JSONResponse({"url": url})
