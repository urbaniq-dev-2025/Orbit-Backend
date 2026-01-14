# Database Scripts

This directory contains utility scripts for database operations.

## Add Dummy Clients

### Option 1: Run Python Script (Recommended)

**Prerequisites:**
1. Client model must be created and migrated to database
2. Database must be running
3. At least one workspace must exist

**Run the script:**

```bash
# From backend directory
cd backend
python -m scripts.add_dummy_clients

# Or from project root
python -m backend.scripts.add_dummy_clients

# Or using Docker
docker-compose exec backend-api python -m scripts.add_dummy_clients
```

**What it does:**
- Finds the first workspace in the database
- Creates 3 dummy clients (abc, xyz, pqr) with all fields filled
- Skips clients that already exist (by name)

---

### Option 2: Run SQL Script Directly

If you prefer to run SQL directly, use the SQL script in this directory.

**Using DBeaver:**
1. Open DBeaver
2. Connect to your database
3. Open SQL Editor
4. Copy and paste the SQL from `add_dummy_clients.sql`
5. Update the `workspace_id` UUID in the script
6. Execute the script

**Using psql:**
```bash
psql -h localhost -p 5432 -U postgres -d orbit -f scripts/add_dummy_clients.sql
```

---

## Notes

- The script will use the **first workspace** found in the database
- Clients are created with realistic dummy data for all fields
- If a client with the same name already exists, it will be skipped
