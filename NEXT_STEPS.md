# BabbleBeaver Next Steps

## ✅ Completed

1. **Database Architecture** - SQLAlchemy ORM with auto-switching (SQLite dev, PostgreSQL prod)
2. **Message Logging** - New ORM-based message_logger_new.py
3. **Token Management** - New ORM-based token_manager_new.py
4. **DigitalOcean Integration** - Complete with cost estimation
5. **Cost Estimation System** - Multi-provider comparison
6. **Documentation** - DATABASE.md and DIGITALOCEAN_AGENT.md

## 🚀 Immediate Action Required

### 1. Update Application to Use New Database Modules

You have two options:

**Option A: Rename files (recommended)**
```bash
# Backup old files
mv message_logger.py message_logger_old.py
mv token_manager.py token_manager_old.py

# Activate new files
mv message_logger_new.py message_logger.py
mv token_manager_new.py token_manager.py

# Test
python3 tools/test_database.py
```

**Option B: Update imports in main.py**

Change the imports in [main.py](main.py):
```python
# OLD
from message_logger import MessageLogger
from token_manager import TokenManager

# NEW
from message_logger_new import MessageLogger
from token_manager_new import TokenManager
```

### 2. Install Dependencies

```bash
pip install sqlalchemy psycopg2-binary
```

Or update from [requirements.txt](requirements.txt):
```bash
pip install -r requirements.txt
```

### 3. Run Database Migration

Migrate existing data from old SQLite files:

```bash
# Dry run first (see what will happen)
python3 tools/migrate_database.py --dry-run

# Actual migration
python3 tools/migrate_database.py

# Answer 'yes' to confirm
```

This will:
- Migrate `chatbot.db` → `db/babblebeaver.db` (messages table)
- Migrate `db/tokens.db` → `db/babblebeaver.db` (api_tokens table)
- Preserve all existing data

### 4. Test the Application

```bash
# Test database
python3 tools/test_database.py

# Test DigitalOcean (if configured)
python3 tools/test_digitalocean.py

# Start the application
uvicorn main:app --host 0.0.0.0 --port 8004
```

Navigate to:
- Chat: http://localhost:8004
- Admin: http://localhost:8004/admin
- Cost Estimates: http://localhost:8004/admin (Cost Estimates tab)

## 📦 Production Deployment

### Option 1: DigitalOcean Managed PostgreSQL

1. **Create Database**
   - Go to DigitalOcean → Databases → Create Database
   - Select PostgreSQL 15 or 16
   - Choose region (same as your app for low latency)
   - Select plan based on traffic (see DATABASE.md for sizing)

2. **Get Connection Details**
   - Click on database → Connection Details
   - Copy the connection string (format: `postgresql://username:password@host:port/database?sslmode=require`)

3. **Configure Application**
   ```env
   # .env.production
   DATABASE_URL=postgresql://doadmin:password@db-postgresql-nyc3-12345.b.db.ondigitalocean.com:25060/babblebeaver?sslmode=require
   ```

4. **Deploy**
   ```bash
   # Set environment variable in production
   export DATABASE_URL="your-connection-string"
   
   # Run application
   uvicorn main:app --host 0.0.0.0 --port 8004
   ```

### Option 2: Google Cloud SQL

1. **Create Cloud SQL Instance**
   ```bash
   gcloud sql instances create babblebeaver-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

2. **Create Database**
   ```bash
   gcloud sql databases create babblebeaver \
     --instance=babblebeaver-db
   ```

3. **Set Password**
   ```bash
   gcloud sql users set-password postgres \
     --instance=babblebeaver-db \
     --password=YOUR_SECURE_PASSWORD
   ```

4. **Use Cloud SQL Proxy**
   ```bash
   # Download proxy
   curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.7.2/cloud-sql-proxy.darwin.amd64
   chmod +x cloud-sql-proxy
   
   # Run proxy
   ./cloud-sql-proxy PROJECT:REGION:INSTANCE --port 5432
   ```

5. **Configure Application**
   ```env
   # .env.production
   DATABASE_URL=postgresql://postgres:password@localhost:5432/babblebeaver
   ```

See [DATABASE.md](devdocs/DATABASE.md) for complete instructions, including Kubernetes deployment.

## 🔒 Security Tasks

### Rotate Exposed Credentials

If any credentials were previously exposed in git history, rotate them immediately:

1. **Google API Key**
   - Go to Google Cloud Console → APIs & Services → Credentials
   - Delete the exposed key
   - Create new API key
   - Update `.env` with new key

2. **Buildly Auth Token**
   - Go to your Buildly dashboard
   - Revoke the exposed token
   - Generate new auth token
   - Update `.env` with new token

### Force Push to Clean Git History

**⚠️ WARNING:** This will rewrite git history. Coordinate with team.

```bash
# Verify current state
git log --oneline | head -5

