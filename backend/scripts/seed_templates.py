"""
Script to seed sample scope templates in the database.

Usage:
    python -m scripts.seed_templates
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import Template


async def seed_templates(session: AsyncSession):
    """Create sample scope templates."""
    
    # Check if templates already exist
    stmt = select(Template).where(Template.is_system == True)  # noqa: E712
    result = await session.execute(stmt)
    existing = result.scalars().all()
    
    if existing:
        print(f"⚠️  Found {len(existing)} existing system templates. Skipping seed.")
        for template in existing:
            print(f"   - {template.name} (ID: {template.id})")
        return
    
    print("📝 Creating sample scope templates...")
    
    templates_data = [
        {
            "name": "Standard Website Scope",
            "description": "A comprehensive template for website development projects",
            "type": "scope",
            "category": "Web Development",
            "sections": {
                "sections": [
                    {
                        "title": "Overview",
                        "content": "This project involves the development of a modern, responsive website that meets the client's business objectives and user needs.",
                        "section_type": "overview",
                        "order": 0
                    },
                    {
                        "title": "Deliverables",
                        "content": "- Responsive website design\n- Content management system\n- SEO optimization\n- Analytics integration\n- Documentation",
                        "section_type": "deliverable",
                        "order": 1
                    },
                    {
                        "title": "Assumptions",
                        "content": "- Client will provide all content and assets\n- Hosting will be provided by client\n- Third-party integrations will be available\n- Client will provide timely feedback",
                        "section_type": "assumption",
                        "order": 2
                    },
                    {
                        "title": "Exclusions",
                        "content": "- Ongoing maintenance (separate agreement)\n- Content creation\n- Photography/videography\n- Third-party licensing fees",
                        "section_type": "exclusion",
                        "order": 3
                    },
                    {
                        "title": "Timeline",
                        "content": "- Discovery & Planning: 2 weeks\n- Design: 3 weeks\n- Development: 6 weeks\n- Testing & QA: 2 weeks\n- Launch: 1 week",
                        "section_type": "timeline",
                        "order": 4
                    }
                ]
            },
            "variables": ["client_name", "project_name", "launch_date"]
        },
        {
            "name": "Mobile App Development Scope",
            "description": "Template for mobile application development projects (iOS/Android)",
            "type": "scope",
            "category": "Mobile Development",
            "sections": {
                "sections": [
                    {
                        "title": "Project Overview",
                        "content": "Development of a native mobile application for iOS and Android platforms, focusing on user experience and performance.",
                        "section_type": "overview",
                        "order": 0
                    },
                    {
                        "title": "Key Deliverables",
                        "content": "- Native iOS application\n- Native Android application\n- Backend API integration\n- App Store submission\n- User documentation",
                        "section_type": "deliverable",
                        "order": 1
                    },
                    {
                        "title": "Technical Requirements",
                        "content": "- iOS 14+ support\n- Android 8.0+ support\n- Push notification integration\n- Analytics and crash reporting\n- Secure authentication",
                        "section_type": "constraint",
                        "order": 2
                    },
                    {
                        "title": "Assumptions",
                        "content": "- Backend API will be available\n- App Store accounts will be provided\n- Design assets will be provided\n- Testing devices will be available",
                        "section_type": "assumption",
                        "order": 3
                    },
                    {
                        "title": "Exclusions",
                        "content": "- Backend API development\n- App Store fees\n- Ongoing maintenance\n- Feature updates beyond scope",
                        "section_type": "exclusion",
                        "order": 4
                    },
                    {
                        "title": "Timeline",
                        "content": "- Planning & Design: 3 weeks\n- iOS Development: 8 weeks\n- Android Development: 8 weeks\n- Testing: 3 weeks\n- App Store Submission: 2 weeks",
                        "section_type": "timeline",
                        "order": 5
                    }
                ]
            },
            "variables": ["app_name", "client_name", "platform"]
        },
        {
            "name": "E-commerce Platform Scope",
            "description": "Comprehensive template for e-commerce website development",
            "type": "scope",
            "category": "E-commerce",
            "sections": {
                "sections": [
                    {
                        "title": "Project Overview",
                        "content": "Development of a full-featured e-commerce platform with shopping cart, payment processing, and order management.",
                        "section_type": "overview",
                        "order": 0
                    },
                    {
                        "title": "Core Features",
                        "content": "- Product catalog with search and filters\n- Shopping cart and checkout\n- Payment gateway integration\n- Order management system\n- Customer accounts\n- Admin dashboard",
                        "section_type": "deliverable",
                        "order": 1
                    },
                    {
                        "title": "Payment Integration",
                        "content": "- Credit card processing\n- PayPal integration\n- Stripe payment gateway\n- Secure payment handling (PCI compliance)",
                        "section_type": "deliverable",
                        "order": 2
                    },
                    {
                        "title": "Assumptions",
                        "content": "- Payment gateway accounts will be set up\n- Product data will be provided\n- Inventory management system available\n- SSL certificate will be provided",
                        "section_type": "assumption",
                        "order": 3
                    },
                    {
                        "title": "Exclusions",
                        "content": "- Product photography\n- Content writing\n- Payment gateway fees\n- Ongoing hosting\n- Inventory management system",
                        "section_type": "exclusion",
                        "order": 4
                    },
                    {
                        "title": "Success Metrics",
                        "content": "- Page load time < 2 seconds\n- 99.9% uptime\n- Mobile responsive design\n- SEO optimized\n- Secure checkout process",
                        "section_type": "success_metrics",
                        "order": 5
                    }
                ]
            },
            "variables": ["store_name", "client_name", "product_count"]
        },
        {
            "name": "API Development Scope",
            "description": "Template for RESTful API development projects",
            "type": "scope",
            "category": "Backend Development",
            "sections": {
                "sections": [
                    {
                        "title": "Project Overview",
                        "content": "Development of a RESTful API to support client applications with authentication, data management, and integration capabilities.",
                        "section_type": "overview",
                        "order": 0
                    },
                    {
                        "title": "API Endpoints",
                        "content": "- Authentication endpoints\n- CRUD operations for core entities\n- Search and filtering\n- File upload/download\n- Reporting endpoints",
                        "section_type": "deliverable",
                        "order": 1
                    },
                    {
                        "title": "Technical Stack",
                        "content": "- RESTful architecture\n- JWT authentication\n- Database design and optimization\n- API documentation (OpenAPI/Swagger)\n- Error handling and logging",
                        "section_type": "deliverable",
                        "order": 2
                    },
                    {
                        "title": "Security Requirements",
                        "content": "- HTTPS only\n- Rate limiting\n- Input validation\n- SQL injection prevention\n- XSS protection\n- CORS configuration",
                        "section_type": "constraint",
                        "order": 3
                    },
                    {
                        "title": "Assumptions",
                        "content": "- Database will be provided\n- Hosting environment will be available\n- Third-party services will be accessible\n- API consumers will follow documentation",
                        "section_type": "assumption",
                        "order": 4
                    },
                    {
                        "title": "Exclusions",
                        "content": "- Frontend development\n- Database hosting\n- Third-party service fees\n- Ongoing monitoring and maintenance",
                        "section_type": "exclusion",
                        "order": 5
                    }
                ]
            },
            "variables": ["api_name", "client_name", "endpoint_count"]
        },
        {
            "name": "SaaS Platform Scope",
            "description": "Template for Software as a Service platform development",
            "type": "scope",
            "category": "SaaS",
            "sections": {
                "sections": [
                    {
                        "title": "Project Overview",
                        "content": "Development of a multi-tenant SaaS platform with user management, subscription billing, and core business features.",
                        "section_type": "overview",
                        "order": 0
                    },
                    {
                        "title": "Core Features",
                        "content": "- Multi-tenant architecture\n- User authentication and authorization\n- Subscription management\n- Billing and invoicing\n- Admin dashboard\n- User dashboard",
                        "section_type": "deliverable",
                        "order": 1
                    },
                    {
                        "title": "Subscription Management",
                        "content": "- Multiple subscription tiers\n- Usage-based billing\n- Payment processing\n- Invoice generation\n- Subscription upgrades/downgrades",
                        "section_type": "deliverable",
                        "order": 2
                    },
                    {
                        "title": "Technical Requirements",
                        "content": "- Scalable architecture\n- Data isolation per tenant\n- High availability (99.9% uptime)\n- Automated backups\n- Monitoring and alerting",
                        "section_type": "constraint",
                        "order": 3
                    },
                    {
                        "title": "Assumptions",
                        "content": "- Cloud infrastructure will be available\n- Payment gateway will be integrated\n- Domain and SSL will be provided\n- Third-party services will be accessible",
                        "section_type": "assumption",
                        "order": 4
                    },
                    {
                        "title": "Exclusions",
                        "content": "- Infrastructure setup\n- Payment gateway fees\n- Ongoing hosting costs\n- Customer support\n- Feature development beyond scope",
                        "section_type": "exclusion",
                        "order": 5
                    },
                    {
                        "title": "Success Metrics",
                        "content": "- System uptime: 99.9%\n- API response time: < 200ms\n- User onboarding completion: > 80%\n- Subscription conversion rate tracking",
                        "section_type": "success_metrics",
                        "order": 6
                    }
                ]
            },
            "variables": ["platform_name", "client_name", "subscription_tiers"]
        }
    ]
    
    created_count = 0
    for template_data in templates_data:
        template = Template(
            workspace_id=None,  # System templates are not workspace-specific
            name=template_data["name"],
            description=template_data["description"],
            type=template_data["type"],
            category=template_data["category"],
            sections=template_data["sections"],
            variables=template_data.get("variables", []),
            is_public=True,
            is_system=True,
            usage_count=0,
            created_by=None,  # System templates have no creator
        )
        session.add(template)
        await session.flush()  # Flush to get the ID
        created_count += 1
        print(f"✅ Created template: {template_data['name']} (ID: {template.id})")
    
    await session.commit()
    print(f"\n📊 Summary:")
    print(f"   Created: {created_count} system templates")
    print(f"   Categories: {', '.join(set(t['category'] for t in templates_data))}")
    print(f"\n✅ Templates seeded successfully!")


async def main():
    async with AsyncSessionLocal() as session:
        try:
            await seed_templates(session)
        except Exception as e:
            await session.rollback()
            print(f"❌ An error occurred during template seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
