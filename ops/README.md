# BabbleBeaver Operations Scripts

This directory contains operational scripts for managing BabbleBeaver in local development.

## startup.sh

A comprehensive script for managing the BabbleBeaver service lifecycle.

### Features

- ✅ Automatic virtual environment setup
- ✅ Dependency installation and updates
- ✅ Environment configuration validation
- ✅ Database migration prompts
- ✅ Service start/stop/restart
- ✅ Status monitoring
- ✅ Log viewing

### Quick Start

```bash
# First time setup
./ops/startup.sh setup

# Start the service
./ops/startup.sh start

# Check status
./ops/startup.sh status

# View logs
./ops/startup.sh logs

# Restart service
./ops/startup.sh restart

# Stop service
./ops/startup.sh stop
```

### Commands

| Command | Description |
|---------|-------------|
| `setup` | Setup/update virtual environment and dependencies |
| `start` | Start the BabbleBeaver service |
| `stop` | Stop the BabbleBeaver service |
| `restart` | Restart the BabbleBeaver service |
| `status` | Show service status and recent logs |
| `logs` | Follow the application logs in real-time |
| `help` | Show help message |

### What It Does

#### Setup Phase (runs automatically with start/restart)

1. **Virtual Environment**
   - Checks if `.venv` exists
   - Creates it if missing
   - Activates the environment

2. **Dependencies**
   - Verifies `requirements.txt` exists
   - Checks if dependencies are up-to-date
   - Installs/updates packages as needed

3. **Configuration**
   - Verifies `.env` file exists
   - Offers to create from `example.env` if missing
   - Suggests running `python setup_admin.py` for guided setup

4. **Database**
   - Checks if database migration is needed
   - Prompts to run migration if applicable

#### Service Management

**Start:**
- Runs setup phase
- Starts uvicorn server in background
- Saves PID to `ops/babblebeaver.pid`
- Redirects logs to `ops/babblebeaver.log`
- Enables auto-reload for development

**Stop:**
- Reads PID from file
- Sends graceful termination signal
- Forces kill if needed
- Cleans up PID file

**Restart:**
- Stops the service
- Runs setup phase
- Starts the service

**Status:**
- Shows if service is running
- Displays process details
- Shows service URLs
- Displays recent logs

### Configuration

The script uses these defaults (can be modified in the script):

```bash
VENV_DIR=".venv"                    # Virtual environment directory
REQUIREMENTS_FILE="requirements.txt"
PID_FILE="ops/babblebeaver.pid"     # Process ID file
LOG_FILE="ops/babblebeaver.log"     # Log file location
APP_MODULE="main:app"               # FastAPI application
DEFAULT_PORT=8000                   # Server port
```

### Files Generated

When running, the script creates:

- `ops/babblebeaver.pid` - Process ID of running service
- `ops/babblebeaver.log` - Application logs

### Examples

#### First Time Setup

```bash
# Run setup
./ops/startup.sh setup

# Follow prompts for .env creation
# Edit .env with your configuration
nano .env

# Start the service
./ops/startup.sh start
```

#### Daily Development

```bash
# Start service (runs setup automatically)
./ops/startup.sh start

# Check if it's running
./ops/startup.sh status

# Make code changes (auto-reloads)
# ...

# View logs
./ops/startup.sh logs

# Restart after major changes
./ops/startup.sh restart

# Stop when done
./ops/startup.sh stop
```

#### Troubleshooting

```bash
# Check status and recent logs
./ops/startup.sh status

# Follow logs in real-time
./ops/startup.sh logs

# Full restart
./ops/startup.sh restart

# Manual check
cat ops/babblebeaver.log
```

### Service URLs

After starting, the service is available at:

- **Main Application:** http://localhost:8000
- **Admin Dashboard:** http://localhost:8000/admin/login-page
- **API Documentation:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Tips

1. **Auto-reload:** The service runs with `--reload` flag, so code changes are automatically detected.

2. **Log Monitoring:** Use `./ops/startup.sh logs` to watch logs in real-time during development.

3. **Quick Restart:** After updating dependencies, use `./ops/startup.sh restart` to refresh everything.

4. **Status Check:** Run `./ops/startup.sh status` to see if the service is running and view recent logs.

5. **Clean State:** If you encounter issues, try:
   ```bash
   ./ops/startup.sh stop
   rm -rf .venv
   ./ops/startup.sh setup
   ./ops/startup.sh start
   ```

### Integration with Other Scripts

The startup script works alongside:

- `setup_admin.py` - Interactive admin configuration
- `migrate_db.py` - Database migration
- `requirements.txt` - Python dependencies

### Requirements

- Python 3.8+
- Bash shell
- `uvicorn` (installed via requirements.txt)

### Notes

- The script is designed for **local development** only
- For production, use a proper process manager (systemd, supervisor, pm2, etc.)
- Logs are appended to `ops/babblebeaver.log` - rotate or clear as needed
- The PID file is cleaned up on normal shutdown

### Customization

To customize the script, edit these variables at the top of `startup.sh`:

```bash
VENV_DIR=".venv"              # Change virtual env location
DEFAULT_PORT=8000             # Change server port
LOG_FILE="ops/app.log"        # Change log location
```

### Troubleshooting

**Problem:** "Virtual environment not found"
```bash
./ops/startup.sh setup
```

**Problem:** "Service failed to start"
```bash
cat ops/babblebeaver.log
# Check for errors and fix configuration
```

**Problem:** "Port already in use"
```bash
# Find process using port 8000
lsof -i :8000
# Kill it or change DEFAULT_PORT in startup.sh
```

**Problem:** "Permission denied"
```bash
chmod +x ./ops/startup.sh
```

### Advanced Usage

**Custom Port:**
```bash
# Edit startup.sh and change DEFAULT_PORT
# Or set PORT environment variable
PORT=8080 ./ops/startup.sh start
```

**Background Logging:**
```bash
# Logs are automatically saved to ops/babblebeaver.log
tail -f ops/babblebeaver.log
```

**Clean Logs:**
```bash
> ops/babblebeaver.log  # Clear log file
./ops/startup.sh restart
```

## Future Enhancements

Potential additions:

- [ ] Support for production deployment configurations
- [ ] Health check endpoint monitoring
- [ ] Automatic log rotation
- [ ] Docker integration
- [ ] Environment-specific configurations
- [ ] Pre-commit hook integration
- [ ] Automated testing before start

---

**Version:** 1.0.0  
**Last Updated:** December 7, 2025  
**Maintained by:** Buildly Labs
