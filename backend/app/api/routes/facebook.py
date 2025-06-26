from fastapi import APIRouter, HTTPException, Depends
import os
from app.utils import FacebookClient

router = APIRouter()

# Load from environment variables
PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")

fb_client = FacebookClient(PAGE_ACCESS_TOKEN, PAGE_ID)

@router.post("/facebook/post")
def post_to_facebook(message: str):
    try:
        result = fb_client.post_to_page(message)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 