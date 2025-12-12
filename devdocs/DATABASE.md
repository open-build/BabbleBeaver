# Database Management Guide

## Overview

BabbleBeaver uses a unified database system that automatically switches between **SQLite** (development) and **PostgreSQL** (production) based on the `DATABASE_URL` environment variable.

## Architecture

### Database Models

Two main tables:

1. **messages** - Chat log storage
   - `id`: Primary key
   - `timestamp`: Message timestamp (indexed)
   - `user_message`: User's input
   - `bot_response`: AI response
   - `provider`: LLM provider used (gemini, openai, digitalocean, etc.)
   - `model`: Specific model name
   - `tokens_used`: Token count
   - `metadata`: JSON field for additional data

2. **api_tokens** - API token management
   - `id`: Primary key
   - `token_hash`: SHA256 hash of token (indexed)
   - `description`: Human-readable label
   - `created_at`: Creation timestamp
   - `expires_at`: Expiration timestamp (nullable)
   - `is_active`: Active status
   - `last_used_at`: Last usage timestamp

### Technology Stack

- **ORM**: SQLAlchemy 2.0+
- **Development DB**: SQLite (`db/babblebeaver.db`)
- **Production DB**: PostgreSQL (via `DATABASE_URL`)
- **Migrations**: Automatic schema creation + manual data migration

## Configuration

### Development (SQLite)

No configuration needed! Just run the application:

```bash
# SQLite will be used automatically
python -m uvicorn main:app --reload --port 8004
```

Database file location: `db/babblebeaver.db`

### Production (PostgreSQL)

Set the `DATABASE_URL` environment variable:

```bash
# .env file
DATABASE_URL=postgresql://username:password@host:port/database
```

#### DigitalOcean Managed PostgreSQL

