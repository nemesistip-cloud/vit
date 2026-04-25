#!/usr/bin/env python
"""Seed initial task categories and tasks for the task system."""

import asyncio
import sys
import os
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.modules.tasks.models import TaskCategory, Task, TaskType, TaskStatus


async def seed_task_data():
    """Seed initial task categories and tasks."""

    async with AsyncSessionLocal() as db:
        try:
            # Create task categories
            categories_data = [
                {
                    "name": "Getting Started",
                    "description": "Basic tasks to help new users get familiar with the platform",
                    "icon": "🚀",
                    "color": "blue",
                    "sort_order": 1
                },
                {
                    "name": "Engagement",
                    "description": "Tasks that encourage active platform participation",
                    "icon": "🎯",
                    "color": "green",
                    "sort_order": 2
                },
                {
                    "name": "Expertise",
                    "description": "Advanced tasks for experienced users",
                    "icon": "🧠",
                    "color": "purple",
                    "sort_order": 3
                },
                {
                    "name": "Community",
                    "description": "Tasks that contribute to the community",
                    "icon": "🤝",
                    "color": "orange",
                    "sort_order": 4
                },
                {
                    "name": "Achievements",
                    "description": "Special milestone tasks",
                    "icon": "🏆",
                    "color": "gold",
                    "sort_order": 5
                }
            ]

            categories = []
            for cat_data in categories_data:
                # Check if category already exists
                result = await db.execute(
                    select(TaskCategory).where(TaskCategory.name == cat_data["name"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    categories.append(existing)
                    continue

                category = TaskCategory(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    icon=cat_data["icon"],
                    color=cat_data["color"],
                    sort_order=cat_data["sort_order"]
                )
                db.add(category)
                categories.append(category)
                print(f"Created category: {category.name}")

            # Create tasks
            tasks_data = [
                # Getting Started
                {
                    "category_id": 1,
                    "title": "Complete Your Profile",
                    "description": "Fill out your profile information to personalize your experience",
                    "short_description": "Set up your user profile",
                    "task_type": TaskType.ONE_TIME.value,
                    "vit_reward": Decimal("5.0"),
                    "xp_reward": 50,
                    "required_count": 1,
                    "icon": "👤",
                    "is_featured": True
                },
                {
                    "category_id": 1,
                    "title": "Make Your First Prediction",
                    "description": "Place your first sports prediction to start earning rewards",
                    "short_description": "Place your first prediction",
                    "task_type": TaskType.ONE_TIME.value,
                    "vit_reward": Decimal("10.0"),
                    "xp_reward": 100,
                    "required_count": 1,
                    "icon": "🎲",
                    "is_featured": True
                },
                {
                    "category_id": 1,
                    "title": "Explore the Dashboard",
                    "description": "Take a tour of the dashboard to understand available features",
                    "short_description": "Explore the platform dashboard",
                    "task_type": TaskType.ONE_TIME.value,
                    "vit_reward": Decimal("2.0"),
                    "xp_reward": 25,
                    "required_count": 1,
                    "icon": "📊"
                },

                # Engagement
                {
                    "category_id": 2,
                    "title": "Daily Predictions",
                    "description": "Make at least 3 predictions in a single day",
                    "short_description": "Make 3 predictions daily",
                    "task_type": TaskType.DAILY.value,
                    "vit_reward": Decimal("15.0"),
                    "xp_reward": 75,
                    "required_count": 3,
                    "icon": "📅",
                    "requirements": {"streak_bonus": 0.05}
                },
                {
                    "category_id": 2,
                    "title": "Weekly Streaker",
                    "description": "Make predictions for 7 consecutive days",
                    "short_description": "Predict for 7 days straight",
                    "task_type": TaskType.PROGRESS.value,
                    "vit_reward": Decimal("50.0"),
                    "xp_reward": 250,
                    "required_count": 7,
                    "icon": "🔥",
                    "requirements": {"reward_multiplier": 1.25}
                },
                {
                    "category_id": 2,
                    "title": "Wallet Explorer",
                    "description": "Explore all wallet features including deposits and transfers",
                    "short_description": "Try all wallet features",
                    "task_type": TaskType.ONE_TIME.value,
                    "vit_reward": Decimal("8.0"),
                    "xp_reward": 60,
                    "required_count": 1,
                    "icon": "💰"
                },

                # Expertise
                {
                    "category_id": 3,
                    "title": "Accuracy Champion",
                    "description": "Achieve 70% or higher prediction accuracy over 20 predictions",
                    "short_description": "Reach 70% prediction accuracy",
                    "task_type": TaskType.PROGRESS.value,
                    "vit_reward": Decimal("100.0"),
                    "xp_reward": 500,
                    "required_count": 20,
                    "icon": "🎯",
                    "requirements": {"min_accuracy": 0.7}
                },
                {
                    "category_id": 3,
                    "title": "Market Analyst",
                    "description": "Analyze odds from multiple bookmakers for 10 different matches",
                    "short_description": "Compare odds from 10 matches",
                    "task_type": TaskType.PROGRESS.value,
                    "vit_reward": Decimal("25.0"),
                    "xp_reward": 150,
                    "required_count": 10,
                    "icon": "📈"
                },
                {
                    "category_id": 3,
                    "title": "Model Trainer",
                    "description": "Participate in model training sessions",
                    "short_description": "Help train AI models",
                    "task_type": TaskType.ONE_TIME.value,
                    "vit_reward": Decimal("20.0"),
                    "xp_reward": 120,
                    "required_count": 1,
                    "icon": "🤖"
                },

                # Community
                {
                    "category_id": 4,
                    "title": "Referral Master",
                    "description": "Successfully refer 5 new users to the platform",
                    "short_description": "Refer 5 new users",
                    "task_type": TaskType.PROGRESS.value,
                    "vit_reward": Decimal("75.0"),
                    "xp_reward": 300,
                    "required_count": 5,
                    "icon": "👥"
                },
                {
                    "category_id": 4,
                    "title": "Feedback Provider",
                    "description": "Provide constructive feedback through the platform",
                    "short_description": "Give platform feedback",
                    "task_type": TaskType.ONE_TIME.value,
                    "vit_reward": Decimal("5.0"),
                    "xp_reward": 30,
                    "required_count": 1,
                    "icon": "💬"
                },
                {
                    "category_id": 4,
                    "title": "Governance Participant",
                    "description": "Vote on governance proposals",
                    "short_description": "Participate in governance",
                    "task_type": TaskType.ONE_TIME.value,
                    "vit_reward": Decimal("10.0"),
                    "xp_reward": 80,
                    "required_count": 1,
                    "icon": "🗳️"
                },

                # Achievements
                {
                    "category_id": 5,
                    "title": "Century Club",
                    "description": "Earn 100 XP through task completion",
                    "short_description": "Reach 100 total XP",
                    "task_type": TaskType.PROGRESS.value,
                    "vit_reward": Decimal("30.0"),
                    "xp_reward": 100,
                    "required_count": 100,
                    "icon": "💯",
                    "is_featured": True
                },
                {
                    "category_id": 5,
                    "title": "VIT Millionaire",
                    "description": "Accumulate 1000 VIT in your wallet",
                    "short_description": "Earn 1000 VIT total",
                    "task_type": TaskType.PROGRESS.value,
                    "vit_reward": Decimal("200.0"),
                    "xp_reward": 1000,
                    "required_count": 1000,
                    "icon": "💎",
                    "is_featured": True
                },
                {
                    "category_id": 5,
                    "title": "Platform Veteran",
                    "description": "Be active on the platform for 30 consecutive days",
                    "short_description": "30 days of activity",
                    "task_type": TaskType.PROGRESS.value,
                    "vit_reward": Decimal("150.0"),
                    "xp_reward": 750,
                    "required_count": 30,
                    "icon": "👑",
                    "is_featured": True
                }
            ]

            for task_data in tasks_data:
                # Check if task already exists (by title)
                result = await db.execute(
                    select(Task).where(Task.title == task_data["title"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    continue

                task = Task(
                    category_id=task_data["category_id"],
                    title=task_data["title"],
                    description=task_data["description"],
                    task_type=task_data["task_type"],
                    vit_reward=task_data["vit_reward"],
                    xp_reward=task_data["xp_reward"],
                    created_by=1,  # Assuming admin user ID 1
                    short_description=task_data.get("short_description"),
                    required_count=task_data["required_count"],
                    icon=task_data.get("icon"),
                    is_featured=task_data.get("is_featured", False),
                    requirements=task_data.get("requirements", {})
                )
                db.add(task)
                print(f"Created task: {task.title}")

            await db.commit()
            print("Task seeding completed successfully!")

        except Exception as e:
            print(f"Error seeding task data: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_task_data())