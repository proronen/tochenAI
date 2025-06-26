from fastapi import APIRouter, HTTPException
import os
from app.utils import TikTokClient

router = APIRouter()

TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_USER_ID = os.getenv("TIKTOK_USER_ID", "")

tiktok_client = TikTokClient(TIKTOK_ACCESS_TOKEN, TIKTOK_USER_ID)

@router.post("/tiktok/post")
def post_to_tiktok(video_url: str, description: str):
    try:
        result = tiktok_client.post_to_account(video_url, description)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 