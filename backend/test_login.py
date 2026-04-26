#!/usr/bin/env python3
"""
Test login credentials directly against the backend
"""
import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import verify_password, UserRole
from app.models.models import User
from sqlalchemy import select


async def test_login():
    """Test login with actual database."""
    await init_db()
    
    # Test credentials
    test_username = "admin"
    test_password = "password123"
    
    async with AsyncSessionLocal() as db:
        # Try to find user
        result = await db.execute(select(User).where(User.username == test_username))
        user = result.scalar_one_or_none()
        
        print("=" * 70)
        print("🔐 LOGIN TEST")
        print("=" * 70)
        
        if not user:
            print(f"❌ User '{test_username}' NOT FOUND in database!")
            print("\nTo create a user, run:")
            print(f"  python manage_db.py create-user admin@example.com {test_username} {test_password} admin")
            return False
        
        print(f"✅ User '{test_username}' found in database")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role.value}")
        print(f"   Active: {user.is_active}")
        
        # Check if user is active
        if not user.is_active:
            print(f"\n❌ User is INACTIVE - cannot login!")
            return False
        
        # Verify password
        password_match = verify_password(test_password, user.hashed_password)
        print(f"\n✅ Password verification: {password_match}")
        
        if password_match:
            print(f"\n✅✅✅ LOGIN WORKS!")
            print(f"   Username: {test_username}")
            print(f"   Password: {test_password}")
            print(f"\nTry logging in at: http://localhost:5175")
            return True
        else:
            print(f"\n❌ Password DOES NOT MATCH!")
            print(f"   Stored hash: {user.hashed_password[:30]}...")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_login())
    sys.exit(0 if success else 1)