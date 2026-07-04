import re

with open('app/api/routes/analytics.py', 'r') as f:
    content = f.read()

# Add get_growth_analytics function
growth_fn = """
@router.get("/growth")
async def get_growth_analytics(db: AsyncSession = Depends(get_db)):
    \"\"\"Return user growth and revenue data for charts.\"\"\"
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    # 1. User growth (daily for last 30 days)
    growth_data = []
    for i in range(30, 0, -1):
        day = now - timedelta(days=i)
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

        count_q = await db.execute(
            select(func.count(User.id)).where(User.created_at <= end)
        )
        total_at_day = count_q.scalar() or 0

        new_q = await db.execute(
            select(func.count(User.id)).where(User.created_at >= start).where(User.created_at <= end)
        )
        new_at_day = new_q.scalar() or 0

        growth_data.append({
            "date": start.strftime("%Y-%m-%d"),
            "total_users": total_at_day,
            "new_users": new_at_day
        })

    # 2. Mock revenue data (link to real transactions later)
    revenue_data = []
    for i in range(30, 0, -1):
        day = now - timedelta(days=i)
        revenue_data.append({
            "date": day.strftime("%Y-%m-%d"),
            "revenue": round(100.0 + (30 - i) * 5.0, 2)
        })

    return {
        "user_growth": growth_data,
        "revenue_growth": revenue_data,
        "total_revenue_30d": sum(r["revenue"] for r in revenue_data)
    }
"""

if '@router.get("/growth")' not in content:
    content = content.replace('@router.get("/system")', growth_fn + '\n@router.get("/system")')

with open('app/api/routes/analytics.py', 'w') as f:
    f.write(content)
