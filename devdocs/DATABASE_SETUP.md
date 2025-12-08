# PostgreSQL Database Setup for BabbleBeaver

## Overview

BabbleBeaver supports both SQLite (local development) and PostgreSQL (production). The database type is automatically determined by the `DATABASE_URL` environment variable.

## Configuration

### Local Development (SQLite)
```bash
# No DATABASE_URL needed - uses SQLite by default
# Data stored in: chatbot.db
```

### Production (PostgreSQL)
```bash
DATABASE_URL=postgresql://username:password@host:5432/database_name
```

## Database Schema

Both databases use the same schema:

```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,                    -- Auto-incrementing ID
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_message TEXT NOT NULL,
    bot_response TEXT,
    provider VARCHAR(50),                     -- 'gemini', 'openai', etc.
    model VARCHAR(100),                       -- Model name used
    tokens_used INTEGER,
    metadata JSONB                            -- JSON in PostgreSQL, TEXT in SQLite
);

-- Indexes for performance
CREATE INDEX idx_timestamp ON messages(timestamp);
CREATE INDEX idx_provider ON messages(provider);
```

## Google Cloud SQL Setup

### 1. Create Cloud SQL Instance

```bash
gcloud sql instances create babblebeaver-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-west1
```

### 2. Create Database

```bash
gcloud sql databases create babblebeaver \
    --instance=babblebeaver-db
```

### 3. Create User

```bash
gcloud sql users create babblebeaver \
    --instance=babblebeaver-db \
    --password=YOUR_SECURE_PASSWORD
```

### 4. Get Connection Name

```bash
gcloud sql instances describe babblebeaver-db --format="value(connectionName)"
# Returns: PROJECT_ID:REGION:INSTANCE_NAME
```

### 5. Configure Connection

#### Option A: Cloud SQL Proxy (Recommended for GKE)

```yaml
# In your Kubernetes deployment
env:
  - name: DATABASE_URL
    value: "postgresql://babblebeaver:PASSWORD@127.0.0.1:5432/babblebeaver"

# Add Cloud SQL Proxy sidecar
containers:
  - name: cloud-sql-proxy
    image: gcr.io/cloudsql-docker/gce-proxy:latest
    command:
      - "/cloud_sql_proxy"
      - "-instances=PROJECT_ID:REGION:INSTANCE_NAME=tcp:5432"
    securityContext:
      runAsNonRoot: true
```

#### Option B: Public IP (Not Recommended)

```bash
# Enable public IP
gcloud sql instances patch babblebeaver-db \
    --assign-ip

# Get public IP
gcloud sql instances describe babblebeaver-db \
    --format="value(ipAddresses[0].ipAddress)"

# Add authorized network (your server's IP)
gcloud sql instances patch babblebeaver-db \
    --authorized-networks=YOUR_SERVER_IP/32

# Connection string
DATABASE_URL=postgresql://babblebeaver:PASSWORD@PUBLIC_IP:5432/babblebeaver
```

#### Option C: Private IP (Best for Production)

```bash
# Create private IP connection
gcloud sql instances patch babblebeaver-db \
    --network=projects/PROJECT_ID/global/networks/default \
    --no-assign-ip

# Use private IP in connection string
DATABASE_URL=postgresql://babblebeaver:PASSWORD@PRIVATE_IP:5432/babblebeaver
```

## AWS RDS Setup

### 1. Create RDS Instance

```bash
aws rds create-db-instance \
    --db-instance-identifier babblebeaver-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username babblebeaver \
    --master-user-password YOUR_SECURE_PASSWORD \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxxxx \
    --db-name babblebeaver
```

### 2. Get Endpoint

