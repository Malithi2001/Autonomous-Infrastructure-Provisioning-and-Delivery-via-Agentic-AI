#!/usr/bin/env python3
"""
Diagnostic script to debug login issues
- Check if user exists
- Verify password hash
- Check user status
"""
import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import verify_password, hash_password, UserRole
from app.models.models import User
from sqlalchemy import select


async def diagnose():
    """Diagnose login issues."""
    await init_db()
    
    async with AsyncSessionLocal() as db:
        # List all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        print("=" * 70)
        print("📋 USERS IN DATABASE")
        print("=" * 70)
        
        if not users:
            print("❌ NO USERS FOUND IN DATABASE!")
            print("\nYou need to create a user first. Use this command:")
            print("  python manage_db.py create-user admin@example.com admin password123 admin")
            return
        
        for user in users:
            print(f"\n👤 User: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role.value}")
            print(f"   Active: {user.is_active}")
            print(f"   ID: {user.id}")
            print(f"   Hashed Password: {user.hashed_password[:20]}...")
            
            # Test password verification
            test_password = "password123"
            is_valid = verify_password(test_password, user.hashed_password)
            print(f"   Password '{test_password}' matches: {is_valid}")
        
        print("\n" + "=" * 70)
        print("🔍 TROUBLESHOOTING")
        print("=" * 70)
        
        # Check specific issues
        for user in users:
            issues = []
            
            if not user.is_active:
                issues.append("❌ User is INACTIVE - needs to be set to active")
            
            if not verify_password("password123", user.hashed_password):
                issues.append("❌ Password 'password123' does NOT match stored hash")
            
            if issues:
                print(f"\n⚠️  Issues with user '{user.username}':")
                for issue in issues:
                    print(f"   {issue}")
            else:
                print(f"\n✅ User '{user.username}' looks good for login!")
                print(f"   Try logging in with:")
                print(f"   Username: {user.username}")
                print(f"   Password: password123")


if __name__ == "__main__":
    asyncio.run(diagnose())