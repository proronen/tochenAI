from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
from app.models import SocialAccount
from app.api.deps import get_current_active_user
from app.core.db import get_session
from sqlmodel import Session
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Facebook/Instagram OAuth Login
@router.get("/facebook/login")
def facebook_login():
    client_id = os.getenv("FACEBOOK_CLIENT_ID", "your_facebook_app_id")
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8000/api/v1/auth/facebook/callback")
    scope = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"
    auth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&response_type=code"
    )
    return RedirectResponse(auth_url)

# Facebook/Instagram OAuth Callback
@router.get("/facebook/callback")
def facebook_callback(request: Request, code: str, current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    client_id = os.getenv("FACEBOOK_CLIENT_ID", "your_facebook_app_id")
    client_secret = os.getenv("FACEBOOK_CLIENT_SECRET", "your_facebook_app_secret")
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8000/api/v1/auth/facebook/callback")

    # 1. Exchange code for access token
    token_url = (
        f"https://graph.facebook.com/v19.0/oauth/access_token"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&client_secret={client_secret}"
        f"&code={code}"
    )
    token_resp = requests.get(token_url)
    if not token_resp.ok:
        raise HTTPException(status_code=400, detail="Failed to get access token from Facebook")
    token_data = token_resp.json()
    access_token = token_data["access_token"]

    # 2. Get user pages (for Facebook and Instagram)
    pages_url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}"
    pages_resp = requests.get(pages_url)
    if not pages_resp.ok:
        raise HTTPException(status_code=400, detail="Failed to get pages from Facebook")
    pages_data = pages_resp.json()

    # 3. Store the first page as a SocialAccount (for demo; you may want to let user pick)
    if not pages_data.get("data"):
        raise HTTPException(status_code=400, detail="No Facebook pages found")
    page = pages_data["data"][0]
    page_access_token = page["access_token"]
    page_id = page["id"]
    page_name = page["name"]

    # 4. Store in SocialAccount table
    social_account = SocialAccount(
        platform="facebook",
        access_token=page_access_token,
        refresh_token=None,
        expires_at=None,
        account_id=page_id,
        account_name=page_name,
        user_id=current_user.id,
    )
    session.add(social_account)
    session.commit()
    session.refresh(social_account)

    # 5. Optionally, check for connected Instagram business account
    ig_url = f"https://graph.facebook.com/v19.0/{page_id}?fields=instagram_business_account&access_token={page_access_token}"
    ig_resp = requests.get(ig_url)
    ig_data = ig_resp.json()
    if ig_data.get("instagram_business_account"):
        ig_id = ig_data["instagram_business_account"]["id"]
        # Store Instagram as a separate SocialAccount
        ig_account = SocialAccount(
            platform="instagram",
            access_token=page_access_token,  # Instagram uses the same token as the page
            refresh_token=None,
            expires_at=None,
            account_id=ig_id,
            account_name=page_name + " (Instagram)",
            user_id=current_user.id,
        )
        session.add(ig_account)
        session.commit()
        session.refresh(ig_account)

    return JSONResponse({"message": "Facebook (and Instagram if available) account connected!"})

# TikTok OAuth Login
@router.get("/tiktok/login")
def tiktok_login():
    client_key = os.getenv("TIKTOK_CLIENT_ID", "your_tiktok_client_id")
    redirect_uri = os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:8000/api/v1/auth/tiktok/callback")
    scope = "user.info.basic,video.list,video.upload"
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}"
        f"&scope={scope}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(auth_url)

# TikTok OAuth Callback
@router.get("/tiktok/callback")
def tiktok_callback(request: Request):
    # Placeholder: exchange code for access token, fetch user info, store in SocialAccount
    return JSONResponse({"message": "TikTok OAuth callback placeholder. Implement token exchange and storage here."}) 