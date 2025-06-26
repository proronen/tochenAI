from fastapi import APIRouter, HTTPException
import os
from app.utils import InstagramClient

router = APIRouter()

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID", "")

instagram_client = InstagramClient(INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_PAGE_ID)

@router.post("/instagram/post")
def post_to_instagram(image_url: str, caption: str):
    try:
        result = instagram_client.post_to_account(image_url, caption)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 