```bash
aws rds describe-db-instances \
    --db-instance-identifier babblebeaver-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

### 3. Connection String

```bash
DATABASE_URL=postgresql://babblebeaver:PASSWORD@ENDPOINT:5432/babblebeaver
```

## Environment Variables

### Development (.env)
```bash
# Use SQLite (default)
# DATABASE_URL not set or empty
```

### Production (.env)
```bash
# PostgreSQL
DATABASE_URL=postgresql://babblebeaver:PASSWORD@host:5432/babblebeaver
```

### Kubernetes Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: babblebeaver-db
type: Opaque
stringData:
  database-url: postgresql://babblebeaver:PASSWORD@127.0.0.1:5432/babblebeaver
```

Use in deployment:
```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: babblebeaver-db
        key: database-url
```

## Migration from SQLite to PostgreSQL

### Export SQLite Data

```bash
sqlite3 chatbot.db .dump > backup.sql
```

### Convert and Import

```python
# migrate_to_postgres.py
import sqlite3
import psycopg2
import os

# Connect to databases
sqlite_conn = sqlite3.connect('chatbot.db')
pg_conn = psycopg2.connect(os.getenv('DATABASE_URL'))

# Copy data
sqlite_cursor = sqlite_conn.cursor()
pg_cursor = pg_conn.cursor()

sqlite_cursor.execute("SELECT * FROM messages")
for row in sqlite_cursor.fetchall():
    pg_cursor.execute("""
        INSERT INTO messages 
        (id, timestamp, user_message, bot_response, provider, model, tokens_used, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, row)

pg_conn.commit()
print("Migration complete!")
```

## Monitoring

### Check Connection

```python
from message_logger import MessageLogger

logger = MessageLogger()
print(f"Database type: {logger.db_type}")

# Test write
id = logger.log_message("test", "response")
print(f"Logged message ID: {id}")

# Test read
messages = logger.retrieve_messages(limit=1)
print(f"Retrieved: {messages}")
```

### PostgreSQL Monitoring

```bash
# Connection count
SELECT count(*) FROM pg_stat_activity WHERE datname = 'babblebeaver';

# Table size
SELECT pg_size_pretty(pg_total_relation_size('messages'));

# Row count
SELECT count(*) FROM messages;

# Recent activity
SELECT user_message, timestamp FROM messages ORDER BY timestamp DESC LIMIT 10;
```

## Performance Tuning

### PostgreSQL Indexes

```sql
-- Already created by default:
CREATE INDEX idx_timestamp ON messages(timestamp);
CREATE INDEX idx_provider ON messages(provider);

-- Optional additional indexes:
CREATE INDEX idx_model ON messages(model);
CREATE INDEX idx_metadata_user ON messages((metadata->>'user'));
```

### Connection Pooling

For high traffic, use connection pooling:

```bash
pip install psycopg2-pool
```

Update message_logger.py to use connection pool for production.

## Troubleshooting

### Connection Refused
```bash
# Check if PostgreSQL is running
pg_isready -h HOST -p 5432

# Test connection
psql postgresql://user:pass@host:5432/dbname
```

### Permission Denied
```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE babblebeaver TO babblebeaver;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO babblebeaver;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO babblebeaver;
```

### SSL Required
```bash
# Add SSL mode to connection string
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## Backup and Recovery

### Automated Backups (Google Cloud SQL)
```bash
gcloud sql backups create \
    --instance=babblebeaver-db
```

### Manual Backup
```bash
pg_dump postgresql://user:pass@host:5432/babblebeaver > backup.sql
```

### Restore
```bash
psql postgresql://user:pass@host:5432/babblebeaver < backup.sql
```

## Cost Optimization

### Google Cloud SQL
- **Development**: db-f1-micro (shared CPU, 0.6GB RAM) ~$7/month
- **Production**: db-n1-standard-1 (1 vCPU, 3.75GB RAM) ~$25/month

### AWS RDS
- **Development**: db.t3.micro (2 vCPU, 1GB RAM) ~$15/month
- **Production**: db.t3.small (2 vCPU, 2GB RAM) ~$30/month

### Cost Saving Tips
1. Use auto-scaling storage (PostgreSQL)
2. Enable automated backups with retention policy
3. Use reserved instances for production
4. Set up alerts for unusual usage