1. Create database in [DigitalOcean Control Panel](https://cloud.digitalocean.com/databases)
2. Choose PostgreSQL version (14+ recommended)
3. Select region and size
4. Get connection details from dashboard
5. Set environment variable:

```env
DATABASE_URL=postgresql://doadmin:password@db-postgresql-nyc3-12345.b.db.ondigitalocean.com:25060/babblebeaver?sslmode=require
```

#### Google Cloud SQL

1. Create Cloud SQL instance in [GCP Console](https://console.cloud.google.com/sql)
2. Choose PostgreSQL
3. Enable Cloud SQL Admin API
4. Create database and user
5. Use Cloud SQL Proxy or public IP
6. Set environment variable:

```env
# With Cloud SQL Proxy
DATABASE_URL=postgresql://username:password@localhost:5432/babblebeaver

# With public IP (SSL recommended)
DATABASE_URL=postgresql://username:password@35.123.456.78:5432/babblebeaver?sslmode=require
```

## Migration from Old Databases

If you have existing `chatbot.db` or `db/tokens.db` files, migrate them:

### Step 1: Install Dependencies

```bash
pip install sqlalchemy psycopg2-binary
```

### Step 2: Run Migration

```bash
# Dry run (see what would be migrated)
python tools/migrate_database.py --dry-run

# Actual migration
python tools/migrate_database.py
```

### Step 3: Verify

```bash
# Check message count
python -c "from message_logger_new import message_logger; print(message_logger.get_analytics())"

# Check token count
python -c "from token_manager_new import token_manager; print(len(token_manager.list_tokens()))"
```

### Step 4: Backup Old Databases

```bash
mkdir -p backups
mv chatbot.db backups/chatbot.db.backup
mv db/tokens.db backups/tokens.db.backup
```

### Step 5: Update Code

Replace old imports:

```python
# Old (deprecated)
from message_logger import message_logger
from token_manager import token_manager

# New (use these)
from message_logger_new import message_logger
from token_manager_new import token_manager
```

Or rename files:
```bash
mv message_logger.py message_logger_old.py
mv message_logger_new.py message_logger.py
mv token_manager.py token_manager_old.py
mv token_manager_new.py token_manager.py
```

## Usage

### Message Logging

```python
from message_logger_new import message_logger

# Log a message
message_id = message_logger.log_message(
    message="What is AI?",
    response="AI stands for Artificial Intelligence...",
    provider="gemini",
    model="gemini-2.0-flash-exp",
    tokens_used=150,
    metadata={
        "user_id": "user123",
        "session_id": "abc-def"
    }
)

# Get recent messages
messages = message_logger.get_messages(limit=50)

# Search messages
results = message_logger.search_messages("API")

# Get analytics
analytics = message_logger.get_analytics()
print(f"Total messages: {analytics['total_messages']}")
print(f"Average tokens: {analytics['average_tokens']}")

# Clean up old data
deleted = message_logger.delete_old_messages(days=30)
```

### Token Management

```python
from token_manager_new import token_manager

# Create a token
token_data = token_manager.create_token(
    description="Production API",
    expires_days=365
)
print(f"Token: {token_data['token']}")  # Show once, then securely store

# Verify a token
is_valid = token_manager.verify_token(token)

# List all tokens
tokens = token_manager.list_tokens()
for token in tokens:
    print(f"{token['description']}: Active={token['is_active']}")

# Revoke a token
token_manager.revoke_token(token_id=123)

# Clean up expired tokens
deleted = token_manager.delete_expired_tokens()
```

## Production Deployment

### Kubernetes with PostgreSQL

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: babblebeaver
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: babblebeaver
        image: babblebeaver:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: url
        # ... other env vars
---
apiVersion: v1
kind: Secret
metadata:
  name: database-credentials
type: Opaque
stringData:
  url: postgresql://user:pass@postgres-service:5432/babblebeaver
```

### Docker Compose with PostgreSQL

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: babblebeaver
      POSTGRES_USER: babblebeaver
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  babblebeaver:
    build: .
    environment:
      DATABASE_URL: postgresql://babblebeaver:${DB_PASSWORD}@postgres:5432/babblebeaver
      # ... other env vars
    depends_on:
      - postgres
    ports:
      - "8004:8004"

volumes:
  postgres_data:
```

### Environment Variables

Production `.env`:

```env
# Database (REQUIRED for production)
DATABASE_URL=postgresql://username:password@host:port/database

# AI Providers
GOOGLE_API_KEY=your-key-here
DIGITALOCEAN_API_TOKEN=your-token-here
DIGITALOCEAN_AGENT_URL=https://your-agent-id.agents.do-ai.run

# Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password-here
API_KEY=generated-api-key-here

# Application
CORS_ALLOWED_DOMAINS=https://yourdomain.com,https://www.yourdomain.com
```

## Database Maintenance

### Backup

**SQLite (Development):**
```bash
# Simple file copy
cp db/babblebeaver.db db/babblebeaver.db.backup
```

**PostgreSQL (Production):**
```bash
# Using pg_dump
pg_dump -h host -U username -d babblebeaver > backup.sql

# Using DigitalOcean
doctl databases backup list database-id
doctl databases backup create database-id
```

### Restore

**SQLite:**
```bash
cp db/babblebeaver.db.backup db/babblebeaver.db
```

**PostgreSQL:**
```bash
psql -h host -U username -d babblebeaver < backup.sql
```

### Cleanup

```python
# Clean old messages (30+ days)
from message_logger_new import message_logger
deleted = message_logger.delete_old_messages(days=30)
print(f"Deleted {deleted} old messages")

# Clean expired tokens
from token_manager_new import token_manager
deleted = token_manager.delete_expired_tokens()
print(f"Deleted {deleted} expired tokens")
```

### Monitoring

```python
# Get database statistics
from message_logger_new import message_logger

analytics = message_logger.get_analytics()
print(f"""
Database Statistics:
  Total Messages: {analytics['total_messages']}
  Total Tokens: {analytics['total_tokens']:,}
  Average Tokens: {analytics['average_tokens']:.2f}
  Providers: {', '.join(analytics['providers'].keys())}
""")
```

## Performance Optimization

### Indexing

Indexes are automatically created on:
- `messages.timestamp` - Fast time-based queries
- `messages.provider` - Filter by provider
- `api_tokens.token_hash` - Fast token lookups

### Connection Pooling

PostgreSQL uses connection pooling automatically:
- Pool size: 10 connections
- Max overflow: 20 connections
- Pre-ping: Enabled (verifies connections)

### Query Optimization

```python
# Good: Use pagination
messages = message_logger.get_messages(limit=50, offset=0)

# Good: Filter by date range
from datetime import datetime, timedelta
start_date = datetime.utcnow() - timedelta(days=7)
messages = message_logger.get_messages(start_date=start_date)

# Bad: Fetching all messages at once
# messages = message_logger.get_messages(limit=999999)  # Don't do this!
```

## Troubleshooting

### "psycopg2 not installed"

```bash
pip install psycopg2-binary
```

### "Could not connect to PostgreSQL"

Check connection string:
```python
import psycopg2
conn = psycopg2.connect("postgresql://user:pass@host:port/db")
conn.close()
print("Connection successful!")
```

### "Permission denied on database"

Grant permissions:
```sql
GRANT ALL PRIVILEGES ON DATABASE babblebeaver TO username;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO username;
```

### "SSL connection required"

Add `?sslmode=require` to DATABASE_URL:
```env
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require
```

### Migration Failed

1. Check old database files exist
2. Ensure new database is accessible
3. Check logs for specific errors
4. Try with `--force` flag
5. Manual migration:

```python
from database import db_manager
db_manager.migrate_from_old_sqlite('chatbot.db')
db_manager.migrate_from_old_sqlite('db/tokens.db')
```

## Best Practices

### Development

✅ **Do:**
- Use SQLite for local development
- Commit migrations to version control
- Test with realistic data volumes
- Run tests against both SQLite and PostgreSQL

❌ **Don't:**
- Commit database files to git
- Use production database for development
- Skip migrations when updating schema

### Production

✅ **Do:**
- Use managed PostgreSQL (DigitalOcean, GCP, AWS)
- Enable SSL/TLS connections
- Set up automated backups
- Monitor database performance
- Use connection pooling
- Implement log rotation (delete old messages)

❌ **Don't:**
- Use SQLite in production (no concurrent writes)
- Store passwords in plain text
- Skip database backups
- Ignore slow query warnings

## Cost Estimates

### DigitalOcean Managed PostgreSQL

| Plan | RAM | Storage | Price/Month |
|------|-----|---------|-------------|
| Basic | 1 GB | 10 GB | $15 |
| Basic | 2 GB | 25 GB | $30 |
| Basic | 4 GB | 38 GB | $60 |
| Professional | 4 GB | 115 GB | $250 |

### Google Cloud SQL

| Type | vCPUs | RAM | Price/Month |
|------|-------|-----|-------------|
| db-f1-micro | Shared | 0.6 GB | ~$7 |
| db-g1-small | Shared | 1.7 GB | ~$25 |
| db-n1-standard-1 | 1 | 3.75 GB | ~$50 |
| db-n1-standard-2 | 2 | 7.5 GB | ~$100 |

**Recommendation**: Start with Basic 1GB plan ($15/month) for <10K messages/day

## Support

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [DigitalOcean Managed Databases](https://docs.digitalocean.com/products/databases/)
- [Google Cloud SQL](https://cloud.google.com/sql/docs)

---

**Last Updated**: December 11, 2025  
**Version**: BabbleBeaver 1.0 with Unified Database System
