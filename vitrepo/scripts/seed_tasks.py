#!/usr/bin/env python
"""Seed initial task categories and tasks for the task system.

Usage:
    python scripts/seed_tasks.py [--admin-id 1]

The script is fully idempotent — re-running it will not create duplicates.
"""

import asyncio
import argparse
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.database import AsyncSessionLocal

# Import ALL models upfront so SQLAlchemy can resolve all mapper relationships
import app.db.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.tasks.models  # noqa: F401
import app.modules.blockchain.models  # noqa: F401
import app.modules.wallet.models  # noqa: F401
import app.modules.trust.models  # noqa: F401
import app.modules.referral.models  # noqa: F401
import app.modules.marketplace.models  # noqa: F401
import app.modules.did.models  # noqa: F401
import app.modules.network.models  # noqa: F401
import app.modules.governance.models  # noqa: F401

from app.modules.tasks.models import TaskCategory, Task, TaskType, TaskStatus


CATEGORIES_DATA = [
    {"name": "Getting Started",      "description": "Basic tasks to help new users get familiar with the platform", "icon": "Rocket",    "color": "blue",   "sort_order": 1},
    {"name": "Predictions",          "description": "Make and track match predictions",                             "icon": "Target",    "color": "green",  "sort_order": 2},
    {"name": "Staking & Blockchain", "description": "Engage with the VITCoin staking system",                      "icon": "Coins",     "color": "yellow", "sort_order": 3},
    {"name": "Social & Referrals",   "description": "Invite friends and grow the community",                       "icon": "Users",     "color": "purple", "sort_order": 4},
    {"name": "Analytics",            "description": "Explore advanced analytics tools",                            "icon": "BarChart2", "color": "cyan",   "sort_order": 5},
    {"name": "Governance",           "description": "Participate in DAO governance",                               "icon": "Vote",      "color": "orange", "sort_order": 6},
    {"name": "Validator",            "description": "Become a trusted validator node",                             "icon": "Shield",    "color": "red",    "sort_order": 7},
    {"name": "Daily Missions",       "description": "Complete daily tasks for bonus VIT",                          "icon": "Calendar",  "color": "teal",   "sort_order": 8},
    {"name": "Engagement",           "description": "Tasks that encourage active platform participation",           "icon": "Zap",       "color": "indigo", "sort_order": 9},
    {"name": "Achievements",         "description": "Special milestone tasks",                                     "icon": "Trophy",    "color": "gold",   "sort_order": 10},
]

