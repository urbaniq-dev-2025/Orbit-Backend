"""
Script to seed activity logs for existing clients/workspaces.

This script generates realistic activity logs for the past 6 months with patterns:
- More activity on weekdays (Mon-Fri)
- Peak hours around 9 AM - 5 PM
- Various entity types (scopes, projects, proposals, quotations, PRDs, AI, documents)
- Distributed across existing workspaces and users

Usage:
    python -m scripts.seed_activity_logs
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import ActivityLog, Client, User, Workspace, WorkspaceMember
from app.services.activity import log_activity


# Activity types and their corresponding entity types
ACTIVITY_CONFIGS = [
    # Scopes
    {"action": "created_scope", "entity_type": "scope", "weight": 30},
    {"action": "updated_scope", "entity_type": "scope", "weight": 25},
    {"action": "approved_scope", "entity_type": "scope", "weight": 10},
    {"action": "viewed_scope", "entity_type": "scope", "weight": 15},
    
    # Projects
    {"action": "created_project", "entity_type": "project", "weight": 20},
    {"action": "updated_project", "entity_type": "project", "weight": 18},
    {"action": "viewed_project", "entity_type": "project", "weight": 12},
    
    # Proposals
    {"action": "created_proposal", "entity_type": "proposal", "weight": 15},
    {"action": "updated_proposal", "entity_type": "proposal", "weight": 12},
    {"action": "sent_proposal", "entity_type": "proposal", "weight": 8},
    {"action": "viewed_proposal", "entity_type": "proposal", "weight": 10},
    
    # Quotations
    {"action": "created_quotation", "entity_type": "quotation", "weight": 18},
    {"action": "updated_quotation", "entity_type": "quotation", "weight": 15},
    {"action": "viewed_quotation", "entity_type": "quotation", "weight": 10},
    
    # PRDs
    {"action": "created_prd", "entity_type": "prd", "weight": 12},
    {"action": "updated_prd", "entity_type": "prd", "weight": 10},
    {"action": "viewed_prd", "entity_type": "prd", "weight": 8},
    
    # AI Activities
    {"action": "used_ai_extraction", "entity_type": "ai", "weight": 20},
    {"action": "used_ai_summary", "entity_type": "ai", "weight": 15},
    {"action": "used_ai_analysis", "entity_type": "ai", "weight": 12},
    
    # Documents
    {"action": "uploaded_document", "entity_type": "document", "weight": 18},
    {"action": "viewed_document", "entity_type": "document", "weight": 12},
    {"action": "downloaded_document", "entity_type": "document", "weight": 8},
    
    # General
    {"action": "viewed_dashboard", "entity_type": None, "weight": 25},
    {"action": "searched_content", "entity_type": None, "weight": 15},
]


def get_weighted_activity_config():
    """Get a random activity config based on weights."""
    total_weight = sum(config["weight"] for config in ACTIVITY_CONFIGS)
    rand = random.uniform(0, total_weight)
    
    current_weight = 0
    for config in ACTIVITY_CONFIGS:
        current_weight += config["weight"]
        if rand <= current_weight:
            return config
    
    return ACTIVITY_CONFIGS[0]


def get_realistic_hour(day_of_week: int) -> int:
    """
    Generate a realistic hour based on day of week.
    Weekdays: peak 9-17 (9 AM - 5 PM), some early morning (7-9) and evening (17-20)
    Weekends: more spread out, less activity overall
    """
    if day_of_week in [0, 6]:  # Weekend (Sunday, Saturday)
        # Weekend: more spread out, less activity
        if random.random() < 0.3:  # 30% chance of activity
            return random.choice([9, 10, 11, 12, 13, 14, 15, 16, 17, 18])
        return random.randint(0, 23)
    else:  # Weekday
        # Weekday: peak hours 9-17, some early morning and evening
        rand = random.random()
        if rand < 0.6:  # 60% during peak hours (9 AM - 5 PM)
            return random.randint(9, 17)
        elif rand < 0.75:  # 15% early morning (7-9 AM)
            return random.randint(7, 8)
        elif rand < 0.9:  # 15% evening (5-8 PM)
            return random.randint(17, 20)
        else:  # 10% other times
            return random.randint(0, 23)


def should_create_activity_for_day(date: datetime) -> bool:
    """Determine if activity should be created for a given day."""
    day_of_week = date.weekday()  # 0=Monday, 6=Sunday
    
    # More activity on weekdays
    if day_of_week < 5:  # Monday-Friday
        return random.random() < 0.85  # 85% chance of activity
    else:  # Weekend
        return random.random() < 0.4  # 40% chance of activity


async def get_existing_data(session: AsyncSession):
    """Get existing workspaces, users, and clients."""
    # Get all workspaces
    workspaces_stmt = select(Workspace)
    workspaces_result = await session.execute(workspaces_stmt)
    workspaces = list(workspaces_result.scalars().all())
    
    if not workspaces:
        print("❌ No workspaces found. Please create workspaces first.")
        return None, None, None
    
    # Get all users
    users_stmt = select(User)
    users_result = await session.execute(users_stmt)
    users = list(users_result.scalars().all())
    
    if not users:
        print("❌ No users found. Please create users first.")
        return None, None, None
    
    # Get all clients
    clients_stmt = select(Client)
    clients_result = await session.execute(clients_stmt)
    clients = list(clients_result.scalars().all())
    
    # Get workspace memberships to map users to workspaces
    members_stmt = select(WorkspaceMember)
    members_result = await session.execute(members_stmt)
    members = list(members_result.scalars().all())
    
    # Build mapping: workspace_id -> [user_ids]
    workspace_users = {}
    for member in members:
        if member.workspace_id not in workspace_users:
            workspace_users[member.workspace_id] = []
        workspace_users[member.workspace_id].append(member.user_id)
    
    # Build mapping: workspace_id -> [client_ids]
    workspace_clients = {}
    for client in clients:
        if client.workspace_id not in workspace_clients:
            workspace_clients[client.workspace_id] = []
        workspace_clients[client.workspace_id].append(client.id)
    
    return workspaces, users, workspace_users, workspace_clients


async def seed_activity_logs():
    """Seed activity logs for the past 6 months."""
    print("🌱 Starting activity log seeding...")
    
    async with AsyncSessionLocal() as session:
        # Get existing data
        result = await get_existing_data(session)
        if result is None:
            return
        
        workspaces, users, workspace_users, workspace_clients = result
        
        print(f"✅ Found {len(workspaces)} workspace(s), {len(users)} user(s)")
        
        if not workspaces:
            print("❌ No workspaces found. Exiting.")
            return
        
        # Calculate date range (last 6 months)
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=180)
        
        # Generate activities
        total_activities = 0
        activities_per_day = random.randint(15, 60)  # Variable activity per day
        
        current_date = start_date
        batch_size = 100
        batch = []
        
        print(f"📅 Generating activities from {start_date.date()} to {now.date()}...")
        
        while current_date < now:
            # Skip some days (more realistic)
            if not should_create_activity_for_day(current_date):
                current_date += timedelta(days=1)
                continue
            
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            # Adjust for PostgreSQL's day_of_week (0=Sunday, 6=Saturday)
            pg_day_of_week = (day_of_week + 1) % 7
            
            # Number of activities for this day
            if pg_day_of_week in [0, 6]:  # Weekend
                num_activities = random.randint(3, 15)
            else:  # Weekday
                num_activities = random.randint(10, 40)
            
            # Create activities for this day
            for _ in range(num_activities):
                # Select random workspace
                workspace = random.choice(workspaces)
                
                # Select random user from workspace (or None)
                user_id = None
                if workspace.id in workspace_users and workspace_users[workspace.id]:
                    user_id = random.choice(workspace_users[workspace.id])
                elif users:
                    user_id = random.choice(users).id
                
                # Get activity config
                activity_config = get_weighted_activity_config()
                
                # Generate realistic hour
                hour = get_realistic_hour(pg_day_of_week)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                # Create timestamp
                activity_time = current_date.replace(
                    hour=hour,
                    minute=minute,
                    second=second,
                    microsecond=random.randint(0, 999999)
                )
                
                # Generate entity_id if entity_type is provided
                entity_id = None
                if activity_config["entity_type"]:
                    # Try to use a real client/project ID if available
                    if workspace.id in workspace_clients and workspace_clients[workspace.id]:
                        # 30% chance to use a real client ID
                        if random.random() < 0.3:
                            entity_id = random.choice(workspace_clients[workspace.id])
                        else:
                            entity_id = uuid.uuid4()
                    else:
                        entity_id = uuid.uuid4()
                
                # Create activity log
                activity = ActivityLog(
                    workspace_id=workspace.id,
                    user_id=user_id,
                    action=activity_config["action"],
                    entity_type=activity_config["entity_type"],
                    entity_id=entity_id,
                    created_at=activity_time,
                )
                
                batch.append(activity)
                total_activities += 1
                
                # Commit in batches
                if len(batch) >= batch_size:
                    session.add_all(batch)
                    await session.flush()
                    batch = []
                    print(f"  ✓ Created {total_activities} activities...", end="\r")
            
            current_date += timedelta(days=1)
        
        # Commit remaining batch
        if batch:
            session.add_all(batch)
            await session.flush()
        
        await session.commit()
        
        print(f"\n✅ Successfully created {total_activities} activity logs!")
        print(f"   Time range: {start_date.date()} to {now.date()}")
        print(f"   Average per day: {total_activities / 180:.1f}")
        print("\n🎉 Activity logs seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_activity_logs())
