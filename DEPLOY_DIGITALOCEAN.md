# DigitalOcean App Platform Deployment Guide

## Prerequisites

1. DigitalOcean account
2. GitHub repository connected to DigitalOcean
3. (Optional) DigitalOcean Managed PostgreSQL database
4. (Optional) DigitalOcean Managed Redis

## Quick Deploy

### Option 1: Deploy Button (Recommended)

Click the button below to deploy directly to DigitalOcean App Platform:

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/Buildly-Labs/BabbleBeaver/tree/main)

### Option 2: Manual Deployment

1. **Go to App Platform**
   - Navigate to: https://cloud.digitalocean.com/apps
   - Click "Create App"

2. **Connect Source**
   - Select "GitHub"
   - Choose your repository: `Buildly-Labs/BabbleBeaver`
   - Select branch: `main` or `prod`

3. **Configure App Settings**
   
   **Resources:**
   - Type: Web Service
   - Name: `babblebeaver`
   - Run Command: `bash /app/start.sh`
   - HTTP Port: 8080
   - Build Command: `pip install -r requirements.txt`
   
   **Plan:**
   - Basic ($5/mo): 512MB RAM, 1 vCPU - Good for testing
   - Professional ($12/mo): 1GB RAM, 1 vCPU - Recommended for production

4. **Environment Variables**
   
   Add these in the "Environment Variables" section:
   
   ```bash
   # REQUIRED - LLM Providers
   GOOGLE_API_KEY=your-google-api-key
   GEMINI_API_KEY=your-gemini-api-key  # Same as GOOGLE_API_KEY
   
   # REQUIRED - Security
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your-strong-password
   API_KEY=your-secure-random-key
   
   # REQUIRED - CORS (add your app URL after deployment)
   CORS_ALLOWED_DOMAINS=https://your-app.ondigitalocean.app
   
   # OPTIONAL - Database (highly recommended)
   DATABASE_URL=${db.DATABASE_URL}  # Auto-populated if you add database component
   
   # OPTIONAL - Redis
   USE_REDIS=true
   REDIS_URL=${redis.REDIS_URL}  # Auto-populated if you add Redis component
   
   # OPTIONAL - Additional LLM Providers
   OPENAI_API_KEY=your-openai-key
   DIGITALOCEAN_API_TOKEN=your-do-ai-token
   DIGITALOCEAN_AGENT_URL=https://your-agent.agents.do-ai.run
   
   # Provider Configuration
   GEMINI_MODEL=gemini-2.0-flash
   GEMINI_PRIORITY=0
   GEMINI_ENABLED=true
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_PRIORITY=1
   OPENAI_ENABLED=false
   DIGITALOCEAN_AGENT_ENABLED=false
   DIGITALOCEAN_PRIORITY=3
   
   # Performance
   WEB_CONCURRENCY=2  # Number of workers
   CONTEXT_CACHE_SIZE=5000
   CONTEXT_CACHE_TTL=7200
   ```

5. **Add Database Component (Recommended)**
   
   - Click "Create" → "Database"
   - Select "PostgreSQL"
   - Choose plan (Dev: $15/mo, Basic: $25/mo)
   - Name: `babblebeaver-db`
   - The `DATABASE_URL` will be auto-populated in your environment variables

6. **Add Redis Component (Optional)**
   
   - Click "Create" → "Database"
   - Select "Redis"
   - Choose plan (Basic: $15/mo)
   - Name: `babblebeaver-redis`
   - The `REDIS_URL` will be auto-populated

7. **Configure Health Check**
   
   - Path: `/health`
   - Port: 8080
   - Initial Delay: 30 seconds
   - Period: 30 seconds
   - Timeout: 10 seconds
   - Success Threshold: 1
   - Failure Threshold: 3

8. **Deploy!**
   - Click "Create Resources"
   - Wait for deployment (typically 3-5 minutes)

## Post-Deployment

### 1. Update CORS
After deployment, get your app URL (e.g., `https://babblebeaver-abc123.ondigitalocean.app`) and update the `CORS_ALLOWED_DOMAINS` environment variable.

### 2. Test Endpoints

