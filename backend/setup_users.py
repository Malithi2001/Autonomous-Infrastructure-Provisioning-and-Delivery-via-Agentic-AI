#!/usr/bin/env python3
"""
Complete setup script to:
1. Create or update test users for all roles
2. Verify they can be found and passwords work
"""
import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password, UserRole, verify_password
from app.models.models import User
from sqlalchemy import select


async def setup_test_users():
    """Create or update test users without deleting unrelated data."""
    
    # Initialize DB
    await init_db()
    
    print("=" * 70)
    print("SETTING UP TEST USERS")
    print("=" * 70)
    
    test_users = [
        {
            "email": "admin@example.com",
            "username": "admin",
            "password": "admin123",
            "role": "admin"
        },
        {
            "email": "viewer@example.com",
            "username": "viewer",
            "password": "viewer123",
            "role": "viewer"
        },
        {
            "email": "developer@example.com",
            "username": "developer", 
            "password": "developer123",
            "role": "developer"
        },
        {
            "email": "engineer@example.com",
            "username": "engineer",
            "password": "engineer123", 
            "role": "engineer"
        },
        {
            "email": "operator@example.com",
            "username": "operator",
            "password": "operator123",
            "role": "operator"
        },
    ]
    
    print("\nSyncing test users...\n")
    
    async with AsyncSessionLocal() as db:
        for user_data in test_users:
            result = await db.execute(
                select(User).where(User.username == user_data["username"])
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    hashed_password=hash_password(user_data["password"]),
                    role=UserRole(user_data["role"]),
                    is_active=True,
                )
                db.add(user)
                action = "created"
            else:
                user.email = user_data["email"]
                user.hashed_password = hash_password(user_data["password"])
                user.role = UserRole(user_data["role"])
                user.is_active = True
                action = "updated"

            print(
                f"   {action.upper():7} {user_data['role']:10} - "
                f"{user_data['username']:12} / {user_data['password']}"
            )
        
        await db.commit()
    
    # Verify users were created and passwords work
    print("\n" + "=" * 70)
    print("VERIFYING LOGIN CREDENTIALS")
    print("=" * 70 + "\n")
    
    async with AsyncSessionLocal() as db:
        for user_data in test_users:
            result = await db.execute(select(User).where(User.username == user_data["username"]))
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"ERROR {user_data['username']:12} - NOT FOUND IN DATABASE!")
                continue
            
            if not user.is_active:
                print(f"ERROR {user_data['username']:12} - USER IS INACTIVE!")
                continue
            
            password_match = verify_password(user_data["password"], user.hashed_password)
            
            if password_match:
                print(f"OK    {user_data['role']:10} - {user_data['username']:12} / {user_data['password']:15} PASSWORD OK")
            else:
                print(f"ERROR {user_data['username']:12} - PASSWORD DOES NOT MATCH!")
    
    print("\n" + "=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    print("\nYou can now login at: http://localhost:5175")
    print("\nTest credentials:")
    for user_data in test_users:
        print(f"  {user_data['username']:12} / {user_data['password']}")


if __name__ == "__main__":
    asyncio.run(setup_test_users())