TASKS_DATA = [
    # Getting Started
    {"category": "Getting Started", "title": "Complete Your Profile",
     "description": "Fill in your username, avatar, and bio in your profile settings.",
     "short_description": "Set up your profile",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("50"), "xp_reward": 100,
     "icon": "User", "color": "blue", "is_featured": True,
     "action_url": "/profile", "action_label": "Go to Profile"},

    {"category": "Getting Started", "title": "Enable Two-Factor Authentication",
     "description": "Secure your account by enabling TOTP 2FA in your security settings.",
     "short_description": "Enable 2FA",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("100"), "xp_reward": 200,
     "icon": "Shield", "color": "green",
     "action_url": "/settings/security", "action_label": "Enable 2FA"},

    {"category": "Getting Started", "title": "Connect Your Wallet",
     "description": "Create or connect your VITCoin wallet to start staking and earning.",
     "short_description": "Set up wallet",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("75"), "xp_reward": 150,
     "icon": "Wallet", "color": "yellow",
     "action_url": "/wallet", "action_label": "Open Wallet"},

    {"category": "Getting Started", "title": "Make Your First Prediction",
     "description": "Use the prediction engine to generate your very first match prediction.",
     "short_description": "First prediction",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("25"), "xp_reward": 50,
     "icon": "Zap", "color": "blue", "is_featured": True,
     "action_url": "/matches", "action_label": "Browse Matches"},

    {"category": "Getting Started", "title": "Explore the Dashboard",
     "description": "Take a tour of the dashboard to understand all available features.",
     "short_description": "Explore the platform dashboard",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("10"), "xp_reward": 25,
     "icon": "LayoutDashboard", "color": "blue",
     "action_url": "/", "action_label": "Go to Dashboard"},

    # Predictions
    {"category": "Predictions", "title": "Make 10 Predictions",
     "description": "Generate predictions for 10 different matches using any strategy.",
     "short_description": "10 predictions",
     "task_type": TaskType.PROGRESS.value, "required_count": 10,
     "vit_reward": Decimal("150"), "xp_reward": 300,
     "icon": "Target", "color": "green",
     "action_url": "/matches", "action_label": "Predict Now"},

    {"category": "Predictions", "title": "Make 50 Predictions",
     "description": "Reach 50 total predictions to prove your analytical commitment.",
     "short_description": "50 predictions",
     "task_type": TaskType.PROGRESS.value, "required_count": 50,
     "vit_reward": Decimal("500"), "xp_reward": 1000,
     "icon": "TrendingUp", "color": "green",
     "action_url": "/matches", "action_label": "Predict Now"},

    {"category": "Predictions", "title": "Achieve 60%+ Accuracy on 20 Settled Predictions",
     "description": "Demonstrate real predictive skill — hit 60%+ accuracy across 20 settled bets.",
     "short_description": "60% accuracy",
     "task_type": TaskType.PROGRESS.value, "required_count": 20,
     "vit_reward": Decimal("750"), "xp_reward": 1500,
     "icon": "Award", "color": "yellow", "is_featured": True,
     "action_url": "/history", "action_label": "View History"},

    # Staking & Blockchain
    {"category": "Staking & Blockchain", "title": "Place Your First Stake",
     "description": "Stake any amount of VITCoin on a match consensus prediction.",
     "short_description": "First stake",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("50"), "xp_reward": 100,
     "icon": "Coins", "color": "yellow",
     "action_url": "/matches", "action_label": "Stake Now"},

    {"category": "Staking & Blockchain", "title": "Stake on 5 Different Matches",
     "description": "Place stakes on at least 5 different match predictions.",
     "short_description": "Stake on 5 matches",
     "task_type": TaskType.PROGRESS.value, "required_count": 5,
     "vit_reward": Decimal("200"), "xp_reward": 400,
     "icon": "Layers", "color": "yellow",
     "action_url": "/matches", "action_label": "Browse Matches"},

    {"category": "Staking & Blockchain", "title": "Win a Stake Payout",
     "description": "Place a stake that wins and receive your first VITCoin payout.",
     "short_description": "Win a stake",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("100"), "xp_reward": 250,
     "icon": "Trophy", "color": "gold", "is_featured": True,
     "action_url": "/wallet", "action_label": "View Stakes"},

    {"category": "Staking & Blockchain", "title": "Become a Validator",
     "description": "Register as a VIT network validator by staking the minimum 500 VIT.",
     "short_description": "Register as validator",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("1000"), "xp_reward": 2000,
     "icon": "Shield", "color": "red", "is_featured": True,
     "action_url": "/validators", "action_label": "Become Validator"},

    # Social & Referrals
    {"category": "Social & Referrals", "title": "Invite Your First Friend",
     "description": "Share your referral link and have one friend sign up to the platform.",
     "short_description": "First referral",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("250"), "xp_reward": 500,
     "icon": "UserPlus", "color": "purple",
     "action_url": "/referrals", "action_label": "Get Referral Link"},

    {"category": "Social & Referrals", "title": "Refer 5 Friends",
     "description": "Build your network — invite 5 friends who complete profile setup.",
     "short_description": "5 referrals",
     "task_type": TaskType.PROGRESS.value, "required_count": 5,
     "vit_reward": Decimal("1000"), "xp_reward": 2000,
     "icon": "Users", "color": "purple",
     "action_url": "/referrals", "action_label": "Refer Friends"},

    # Analytics
    {"category": "Analytics", "title": "View the CLV Dashboard",
     "description": "Visit the Closing Line Value analytics dashboard to understand market efficiency.",
     "short_description": "Explore CLV",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("30"), "xp_reward": 60,
     "icon": "BarChart2", "color": "cyan",
     "action_url": "/analytics", "action_label": "Open Analytics"},

    {"category": "Analytics", "title": "Export Your Prediction History",
     "description": "Download a full CSV export of your prediction history for analytics.",
     "short_description": "Export history",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("50"), "xp_reward": 75,
     "icon": "Download", "color": "cyan",
     "action_url": "/exports", "action_label": "Export Now"},

    {"category": "Analytics", "title": "Market Analyst",
     "description": "Analyze odds from multiple bookmakers for 10 different matches.",
     "short_description": "Compare odds from 10 matches",
     "task_type": TaskType.PROGRESS.value, "required_count": 10,
     "vit_reward": Decimal("25"), "xp_reward": 150,
     "icon": "TrendingUp", "color": "cyan",
     "action_url": "/matches", "action_label": "Browse Odds"},

    # Governance
    {"category": "Governance", "title": "Cast Your First Governance Vote",
     "description": "Vote on an active VIT DAO proposal using your VIT token balance.",
     "short_description": "First vote",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("100"), "xp_reward": 200,
     "icon": "Vote", "color": "orange",
     "action_url": "/governance", "action_label": "Vote Now"},

    {"category": "Governance", "title": "Submit a Governance Proposal",
     "description": "Create and submit a governance proposal for the VIT community to vote on.",
     "short_description": "Create proposal",
     "task_type": TaskType.ONE_TIME.value, "vit_reward": Decimal("500"), "xp_reward": 1000,
     "icon": "FileText", "color": "orange", "is_featured": True,
     "action_url": "/governance/new", "action_label": "Create Proposal"},

    # Validator
    {"category": "Validator", "title": "Submit 10 Validator Predictions",
     "description": "Submit 10 match predictions as an active validator node.",
     "short_description": "10 validator predictions",
     "task_type": TaskType.PROGRESS.value, "required_count": 10,
     "vit_reward": Decimal("300"), "xp_reward": 600,
     "icon": "CheckCircle", "color": "red",
     "action_url": "/validators", "action_label": "Submit Predictions"},

    {"category": "Validator", "title": "Achieve 70%+ Validator Accuracy",
     "description": "Maintain a trust score above 0.70 after at least 20 settled predictions.",
     "short_description": "70% validator accuracy",
     "task_type": TaskType.PROGRESS.value, "required_count": 20,
     "vit_reward": Decimal("2000"), "xp_reward": 4000,
     "icon": "Star", "color": "gold", "is_featured": True,
     "action_url": "/validators", "action_label": "View Validator Stats"},

    # Daily Missions
    {"category": "Daily Missions", "title": "Daily Login Bonus",
     "description": "Log in to the VIT platform each day to claim your daily VIT reward.",
     "short_description": "Daily login",
     "task_type": TaskType.DAILY.value, "max_completions": 365, "reset_period_days": 1,
     "vit_reward": Decimal("5"), "xp_reward": 10,
     "icon": "Sun", "color": "teal",
     "action_url": "/", "action_label": "Claim Daily"},

    {"category": "Daily Missions", "title": "Daily Prediction Challenge",
     "description": "Make at least one prediction every day to maintain your streak.",
     "short_description": "Daily prediction",
     "task_type": TaskType.DAILY.value, "max_completions": 365, "reset_period_days": 1,
     "vit_reward": Decimal("10"), "xp_reward": 20,
     "icon": "Zap", "color": "teal",
     "action_url": "/matches", "action_label": "Predict Today"},

    {"category": "Daily Missions", "title": "Daily Predictions (3/day)",
     "description": "Make at least 3 predictions in a single day for a bonus reward.",
     "short_description": "Make 3 predictions daily",
     "task_type": TaskType.DAILY.value, "required_count": 3,
     "max_completions": 365, "reset_period_days": 1,
     "vit_reward": Decimal("15"), "xp_reward": 75,
     "icon": "Calendar", "color": "teal",
     "action_url": "/matches", "action_label": "Predict Now"},

    # Engagement
    {"category": "Engagement", "title": "Weekly Streaker",
     "description": "Make predictions for 7 consecutive days.",
     "short_description": "Predict for 7 days straight",
     "task_type": TaskType.PROGRESS.value, "required_count": 7,
     "vit_reward": Decimal("50"), "xp_reward": 250,
     "icon": "Flame", "color": "orange",
     "action_url": "/matches", "action_label": "Keep Streak"},

    {"category": "Engagement", "title": "Wallet Explorer",
     "description": "Explore all wallet features including deposits, transfers and history.",
     "short_description": "Try all wallet features",
     "task_type": TaskType.ONE_TIME.value,
     "vit_reward": Decimal("8"), "xp_reward": 60,
     "icon": "Wallet2", "color": "indigo",
     "action_url": "/wallet", "action_label": "Open Wallet"},

    {"category": "Engagement", "title": "Model Trainer",
     "description": "Participate in model training sessions to improve the AI prediction engine.",
     "short_description": "Help train AI models",
     "task_type": TaskType.ONE_TIME.value,
     "vit_reward": Decimal("20"), "xp_reward": 120,
     "icon": "Brain", "color": "indigo",
     "action_url": "/training", "action_label": "Start Training"},

    # Achievements
    {"category": "Achievements", "title": "Century Club",
     "description": "Earn 100 XP through task completion.",
     "short_description": "Reach 100 total XP",
     "task_type": TaskType.PROGRESS.value, "required_count": 100,
     "vit_reward": Decimal("30"), "xp_reward": 100,
     "icon": "Medal", "color": "gold", "is_featured": True,
     "action_url": "/tasks", "action_label": "View Tasks"},

    {"category": "Achievements", "title": "VIT Millionaire",
     "description": "Accumulate 1000 VIT in your wallet through earnings and rewards.",
     "short_description": "Earn 1000 VIT total",
     "task_type": TaskType.PROGRESS.value, "required_count": 1000,
     "vit_reward": Decimal("200"), "xp_reward": 1000,
     "icon": "Diamond", "color": "gold", "is_featured": True,
     "action_url": "/wallet", "action_label": "View Wallet"},

    {"category": "Achievements", "title": "Platform Veteran",
     "description": "Be active on the platform for 30 consecutive days.",
     "short_description": "30 days of activity",
     "task_type": TaskType.PROGRESS.value, "required_count": 30,
     "vit_reward": Decimal("150"), "xp_reward": 750,
     "icon": "Crown", "color": "gold", "is_featured": True,
     "action_url": "/", "action_label": "Stay Active"},

    {"category": "Achievements", "title": "Feedback Provider",
     "description": "Provide constructive feedback through the platform feedback system.",
     "short_description": "Give platform feedback",
     "task_type": TaskType.ONE_TIME.value,
     "vit_reward": Decimal("5"), "xp_reward": 30,
     "icon": "MessageSquare", "color": "indigo",
     "action_url": "/feedback", "action_label": "Give Feedback"},
]


