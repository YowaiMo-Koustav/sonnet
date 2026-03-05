"""add fulltext search index

Revision ID: 20260223_1832
Revises: 20260224_1400
Create Date: 2026-02-23 18:32:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260223_1832'
down_revision = '20260224_1400'
branch_labels = None
depends_on = None


def upgrade():
    """Add full-text search capabilities to schemes table."""
    # Check if we're using PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # Enable pg_trgm extension for fuzzy matching
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        
        # Add tsvector column for full-text search
        op.add_column('schemes', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR))
        
        # Create GIN index on the tsvector column for fast full-text search
        op.execute("""
            CREATE INDEX idx_schemes_search_vector ON schemes USING GIN(search_vector)
        """)
        
        # Create trigger to automatically update search_vector when name or description changes
        op.execute("""
            CREATE OR REPLACE FUNCTION schemes_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := 
                    setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        op.execute("""
            CREATE TRIGGER schemes_search_vector_trigger
            BEFORE INSERT OR UPDATE ON schemes
            FOR EACH ROW
            EXECUTE FUNCTION schemes_search_vector_update();
        """)
        
        # Update existing rows
        op.execute("""
            UPDATE schemes SET search_vector = 
                setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(description, '')), 'B')
        """)


def downgrade():
    """Remove full-text search capabilities."""
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        # Drop trigger and function
        op.execute("DROP TRIGGER IF EXISTS schemes_search_vector_trigger ON schemes")
        op.execute("DROP FUNCTION IF EXISTS schemes_search_vector_update()")
        
        # Drop index
        op.execute("DROP INDEX IF EXISTS idx_schemes_search_vector")
        
        # Drop column
        op.drop_column('schemes', 'search_vector')
