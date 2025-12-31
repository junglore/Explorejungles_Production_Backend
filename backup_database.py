"""
Quick backup script for database
Run this before syncing with colleague's files
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

def backup_database():
    """Create a backup of the database"""
    
    # Configuration
    db_name = "Junglore_KE"
    db_user = "postgres"
    backup_dir = Path("database_backups")
    
    # Create backup directory if it doesn't exist
    backup_dir.mkdir(exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{db_name}_{timestamp}.sql"
    
    print("=" * 70)
    print("💾 DATABASE BACKUP")
    print("=" * 70)
    print(f"\nDatabase: {db_name}")
    print(f"Backup to: {backup_file}")
    print("\nStarting backup...")
    
    try:
        # Run pg_dump
        cmd = [
            "pg_dump",
            "-U", db_user,
            "-d", db_name,
            "-f", str(backup_file),
            "--clean",  # Include DROP commands
            "--if-exists",  # Use IF EXISTS
            "--no-owner",  # Don't include ownership commands
            "--no-privileges"  # Don't include privilege commands
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            file_size = backup_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            print("\n✅ Backup completed successfully!")
            print(f"\nBackup file: {backup_file}")
            print(f"File size: {file_size_mb:.2f} MB")
            
            # List all backups
            backups = sorted(backup_dir.glob("*.sql"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            print(f"\n📁 Available backups ({len(backups)}):")
            for i, backup in enumerate(backups[:5], 1):
                size = backup.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"  {i}. {backup.name}")
                print(f"     Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"     Size: {size:.2f} MB")
            
            if len(backups) > 5:
                print(f"  ... and {len(backups) - 5} more")
            
            print("\n" + "=" * 70)
            print("💡 TO RESTORE THIS BACKUP:")
            print("=" * 70)
            print(f"\npsql -U postgres -d {db_name} < {backup_file}")
            print("\n" + "=" * 70)
            
            return True
            
        else:
            print("\n❌ Backup failed!")
            print(f"\nError: {result.stderr}")
            print("\n💡 Make sure PostgreSQL is running and credentials are correct")
            return False
            
    except FileNotFoundError:
        print("\n❌ pg_dump not found!")
        print("\n💡 Make sure PostgreSQL is installed and in your PATH")
        print("   Add to PATH: C:\\Program Files\\PostgreSQL\\[version]\\bin")
        return False
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def list_backups():
    """List all available backups"""
    backup_dir = Path("database_backups")
    
    if not backup_dir.exists():
        print("No backups found")
        return
    
    backups = sorted(backup_dir.glob("*.sql"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not backups:
        print("No backups found")
        return
    
    print("\n📁 Available Backups:")
    for i, backup in enumerate(backups, 1):
        size = backup.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"\n{i}. {backup.name}")
        print(f"   Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Size: {size:.2f} MB")
        print(f"   Path: {backup.absolute()}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_backups()
    else:
        print("\n⚠️  IMPORTANT: Backing up database before syncing with colleague")
        print("This is ESSENTIAL before running migrations!\n")
        
        success = backup_database()
        
        if success:
            print("\n✅ Ready to sync!")
            print("\nNext steps:")
            print("1. Run: python compare_migrations.py path\\to\\their\\versions")
            print("2. Run: python generate_sync_report.py")
            print("3. Run: alembic upgrade head (or alembic stamp head)")
        else:
            print("\n⚠️  Backup failed! Fix the error before proceeding.")
            sys.exit(1)
