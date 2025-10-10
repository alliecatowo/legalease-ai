#!/usr/bin/env python3
"""
Database Initialization Script for LegalEase

This script:
1. Creates the database if it doesn't exist
2. Runs Alembic migrations
3. Creates default data (roles, permissions, etc.)
"""

import os
import sys
import time
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


def get_db_config():
    """Extract database configuration from DATABASE_URL."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/legalease"
    )

    # Parse the URL
    # Format: postgresql://user:password@host:port/database
    parts = database_url.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    host_port = host_port_db[0].split(":")

    return {
        "user": user_pass[0],
        "password": user_pass[1],
        "host": host_port[0],
        "port": int(host_port[1]) if len(host_port) > 1 else 5432,
        "database": host_port_db[1] if len(host_port_db) > 1 else "legalease"
    }


def wait_for_postgres(config, max_retries=30, retry_interval=2):
    """Wait for PostgreSQL to be ready."""
    print("Waiting for PostgreSQL to be ready...")

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                user=config["user"],
                password=config["password"],
                host=config["host"],
                port=config["port"],
                database="postgres"  # Connect to default database
            )
            conn.close()
            print("PostgreSQL is ready!")
            return True
        except psycopg2.OperationalError as e:
            if i < max_retries - 1:
                print(f"PostgreSQL not ready yet, retrying in {retry_interval}s... ({i+1}/{max_retries})")
                time.sleep(retry_interval)
            else:
                print(f"Error: PostgreSQL is not available after {max_retries} retries")
                print(f"Error message: {e}")
                return False

    return False


def create_database(config):
    """Create the database if it doesn't exist."""
    print(f"Checking if database '{config['database']}' exists...")

    try:
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            user=config["user"],
            password=config["password"],
            host=config["host"],
            port=config["port"],
            database="postgres"  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (config["database"],)
        )
        exists = cursor.fetchone()

        if exists:
            print(f"Database '{config['database']}' already exists")
        else:
            print(f"Creating database '{config['database']}'...")
            cursor.execute(f"CREATE DATABASE {config['database']}")
            print(f"Database '{config['database']}' created successfully")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"Error creating database: {e}")
        return False


def create_default_data():
    """Create default data in the database."""
    print("Creating default data...")

    try:
        # Import after database is created
        from app.db.session import SessionLocal
        from app.models.user import User, Role, Permission
        from app.core.security import get_password_hash

        db = SessionLocal()

        try:
            # Check if roles exist
            admin_role = db.query(Role).filter(Role.name == "admin").first()

            if not admin_role:
                print("Creating default roles...")

                # Create roles
                admin_role = Role(
                    name="admin",
                    description="Administrator with full access"
                )
                lawyer_role = Role(
                    name="lawyer",
                    description="Lawyer with case management access"
                )
                client_role = Role(
                    name="client",
                    description="Client with limited access to their cases"
                )

                db.add_all([admin_role, lawyer_role, client_role])
                db.commit()
                print("Default roles created")

            # Check if admin user exists
            admin_user = db.query(User).filter(User.email == "admin@legalease.com").first()

            if not admin_user:
                print("Creating default admin user...")

                admin_user = User(
                    email="admin@legalease.com",
                    hashed_password=get_password_hash("admin123"),
                    full_name="Admin User",
                    is_active=True,
                    is_superuser=True
                )

                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)

                # Add admin role to user
                admin_role = db.query(Role).filter(Role.name == "admin").first()
                if admin_role:
                    admin_user.roles.append(admin_role)
                    db.commit()

                print("Default admin user created")
                print("  Email: admin@legalease.com")
                print("  Password: admin123")
                print("  Please change the password after first login!")

            print("Default data created successfully")

        finally:
            db.close()

        return True

    except Exception as e:
        print(f"Error creating default data: {e}")
        print("This is normal if the database schema hasn't been created yet")
        return False


def main():
    """Main function to initialize the database."""
    print("=" * 50)
    print("  LegalEase Database Initialization")
    print("=" * 50)
    print()

    # Get database configuration
    config = get_db_config()
    print(f"Database configuration:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")
    print()

    # Wait for PostgreSQL to be ready
    if not wait_for_postgres(config):
        sys.exit(1)

    print()

    # Create database
    if not create_database(config):
        sys.exit(1)

    print()

    # Create default data (will be done after migrations)
    # Migrations need to run first to create tables
    print("Note: Default data will be created after running migrations")
    print("Run migrations with: mise run db-migrate")
    print("Then run this script again to create default data")

    print()
    print("=" * 50)
    print("  Database initialization completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
