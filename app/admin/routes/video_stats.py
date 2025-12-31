"""
Enhanced Video Statistics and Analytics
Comprehensive admin view for individual video performance and comment moderation
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime, timedelta

from app.db.database import get_db_session
from app.models.video_series import VideoSeries, SeriesVideo
from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
from app.models.video_engagement import VideoComment, VideoLike, VideoCommentLike
from app.models.user import User
from app.admin.templates.base import create_html_page

router = APIRouter()


@router.get("/video/{slug}/stats", response_class=HTMLResponse)
async def video_stats_page(request: Request, slug: str):
    """Comprehensive video statistics and analytics page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as session:
            # Try to find in series first
            series_result = await session.execute(
                select(SeriesVideo, VideoSeries)
                .join(VideoSeries, SeriesVideo.series_id == VideoSeries.id)
                .where(SeriesVideo.slug == slug)
            )
            series_data = series_result.first()
            
            video = None
            video_type = None
            parent_name = None
            parent_id = None
            back_url = "/admin/videos/all"
            
            if series_data:
                video, parent = series_data
                video_type = "series"
                parent_name = parent.title
                parent_id = str(parent.id)
                back_url = f"/admin/videos/series/{parent_id}"
            else:
                # Try channel video
                channel_result = await session.execute(
                    select(GeneralKnowledgeVideo, VideoChannel)
                    .join(VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id)
                    .where(GeneralKnowledgeVideo.slug == slug)
                )
                channel_data = channel_result.first()
                
                if channel_data:
                    video, parent = channel_data
                    video_type = "channel"
                    parent_name = parent.name
                    parent_id = str(parent.id)
                    back_url = f"/admin/videos/channels/{parent_id}"
            
            if not video:
                raise HTTPException(status_code=404, detail="Video not found")
            
            # Get engagement stats
            # Total comments (excluding deleted and replies)
            total_comments_result = await session.execute(
                select(func.count(VideoComment.id))
                .where(
                    VideoComment.video_slug == slug,
                    VideoComment.is_deleted == 0,
                    VideoComment.parent_id == None
                )
            )
            total_comments = total_comments_result.scalar() or 0
            
            # Total likes
            total_likes_result = await session.execute(
                select(func.count(VideoLike.id))
                .where(VideoLike.video_slug == slug, VideoLike.vote == 1)
            )
            total_likes = total_likes_result.scalar() or 0
            
            # Total dislikes
            total_dislikes_result = await session.execute(
                select(func.count(VideoLike.id))
                .where(VideoLike.video_slug == slug, VideoLike.vote == -1)
            )
            total_dislikes = total_dislikes_result.scalar() or 0
            
            # Get comments with user info (eagerly load relationships)
            comments_result = await session.execute(
                select(VideoComment)
                .options(selectinload(VideoComment.user))
                .where(
                    VideoComment.video_slug == slug,
                    VideoComment.is_deleted == 0,
                    VideoComment.parent_id == None  # Top-level comments only
                )
                .order_by(desc(VideoComment.created_at))
            )
            all_comments = comments_result.scalars().all()
            
            # Convert to dictionaries immediately
            comments_data = [
                {
                    'id': str(comment.id),
                    'content': comment.content,
                    'user_name': comment.user.full_name if comment.user else 'Unknown User',
                    'user_email': comment.user.email if comment.user else '',
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M') if comment.created_at else '',
                    'likes_count': comment.likes_count or 0,
                    'replies_count': comment.replies_count or 0
                }
                for comment in all_comments
            ]
            
            # Calculate engagement rate
            views = video.views or 0
            engagement_rate = ((total_likes + total_comments) / max(views, 1)) * 100 if views > 0 else 0
        
        # Build stats cards
        stats_html = f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="stat-icon">
                    <i class="fas fa-eye"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{views:,}</div>
                    <div class="stat-label">Total Views</div>
                </div>
            </div>
            
            <div class="stat-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                <div class="stat-icon">
                    <i class="fas fa-comments"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{total_comments:,}</div>
                    <div class="stat-label">Comments</div>
                </div>
            </div>
            
            <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="stat-icon">
                    <i class="fas fa-thumbs-up"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{total_likes:,}</div>
                    <div class="stat-label">Likes</div>
                </div>
            </div>
            
            <div class="stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <div class="stat-icon">
                    <i class="fas fa-thumbs-down"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{total_dislikes:,}</div>
                    <div class="stat-label">Dislikes</div>
                </div>
            </div>
            
            <div class="stat-card" style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);">
                <div class="stat-icon">
                    <i class="fas fa-chart-line"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{engagement_rate:.1f}%</div>
                    <div class="stat-label">Engagement Rate</div>
                </div>
            </div>
        </div>
        """
        
        # Build comments list
        comments_section = ""
        if comments_data:
            comments_list = ""
            for comment in comments_data:
                replies_badge = f'<span style="margin-left: 1rem; color: #718096; font-size: 0.9rem;"><i class="fas fa-reply"></i> {comment["replies_count"]} replies</span>' if comment['replies_count'] > 0 else ''
                
                comments_list += f"""
                <div class="comment-card" id="comment-{comment['id']}">
                    <div style="display: flex; gap: 1rem; align-items: start;">
                        <div class="comment-avatar">
                            {comment['user_name'][:2].upper()}
                        </div>
                        <div style="flex: 1;">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                                <div>
                                    <strong style="color: #2d3748; font-size: 1rem;">{comment['user_name']}</strong>
                                    <p style="margin: 0; font-size: 0.85rem; color: #718096;">{comment['user_email']}</p>
                                    <p style="margin: 0.25rem 0 0 0; font-size: 0.8rem; color: #a0aec0;">
                                        <i class="fas fa-clock"></i> {comment['created_at']}
                                    </p>
                                </div>
                                <button onclick="deleteComment('{comment['id']}')" class="btn btn-danger" style="padding: 0.5rem 1rem;">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </div>
                            <p style="margin: 0.75rem 0 0 0; color: #2d3748; line-height: 1.6;">{comment['content']}</p>
                            <div style="margin-top: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
                                <span style="color: #667eea; font-size: 0.9rem;">
                                    <i class="fas fa-thumbs-up"></i> {comment['likes_count']} likes
                                </span>
                                {replies_badge}
                            </div>
                        </div>
                    </div>
                </div>
                """
            
            comments_section = f"""
            <div style="background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                <h3 style="font-size: 1.25rem; font-weight: 700; color: #2d3748; margin: 0 0 1.5rem 0;">
                    <i class="fas fa-comments"></i> Comments ({len(comments_data)})
                </h3>
                {comments_list}
            </div>
            """
        else:
            comments_section = """
            <div style="background: white; border-radius: 12px; padding: 3rem; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                <i class="fas fa-comments" style="font-size: 3rem; color: #cbd5e0; margin-bottom: 1rem;"></i>
                <h3 style="color: #2d3748; margin: 0 0 0.5rem 0;">No Comments Yet</h3>
                <p style="color: #718096; margin: 0;">This video hasn't received any comments.</p>
            </div>
            """
        
        # Video info section
        video_info = f"""
        <div style="background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                <div>
                    <h3 style="font-size: 1.1rem; font-weight: 700; color: #2d3748; margin: 0 0 1rem 0;">
                        <i class="fas fa-info-circle"></i> Video Information
                    </h3>
                    <div style="display: grid; gap: 0.75rem;">
                        <div>
                            <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Type</label>
                            <span style="font-weight: 600; color: #2d3748; text-transform: capitalize;">{video_type}</span>
                        </div>
                        <div>
                            <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">
                                {'Series' if video_type == 'series' else 'Channel'}
                            </label>
                            <span style="font-weight: 600; color: #2d3748;">{parent_name}</span>
                        </div>
                        <div>
                            <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Slug</label>
                            <code style="font-size: 0.9rem; background: #f7fafc; padding: 0.25rem 0.5rem; border-radius: 4px; color: #667eea;">{slug}</code>
                        </div>
                    </div>
                </div>
                
                <div>
                    <h3 style="font-size: 1.1rem; font-weight: 700; color: #2d3748; margin: 0 0 1rem 0;">
                        <i class="fas fa-chart-pie"></i> Engagement Breakdown
                    </h3>
                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #718096;">Like Ratio</span>
                            <strong style="color: #48bb78;">{(total_likes / max(total_likes + total_dislikes, 1) * 100):.1f}%</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #718096;">Comments per View</span>
                            <strong style="color: #667eea;">{(total_comments / max(views, 1)):.3f}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #718096;">Likes per View</span>
                            <strong style="color: #f093fb;">{(total_likes / max(views, 1)):.3f}</strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        content = f"""
        <div class="page-header">
            <div>
                <h1 class="page-title">
                    <i class="fas fa-chart-bar"></i> {video.title}
                </h1>
                <p class="page-subtitle">{video.subtitle if video.subtitle else 'Video Analytics & Engagement'}</p>
            </div>
            <div style="display: flex; gap: 1rem;">
                <a href="{back_url}" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back
                </a>
                <a href="/admin/videos/analytics?period=week" class="btn btn-secondary">
                    <i class="fas fa-chart-line"></i> All Analytics
                </a>
            </div>
        </div>
        
        {stats_html}
        {video_info}
        {comments_section}
        
        <style>
            .stat-card {{
                border-radius: 12px;
                padding: 1.5rem;
                color: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
            }}
            
            .stat-icon {{
                font-size: 2rem;
                margin-bottom: 1rem;
                opacity: 0.9;
            }}
            
            .stat-content {{
                
            }}
            
            .stat-value {{
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 0.25rem;
            }}
            
            .stat-label {{
                font-size: 0.9rem;
                opacity: 0.9;
                font-weight: 500;
            }}
            
            .comment-card {{
                padding: 1.5rem;
                background: #f7fafc;
                border-radius: 12px;
                margin-bottom: 1rem;
                transition: background 0.2s ease;
            }}
            
            .comment-card:hover {{
                background: #edf2f7;
            }}
            
            .comment-avatar {{
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 1.2rem;
                flex-shrink: 0;
            }}
        </style>
        
        <script>
            async function deleteComment(commentId) {{
                if (!confirm('Are you sure you want to delete this comment? This action cannot be undone.')) {{
                    return;
                }}
                
                try {{
                    const response = await fetch(`/admin/video/comment/${{commentId}}/delete`, {{
                        method: 'POST'
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status) {{
                        // Remove comment from DOM
                        const commentElement = document.getElementById(`comment-${{commentId}}`);
                        if (commentElement) {{
                            commentElement.style.transition = 'opacity 0.3s ease';
                            commentElement.style.opacity = '0';
                            setTimeout(() => commentElement.remove(), 300);
                        }}
                        
                        showNotification('Comment deleted successfully', 'success');
                        
                        // Reload page after 1 second to update counts
                        setTimeout(() => location.reload(), 1000);
                    }} else {{
                        showNotification('Failed to delete comment: ' + result.message, 'error');
                    }}
                }} catch (error) {{
                    console.error('Error:', error);
                    showNotification('Error deleting comment', 'error');
                }}
            }}
            
            function showNotification(message, type) {{
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 2rem;
                    right: 2rem;
                    padding: 1rem 1.5rem;
                    background: ${{type === 'success' ? '#48bb78' : '#f56565'}};
                    color: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
                    z-index: 9999;
                    font-weight: 600;
                    animation: slideIn 0.3s ease;
                `;
                notification.innerHTML = `<i class="fas fa-${{type === 'success' ? 'check-circle' : 'exclamation-circle'}}"></i> ${{message}}`;
                document.body.appendChild(notification);
                
                setTimeout(() => {{
                    notification.style.animation = 'slideOut 0.3s ease';
                    setTimeout(() => notification.remove(), 300);
                }}, 3000);
            }}
            
            // Add animations
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideIn {{
                    from {{
                        transform: translateX(400px);
                        opacity: 0;
                    }}
                    to {{
                        transform: translateX(0);
                        opacity: 1;
                    }}
                }}
                
                @keyframes slideOut {{
                    from {{
                        transform: translateX(0);
                        opacity: 1;
                    }}
                    to {{
                        transform: translateX(400px);
                        opacity: 0;
                    }}
                }}
            `;
            document.head.appendChild(style);
        </script>
        """
        
        return HTMLResponse(content=create_html_page(f"Stats - {video.title}", content, "videos"))
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in video stats: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))