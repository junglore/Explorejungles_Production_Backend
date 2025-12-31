"""add discussion forum system with varchar enums

Revision ID: 013_add_discussion_forum_v2
Revises: 010_add_oauth_fields
Create Date: 2025-10-28 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '013_add_discussion_forum_v2'
down_revision = '010_add_oauth_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Add community fields to users table if they don't exist
    if 'users' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'organization' not in existing_columns:
            op.add_column('users', sa.Column('organization', sa.String(length=200), nullable=True))
        if 'professional_title' not in existing_columns:
            op.add_column('users', sa.Column('professional_title', sa.String(length=200), nullable=True))
        if 'discussion_count' not in existing_columns:
            op.add_column('users', sa.Column('discussion_count', sa.Integer(), nullable=False, server_default='0'))
        if 'comment_count' not in existing_columns:
            op.add_column('users', sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'))
        if 'reputation_score' not in existing_columns:
            op.add_column('users', sa.Column('reputation_score', sa.Integer(), nullable=False, server_default='0'))

    # Create user_badges table if it doesn't exist
    if 'user_badges' not in existing_tables:
        op.execute("""
            CREATE TABLE user_badges (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                slug VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                color VARCHAR(20),
                icon VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.create_index('ix_user_badges_name', 'user_badges', ['name'])
        op.create_index('ix_user_badges_slug', 'user_badges', ['slug'])
        op.create_index('ix_user_badges_is_active', 'user_badges', ['is_active'])

    # Create user_badge_assignments table if it doesn't exist
    if 'user_badge_assignments' not in existing_tables:
        op.execute("""
            CREATE TABLE user_badge_assignments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                badge_id UUID NOT NULL REFERENCES user_badges(id) ON DELETE CASCADE,
                assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
                assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                note TEXT,
                CONSTRAINT uq_user_badge UNIQUE (user_id, badge_id)
            )
        """)
        op.create_index('ix_badge_assignments_user', 'user_badge_assignments', ['user_id', 'assigned_at'])
        op.create_index('ix_badge_assignments_badge', 'user_badge_assignments', ['badge_id', 'assigned_at'])

    # Create discussions table if it doesn't exist
    if 'discussions' not in existing_tables:
        op.execute("""
            CREATE TABLE discussions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
                type VARCHAR(50) NOT NULL DEFAULT 'thread',
                title VARCHAR(500) NOT NULL,
                slug VARCHAR(600) NOT NULL UNIQUE,
                content TEXT NOT NULL,
                excerpt TEXT,
                park_name VARCHAR(200),
                location VARCHAR(200),
                banner_image VARCHAR(500),
                media_url VARCHAR(500),
                tags TEXT[] DEFAULT '{}',
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                is_pinned BOOLEAN NOT NULL DEFAULT false,
                is_locked BOOLEAN NOT NULL DEFAULT false,
                rejection_reason TEXT,
                reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMPTZ,
                view_count INTEGER NOT NULL DEFAULT 0,
                like_count INTEGER NOT NULL DEFAULT 0,
                comment_count INTEGER NOT NULL DEFAULT 0,
                reply_count INTEGER NOT NULL DEFAULT 0,
                last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                published_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                content_metadata JSONB DEFAULT '{}'
            )
        """)
        
        # Create indexes for discussions
        op.create_index('ix_discussions_title', 'discussions', ['title'])
        op.create_index('ix_discussions_slug', 'discussions', ['slug'])
        op.create_index('ix_discussions_author_id', 'discussions', ['author_id'])
        op.create_index('ix_discussions_category_id', 'discussions', ['category_id'])
        op.create_index('ix_discussions_type', 'discussions', ['type'])
        op.create_index('ix_discussions_status', 'discussions', ['status'])
        op.create_index('ix_discussions_is_pinned', 'discussions', ['is_pinned'])
        op.create_index('ix_discussions_view_count', 'discussions', ['view_count'])
        op.create_index('ix_discussions_comment_count', 'discussions', ['comment_count'])
        op.create_index('ix_discussions_last_activity_at', 'discussions', ['last_activity_at'])
        op.create_index('ix_discussions_published_at', 'discussions', ['published_at'])
        op.create_index('ix_discussions_park_name', 'discussions', ['park_name'])
        op.create_index('ix_discussions_status_activity', 'discussions', ['status', 'last_activity_at'])
        op.create_index('ix_discussions_category_status', 'discussions', ['category_id', 'status', 'created_at'])
        op.create_index('ix_discussions_type_status', 'discussions', ['type', 'status', 'created_at'])
        op.create_index('ix_discussions_pinned_status', 'discussions', ['is_pinned', 'status', 'created_at'])
        op.create_index('ix_discussions_park_status', 'discussions', ['park_name', 'status', 'created_at'])
        op.create_index('ix_discussions_engagement', 'discussions', ['status', 'like_count', 'comment_count'])

    # Create discussion_comments table if it doesn't exist
    if 'discussion_comments' not in existing_tables:
        op.execute("""
            CREATE TABLE discussion_comments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                discussion_id UUID NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
                author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                parent_comment_id UUID REFERENCES discussion_comments(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                depth_level INTEGER NOT NULL DEFAULT 0,
                path VARCHAR(500),
                like_count INTEGER NOT NULL DEFAULT 0,
                dislike_count INTEGER NOT NULL DEFAULT 0,
                reply_count INTEGER NOT NULL DEFAULT 0,
                is_edited BOOLEAN NOT NULL DEFAULT false,
                edited_at TIMESTAMPTZ,
                is_flagged BOOLEAN NOT NULL DEFAULT false,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        
        # Create indexes for comments
        op.create_index('ix_discussion_comments_discussion_id', 'discussion_comments', ['discussion_id'])
        op.create_index('ix_discussion_comments_author_id', 'discussion_comments', ['author_id'])
        op.create_index('ix_discussion_comments_parent_comment_id', 'discussion_comments', ['parent_comment_id'])
        op.create_index('ix_discussion_comments_path', 'discussion_comments', ['path'])
        op.create_index('ix_discussion_comments_is_flagged', 'discussion_comments', ['is_flagged'])
        op.create_index('ix_discussion_comments_status', 'discussion_comments', ['status'])
        op.create_index('ix_discussion_comments_created_at', 'discussion_comments', ['created_at'])
        op.create_index('ix_comments_discussion_created', 'discussion_comments', ['discussion_id', 'status', 'created_at'])
        op.create_index('ix_comments_parent_created', 'discussion_comments', ['parent_comment_id', 'status', 'created_at'])
        op.create_index('ix_comments_author_status', 'discussion_comments', ['author_id', 'status', 'created_at'])
        op.create_index('ix_comments_flagged', 'discussion_comments', ['is_flagged', 'status', 'created_at'])

    # Create discussion_likes table if it doesn't exist
    if 'discussion_likes' not in existing_tables:
        op.execute("""
            CREATE TABLE discussion_likes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                discussion_id UUID NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_discussion_like_user UNIQUE (discussion_id, user_id)
            )
        """)
        op.create_index('ix_discussion_likes_user', 'discussion_likes', ['user_id', 'created_at'])
        op.create_index('ix_discussion_likes_discussion', 'discussion_likes', ['discussion_id', 'created_at'])

    # Create comment_votes table if it doesn't exist
    if 'comment_votes' not in existing_tables:
        op.execute("""
            CREATE TABLE comment_votes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                comment_id UUID NOT NULL REFERENCES discussion_comments(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                vote_type VARCHAR(20) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_comment_vote_user UNIQUE (comment_id, user_id)
            )
        """)
        op.create_index('ix_comment_votes_user', 'comment_votes', ['user_id', 'vote_type', 'created_at'])
        op.create_index('ix_comment_votes_comment', 'comment_votes', ['comment_id', 'vote_type'])

    # Create discussion_views table if it doesn't exist
    if 'discussion_views' not in existing_tables:
        op.execute("""
            CREATE TABLE discussion_views (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                discussion_id UUID NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                ip_address VARCHAR(45),
                viewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.create_index('ix_discussion_views_unique', 'discussion_views', ['discussion_id', 'user_id'])
        op.create_index('ix_discussion_views_ip', 'discussion_views', ['discussion_id', 'ip_address', 'viewed_at'])

    # Create discussion_saves table if it doesn't exist
    if 'discussion_saves' not in existing_tables:
        op.execute("""
            CREATE TABLE discussion_saves (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                discussion_id UUID NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_discussion_save_user UNIQUE (discussion_id, user_id)
            )
        """)
        op.create_index('ix_discussion_saves_user', 'discussion_saves', ['user_id', 'created_at'])

    # Create discussion_reports table if it doesn't exist
    if 'discussion_reports' not in existing_tables:
        op.execute("""
            CREATE TABLE discussion_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                discussion_id UUID REFERENCES discussions(id) ON DELETE CASCADE,
                comment_id UUID REFERENCES discussion_comments(id) ON DELETE CASCADE,
                reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                report_type VARCHAR(50) NOT NULL,
                reason TEXT NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
                reviewed_at TIMESTAMPTZ,
                admin_notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.create_index('ix_discussion_reports_status', 'discussion_reports', ['status'])
        op.create_index('ix_reports_status_created', 'discussion_reports', ['status', 'created_at'])
        op.create_index('ix_reports_discussion', 'discussion_reports', ['discussion_id', 'status'])
        op.create_index('ix_reports_comment', 'discussion_reports', ['comment_id', 'status'])
        op.create_index('ix_reports_reporter', 'discussion_reports', ['reporter_id', 'created_at'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop tables in reverse order if they exist
    if 'discussion_reports' in existing_tables:
        op.drop_table('discussion_reports')
    if 'discussion_saves' in existing_tables:
        op.drop_table('discussion_saves')
    if 'discussion_views' in existing_tables:
        op.drop_table('discussion_views')
    if 'comment_votes' in existing_tables:
        op.drop_table('comment_votes')
    if 'discussion_likes' in existing_tables:
        op.drop_table('discussion_likes')
    if 'discussion_comments' in existing_tables:
        op.drop_table('discussion_comments')
    if 'discussions' in existing_tables:
        op.drop_table('discussions')
    if 'user_badge_assignments' in existing_tables:
        op.drop_table('user_badge_assignments')
    if 'user_badges' in existing_tables:
        op.drop_table('user_badges')
    
    # Remove columns from users table if they exist
    if 'users' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        if 'reputation_score' in existing_columns:
            op.drop_column('users', 'reputation_score')
        if 'comment_count' in existing_columns:
            op.drop_column('users', 'comment_count')
        if 'discussion_count' in existing_columns:
            op.drop_column('users', 'discussion_count')
        if 'professional_title' in existing_columns:
            op.drop_column('users', 'professional_title')
        if 'organization' in existing_columns:
            op.drop_column('users', 'organization')