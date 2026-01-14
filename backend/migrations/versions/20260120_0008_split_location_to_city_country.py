"""split location to city and country

Revision ID: 20260120_0008
Revises: 20260120_0007
Create Date: 2026-01-20 16:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260120_0008"
down_revision = "20260120_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add city and country columns
    op.add_column("clients", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("clients", sa.Column("country", sa.String(length=100), nullable=True))
    
    # Migrate existing location data to city/country
    # Try to parse location into city and country
    # For existing data, we'll set city to the location value and country to None
    # This allows manual correction later if needed
    connection = op.get_bind()
    
    # Get all clients with location data
    result = connection.execute(sa.text("SELECT id, location FROM clients WHERE location IS NOT NULL"))
    clients_with_location = result.fetchall()
    
    # Update each client: set city to location value, country to NULL
    # The dummy data will be updated separately by the script
    for client_id, location in clients_with_location:
        if location:
            # Simple migration: set city to location, country to NULL
            # For known US locations, we can set country to "United States"
            country = None
            if location in ["Boston", "Massachusetts", "California"]:
                country = "United States"
            
            connection.execute(
                sa.text("UPDATE clients SET city = :city, country = :country WHERE id = :id"),
                {"city": location, "country": country, "id": client_id}
            )
    
    # Drop the location column
    op.drop_column("clients", "location")


def downgrade() -> None:
    # Add location column back
    op.add_column("clients", sa.Column("location", sa.String(length=255), nullable=True))
    
    # Migrate city and country back to location
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id, city, country FROM clients"))
    clients = result.fetchall()
    
    for client_id, city, country in clients:
        # Combine city and country into location
        location_parts = []
        if city:
            location_parts.append(city)
        if country:
            location_parts.append(country)
        location = ", ".join(location_parts) if location_parts else None
        
        if location:
            connection.execute(
                sa.text("UPDATE clients SET location = :location WHERE id = :id"),
                {"location": location, "id": client_id}
            )
    
    # Drop city and country columns
    op.drop_column("clients", "country")
    op.drop_column("clients", "city")
