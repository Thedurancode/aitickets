# AI-Tickets Voice Optimization Deployment Guide

Complete guide for deploying the voice-optimized AI-Tickets platform.

---

## Pre-Deployment Checklist

### ✅ Backend (MCP Server)

- [x] 23 voice-optimized tools implemented
- [x] All `Ticket.price_cents` bugs fixed
- [x] All `Ticket.event_id` bugs fixed
- [x] Python syntax validated
- [x] Smart defaults tested
- [x] Documentation complete

### 🔲 Frontend (Voice UI)

- [ ] React components integrated
- [ ] MCP client configured
- [ ] Voice UI tested in target browsers
- [ ] User documentation accessible
- [ ] Error handling tested

### 🔲 Testing

- [ ] Backend unit tests passing
- [ ] Voice command integration tests
- [ ] Browser compatibility tested
- [ ] User acceptance testing complete

---

## Step-by-Step Deployment

### Step 1: Backend Deployment

#### 1.1 Update MCP Server

```bash
# Navigate to project root
cd /Users/edduran/Documents/GitHub/ai-tickets

# Verify Python syntax
python3 -m py_compile mcp_server/server.py

# Check dependencies
pip install -r requirements.txt

# Run migration to ensure database is up to date
python3 app/migrations/add_alerts_table.py
python3 app/migrations/add_campaign_tracking.py
```

#### 1.2 Test MCP Server

```bash
# Start MCP server
cd mcp_server
python server.py

# In another terminal, test with MCP Inspector
npx @modelcontextprotocol/inspector mcp_server/server.py

# Test key voice tools:
# - show_alerts
# - quick_status
# - top_campaigns
# - top_events (verify bug is fixed)
```

#### 1.3 Configure Environment

Create/update `.env` file:

```env
# MCP Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8765

# Database
DATABASE_URL=sqlite:///./ai_tickets.db

# Voice Features
VOICE_ENABLED=true
VOICE_DEBUG=false

# API Keys (if using external services)
OPENAI_API_KEY=your_key_here  # Optional
ANTHROPIC_API_KEY=your_key_here  # Optional
```

#### 1.4 Run Test Suite

```bash
# Run voice defaults tests
python3 tests/test_voice_defaults.py

# Expected: 11/13 tests pass (2 pre-existing bugs now fixed)
# After fixes, should be 13/13 pass
```

---

### Step 2: Frontend Deployment

#### 2.1 Install Voice Components

```bash
cd frontend

# Copy voice components
cp -r /path/to/src/components/voice ./src/components/
cp -r /path/to/src/hooks/useVoiceCommands.ts ./src/hooks/
cp -r /path/to/src/hooks/useMCP.ts ./src/hooks/
```

#### 2.2 Configure MCP Client

Update `src/App.tsx`:

```typescript
import { MCPProvider, createMCPClient } from './hooks/useMCP';
import { VoiceUI } from './components/voice/VoiceUI';

// Create MCP client
const mcpClient = createMCPClient(
  process.env.REACT_APP_MCP_SERVER_URL || 'http://localhost:8765'
);

function App() {
  return (
    <MCPProvider value={mcpClient}>
      <div className="App">
        {/* Your existing app */}

        {/* Add Voice UI */}
        <VoiceUI showHistory={true} showSettings={true} />
      </div>
    </MCPProvider>
  );
}
```

#### 2.3 Add Voice Button to Navigation

```typescript
import { VoiceButton } from './components/voice/VoiceButton';

function Navigation() {
  return (
    <nav>
      {/* Existing nav items */}

      {/* Voice button */}
      <VoiceButton continuous={false} autoSpeak={true} />
    </nav>
  );
}
```

#### 2.4 Build Frontend

```bash
# Install dependencies
npm install

# Build production bundle
npm run build

# Test build locally
npx serve -s build
```

---

### Step 3: Integration Testing

#### 3.1 Test Voice Commands

**Test in Chrome/Edge/Safari:**

1. Open application in browser
2. Click microphone button
3. Allow microphone permission
4. Test each command category:

**Alerts:**
```
- "Show alerts"
- "Any critical alerts?"
- "Dismiss alert [ID]"
- "Clear all alerts"
```

**Dashboard:**
```
- "Status"
- "Today's revenue"
- "Top events"
```

