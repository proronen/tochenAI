import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List
import string
import random
import emails  # type: ignore
import jwt
from jinja2 import Template
from jwt.exceptions import InvalidTokenError
import requests
import os
import uuid
from openai import OpenAI
from sqlmodel import Session, select
import re
from email_validator import validate_email, EmailNotValidError

from app.core import security
from app.core.config import settings
from app.models import LLMUsageCreate, User, LLMUsage
from app.crud import check_user_quota, increment_user_usage, create_llm_usage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def random_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


class FacebookClient:
    def __init__(self, page_access_token: str, page_id: str):
        self.page_access_token = page_access_token
        self.page_id = page_id
        self.base_url = f"https://graph.facebook.com/{self.page_id}"

    def post_to_page(self, message: str) -> dict:
        url = f"{self.base_url}/feed"
        payload = {
            "message": message,
            "access_token": self.page_access_token
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return response.json()


class TikTokClient:
    def __init__(self, access_token: str, user_id: str):
        self.access_token = access_token
        self.user_id = user_id
        self.base_url = f"https://open-api.tiktok.com/share/video/upload/"
        # Note: TikTok's API for posting is limited and may require business approval.

    def post_to_account(self, video_url: str, description: str) -> dict:
        # This is a placeholder. TikTok's API for posting is not as open as Facebook/Instagram.
        payload = {
            "access_token": self.access_token,
            "open_id": self.user_id,
            "video_url": video_url,
            "description": description
        }
        response = requests.post(self.base_url, data=payload)
        response.raise_for_status()
        return response.json()


class InstagramClient:
    def __init__(self, access_token: str, page_id: str):
        self.access_token = access_token
        self.page_id = page_id
        self.base_url = f"https://graph.facebook.com/v19.0/{self.page_id}"
        # Instagram posting is done via the Facebook Graph API for Instagram Business accounts.

    def post_to_account(self, image_url: str, caption: str) -> dict:
        # Step 1: Create a media object
        media_url = f"{self.base_url}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }
        response = requests.post(media_url, data=payload)
        response.raise_for_status()
        media_id = response.json().get("id")
        # Step 2: Publish the media object
        publish_url = f"{self.base_url}/media_publish"
        publish_payload = {
            "creation_id": media_id,
            "access_token": self.access_token
        }
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_response.raise_for_status()
        return publish_response.json()


# LLM Cost per 1K tokens (approximate)
LLM_COSTS = {
    "openai": {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-4o": {"input": 0.005, "output": 0.015},
    },
    "anthropic": {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    },
    "gemini": {
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},  # per 1K tokens
        "gemini-1.5-pro": {"input": 0.00375, "output": 0.015},
        "gemini-1.0-pro": {"input": 0.0005, "output": 0.0015},
    }
}


def calculate_llm_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate the cost of an LLM request"""
    if provider not in LLM_COSTS or model not in LLM_COSTS[provider]:
        return 0.0
    
    costs = LLM_COSTS[provider][model]
    input_cost = (prompt_tokens / 1000) * costs["input"]
    output_cost = (completion_tokens / 1000) * costs["output"]
    return input_cost + output_cost


def enforce_quota_and_track_usage(
    session,
    user_id: uuid.UUID,
    provider: str,
    model: str,
    request_type: str,
    prompt_tokens: int,
    completion_tokens: int,
    success: bool = True,
    error_message: Optional[str] = None
) -> bool:
    """
    Enforce quota and track LLM usage for a user.
    Returns True if quota check passed, False otherwise.
    """
    # Check quota first
    if not check_user_quota(session=session, user_id=user_id):
        return False
    
    # Calculate cost
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = calculate_llm_cost(provider, model, prompt_tokens, completion_tokens)
    
    # Create usage record
    usage_create = LLMUsageCreate(
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        request_type=request_type,
        success=success,
        error_message=error_message
    )
    
    create_llm_usage(session=session, usage_create=usage_create, user_id=user_id)
    
    # Increment usage count only on success
    if success:
        increment_user_usage(session=session, user_id=user_id)
    
    return True


class LLMClient:
    """Base LLM client with quota enforcement"""
    
    def __init__(self, session, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id
    
    def _enforce_quota_and_track(self, provider: str, model: str, request_type: str, 
                                prompt_tokens: int, completion_tokens: int, 
                                success: bool = True, error_message: Optional[str] = None) -> bool:
        return enforce_quota_and_track_usage(
            session=self.session,
            user_id=self.user_id,
            provider=provider,
            model=model,
            request_type=request_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=success,
            error_message=error_message
        )


class OpenAIClient(LLMClient):
    """OpenAI client with quota enforcement"""
    
    def __init__(self, session, user_id: uuid.UUID, api_key: Optional[str] = None):
        super().__init__(session, user_id)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
    
    def generate_content(self, prompt: str, model: str = "gpt-4", max_tokens: int = 1000) -> Dict[str, Any]:
        """Generate content using OpenAI API with quota enforcement"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Track usage
            self._enforce_quota_and_track(
                provider="openai",
                model=model,
                request_type="content_generation",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                success=True
            )
            
            return {
                "content": result["choices"][0]["message"]["content"],
                "tokens_used": prompt_tokens + completion_tokens,
                "cost_usd": calculate_llm_cost("openai", model, prompt_tokens, completion_tokens)
            }
            
        except Exception as e:
            # Track failed request
            self._enforce_quota_and_track(
                provider="openai",
                model=model,
                request_type="content_generation",
                prompt_tokens=0,
                completion_tokens=0,
                success=False,
                error_message=str(e)
            )
            raise