```bash
# Health check
curl https://your-app.ondigitalocean.app/health

# Chat endpoint (requires API key)
curl -X POST https://your-app.ondigitalocean.app/chat \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "history": []}'
```

### 3. Access Admin Panel

Navigate to: `https://your-app.ondigitalocean.app/admin`

Login with your `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

### 4. Run Database Migration (if upgrading from SQLite)

If you have existing data in SQLite, you can migrate it:

```bash
# Connect to your app console
doctl apps create-deployment <app-id>

# In the console
python tools/migrate_database.py
```

## Troubleshooting

### Error: `TypeError: str expected, not NoneType`

**Cause**: Missing environment variables.

**Solution**: Ensure all REQUIRED environment variables are set in App Platform settings.

### Error: Health checks failing

**Cause**: App not starting properly or taking too long to start.

**Solutions**:
1. Check runtime logs in App Platform dashboard
2. Increase health check initial delay to 60 seconds
3. Ensure `PORT` environment variable is not set (App Platform sets it automatically)

### Error: `FutureWarning: Python 3.9 past end of life`

**Cause**: App Platform using old Python version.

**Solution**: Add a `runtime.txt` file:

```txt
python-3.11
```

### Database connection issues

**Cause**: Database component not linked or `DATABASE_URL` not set.

**Solutions**:
1. Verify database component is created and linked in App Platform
2. Check `DATABASE_URL` is auto-populated in environment variables
3. For external databases, use connection pooling (`?pool_size=10`)

### Out of memory errors

**Cause**: Insufficient RAM for your workload.

**Solutions**:
1. Upgrade to Professional plan ($12/mo)
2. Reduce `WEB_CONCURRENCY` (number of workers)
3. Reduce `CONTEXT_CACHE_SIZE`

## Monitoring & Logs

### View Logs
```bash
# Using doctl CLI
doctl apps logs <app-id> --type run

# Or in dashboard
Apps → Your App → Runtime Logs
```

### Metrics

App Platform provides built-in metrics:
- CPU usage
- Memory usage
- Request rate
- Response time

Access at: Apps → Your App → Insights

## Scaling

### Vertical Scaling (More Resources)
- Basic ($5/mo): 512MB RAM, 1 vCPU
- Professional ($12/mo): 1GB RAM, 1 vCPU
- Professional Plus ($24/mo): 2GB RAM, 2 vCPUs
- Professional Max ($48/mo): 4GB RAM, 4 vCPUs

### Horizontal Scaling (More Instances)
App Platform doesn't support horizontal scaling directly. For high traffic:
1. Use Redis for session caching
2. Use PostgreSQL connection pooling
3. Consider Kubernetes deployment (see `devdocs/DATABASE.md`)

## Cost Estimates

**Minimal Setup** (~$5/month):
- App Platform Basic: $5/mo
- SQLite database (included)

**Recommended Production** (~$35-50/month):
- App Platform Professional: $12/mo
- PostgreSQL Dev Database: $15/mo
- Redis Basic (optional): $15/mo

**High Traffic** (~$90-150/month):
- App Platform Professional Plus: $24/mo
- PostgreSQL Basic Database: $25/mo
- Redis Basic: $15/mo
- DigitalOcean AI (pay per request): $20-50/mo

## CI/CD

App Platform automatically deploys on git push to your configured branch.

To configure:
1. Go to App → Settings → App Spec
2. Under `source`:
   ```yaml
   branch: main
   auto_deploy: true
   ```

## Custom Domain

1. Go to Settings → Domains
2. Add your domain
3. Update DNS records as instructed
4. Wait for SSL certificate provisioning (automatic)

## Environment-Specific Deployments

Create multiple apps for different environments:
- `babblebeaver-dev` → `dev` branch
- `babblebeaver-staging` → `staging` branch
- `babblebeaver-prod` → `main` branch

## Rollback

1. Go to Activity → Deployments
2. Find previous working deployment
3. Click "Rollback to this deployment"

## Support

- DigitalOcean Documentation: https://docs.digitalocean.com/products/app-platform/
- Community Support: https://www.digitalocean.com/community/
- BabbleBeaver Issues: https://github.com/Buildly-Labs/BabbleBeaver/issues

---

**Need help?** Open an issue on GitHub or contact the Buildly Labs team.
