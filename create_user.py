#!/usr/bin/env python3
"""
Simple script to create a user in the database
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password, UserRole
from app.models.models import User
from sqlalchemy import select


async def create_user():
    """Create a new user in the database."""
    # User details - change these as needed
    email = "admin@example.com"
    username = "admin"
    password = "password123"
    role = "admin"  # admin, developer, operator, viewer

    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"❌ User with email {email} already exists!")
            return

        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            print(f"❌ User with username {username} already exists!")
            return

        # Create user
        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            role=UserRole(role.lower()),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        print("✅ User created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   Role: {user.role.value}")
        print(f"   Password: {password}")


if __name__ == "__main__":
    asyncio.run(init_db())
    asyncio.run(create_user())