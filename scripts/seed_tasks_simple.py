#!/usr/bin/env python3
"""Simple task seeding script that avoids complex imports."""

import asyncio
import sys
import os
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Direct database connection
DATABASE_URL = os.getenv("VIT_DATABASE_URL") or "sqlite+aiosqlite:///./vit.db"

async def seed_tasks():
    """Seed tasks directly with SQL."""

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Create categories
            categories = [
                (1, "Getting Started", "Basic tasks to help new users get familiar with the platform", "🚀", "blue", 1),
                (2, "Engagement", "Tasks that encourage active platform participation", "🎯", "green", 2),
                (3, "Expertise", "Advanced tasks for experienced users", "🧠", "purple", 3),
                (4, "Community", "Tasks that contribute to the community", "🤝", "orange", 4),
                (5, "Achievements", "Special milestone tasks", "🏆", "gold", 5)
            ]

            for cat_id, name, desc, icon, color, sort_order in categories:
                await session.execute(text("""
                    INSERT OR IGNORE INTO task_categories
                    (id, name, description, icon, color, sort_order, is_active, created_at)
                    VALUES (:id, :name, :desc, :icon, :color, :sort_order, 1, CURRENT_TIMESTAMP)
                """), {"id": cat_id, "name": name, "desc": desc, "icon": icon, "color": color, "sort_order": sort_order})

            # Create tasks
            tasks = [
                (1, 1, "Complete Your Profile", "Fill out your profile information to personalize your experience", "Set up your user profile", "one_time", 1, 1, 5.0, 50, "👤", 1, "{}", None, None, None, 0),
                (2, 1, "Make Your First Prediction", "Place your first sports prediction to start earning rewards", "Place your first prediction", "one_time", 1, 1, 10.0, 100, "🎲", 1, "{}", None, None, None, 0),
                (3, 1, "Explore the Dashboard", "Take a tour of the dashboard to understand available features", "Explore the platform dashboard", "one_time", 1, 1, 2.0, 25, "📊", 0, "{}", None, None, None, 0),
                (4, 2, "Daily Predictions", "Make at least 3 predictions in a single day", "Make 3 predictions daily", "daily", 3, 1, 15.0, 75, "📅", 0, "{}", None, None, None, 0),
                (5, 2, "Weekly Streaker", "Make predictions for 7 consecutive days", "Predict for 7 days straight", "progress", 7, 1, 50.0, 250, "🔥", 0, "{}", None, None, None, 0),
                (6, 2, "Wallet Explorer", "Explore all wallet features including deposits and transfers", "Try all wallet features", "one_time", 1, 1, 8.0, 60, "💰", 0, "{}", None, None, None, 0),
                (7, 3, "Accuracy Champion", "Achieve 70% or higher prediction accuracy over 20 predictions", "Reach 70% prediction accuracy", "progress", 20, 1, 100.0, 500, "🎯", 0, '{"min_accuracy": 0.7}', None, None, None, 0),
                (8, 3, "Market Analyst", "Analyze odds from multiple bookmakers for 10 different matches", "Compare odds from 10 matches", "progress", 10, 1, 25.0, 150, "📈", 0, "{}", None, None, None, 0),
                (9, 3, "Model Trainer", "Participate in model training sessions", "Help train AI models", "one_time", 1, 1, 20.0, 120, "🤖", 0, "{}", None, None, None, 0),
                (10, 4, "Referral Master", "Successfully refer 5 new users to the platform", "Refer 5 new users", "progress", 5, 1, 75.0, 300, "👥", 0, "{}", None, None, None, 0),
                (11, 4, "Feedback Provider", "Provide constructive feedback through the platform", "Give platform feedback", "one_time", 1, 1, 5.0, 30, "💬", 0, "{}", None, None, None, 0),
                (12, 4, "Governance Participant", "Vote on governance proposals", "Participate in governance", "one_time", 1, 1, 10.0, 80, "🗳️", 0, "{}", None, None, None, 0),
                (13, 5, "Century Club", "Earn 100 XP through task completion", "Reach 100 total XP", "progress", 100, 1, 30.0, 100, "💯", 1, "{}", None, None, None, 0),
                (14, 5, "VIT Millionaire", "Accumulate 1000 VIT in your wallet", "Earn 1000 VIT total", "progress", 1000, 1, 200.0, 1000, "💎", 1, "{}", None, None, None, 0),
                (15, 5, "Platform Veteran", "Be active on the platform for 30 consecutive days", "30 days of activity", "progress", 30, 1, 150.0, 750, "👑", 1, "{}", None, None, None, 0)
            ]

            for task_data in tasks:
                task_dict = {
                    "id": task_data[0], "category_id": task_data[1], "title": task_data[2],
                    "description": task_data[3], "short_description": task_data[4], "task_type": task_data[5],
                    "required_count": task_data[6], "max_completions": task_data[7], "vit_reward": task_data[8],
                    "xp_reward": task_data[9], "icon": task_data[10], "is_featured": task_data[11],
                    "requirements": task_data[12], "expires_at": task_data[13], "color": task_data[15],
                    "sort_order": task_data[16]
                }
                await session.execute(text("""
                    INSERT OR IGNORE INTO tasks
                    (id, category_id, title, description, short_description, task_type, required_count, max_completions, vit_reward, xp_reward, icon, is_featured, requirements, expires_at, color, sort_order, status, created_by, created_at)
                    VALUES (:id, :category_id, :title, :description, :short_description, :task_type, :required_count, :max_completions, :vit_reward, :xp_reward, :icon, :is_featured, :requirements, :expires_at, :color, :sort_order, 'active', 1, CURRENT_TIMESTAMP)
                """), task_dict)

            await session.commit()
            print("✅ Task seeding completed successfully!")

        except Exception as e:
            print(f"❌ Error seeding tasks: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(seed_tasks())