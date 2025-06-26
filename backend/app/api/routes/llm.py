from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel
from typing import Any

from app.api.deps import CurrentUser, SessionDep
from app.utils import OpenAIClient, AnthropicClient
from app.models import Message

router = APIRouter(prefix="/llm", tags=["llm"])


class GenerateContentRequest(SQLModel):
    prompt: str
    provider: str = "openai"  # openai or anthropic
    model: str = "gpt-4"
    max_tokens: int = 1000


class GeneratePostRequest(SQLModel):
    business_description: str
    client_avatars: str | None = None
    platform: str = "general"  # facebook, instagram, tiktok, general
    tone: str = "professional"  # professional, casual, friendly, etc.
    max_tokens: int = 500


class GenerateHashtagsRequest(SQLModel):
    content: str
    platform: str = "general"  # instagram, tiktok, general
    count: int = 10
    max_tokens: int = 200


@router.post("/generate-content")
def generate_content(
    request: GenerateContentRequest,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Generate content using LLM with quota enforcement.
    """
    try:
        if request.provider == "openai":
            client = OpenAIClient(session=session, user_id=current_user.id)
        elif request.provider == "anthropic":
            client = AnthropicClient(session=session, user_id=current_user.id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        result = client.generate_content(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens
        )
        
        return {
            "content": result["content"],
            "tokens_used": result["tokens_used"],
            "cost_usd": result["cost_usd"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM request failed: {str(e)}")


@router.post("/generate-post")
def generate_social_media_post(
    request: GeneratePostRequest,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Generate a social media post using LLM with quota enforcement.
    """
    try:
        # Build context-aware prompt
        context = f"Business: {request.business_description}"
        if request.client_avatars:
            context += f"\nTarget Audience: {request.client_avatars}"
        
        platform_instructions = {
            "facebook": "Create a Facebook post that is engaging and encourages interaction",
            "instagram": "Create an Instagram caption that is visually descriptive and uses emojis appropriately",
            "tiktok": "Create a TikTok caption that is trendy, short, and uses popular hashtags",
            "general": "Create a social media post that works across platforms"
        }
        
        prompt = f"""
{context}

Platform: {request.platform}
Tone: {request.tone}
Instructions: {platform_instructions.get(request.platform, platform_instructions['general'])}

Please generate a compelling social media post that:
1. Matches the business description and target audience
2. Uses the specified tone
3. Is optimized for the specified platform
4. Is engaging and encourages interaction
5. Stays within {request.max_tokens} characters

Generate only the post content, no additional explanations.
"""
        
        client = OpenAIClient(session=session, user_id=current_user.id)
        result = client.generate_content(
            prompt=prompt,
            model="gpt-4",
            max_tokens=request.max_tokens
        )
        
        return {
            "post_content": result["content"],
            "tokens_used": result["tokens_used"],
            "cost_usd": result["cost_usd"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post generation failed: {str(e)}")


@router.post("/generate-hashtags")
def generate_hashtags(
    request: GenerateHashtagsRequest,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Generate hashtags using LLM with quota enforcement.
    """
    try:
        platform_instructions = {
            "instagram": "Generate Instagram hashtags that are popular and relevant",
            "tiktok": "Generate TikTok hashtags that are trending and viral",
            "general": "Generate general social media hashtags"
        }
        
        prompt = f"""
Content: {request.content}

Platform: {request.platform}
Instructions: {platform_instructions.get(request.platform, platform_instructions['general'])}

Please generate {request.count} relevant hashtags for this content.
Return only the hashtags separated by commas, no additional text.
Example format: #hashtag1, #hashtag2, #hashtag3
"""
        
        client = OpenAIClient(session=session, user_id=current_user.id)
        result = client.generate_content(
            prompt=prompt,
            model="gpt-3.5-turbo",
            max_tokens=request.max_tokens
        )
        
        # Parse hashtags from response
        hashtags_text = result["content"].strip()
        hashtags = [tag.strip() for tag in hashtags_text.split(",") if tag.strip()]
        
        return {
            "hashtags": hashtags,
            "tokens_used": result["tokens_used"],
            "cost_usd": result["cost_usd"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hashtag generation failed: {str(e)}")


@router.get("/providers")
def get_available_providers() -> Any:
    """
    Get available LLM providers and models.
    """
    return {
        "openai": {
            "models": ["gpt-4", "gpt-3.5-turbo", "gpt-4o"],
            "default_model": "gpt-4"
        },
        "anthropic": {
            "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "default_model": "claude-3-sonnet"
        }
    } 