async def seed_task_data(admin_id: int = 1):
    """Seed initial task categories and tasks. Fully idempotent."""
    async with AsyncSessionLocal() as db:
        try:
            # Verify admin user exists
            from app.db.models import User
            user_res = await db.execute(select(User).where(User.id == admin_id))
            admin_user = user_res.scalar_one_or_none()
            if not admin_user:
                print(f"ERROR: No user with id={admin_id}. Run with --admin-id <valid_user_id>")
                print("       Tip: Try --admin-id 1 or check the users table.")
                return

            cat_map: dict[str, int] = {}
            cats_created = 0

            for cat_data in CATEGORIES_DATA:
                result = await db.execute(
                    select(TaskCategory).where(TaskCategory.name == cat_data["name"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    cat_map[existing.name] = existing.id
                    continue

                category = TaskCategory(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    icon=cat_data["icon"],
                    color=cat_data["color"],
                    sort_order=cat_data["sort_order"],
                )
                db.add(category)
                await db.flush()
                cat_map[category.name] = category.id
                cats_created += 1
                print(f"  [+] Category: {category.name}")

            tasks_created = 0

            for task_data in TASKS_DATA:
                cat_name = task_data.get("category")
                cat_id = cat_map.get(cat_name)
                if not cat_id:
                    print(f"  [!] Unknown category '{cat_name}' — skipping task '{task_data['title']}'")
                    continue

                result = await db.execute(
                    select(Task).where(Task.title == task_data["title"])
                )
                existing = result.scalar_one_or_none()
                if existing:
                    continue

                task = Task(
                    category_id=cat_id,
                    created_by=admin_id,
                    status=TaskStatus.ACTIVE.value,
                    task_type=task_data.get("task_type", TaskType.ONE_TIME.value),
                    title=task_data["title"],
                    description=task_data["description"],
                    short_description=task_data.get("short_description"),
                    required_count=task_data.get("required_count", 1),
                    max_completions=task_data.get("max_completions", 1),
                    vit_reward=task_data.get("vit_reward", Decimal("0")),
                    xp_reward=task_data.get("xp_reward", 0),
                    reset_period_days=task_data.get("reset_period_days"),
                    icon=task_data.get("icon"),
                    color=task_data.get("color"),
                    sort_order=task_data.get("sort_order", 0),
                    is_featured=task_data.get("is_featured", False),
                    action_url=task_data.get("action_url"),
                    action_label=task_data.get("action_label"),
                    requirements=task_data.get("requirements", {}),
                )
                db.add(task)
                tasks_created += 1
                print(f"  [+] Task: {task.title}")

            await db.commit()
            print(f"\n✓ Seed complete — {cats_created} new categories, {tasks_created} new tasks")
            print(f"  Total categories: {len(cat_map)}, Total tasks defined: {len(TASKS_DATA)}")

        except Exception as e:
            print(f"[ERROR] Seed failed: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed VIT platform tasks and categories")
    parser.add_argument("--admin-id", type=int, default=1,
                        help="User ID to use as task creator (default: 1)")
    args = parser.parse_args()
    asyncio.run(seed_task_data(args.admin_id))