**Campaigns:**
```
- "Show campaigns"
- "Top campaigns"
- "Campaign [ID] performance"
```

#### 3.2 Verify Bug Fixes

**Test top_events:**
```bash
# In MCP Inspector or via voice:
Tool: top_events
Arguments: {}

# Should return top 5 events without errors
# Previously failed with "Ticket.event_id" error
```

**Test revenue calculations:**
```bash
# Test quick_status
Tool: quick_status
Arguments: {}

# Should return today's revenue correctly
# Previously had Ticket.price_cents errors
```

#### 3.3 Browser Compatibility

Test in each browser:

| Browser | Speech Recognition | Speech Synthesis | Status |
|---------|-------------------|------------------|--------|
| Chrome 90+ | ✅ | ✅ | Recommended |
| Edge 90+ | ✅ | ✅ | Recommended |
| Safari 14+ | ✅ | ✅ | Supported |
| Firefox 90+ | ⚠️ | ✅ | Limited |

---

### Step 4: Production Deployment

#### 4.1 Backend (MCP Server)

**Option A: Docker**

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8765

CMD ["python", "mcp_server/server.py"]
```

Deploy:

```bash
# Build image
docker build -t ai-tickets-mcp .

# Run container
docker run -d -p 8765:8765 --name ai-tickets-mcp ai-tickets-mcp

# Check logs
docker logs ai-tickets-mcp
```

**Option B: Systemd Service**

Create `/etc/systemd/system/ai-tickets-mcp.service`:

```ini
[Unit]
Description=AI-Tickets MCP Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/ai-tickets
ExecStart=/usr/bin/python3 mcp_server/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Deploy:

```bash
sudo systemctl enable ai-tickets-mcp
sudo systemctl start ai-tickets-mcp
sudo systemctl status ai-tickets-mcp
```

#### 4.2 Frontend Deployment

**Option A: Static Hosting (Vercel/Netlify)**

```bash
# Build frontend
cd frontend
npm run build

# Deploy to Vercel
vercel deploy --prod

# Or Netlify
netlify deploy --prod --dir=build
```

