"""
Compare migration files between two directories
Use this when colleague gives you their alembic/versions folder
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def extract_revision_id(filename):
    """Extract revision ID from migration filename"""
    return filename.split('_')[0]

def compare_migrations(your_dir, their_dir):
    """Compare migration files between two directories"""
    
    print("=" * 80)
    print("🔍 MIGRATION FILES COMPARISON")
    print("=" * 80)
    print(f"\nYour directory:  {your_dir}")
    print(f"Their directory: {their_dir}")
    
    # Get migration files
    your_files = {f.name: f for f in Path(your_dir).glob("*.py") if not f.name.startswith("__")}
    their_files = {f.name: f for f in Path(their_dir).glob("*.py") if not f.name.startswith("__")}
    
    # Files only in your directory
    only_yours = set(your_files.keys()) - set(their_files.keys())
    # Files only in their directory
    only_theirs = set(their_files.keys()) - set(your_files.keys())
    # Files in both
    in_both = set(your_files.keys()) & set(their_files.keys())
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total in your directory:   {len(your_files)}")
    print(f"  Total in their directory:  {len(their_files)}")
    print(f"  Only in yours:             {len(only_yours)}")
    print(f"  Only in theirs:            {len(only_theirs)}")
    print(f"  In both:                   {len(in_both)}")
    
    # Check for conflicts
    print("\n" + "=" * 80)
    print("📁 FILES ONLY IN YOUR DIRECTORY (Your local changes)")
    print("=" * 80)
    if only_yours:
        for filename in sorted(only_yours):
            revision_id = extract_revision_id(filename)
            print(f"  ⚠️  {filename[:70]}")
            print(f"      → Revision: {revision_id}")
            print(f"      → Action: KEEP IT or share with colleague\n")
    else:
        print("  ✅ None (good - means you don't have uncommitted migrations)\n")
    
    print("=" * 80)
    print("📁 FILES ONLY IN THEIR DIRECTORY (New from colleague)")
    print("=" * 80)
    if only_theirs:
        for filename in sorted(only_theirs):
            revision_id = extract_revision_id(filename)
            print(f"  🆕 {filename[:70]}")
            print(f"      → Revision: {revision_id}")
            print(f"      → Action: COPY THIS to your alembic/versions/\n")
    else:
        print("  ✅ None (you already have all their migrations)\n")
    
    print("=" * 80)
    print("📁 FILES IN BOTH DIRECTORIES")
    print("=" * 80)
    if in_both:
        conflicts = []
        for filename in sorted(in_both):
            your_file = your_files[filename]
            their_file = their_files[filename]
            
            # Compare file sizes as quick check
            your_size = your_file.stat().st_size
            their_size = their_file.stat().st_size
            
            if your_size != their_size:
                conflicts.append((filename, your_size, their_size))
                print(f"  ⚠️  {filename[:70]}")
                print(f"      → CONFLICT: Different file sizes!")
                print(f"      → Your version:  {your_size} bytes")
                print(f"      → Their version: {their_size} bytes")
                print(f"      → Action: MANUALLY COMPARE FILES\n")
            else:
                print(f"  ✅ {filename[:70]}")
        
        if conflicts:
            print("\n" + "!" * 80)
            print(f"⚠️  WARNING: {len(conflicts)} file(s) with conflicts detected!")
            print("!" * 80)
    else:
        print("  None\n")
    
    print("\n" + "=" * 80)
    print("💡 RECOMMENDED ACTIONS")
    print("=" * 80)
    
    if only_theirs:
        print("\n1️⃣  COPY NEW FILES FROM COLLEAGUE:")
        print("   PowerShell command:")
        print(f"   Copy-Item '{their_dir}\\*.py' -Destination '{your_dir}' -Exclude '__init__.py'")
        print("\n   Or manually copy these files:")
        for filename in sorted(only_theirs):
            print(f"   - {filename}")
    
    if only_yours:
        print("\n2️⃣  YOUR LOCAL MIGRATIONS (share with colleague):")
        for filename in sorted(only_yours):
            print(f"   - {filename}")
        print("\n   Consider sharing these back to your colleague!")
    
    if in_both and not any(your_files[f].stat().st_size != their_files[f].stat().st_size for f in in_both):
        print("\n✅ All common files match - no conflicts!")
    
    print("\n3️⃣  AFTER COPYING NEW FILES:")
    print("   Run: python sync_manual_migrations.py")
    print("   Then: alembic upgrade head")
    print("\n" + "=" * 80)

def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_migrations.py <their_alembic_versions_folder>")
        print("\nExample:")
        print("  python compare_migrations.py D:\\colleague\\alembic\\versions")
        print("  python compare_migrations.py \"F:\\USB Drive\\project\\alembic\\versions\"")
        sys.exit(1)
    
    your_dir = "alembic/versions"
    their_dir = sys.argv[1]
    
    if not os.path.exists(your_dir):
        print(f"❌ Error: Your alembic/versions directory not found: {your_dir}")
        sys.exit(1)
    
    if not os.path.exists(their_dir):
        print(f"❌ Error: Their directory not found: {their_dir}")
        sys.exit(1)
    
    compare_migrations(your_dir, their_dir)

if __name__ == "__main__":
    main()