# Force push (removes old tokens from history)
git push --force --all origin
git push --force --tags origin

# Verify on GitHub that old tokens are gone
```

## 📊 Cost Estimation

### DigitalOcean Costs

**Database (Managed PostgreSQL):**
- Development: $15/month (1GB RAM, 10GB storage)
- Production: $60/month (4GB RAM, 80GB storage)
- High Traffic: $200/month (16GB RAM, 320GB storage)

**AI Agent Costs:**
- Simple Chat: $0.000117 per request
- Context-Aware: $0.000523 per request
- Agent with Tools: $0.000798 per request

**Monthly Estimates (1000 requests/day):**
- Simple Chat: $3.51/month
- Context-Aware: $15.69/month
- Agent with Tools: $23.94/month

See [DIGITALOCEAN_AGENT.md](devdocs/DIGITALOCEAN_AGENT.md) for complete pricing.

## 📝 Documentation

All documentation is complete:

- **[DATABASE.md](devdocs/DATABASE.md)** - Database setup, migration, production deployment
- **[DIGITALOCEAN_AGENT.md](devdocs/DIGITALOCEAN_AGENT.md)** - DigitalOcean integration guide
- **[README.md](README.md)** - Main project documentation (updated)

## 🧪 Testing Checklist

Before production deployment:

- [ ] Database migration completed (`python3 tools/migrate_database.py`)
- [ ] Database tests pass (`python3 tools/test_database.py`)
- [ ] Message logging works (test via chat interface)
- [ ] Token management works (test via admin interface)
- [ ] DigitalOcean agent works (`python3 tools/test_digitalocean.py`)
- [ ] Cost estimation API works (`curl http://localhost:8004/api/cost-estimate`)
- [ ] Admin UI Cost Estimates tab loads
- [ ] PostgreSQL connection works in production
- [ ] Exposed credentials rotated
- [ ] Git history cleaned (force push completed)

## 💡 Recommended Workflow

1. **Local Development**
   ```bash
   # No DATABASE_URL set = SQLite automatic
   python3 tools/migrate_database.py  # One-time migration
   uvicorn main:app --reload
   ```

2. **Staging/Testing**
   ```bash
   # Use small PostgreSQL instance
   export DATABASE_URL="postgresql://user:pass@staging-db:5432/babblebeaver"
   uvicorn main:app --host 0.0.0.0 --port 8004
   ```

3. **Production**
   ```bash
   # Use managed PostgreSQL with connection pooling
   export DATABASE_URL="postgresql://user:pass@prod-db:5432/babblebeaver?sslmode=require"
   
   # Run with production settings
   uvicorn main:app \
     --host 0.0.0.0 \
     --port 8004 \
     --workers 4 \
     --log-level info
   ```

## 🆘 Troubleshooting

### Database connection fails
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
python3 -c "from database import db_manager; print(db_manager.db_type)"

# Check PostgreSQL connectivity
psql "$DATABASE_URL" -c "SELECT version();"
```

### Migration issues
```bash
# Check old databases exist
ls -lh chatbot.db db/tokens.db

# Dry run migration
python3 tools/migrate_database.py --dry-run

# Check new database
python3 -c "from database import db_manager; with db_manager.get_session() as s: print(s.query(Message).count(), 'messages')"
```

### DigitalOcean agent not working
```bash
# Check credentials
echo $DIGITALOCEAN_API_TOKEN
echo $DIGITALOCEAN_AGENT_URL

# Test connection
python3 tools/test_digitalocean.py

# Check main.py configuration
grep -A5 "DIGITALOCEAN" main.py
```

See [DATABASE.md](devdocs/DATABASE.md) and [DIGITALOCEAN_AGENT.md](devdocs/DIGITALOCEAN_AGENT.md) for more troubleshooting.

---

**Questions?** Check the documentation or open an issue on GitHub.

**Ready to deploy?** Follow the production deployment steps above! 🚀
