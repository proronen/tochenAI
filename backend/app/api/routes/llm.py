from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel
from typing import Any

from app.api.deps import CurrentUser, SessionDep, get_current_active_user
from app.utils import OpenAIClient, AnthropicClient, GeminiClient, ImageGenerationClient
from app.models import Message, User

router = APIRouter(prefix="/llm", tags=["llm"])


class GenerateContentRequest(SQLModel):
    prompt: str
    provider: str = "openai"  # openai, anthropic, gemini
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
    count: int = 5
    max_tokens: int = 200


class GeneratePostIdeasRequest(SQLModel):
    business_description: str
    client_avatars: str | None = None
    additional_instructions: str | None = None
    provider: str = "gemini"  # Default to Gemini
    model: str = "gemini-1.5-flash"
    count: int = 5


class GeneratePostContentRequest(SQLModel):
    post_idea: str
    business_description: str
    client_avatars: str | None = None
    platform: str = "general"
    tone: str = "professional"
    provider: str = "gemini"
    model: str = "gemini-1.5-flash"


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
        elif request.provider == "gemini":
            client = GeminiClient(session=session, user_id=current_user.id)
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


@router.post("/generate-post-ideas")
def generate_post_ideas(
    request: GeneratePostIdeasRequest,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Generate post ideas using LLM with quota enforcement.
    """
    try:
        # Build context-aware prompt for post ideas
        context = f"Business: {request.business_description}"
        if request.client_avatars:
            context += f"\nTarget Audience: {request.client_avatars}"
        
        instructions = request.additional_instructions or ""
        
        prompt = f"""
{context}

{instructions}

Please generate {request.count} unique and creative post ideas for social media content. Each idea should be:
1. Relevant to the business and target audience
2. Engaging and shareable
3. Different from each other to avoid repetition
4. Suitable for various social media platforms

Format your response as a numbered list, with each idea being 1-2 sentences long.
Example format:
1. [Post idea 1]
2. [Post idea 2]
3. [Post idea 3]
...

Generate only the numbered list, no additional explanations.
"""
        
        if request.provider == "openai":
            client = OpenAIClient(session=session, user_id=current_user.id)
        elif request.provider == "anthropic":
            client = AnthropicClient(session=session, user_id=current_user.id)
        elif request.provider == "gemini":
            client = GeminiClient(session=session, user_id=current_user.id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        result = client.generate_content(
            prompt=prompt,
            model=request.model,
            max_tokens=2000
        )
        
        # Parse the numbered list into individual ideas
        content = result["content"]
        ideas = []
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                # Remove numbering and clean up
                idea = line.replace('•', '').replace('-', '').strip()
                if idea and idea[0].isdigit():
                    # Remove the number and dot
                    idea = '.'.join(idea.split('.')[1:]).strip()
                if idea:
                    ideas.append(idea)
        
        return {
            "ideas": ideas[:request.count],  # Ensure we don't exceed requested count
            "tokens_used": result["tokens_used"],
            "cost_usd": result["cost_usd"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post ideas generation failed: {str(e)}")


@router.post("/generate-post-content")
def generate_post_content(
    request: GeneratePostContentRequest,
    session: SessionDep,
    current_user: CurrentUser
) -> Any:
    """
    Generate post content (text and image description) based on a post idea.
    """
    try:
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

Post Idea: {request.post_idea}

Platform: {request.platform}
Tone: {request.tone}
Instructions: {platform_instructions.get(request.platform, platform_instructions['general'])}

Please generate:
1. A compelling social media post text (200-500 characters)
2. A brief image description for the visual content (50-100 characters)

Format your response as:
POST TEXT:
[Your post text here]

IMAGE DESCRIPTION:
[Brief description of the visual content]

The post should:
- Match the business description and target audience
- Use the specified tone
- Be optimized for the specified platform
- Be engaging and encourage interaction
- Relate to the provided post idea
"""
        
        if request.provider == "openai":
            client = OpenAIClient(session=session, user_id=current_user.id)
        elif request.provider == "anthropic":
            client = AnthropicClient(session=session, user_id=current_user.id)
        elif request.provider == "gemini":
            client = GeminiClient(session=session, user_id=current_user.id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        result = client.generate_content(
            prompt=prompt,
            model=request.model,
            max_tokens=1000
        )
        
        # Parse the response to extract post text and image description
        content = result["content"]
        post_text = ""
        image_description = ""
        
        lines = content.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("POST TEXT:"):
                current_section = "post_text"
            elif line.startswith("IMAGE DESCRIPTION:"):
                current_section = "image_description"
            elif line and current_section == "post_text":
                post_text += line + " "
            elif line and current_section == "image_description":
                image_description += line + " "
        
        return {
            "post_text": post_text.strip(),
            "image_description": image_description.strip(),
            "tokens_used": result["tokens_used"],
            "cost_usd": result["cost_usd"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post content generation failed: {str(e)}")


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
        },
        "gemini": {
            "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"],
            "default_model": "gemini-1.5-flash"
        }
    }


@router.post("/generate-image")
def generate_image(
    request: dict,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user)
):
    """Generate image using DALL-E"""
    try:
        prompt = request.get("prompt")
        size = request.get("size", "1024x1024")
        quality = request.get("quality", "standard")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        client = ImageGenerationClient(session=session, user_id=current_user.id)
        result = client.generate_image(prompt=prompt, size=size, quality=quality)
        
        return {
            "success": True,
            "image_url": result["image_url"],
            "cost_usd": result["cost_usd"],
            "provider": result["provider"],
            "model": result["model"]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}") 