"""
Test script for scope creation with input processing and hours estimation.

This script tests the complete flow:
1. Creates a scope with text input
2. Processes the input
3. Triggers extraction
4. Verifies scope sections with hours estimation
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models import Scope, ScopeSection, Template
from app.schemas.scope import ScopeCreate
from app.services import scopes as scope_service
from app.services.scope_input_handler import create_scope_with_input
from sqlalchemy import select

settings = get_settings()

# Database connection
engine = create_async_engine(settings.database_url, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def test_scope_creation():
    """Test scope creation with text input."""
    print("=" * 60)
    print("Testing Scope Creation with Input Processing")
    print("=" * 60)
    
    async with async_session() as session:
        # 1. Get a test user and workspace
        from app.models import User, Workspace, WorkspaceMember
        
        user_stmt = select(User).limit(1)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("❌ No users found. Please create a test user first.")
            print("   Run: python scripts/create_test_user.py")
            return
        
        print(f"✅ Using user: {user.email}")
        
        # Get user's workspace
        workspace_stmt = select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active"
        ).limit(1)
        workspace_result = await session.execute(workspace_stmt)
        workspace_member = workspace_result.scalar_one_or_none()
        
        if not workspace_member:
            print("❌ User has no workspace. Please create a workspace first.")
            return
        
        workspace_id = workspace_member.workspace_id
        print(f"✅ Using workspace: {workspace_id}")
        
        # 2. Get a template (optional)
        template_stmt = select(Template).where(
            Template.type == "scope",
            Template.is_system == True
        ).limit(1)
        template_result = await session.execute(template_stmt)
        template = template_result.scalar_one_or_none()
        
        template_id = template.id if template else None
        if template:
            print(f"✅ Using template: {template.name}")
        else:
            print("⚠️  No template found, proceeding without template")
        
        # 3. Create scope with text input
        print("\n" + "=" * 60)
        print("Creating scope with text input...")
        print("=" * 60)
        
        test_requirements = """
        We need a mobile food delivery application with the following features:
        
        1. User Authentication
           - Email/Password login
           - Social login (Google, Facebook)
           - Password reset functionality
        
        2. Restaurant Browsing
           - List of restaurants with filters (cuisine, rating, distance)
           - Restaurant detail page with menu
           - Search functionality
        
        3. Order Management
           - Add items to cart
           - Modify cart items
           - Apply promo codes
           - Place order
           - Order tracking in real-time
        
        4. Payment Integration
           - Stripe payment gateway
           - Multiple payment methods (card, wallet)
           - Payment history
        
        5. Admin Panel
           - Restaurant management
           - Menu management
           - Order management
           - Analytics dashboard
        """
        
        scope_create = ScopeCreate(
            workspace_id=workspace_id,
            title="Food Delivery App - Test Scope",
            description="Test scope creation with hours estimation",
            input_type="text",
            input_data=test_requirements.strip(),
            template_id=template_id,
            developer_level="mid",
            developer_experience_years=3,
        )
        
        try:
            result = await create_scope_with_input(
                session,
                user.id,
                scope_create,
            )
            
            scope_id = result["scope_id"]
            print(f"✅ Scope created: {scope_id}")
            
            if result.get("extraction_id"):
                print(f"✅ Extraction triggered: {result['extraction_id']}")
            
            # 4. Wait a bit for processing
            print("\n⏳ Waiting for extraction to complete...")
            await asyncio.sleep(5)
            
            # 5. Fetch scope with sections
            scope = await scope_service.get_scope(session, scope_id, user.id, include_sections=True)
            
            print("\n" + "=" * 60)
            print("Scope Details")
            print("=" * 60)
            print(f"Title: {scope.title}")
            print(f"Status: {scope.status}")
            print(f"Progress: {scope.progress}%")
            print(f"Confidence Score: {scope.confidence_score}")
            print(f"Risk Level: {scope.risk_level}")
            print(f"Number of Sections: {len(scope.sections)}")
            
            # 6. Display sections with hours
            print("\n" + "=" * 60)
            print("Scope Sections with Hours Estimation")
            print("=" * 60)
            
            total_hours = 0
            for section in sorted(scope.sections, key=lambda s: s.order_index):
                print(f"\n📋 {section.title}")
                print(f"   Type: {section.section_type}")
                print(f"   AI Generated: {section.ai_generated}")
                print(f"   Confidence: {section.confidence_score}%")
                
                # Try to parse hours from content
                try:
                    content_data = json.loads(section.content) if section.content else {}
                    if isinstance(content_data, dict):
                        module_hours = content_data.get("total_hours", 0)
                        if module_hours:
                            total_hours += module_hours
                            print(f"   ⏱️  Module Hours: {module_hours}")
                        
                        # Show features if available
                        features = content_data.get("features", [])
                        if features:
                            print(f"   Features: {len(features)}")
                            for feature in features[:3]:  # Show first 3
                                feature_hours = feature.get("total_hours", 0)
                                sub_features = feature.get("sub_features", [])
                                print(f"      - {feature.get('name', 'Unknown')}: {feature_hours}h ({len(sub_features)} sub-features)")
                except (json.JSONDecodeError, TypeError):
                    # Content is not JSON, just show preview
                    content_preview = section.content[:100] if section.content else ""
                    print(f"   Content: {content_preview}...")
            
            print("\n" + "=" * 60)
            print(f"📊 Total Estimated Hours: {total_hours}")
            print("=" * 60)
            
            # 7. Verify document was created
            from app.models import Document
            doc_stmt = select(Document).where(Document.scope_id == scope_id)
            doc_result = await session.execute(doc_stmt)
            documents = doc_result.scalars().all()
            
            print(f"\n📄 Documents: {len(documents)}")
            for doc in documents:
                print(f"   - {doc.filename}: {doc.processing_status}")
                if doc.extracted_text:
                    text_length = len(doc.extracted_text)
                    print(f"     Extracted text: {text_length} characters")
            
            print("\n" + "=" * 60)
            print("✅ Test completed successfully!")
            print("=" * 60)
            print(f"\nScope ID: {scope_id}")
            print(f"You can view the scope at: GET /api/scopes/{scope_id}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_scope_creation())
