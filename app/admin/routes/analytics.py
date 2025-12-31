"""
Admin Analytics Routes
Provides analytics and insights for video performance
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from app.db.database import get_db_session
from app.models.video_series import VideoSeries, SeriesVideo
from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
from app.models.video_engagement import VideoComment, VideoLike
from app.admin.templates.base import create_html_page

router = APIRouter()


@router.get("/videos/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    request: Request, 
    period: str = "week",
    start_date_str: str = None,
    end_date_str: str = None
):
    """Analytics dashboard with charts and metrics"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        # Calculate date range based on period or custom dates
        now = datetime.utcnow()
        end_date = now
        
        if start_date_str and end_date_str:
            # Custom date range
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            period = "custom"
        elif period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        elif period == "year":
            start_date = now - timedelta(days=365)
        else:  # all-time
            start_date = datetime(2000, 1, 1)
        
        async with get_db_session() as session:
            # Get top videos by views
            series_views = await session.execute(
                select(
                    SeriesVideo.title,
                    SeriesVideo.views,
                    SeriesVideo.slug,
                    VideoSeries.title.label('series_name')
                )
                .join(VideoSeries, SeriesVideo.series_id == VideoSeries.id)
                .where(SeriesVideo.created_at >= start_date)
                .order_by(desc(SeriesVideo.views))
                .limit(10)
            )
            
            channel_views = await session.execute(
                select(
                    GeneralKnowledgeVideo.title,
                    GeneralKnowledgeVideo.views,
                    GeneralKnowledgeVideo.slug,
                    VideoChannel.name.label('channel_name')
                )
                .join(VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id)
                .where(GeneralKnowledgeVideo.created_at >= start_date)
                .order_by(desc(GeneralKnowledgeVideo.views))
                .limit(10)
            )
            
            # Combine and sort
            top_videos = []
            for video in series_views.all():
                top_videos.append({
                    'title': video.title,
                    'views': video.views,
                    'slug': video.slug,
                    'type': 'series',
                    'parent': video.series_name
                })
            
            for video in channel_views.all():
                top_videos.append({
                    'title': video.title,
                    'views': video.views,
                    'slug': video.slug,
                    'type': 'channel',
                    'parent': video.channel_name
                })
            
            top_videos.sort(key=lambda x: x['views'], reverse=True)
            top_videos = top_videos[:10]
            
            # Get most commented videos
            series_comments = await session.execute(
                select(
                    SeriesVideo.title,
                    SeriesVideo.slug,
                    VideoSeries.title.label('series_name'),
                    func.count(VideoComment.id).label('comment_count')
                )
                .join(VideoSeries, SeriesVideo.series_id == VideoSeries.id)
                .outerjoin(VideoComment, VideoComment.video_slug == SeriesVideo.slug)
                .where(SeriesVideo.created_at >= start_date)
                .group_by(SeriesVideo.id, SeriesVideo.title, SeriesVideo.slug, VideoSeries.title)
                .order_by(desc('comment_count'))
                .limit(10)
            )
            
            channel_comments = await session.execute(
                select(
                    GeneralKnowledgeVideo.title,
                    GeneralKnowledgeVideo.slug,
                    VideoChannel.name.label('channel_name'),
                    func.count(VideoComment.id).label('comment_count')
                )
                .join(VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id)
                .outerjoin(VideoComment, VideoComment.video_slug == GeneralKnowledgeVideo.slug)
                .where(GeneralKnowledgeVideo.created_at >= start_date)
                .group_by(GeneralKnowledgeVideo.id, GeneralKnowledgeVideo.title, GeneralKnowledgeVideo.slug, VideoChannel.name)
                .order_by(desc('comment_count'))
                .limit(10)
            )
            
            most_commented = []
            for video in series_comments.all():
                most_commented.append({
                    'title': video.title,
                    'slug': video.slug,
                    'comment_count': video.comment_count,
                    'type': 'series',
                    'parent': video.series_name
                })
            
            for video in channel_comments.all():
                most_commented.append({
                    'title': video.title,
                    'slug': video.slug,
                    'comment_count': video.comment_count,
                    'type': 'channel',
                    'parent': video.channel_name
                })
            
            most_commented.sort(key=lambda x: x['comment_count'], reverse=True)
            most_commented = most_commented[:10]
            
            # Get total stats
            total_series_views_result = await session.execute(
                select(func.sum(SeriesVideo.views))
            )
            total_series_views_value = total_series_views_result.scalar() or 0
            
            total_channel_views_result = await session.execute(
                select(func.sum(GeneralKnowledgeVideo.views))
            )
            total_channel_views_value = total_channel_views_result.scalar() or 0
            
            total_views = total_series_views_value + total_channel_views_value
            
            total_comments_result = await session.execute(
                select(func.count(VideoComment.id))
                .where(VideoComment.is_deleted == 0)
            )
            total_comments_count = total_comments_result.scalar() or 0
            
            total_likes_result = await session.execute(
                select(func.count(VideoLike.id))
                .where(VideoLike.vote == 1)
            )
            total_likes_count = total_likes_result.scalar() or 0
            
            total_dislikes_result = await session.execute(
                select(func.count(VideoLike.id))
                .where(VideoLike.vote == -1)
            )
            total_dislikes_count = total_dislikes_result.scalar() or 0
            
            # Get all recent comments (last 50) with user data eagerly loaded
            all_comments_result = await session.execute(
                select(VideoComment)
                .options(selectinload(VideoComment.user))
                .where(VideoComment.is_deleted == 0)
                .order_by(desc(VideoComment.created_at))
                .limit(50)
            )
            all_comments = all_comments_result.scalars().all()
            
            # Convert to dict to avoid lazy loading issues
            comments_data = []
            for comment in all_comments:
                comments_data.append({
                    'id': comment.id,
                    'content': comment.content,
                    'video_slug': comment.video_slug,
                    'created_at': comment.created_at,
                    'likes_count': comment.likes_count,
                    'parent_id': comment.parent_id,
                    'user_name': comment.user.full_name if comment.user else 'Anonymous',
                    'user_email': comment.user.email if comment.user else None
                })
            
            # Get total videos count
            total_series = await session.execute(select(func.count(SeriesVideo.id)))
            total_channel = await session.execute(select(func.count(GeneralKnowledgeVideo.id)))
            total_videos_count = (total_series.scalar() or 0) + (total_channel.scalar() or 0)
        
        # Build charts data
        top_videos_labels = [v['title'][:25] + '...' if len(v['title']) > 25 else v['title'] for v in top_videos]
        top_videos_data = [v['views'] for v in top_videos]
        
        most_commented_labels = [v['title'][:25] + '...' if len(v['title']) > 25 else v['title'] for v in most_commented]
        most_commented_data = [v['comment_count'] for v in most_commented]
        
        content = f"""
        <style>
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 1.25rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
                transition: transform 0.2s, box-shadow 0.2s;
                border-left: 4px solid;
            }}
            .stat-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
            }}
            .stat-icon {{
                width: 48px;
                height: 48px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                margin-bottom: 1rem;
            }}
            .stat-label {{
                font-size: 0.875rem;
                color: #64748b;
                margin-bottom: 0.5rem;
                font-weight: 500;
            }}
            .stat-value {{
                font-size: 2rem;
                font-weight: 700;
                color: #1e293b;
            }}
            .date-picker {{
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 2rem;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }}
            .chart-container {{
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
                margin-bottom: 2rem;
            }}
            .comments-section {{
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }}
            .comment-item {{
                padding: 1rem;
                border-bottom: 1px solid #e2e8f0;
                transition: background 0.2s;
            }}
            .comment-item:hover {{
                background: #f8fafc;
            }}
            .comment-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }}
            .comment-meta {{
                display: flex;
                gap: 1rem;
                font-size: 0.875rem;
                color: #64748b;
            }}
            .filter-tabs {{
                display: flex;
                gap: 0.5rem;
                margin-bottom: 1.5rem;
                border-bottom: 2px solid #e2e8f0;
            }}
            .filter-tab {{
                padding: 0.75rem 1.5rem;
                background: transparent;
                border: none;
                cursor: pointer;
                font-weight: 500;
                color: #64748b;
                border-bottom: 3px solid transparent;
                transition: all 0.2s;
            }}
            .filter-tab.active {{
                color: #667eea;
                border-bottom-color: #667eea;
            }}
            .custom-date-section {{
                display: none;
                gap: 1rem;
                align-items: end;
                margin-top: 1rem;
            }}
            .custom-date-section.active {{
                display: flex;
            }}
        </style>
        
        <div class="page-header">
            <div>
                <h1 class="page-title"><i class="fas fa-chart-line"></i> Analytics Dashboard</h1>
                <p class="page-subtitle">Comprehensive video performance and engagement metrics</p>
            </div>
            <a href="/admin/videos" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to Videos
            </a>
        </div>
        
        <!-- Date Filter -->
        <div class="date-picker">
            <div class="filter-tabs">
                <button class="filter-tab {{'active' if period == 'today' else ''}}" onclick="selectPeriod('today')">Today</button>
                <button class="filter-tab {{'active' if period == 'week' else ''}}" onclick="selectPeriod('week')">Last 7 Days</button>
                <button class="filter-tab {{'active' if period == 'month' else ''}}" onclick="selectPeriod('month')">Last 30 Days</button>
                <button class="filter-tab {{'active' if period == 'year' else ''}}" onclick="selectPeriod('year')">Last Year</button>
                <button class="filter-tab {{'active' if period == 'all' else ''}}" onclick="selectPeriod('all')">All Time</button>
                <button class="filter-tab {{'active' if period == 'custom' else ''}}" onclick="toggleCustomDate()">
                    <i class="fas fa-calendar-alt"></i> Custom Range
                </button>
            </div>
            
            <div id="customDateSection" class="custom-date-section {{'active' if period == 'custom' else ''}}">
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 500; color: #475569;">Start Date</label>
                    <input type="date" id="startDate" class="form-input" value="{start_date_str or ''}" style="width: auto;">
                </div>
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 500; color: #475569;">End Date</label>
                    <input type="date" id="endDate" class="form-input" value="{end_date_str or ''}" style="width: auto;">
                </div>
                <button class="btn btn-primary" onclick="applyCustomDate()">
                    <i class="fas fa-check"></i> Apply Range
                </button>
            </div>
        </div>
        
        <!-- Summary Stats -->
        <div class="stats-grid">
            <div class="stat-card" style="border-left-color: #667eea;">
                <div class="stat-icon" style="background: #ede9fe; color: #667eea;">
                    <i class="fas fa-video"></i>
                </div>
                <div class="stat-label">Total Videos</div>
                <div class="stat-value">{total_videos_count:,}</div>
            </div>
            
            <div class="stat-card" style="border-left-color: #4facfe;">
                <div class="stat-icon" style="background: #dbeafe; color: #4facfe;">
                    <i class="fas fa-eye"></i>
                </div>
                <div class="stat-label">Total Views</div>
                <div class="stat-value">{total_views:,}</div>
            </div>
            
            <div class="stat-card" style="border-left-color: #f093fb;">
                <div class="stat-icon" style="background: #fce7f3; color: #f093fb;">
                    <i class="fas fa-comments"></i>
                </div>
                <div class="stat-label">Total Comments</div>
                <div class="stat-value">{total_comments_count:,}</div>
            </div>
            
            <div class="stat-card" style="border-left-color: #38ef7d;">
                <div class="stat-icon" style="background: #d1fae5; color: #38ef7d;">
                    <i class="fas fa-thumbs-up"></i>
                </div>
                <div class="stat-label">Total Likes</div>
                <div class="stat-value">{total_likes_count:,}</div>
            </div>
            
            <div class="stat-card" style="border-left-color: #f5576c;">
                <div class="stat-icon" style="background: #fee2e2; color: #f5576c;">
                    <i class="fas fa-thumbs-down"></i>
                </div>
                <div class="stat-label">Total Dislikes</div>
                <div class="stat-value">{total_dislikes_count:,}</div>
            </div>
            
            <div class="stat-card" style="border-left-color: #ffd700;">
                <div class="stat-icon" style="background: #fef3c7; color: #fbbf24;">
                    <i class="fas fa-percentage"></i>
                </div>
                <div class="stat-label">Engagement Rate</div>
                <div class="stat-value">{(total_likes_count + total_comments_count) / max(total_views, 1) * 100:.1f}%</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
            <div class="chart-container">
                <h3 style="margin: 0 0 1.5rem 0; color: #1e293b; font-size: 1.125rem;">
                    <i class="fas fa-trophy" style="color: #667eea;"></i> Top Videos by Views
                </h3>
                <canvas id="viewsChart" style="max-height: 350px;"></canvas>
            </div>
            
            <div class="chart-container">
                <h3 style="margin: 0 0 1.5rem 0; color: #1e293b; font-size: 1.125rem;">
                    <i class="fas fa-comment-dots" style="color: #f093fb;"></i> Most Commented Videos
                </h3>
                <canvas id="commentsChart" style="max-height: 350px;"></canvas>
            </div>
        </div>
        
        <!-- Top Performing Videos Table -->
        <div class="chart-container" style="margin-bottom: 2rem;">
            <h3 style="margin: 0 0 1.5rem 0; color: #1e293b; font-size: 1.125rem;">
                <i class="fas fa-fire" style="color: #f5576c;"></i> Top Performing Videos
            </h3>
            <div style="overflow-x: auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="width: 60px;">Rank</th>
                            <th>Video Title</th>
                            <th style="width: 100px;">Type</th>
                            <th>Collection</th>
                            <th style="width: 120px;">Views</th>
                            <th style="width: 100px;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''
                        <tr>
                            <td>
                                <div style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 700; font-size: 0.875rem;">
                                    #{i+1}
                                </div>
                            </td>
                            <td><strong style="color: #1e293b;">{v['title']}</strong></td>
                            <td>
                                <span class="badge" style="background: {'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' if v['type'] == 'series' else 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'}; color: white; padding: 0.375rem 0.75rem; border-radius: 6px; font-size: 0.75rem;">
                                    {v['type'].title()}
                                </span>
                            </td>
                            <td style="color: #64748b;">{v['parent']}</td>
                            <td><strong style="color: #667eea;">{v['views']:,}</strong> views</td>
                            <td>
                                <a href="/admin/video/{v['slug']}/details" class="btn-icon" title="View Details" style="background: #ede9fe; color: #667eea; padding: 0.5rem; border-radius: 6px; text-decoration: none; display: inline-block;">
                                    <i class="fas fa-chart-bar"></i>
                                </a>
                            </td>
                        </tr>
                        ''' for i, v in enumerate(top_videos)])}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- All Comments Section -->
        <div class="comments-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="margin: 0; color: #1e293b; font-size: 1.125rem;">
                    <i class="fas fa-comments" style="color: #f093fb;"></i> Recent Comments 
                    <span style="color: #94a3b8; font-size: 0.875rem;">({len(all_comments)} latest)</span>
                </h3>
                <div>
                    <input type="text" id="commentSearch" placeholder="🔍 Search comments..." 
                        style="padding: 0.5rem 1rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.875rem;" 
                        onkeyup="filterComments()">
                </div>
            </div>
            
            <div id="commentsContainer">
                {"".join([f'''
                <div class="comment-item" data-comment-text="{comment['content'].lower() if comment['content'] else ''}" data-video="{comment['video_slug']}">
                    <div class="comment-header">
                        <div>
                            <strong style="color: #1e293b;">{comment['user_name']}</strong>
                            <span style="color: #94a3b8; font-size: 0.875rem; margin-left: 0.5rem;">
                                @{comment['user_email'].split('@')[0] if comment['user_email'] else 'user'}
                            </span>
                        </div>
                        <div class="comment-meta">
                            <span><i class="fas fa-video"></i> {comment['video_slug'][:30]}</span>
                            <span><i class="fas fa-clock"></i> {comment['created_at'].strftime('%b %d, %Y %I:%M %p') if comment['created_at'] else 'Unknown'}</span>
                        </div>
                    </div>
                    <p style="margin: 0.5rem 0; color: #475569; line-height: 1.6;">{comment['content'] if comment['content'] else '[No content]'}</p>
                    <div style="display: flex; gap: 1rem; align-items: center; margin-top: 0.75rem;">
                        <span style="color: #64748b; font-size: 0.875rem;">
                            <i class="fas fa-thumbs-up" style="color: #38ef7d;"></i> {comment['likes_count'] or 0} likes
                        </span>
                        {f'<span style="color: #64748b; font-size: 0.875rem;"><i class="fas fa-reply"></i> Reply to ID #{comment["parent_id"]}</span>' if comment['parent_id'] else ''}
                        <div style="margin-left: auto;">
                            <button class="btn-icon" onclick="deleteComment({comment['id']}, '{comment['video_slug']}')" 
                                style="background: #fee2e2; color: #f5576c; padding: 0.375rem 0.75rem; border-radius: 6px; border: none; cursor: pointer; font-size: 0.875rem; transition: all 0.2s;"
                                onmouseover="this.style.background='#fecaca'" onmouseout="this.style.background='#fee2e2'">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                </div>
                ''' for comment in comments_data]) if comments_data else '<p style="text-align: center; color: #94a3b8; padding: 2rem;">No comments found</p>'}
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            // Period selection
            function selectPeriod(period) {{
                window.location.href = '/admin/videos/analytics?period=' + period;
            }}
            
            // Toggle custom date picker
            function toggleCustomDate() {{
                const section = document.getElementById('customDateSection');
                section.classList.toggle('active');
                
                // Update active tab
                document.querySelectorAll('.filter-tab').forEach(tab => {{
                    tab.classList.remove('active');
                }});
                event.target.classList.add('active');
            }}
            
            // Apply custom date range
            function applyCustomDate() {{
                const startDate = document.getElementById('startDate').value;
                const endDate = document.getElementById('endDate').value;
                
                if (!startDate || !endDate) {{
                    alert('Please select both start and end dates');
                    return;
                }}
                
                window.location.href = `/admin/videos/analytics?period=custom&start_date_str=${{startDate}}&end_date_str=${{endDate}}`;
            }}
            
            // Filter comments
            function filterComments() {{
                const searchTerm = document.getElementById('commentSearch').value.toLowerCase();
                const comments = document.querySelectorAll('.comment-item');
                
                comments.forEach(comment => {{
                    const text = comment.getAttribute('data-comment-text');
                    const video = comment.getAttribute('data-video').toLowerCase();
                    
                    if (text.includes(searchTerm) || video.includes(searchTerm)) {{
                        comment.style.display = '';
                    }} else {{
                        comment.style.display = 'none';
                    }}
                }});
            }}
            
            // Delete comment
            async function deleteComment(commentId, videoSlug) {{
                if (!confirm('Are you sure you want to delete this comment? This action cannot be undone.')) {{
                    return;
                }}
                
                try {{
                    const response = await fetch(`/admin/video/comment/${{commentId}}/delete`, {{
                        method: 'POST'
                    }});
                    
                    if (response.ok) {{
                        alert('Comment deleted successfully');
                        location.reload();
                    }} else {{
                        alert('Failed to delete comment');
                    }}
                }} catch (error) {{
                    console.error('Error:', error);
                    alert('Error deleting comment');
                }}
            }}
            
            // Views Chart
            const viewsCtx = document.getElementById('viewsChart').getContext('2d');
            new Chart(viewsCtx, {{
                type: 'bar',
                data: {{
                    labels: {top_videos_labels},
                    datasets: [{{
                        label: 'Views',
                        data: {top_videos_data},
                        backgroundColor: 'rgba(102, 126, 234, 0.85)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 0,
                        borderRadius: 8,
                        barThickness: 40
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            cornerRadius: 8,
                            titleFont: {{
                                size: 14,
                                weight: 'bold'
                            }},
                            bodyFont: {{
                                size: 13
                            }},
                            callbacks: {{
                                label: function(context) {{
                                    return 'Views: ' + context.parsed.y.toLocaleString();
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{
                                color: 'rgba(0, 0, 0, 0.05)',
                                drawBorder: false
                            }},
                            ticks: {{
                                callback: function(value) {{
                                    return value.toLocaleString();
                                }},
                                font: {{
                                    size: 12
                                }},
                                color: '#64748b'
                            }}
                        }},
                        x: {{
                            grid: {{
                                display: false
                            }},
                            ticks: {{
                                font: {{
                                    size: 11
                                }},
                                color: '#64748b'
                            }}
                        }}
                    }}
                }}
            }});
            
            // Comments Chart
            const commentsCtx = document.getElementById('commentsChart').getContext('2d');
            new Chart(commentsCtx, {{
                type: 'bar',
                data: {{
                    labels: {most_commented_labels},
                    datasets: [{{
                        label: 'Comments',
                        data: {most_commented_data},
                        backgroundColor: 'rgba(245, 87, 108, 0.85)',
                        borderColor: 'rgba(245, 87, 108, 1)',
                        borderWidth: 0,
                        borderRadius: 8,
                        barThickness: 40
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            cornerRadius: 8,
                            titleFont: {{
                                size: 14,
                                weight: 'bold'
                            }},
                            bodyFont: {{
                                size: 13
                            }},
                            callbacks: {{
                                label: function(context) {{
                                    return 'Comments: ' + context.parsed.y.toLocaleString();
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{
                                color: 'rgba(0, 0, 0, 0.05)',
                                drawBorder: false
                            }},
                            ticks: {{
                                font: {{
                                    size: 12
                                }},
                                color: '#64748b'
                            }}
                        }},
                        x: {{
                            grid: {{
                                display: false
                            }},
                            ticks: {{
                                font: {{
                                    size: 11
                                }},
                                color: '#64748b'
                            }}
                        }}
                    }}
                }}
            }});
        </script>
        """
        
        return create_html_page("Analytics Dashboard", content)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return create_html_page("Error", f"""
            <div class="card">
                <h2 style="color: #dc2626; margin-bottom: 1rem;">
                    <i class="fas fa-exclamation-triangle"></i> Error Loading Analytics
                </h2>
                <p style="color: #64748b;">An error occurred while loading the analytics dashboard:</p>
                <pre style="background: #f8fafc; padding: 1rem; border-radius: 8px; overflow-x: auto; color: #dc2626; margin-top: 1rem;">{str(e)}</pre>
                <a href="/admin/videos" class="btn btn-primary" style="margin-top: 1.5rem; text-decoration: none;">
                    <i class="fas fa-arrow-left"></i> Back to Videos
                </a>
            </div>
        """)