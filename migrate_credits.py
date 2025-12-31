import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def add_credits_column():
    """Add credits_on_completion column to quizzes table using direct PostgreSQL connection"""
    
    # Database connection parameters
    conn_params = {
        'host': 'localhost',
        'database': 'ke_junglore_db',
        'user': 'postgres',
        'password': 'devpassword',
        'port': 5432
    }
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("🔧 Checking if credits_on_completion column exists...")
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'quizzes' 
            AND column_name = 'credits_on_completion'
        """)
        
        exists = cursor.fetchone()
        
        if not exists:
            print("Adding credits_on_completion column to quizzes table...")
            cursor.execute("""
                ALTER TABLE quizzes 
                ADD COLUMN credits_on_completion INTEGER DEFAULT 50 NOT NULL
            """)
            print("✅ Successfully added credits_on_completion column")
            print("   Default value: 50 credits per quiz completion")
        else:
            print("✅ credits_on_completion column already exists")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Database Migration: Adding Credits Column")
    print("=" * 50)
    
    success = add_credits_column()
    
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")