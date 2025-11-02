import logging
logging.basicConfig(level=logging.INFO)
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import func, and_, case

from app.api.deps import get_current_active_user
from app.models import User, Post, PostStatus
from app.core.db import get_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def get_analytics_overview(
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get basic analytics overview for the user's posts"""

    # Get total posts count
    total_posts = session.exec(
        select(func.count(Post.id)).where(Post.owner_id == current_user.id)
    ).one()
    
    # Get posts by status
    status_counts = session.exec(
        select(Post.status, func.count(Post.id))
        .where(Post.owner_id == current_user.id)
        .group_by(Post.status)
    ).all()
    
    status_breakdown = {status.value: 0 for status in PostStatus}
    for status, count in status_counts:
        status_breakdown[status.value] = count
    
    # Get total engagement
    total_engagement = session.exec(
        select(func.sum(Post.likes + Post.comments + Post.shares))
        .where(Post.owner_id == current_user.id)
    ).one() or 0
    
    # Get average engagement rate
    avg_engagement_rate = session.exec(
        select(func.avg(Post.engagement_rate))
        .where(Post.owner_id == current_user.id)
    ).one() or 0.0
    
    # Get platform breakdown
    platform_breakdown = {
        "facebook": session.exec(
            select(func.count(Post.id))
            .where(and_(Post.owner_id == current_user.id, Post.to_facebook == True))
        ).one(),
        "instagram": session.exec(
            select(func.count(Post.id))
            .where(and_(Post.owner_id == current_user.id, Post.to_instagram == True))
        ).one(),
        "tiktok": session.exec(
            select(func.count(Post.id))
            .where(and_(Post.owner_id == current_user.id, Post.to_tiktok == True))
        ).one()
    }
    
    return {
        "total_posts": total_posts,
        "status_breakdown": status_breakdown,
        "total_engagement": total_engagement,
        "avg_engagement_rate": round(avg_engagement_rate, 2),
        "platform_breakdown": platform_breakdown
    }


@router.get("/engagement-trends")
def get_engagement_trends(
    days: int = 30,
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get engagement trends over time"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily engagement data
    statement = (
        select(
            func.date(Post.posted_at).label('date'),
            func.sum(Post.likes).label('likes'),
            func.sum(Post.comments).label('comments'),
            func.sum(Post.shares).label('shares'),
            func.sum(Post.views).label('views'),
            func.avg(Post.engagement_rate).label('avg_engagement_rate')
        )
        .where(
            and_(
                Post.owner_id == current_user.id,
                Post.posted_at >= start_date,
                Post.status == PostStatus.POSTED
            )
        )
        .group_by(func.date(Post.posted_at))
    )
    
    daily_data = session.exec(statement).all()
    
    # Format data for frontend
    trends = []
    for row in daily_data:
        trends.append({
            "date": row.date.isoformat() if row.date else None,
            "likes": row.likes or 0,
            "comments": row.comments or 0,
            "shares": row.shares or 0,
            "views": row.views or 0,
            "avg_engagement_rate": round(row.avg_engagement_rate or 0, 2)
        })
    
    return {
        "period_days": days,
        "trends": trends
    }


@router.get("/platform-performance")
def get_platform_performance(
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get performance metrics by platform"""
    
    platforms = ["facebook", "instagram", "tiktok"]
    performance = {}
    
    for platform in platforms:
        platform_field = f"to_{platform}"
        platform_id_field = f"{platform}_post_id"
        
        # Get posts for this platform
        platform_posts = session.exec(
            select(func.count(Post.id)).where(
                and_(
                    Post.owner_id == current_user.id,
                    getattr(Post, platform_field) == True,
                    getattr(Post, platform_id_field).isnot(None)
                )
            )
        ).one()
        
        # Get engagement metrics
        total_likes = session.exec(
            select(func.sum(Post.likes)).where(
                and_(
                    Post.owner_id == current_user.id,
                    getattr(Post, platform_field) == True,
                    getattr(Post, platform_id_field).isnot(None)
                )
            )
        ).one() or 0
        
        total_comments = session.exec(
            select(func.sum(Post.comments)).where(
                and_(
                    Post.owner_id == current_user.id,
                    getattr(Post, platform_field) == True,
                    getattr(Post, platform_id_field).isnot(None)
                )
            )
        ).one() or 0
        
        total_shares = session.exec(
            select(func.sum(Post.shares)).where(
                and_(
                    Post.owner_id == current_user.id,
                    getattr(Post, platform_field) == True,
                    getattr(Post, platform_id_field).isnot(None)
                )
            )
        ).one() or 0
        
        avg_engagement_rate = session.exec(
            select(func.avg(Post.engagement_rate)).where(
                and_(
                    Post.owner_id == current_user.id,
                    getattr(Post, platform_field) == True,
                    getattr(Post, platform_id_field).isnot(None)
                )
            )
        ).one() or 0.0
        
        performance[platform] = {
            "total_posts": platform_posts,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_engagement": total_likes + total_comments + total_shares,
            "avg_engagement_rate": round(avg_engagement_rate, 2)
        }
    
    return performance


@router.get("/hashtag-performance")
def get_hashtag_performance(
    limit: int = 20,
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get performance metrics for hashtags"""
    
    # This is a simplified version - in a real implementation, you'd want to
    # parse hashtags from the hashtags field and aggregate them
    posts_with_hashtags = session.exec(
        select(
            Post.id,
            Post.hashtags,
            Post.likes,
            Post.comments,
            Post.shares,
            Post.engagement_rate
        ).where(
            and_(
                Post.owner_id == current_user.id,
                Post.hashtags.isnot(None),
                Post.hashtags != "",
                Post.status == PostStatus.POSTED
            )
        )
    ).all()
    
    # Simple hashtag analysis (you could make this more sophisticated)
    hashtag_stats = {}
    
    for post in posts_with_hashtags:
        if post.hashtags:
            hashtags = [tag.strip() for tag in post.hashtags.split(',') if tag.strip()]
            for hashtag in hashtags:
                if hashtag not in hashtag_stats:
                    hashtag_stats[hashtag] = {
                        "count": 0,
                        "total_likes": 0,
                        "total_comments": 0,
                        "total_shares": 0,
                        "avg_engagement_rate": 0.0
                    }
                
                hashtag_stats[hashtag]["count"] += 1
                hashtag_stats[hashtag]["total_likes"] += post.likes
                hashtag_stats[hashtag]["total_comments"] += post.comments
                hashtag_stats[hashtag]["total_shares"] += post.shares
                hashtag_stats[hashtag]["avg_engagement_rate"] += post.engagement_rate
    
    # Calculate averages and sort by performance
    for hashtag, stats in hashtag_stats.items():
        if stats["count"] > 0:
            stats["avg_engagement_rate"] = round(stats["avg_engagement_rate"] / stats["count"], 2)
            stats["total_engagement"] = stats["total_likes"] + stats["total_comments"] + stats["total_shares"]
    
    # Sort by total engagement and return top hashtags
    sorted_hashtags = sorted(
        hashtag_stats.items(), 
        key=lambda x: x[1]["total_engagement"], 
        reverse=True
    )[:limit]
    
    return {
        "top_hashtags": [{"hashtag": tag, **stats} for tag, stats in sorted_hashtags],
        "total_unique_hashtags": len(hashtag_stats)
    }