class AnthropicClient(LLMClient):
    """Anthropic client with quota enforcement"""
    
    def __init__(self, session, user_id: uuid.UUID, api_key: Optional[str] = None):
        super().__init__(session, user_id)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1"
    
    def generate_content(self, prompt: str, model: str = "claude-3-sonnet", max_tokens: int = 1000) -> Dict[str, Any]:
        """Generate content using Anthropic API with quota enforcement"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(f"{self.base_url}/messages", headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            usage = result.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
            
            # Track usage
            self._enforce_quota_and_track(
                provider="anthropic",
                model=model,
                request_type="content_generation",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                success=True
            )
            
            return {
                "content": result["content"][0]["text"],
                "tokens_used": prompt_tokens + completion_tokens,
                "cost_usd": calculate_llm_cost("anthropic", model, prompt_tokens, completion_tokens)
            }
            
        except Exception as e:
            # Track failed request
            self._enforce_quota_and_track(
                provider="anthropic",
                model=model,
                request_type="content_generation",
                prompt_tokens=0,
                completion_tokens=0,
                success=False,
                error_message=str(e)
            )
            raise


class GeminiClient(LLMClient):
    """Google Gemini client with quota enforcement"""
    
    def __init__(self, session, user_id: uuid.UUID, api_key: Optional[str] = None):
        super().__init__(session, user_id)
        self.api_key = "AIzaSyAHC4YopCb5ccNH4rpPYzOlM8ao4tc2Iyc"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def generate_content(self, prompt: str, model: str = "gemini-1.5-flash", max_tokens: int = 1000) -> Dict[str, Any]:
        """Generate content using Gemini API with quota enforcement"""
        try:
            url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract content from Gemini response
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Gemini doesn't provide token usage in the same way, so we estimate
            # Rough estimation: 1 token ≈ 4 characters for English text
            estimated_tokens = len(prompt + content) // 4
            
            # Track usage with estimated tokens
            self._enforce_quota_and_track(
                provider="gemini",
                model=model,
                request_type="content_generation",
                prompt_tokens=estimated_tokens // 2,  # Rough split
                completion_tokens=estimated_tokens // 2,
                success=True
            )
            
            return {
                "content": content,
                "tokens_used": estimated_tokens,
                "cost_usd": calculate_llm_cost("gemini", model, estimated_tokens // 2, estimated_tokens // 2)
            }
            
        except Exception as e:
            # Track failed request
            self._enforce_quota_and_track(
                provider="gemini",
                model=model,
                request_type="content_generation",
                prompt_tokens=0,
                completion_tokens=0,
                success=False,
                error_message=str(e)
            )
            raise


class ImageGenerationClient:
    """Image generation client using OpenAI DALL-E"""
    
    def __init__(self, session: Session, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=self.api_key)
    
    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "standard") -> Dict[str, Any]:
        """Generate image using DALL-E API with quota enforcement"""
        
        # Check user quota
        user = self.session.get(User, self.user_id)
        if not user:
            raise ValueError("User not found")
        
        if not user.is_superuser and user.usage_count >= user.quota:
            raise ValueError("User quota exceeded")
        
        try:
            # Generate image using DALL-E
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
            
            # Get the image URL
            image_url = response.data[0].url
            
            # Calculate cost (DALL-E 3 pricing: $0.04 per image)
            cost_usd = 0.04
            
            # Record usage
            usage_data = LLMUsageCreate(
                user_id=self.user_id,
                provider="openai",
                model="dall-e-3",
                input_tokens=0,  # DALL-E doesn't use tokens in the same way
                output_tokens=0,
                cost_usd=cost_usd,
                request_type="image_generation",
                prompt=prompt,
                response_data={"image_url": image_url}
            )
            
            create_llm_usage(session=self.session, usage_create=usage_data, user_id=self.user_id)
            
            # Update user usage count
            user.usage_count += 1
            self.session.add(user)
            self.session.commit()
            
            return {
                "image_url": image_url,
                "prompt": prompt,
                "cost_usd": cost_usd,
                "provider": "openai",
                "model": "dall-e-3"
            }
            
        except Exception as e:
            raise Exception(f"Image generation failed: {str(e)}")