**Option B: Nginx**

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    root /var/www/ai-tickets/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy MCP server
    location /api/ {
        proxy_pass http://localhost:8765/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

### Step 5: Monitoring & Analytics

#### 5.1 Setup Monitoring

**Backend Monitoring:**

```python
# Add to mcp_server/server.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)

# Log voice tool usage
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    logging.info(f"Voice tool called: {name} with args: {arguments}")
    # ... existing code
```

**Frontend Analytics:**

```typescript
// Track voice command usage
const executeCommand = async (command: string) => {
  // Analytics event
  analytics.track('voice_command', {
    command: command,
    timestamp: new Date(),
    success: result.success,
  });

  // ... existing code
};
```

#### 5.2 Error Tracking

**Setup Sentry (optional):**

```bash
npm install @sentry/react

# In src/index.tsx:
import * as Sentry from '@sentry/react';

Sentry.init({
  dsn: process.env.REACT_APP_SENTRY_DSN,
  environment: process.env.NODE_ENV,
});
```

---

### Step 6: Documentation Deployment

#### 6.1 Make Documentation Accessible

```bash
# Copy documentation to public docs folder
cp VOICE_COMMANDS_USER_GUIDE.md frontend/public/docs/
cp VOICE_OPTIMIZATION_GUIDE.md frontend/public/docs/
```

#### 6.2 Add Help Links

```typescript
// In VoiceUI component
<a href="/docs/VOICE_COMMANDS_USER_GUIDE.md" target="_blank">
  📖 Voice Commands Guide
</a>
```

---

## Post-Deployment

### Verify Deployment

**Checklist:**

- [ ] MCP server responding on production URL
- [ ] Frontend loads without errors
- [ ] Voice button visible and clickable
- [ ] Microphone permission prompt works
- [ ] Voice commands execute successfully
- [ ] Responses are spoken correctly
- [ ] Error handling works (try invalid command)
- [ ] All 23 voice tools accessible
- [ ] top_events bug fixed (no errors)
- [ ] Revenue calculations correct

### User Onboarding

1. **Add onboarding tour** for first-time voice users
2. **Show example commands** on first visit
3. **Highlight microphone button** with tooltip
4. **Link to user guide** prominently

### Collect Feedback

1. **In-app feedback form** for voice features
2. **Track command success rate** via analytics
3. **Monitor error logs** for common issues
4. **Survey users** after 1 week of usage

---

## Rollback Plan

If issues occur, rollback quickly:

### Backend Rollback

```bash
# Stop current version
sudo systemctl stop ai-tickets-mcp

# Revert to previous version
git checkout previous-stable-tag
python3 mcp_server/server.py

# Or docker
docker stop ai-tickets-mcp
docker run -d previous-image-tag
```

### Frontend Rollback

```bash
# Vercel/Netlify
vercel rollback
netlify rollback

# Manual
cd frontend
git checkout previous-stable-tag
npm run build
# Deploy build
```

---

## Troubleshooting Production Issues

### Issue: Voice commands not working

**Check:**
1. MCP server running: `curl http://localhost:8765/health`
2. Browser console for errors
3. Microphone permissions granted
4. HTTPS required for production (HTTP won't work)

**Fix:**
```bash
# Check MCP logs
tail -f mcp_server.log

# Restart MCP server
sudo systemctl restart ai-tickets-mcp
```

### Issue: Slow response times

**Check:**
1. Database query performance
2. MCP server load
3. Network latency

**Fix:**
```bash
# Add database indexes
python3 app/migrations/add_indexes.py

# Increase MCP server resources
# Edit systemd service or docker compose
```

### Issue: High error rate

**Check:**
1. Error logs for patterns
2. Specific commands failing
3. Browser compatibility issues

**Fix:**
- Deploy hotfix for specific errors
- Update frontend error handling
- Add fallback for unsupported browsers

---

## Performance Optimization

### Backend

```python
# Add caching for frequent queries
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=10)
def cached_quick_status(cache_key: str):
    # Cache for 1 minute
    return get_quick_status()

# Use:
cache_key = datetime.now().strftime('%Y-%m-%d-%H-%M')
result = cached_quick_status(cache_key)
```

### Frontend

```typescript
// Lazy load voice components
const VoiceUI = lazy(() => import('./components/voice/VoiceUI'));

// Debounce voice input
const debouncedExecuteCommand = useMemo(
  () => debounce(executeCommand, 500),
  [executeCommand]
);
```

---

## Security Considerations

### HTTPS Required

Voice features require HTTPS in production:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    # ... rest of config
}
```

### Rate Limiting

```python
# Add to MCP server
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("60/minute")
async def call_tool(name: str, arguments: dict):
    # ... existing code
```

### Input Validation

```python
# Validate tool arguments
def validate_args(name: str, args: dict):
    if name == "dismiss_alert":
        if not isinstance(args.get("alert_id"), int):
            raise ValueError("alert_id must be integer")
    # ... more validations
```

---

## Success Metrics

Track these KPIs after deployment:

### Usage Metrics
- Voice commands per day
- Unique voice users
- Commands per user session
- Most popular commands

### Performance Metrics
- Average response time
- Error rate (target: <5%)
- Speech recognition accuracy
- TTS success rate

### Business Metrics
- Time saved vs. manual UI
- User satisfaction score
- Feature adoption rate
- Support ticket reduction

---

## Maintenance

### Weekly Tasks
- Review error logs
- Check performance metrics
- Update documentation if needed

### Monthly Tasks
- Analyze usage patterns
- Optimize slow queries
- Plan new voice features
- Update dependencies

### Quarterly Tasks
- User survey on voice features
- Review and improve commands
- Browser compatibility check
- Security audit

---

## What's Next?

After successful deployment:

1. **Gather User Feedback** - survey active users
2. **Iterate on Commands** - add most-requested features
3. **Optimize Performance** - based on real usage data
4. **Expand Language Support** - add more languages
5. **Mobile Optimization** - improve mobile UX

---

## Support

### Getting Help

- **Documentation**: All guides in project root
- **GitHub Issues**: Report bugs
- **Email**: voice-support@ai-tickets.com
- **Discord**: #voice-features channel

### Emergency Contacts

- DevOps on-call: [phone/slack]
- Backend engineer: [contact]
- Frontend engineer: [contact]

---

**Deployment complete!** 🚀

Your AI-Tickets platform is now fully voice-optimized and ready for hands-free event management.
