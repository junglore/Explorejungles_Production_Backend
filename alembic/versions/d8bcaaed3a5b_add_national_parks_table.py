"""Add national parks table

Revision ID: d8bcaaed3a5b
Revises: 013_add_discussion_forum_v2
Create Date: 2025-10-31 12:31:02.069201

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8bcaaed3a5b'
down_revision = '013_add_discussion_forum_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Ensure uuid-ossp extension is enabled
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Check if table exists
    existing_tables = inspector.get_table_names()
    
    # Create national_parks table if it doesn't exist
    if 'national_parks' not in existing_tables:
        op.create_table(
            'national_parks',
            sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('slug', sa.String(length=250), nullable=False),
            sa.Column('state', sa.String(length=100), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
            sa.UniqueConstraint('slug')
        )
        
        # Create indexes for performance
        op.create_index('ix_national_parks_name', 'national_parks', ['name'])
        op.create_index('ix_national_parks_slug', 'national_parks', ['slug'])
        
        # Add some default national parks
        op.execute("""
            INSERT INTO national_parks (name, slug, state, description, is_active) VALUES
            ('Jim Corbett National Park', 'jim-corbett-national-park', 'Uttarakhand', 'India''s oldest national park, famous for Bengal tigers', true),
            ('Kaziranga National Park', 'kaziranga-national-park', 'Assam', 'UNESCO World Heritage Site, home to one-horned rhinoceros', true),
            ('Ranthambore National Park', 'ranthambore-national-park', 'Rajasthan', 'Famous for tiger sightings and historic fort ruins', true),
            ('Bandhavgarh National Park', 'bandhavgarh-national-park', 'Madhya Pradesh', 'Known for highest density of Bengal tigers', true),
            ('Kanha National Park', 'kanha-national-park', 'Madhya Pradesh', 'Inspiration for Kipling''s Jungle Book', true),
            ('Sundarbans National Park', 'sundarbans-national-park', 'West Bengal', 'UNESCO World Heritage Site, largest mangrove forest', true),
            ('Periyar National Park', 'periyar-national-park', 'Kerala', 'Famous for elephant and tiger reserve', true),
            ('Gir National Park', 'gir-national-park', 'Gujarat', 'Only home of Asiatic lions', true),
            ('Hemis National Park', 'hemis-national-park', 'Ladakh', 'India''s largest national park, home to snow leopards', true),
            ('Bandipur National Park', 'bandipur-national-park', 'Karnataka', 'Part of Nilgiri Biosphere Reserve', true)
        """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_national_parks_slug', table_name='national_parks')
    op.drop_index('ix_national_parks_name', table_name='national_parks')
    
    # Drop table
    op.drop_table('national_parks')