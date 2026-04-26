#!/usr/bin/env python3
"""
Database management script for Smart DevOps Assistant
- Create users
- View database contents
- Reset database
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password, UserRole
from app.models.models import User
from sqlalchemy import select

TEST_USERS = [
    {
        "email": "viewer@example.com",
        "username": "viewer",
        "password": "viewer123",
        "role": "viewer",
    },
    {
        "email": "developer@example.com",
        "username": "developer",
        "password": "developer123",
        "role": "developer",
    },
    {
        "email": "engineer@example.com",
        "username": "engineer",
        "password": "engineer123",
        "role": "engineer",
    },
    {
        "email": "operator@example.com",
        "username": "operator",
        "password": "operator123",
        "role": "operator",
    },
    {
        "email": "admin@example.com",
        "username": "admin",
        "password": "admin123",
        "role": "admin",
    },
]


async def create_user(email: str, username: str, password: str, role: str = "developer"):
    """Create a new user in the database."""
    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"ERROR: User with email {email} already exists!")
            return

        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            print(f"ERROR: User with username {username} already exists!")
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

        print("User created successfully.")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   Role: {user.role.value}")


async def seed_test_users():
    """Create or update the standard test users for every role."""
    async with AsyncSessionLocal() as db:
        for user_data in TEST_USERS:
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
                f"{action.upper():7} {user_data['username']:10} "
                f"({user_data['role']}) / {user_data['password']}"
            )

        await db.commit()


async def list_users():
    """List all users in the database."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print("No users found in database.")
            return

        print("Users in database:")
        print("-" * 60)
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Username: {user.username}")
            print(f"Role: {user.role.value}")
            print(f"Active: {user.is_active}")
            print("-" * 60)


async def reset_database():
    """Reset the database (drop all tables and recreate)."""
    from app.core.database import engine, Base

    print("WARNING: This will delete all data!")
    confirm = input("Are you sure? Type 'YES' to continue: ")
    if confirm != "YES":
        print("Operation cancelled.")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("Database reset complete.")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_db.py <command> [args...]")
        print("\nCommands:")
        print("  create-user <email> <username> <password> [role]")
        print("  seed-test-users")
        print("  list-users")
        print("  reset-db")
        print("\nExamples:")
        print("  python manage_db.py create-user admin@example.com admin password123 admin")
        print("  python manage_db.py seed-test-users")
        print("  python manage_db.py list-users")
        print("  python manage_db.py reset-db")
        return

    command = sys.argv[1]

    # Initialize database
    await init_db()

    if command == "create-user":
        if len(sys.argv) < 5:
            print("Usage: create-user <email> <username> <password> [role]")
            return
        email, username, password = sys.argv[2:5]
        role = sys.argv[5] if len(sys.argv) > 5 else "developer"
        await create_user(email, username, password, role)

    elif command == "seed-test-users":
        await seed_test_users()

    elif command == "list-users":
        await list_users()

    elif command == "reset-db":
        await reset_database()

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
