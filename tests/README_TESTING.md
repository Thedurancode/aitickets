# AI Tickets - Intelligence Testing Guide

Complete guide to testing the autonomous intelligence features.

---

## 🚀 Quick Start

### Option 1: Manual Demonstration (Recommended)

Run the interactive intelligence demonstration:

```bash
# From project root
python tests/manual_test_intelligence.py
```

**What it does:**
- Tests all 7 intelligence systems
- Shows real-time results
- No setup required (uses existing data)
- Takes ~30 seconds

**Output:**
```
================================================================================
  INVENTORY INTELLIGENCE TEST
================================================================================

✓ Event: Drake World Tour 2026
✓ Days until event: 30
✓ Overall sell-through: 15.2%
✓ Pressure level: LOW

💡 Recommendations:
  • [MEDIUM] MAINTAIN: Healthy sell-through rate
    → Continue current marketing strategy
```

---

### Option 2: Full E2E Test Suite

Run comprehensive pytest suite:

```bash
# Install pytest if needed
pip install pytest pytest-asyncio

# Run full test suite
pytest tests/test_e2e_event_lifecycle.py -v -s

# Run specific test
pytest tests/test_e2e_event_lifecycle.py::TestEventLifecycleE2E::test_01_create_event_with_auto_onboarding -v -s
```

**What it tests:**
- Complete event lifecycle from creation to optimization
- All 15 intelligence steps
- MCP voice integration
- Database operations
- API endpoints

**Duration:** ~2-3 minutes

---

## 📋 Test Coverage

### 1. Event Lifecycle Tests (E2E)

**File:** `tests/test_e2e_event_lifecycle.py`

**Tests:**
1. ✅ Event creation with auto-onboarding
2. ✅ Ticket tier creation
3. ✅ Research agent (artist discovery)
4. ✅ Inventory pressure monitoring
5. ✅ Ticket sales simulation
6. ✅ Channel attribution analysis
7. ✅ Performance prediction
8. ✅ Cross-sell recommendations
9. ✅ RFM customer segmentation
10. ✅ Refund pattern detection
11. ✅ Optimal send time calculation
12. ✅ Full intelligence health check
13. ✅ Event comparison (historical)
14. ✅ Pattern analysis
15. ✅ Churn risk detection

**Plus MCP Voice Integration Tests:**
- ✅ Inventory check tool
- ✅ Performance prediction tool
- ✅ Best customers tool

---

### 2. Intelligence System Tests (Manual)

**File:** `tests/manual_test_intelligence.py`

**Features Demonstrated:**

#### A. Inventory Intelligence
```python
# Tests inventory pressure and recommendations
✓ Sell-through analysis
✓ Pressure level (LOW/MEDIUM/HIGH)
✓ Per-tier analysis
✓ AI recommendations (price increases, flash sales, urgency campaigns)
```

#### B. Send Time Optimization
```python
# Calculates optimal email send times
✓ Audience-based timing (genre, demographics)
✓ Event timing (weekend vs weekday)
✓ Pricing-based (professional vs casual)
✓ Confidence scoring
```

#### C. Customer Intelligence
```python
# RFM analysis for segmentation
✓ VIP identification
✓ High-value customers
✓ Regular customers
✓ RFM scores (Recency, Frequency, Monetary)
```

#### D. Event Pattern Analysis
```python
# Identifies success factors
✓ Best-performing venues
✓ Top categories
✓ Seasonal trends
✓ Historical benchmarking
```

#### E. Churn Detection
```python
# Flags at-risk customers
✓ Risk levels (HIGH/MEDIUM/LOW)
✓ Inactivity tracking
✓ Win-back recommendations
```

#### F. Artist Research
```python
# Web search via Perplexity AI
✓ Artist bio
✓ Genre identification
✓ Social media discovery
✓ Fan demographics
```

#### G. Performance Prediction
```python
# AI forecasting
✓ Sell-through prediction
✓ Revenue forecast
✓ Confidence levels
✓ Historical basis
```

---

## 🎯 Testing Scenarios

### Scenario 1: New Event Creation

```bash
# 1. Create event via API
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Taylor Swift Eras Tour",
    "event_date": "2026-08-15",
    "event_time": "19:30:00",
    "venue_id": 1,
    "category_id": 1
  }' \
  -G --data-urlencode "auto_onboard=true"

# 2. Watch background onboarding complete
# 3. Check research report
curl http://localhost:8000/api/event-research/events/{id}/report

# 4. View generated flyer and marketing plan
```

**Expected:**
- Artist researched via web
- Description auto-generated
- Flyer created
- Meta ads configured
- Dynamic pricing enabled

---

### Scenario 2: Inventory Monitoring

```bash
# Check pressure for event
curl http://localhost:8000/api/intelligence/events/{id}/inventory-pressure
```

**Expected Output:**
```json
{
  "pressure_level": "HIGH",
  "overall_sell_through_pct": 85.0,
  "recommendations": [
    {
      "action": "INCREASE_PRICE",
      "priority": "HIGH",
      "reason": "85% sold with 30 days remaining",
      "suggestion": "Increase price by 20-30% using dynamic pricing"
    }
  ]
}
```

---

### Scenario 3: Customer Intelligence

```bash
# Get VIP customers
curl http://localhost:8000/api/intelligence/customers/best?limit=20

# Check churn risk
curl http://localhost:8000/api/intelligence/customers/churn-risk
```

**Expected:**
- RFM scores calculated
- VIP segment identified
- At-risk customers flagged
- Win-back actions recommended

---

### Scenario 4: Performance Prediction

```bash
# Predict event performance
curl http://localhost:8000/api/intelligence/events/{id}/predict-performance
```

**Expected:**
```json
{
  "predictions": {
    "sell_through_rate": 0.82,
    "tickets_sold": 14750,
    "revenue_usd": "$1,106,250.00"
  },
  "confidence": "HIGH",
  "basis": "Based on 8 similar past events"
}
```

---

## 🎤 Voice Testing (MCP)

Test voice-accessible tools:

```python
# In Python/iPython
from mcp_server.server import list_tools
import asyncio

# List all tools
tools = asyncio.run(list_tools())
print(f"Total tools: {len(tools)}")

# Find intelligence tools
intelligence_tools = [t for t in tools if 'intelligence' in t.description.lower()
                     or any(keyword in t.name for keyword in
                     ['check', 'predict', 'detect', 'analyze', 'find', 'compare'])]

print(f"Intelligence tools: {len(intelligence_tools)}")
for tool in intelligence_tools:
    print(f"  • {tool.name}")
```

**Expected:** 10+ intelligence tools available

---

## 📊 Interpreting Results

### Inventory Pressure Levels

- **LOW** (<50% sold): Continue marketing
- **MEDIUM** (50-80% sold): Monitor closely
- **HIGH** (>80% sold): Increase prices or trigger urgency

### RFM Scores

- **12-15**: VIP customers (high recency, frequency, monetary)
- **9-11**: High-value customers
- **6-8**: Regular customers
- **<6**: At-risk or new customers

### Confidence Levels

- **HIGH**: Based on 5+ similar events
- **MEDIUM**: Based on 2-4 similar events
- **LOW**: Based on <2 similar events or different characteristics

---

## 🐛 Troubleshooting

### Issue: "No historical data available"

**Solution:** Some features require historical event data. Either:
- Create and complete a few test events first
- Tests will show graceful fallbacks

### Issue: "Artist research failed"

**Solution:** Web search requires OpenRouter API key:
```bash
# Set in .env
OPENROUTER_API_KEY=your_key_here
```

### Issue: Tests fail with database errors

**Solution:** Ensure database is initialized:
```bash
# Initialize database
python -c "from app.database import init_db; init_db()"
```

### Issue: Import errors

**Solution:** Ensure you're in the project root and virtual env is activated:
```bash
cd /path/to/ai-tickets
source .venv/bin/activate  # or venv/bin/activate
```

---

## 📈 Performance Benchmarks

**Expected test durations:**

| Test Type | Duration | Coverage |
|-----------|----------|----------|
| Manual demonstration | ~30 sec | 7 features |
| Full E2E suite | ~2-3 min | 15 tests |
| Single test | ~5-10 sec | 1 feature |

**API response times:**

| Endpoint | Typical Response |
|----------|-----------------|
| Inventory check | <200ms |
| Send time calculation | <100ms |
| Performance prediction | <500ms |
| Customer RFM analysis | <1s |
| Pattern analysis | <2s |

---

## ✅ Success Criteria

All tests should show:

✓ **Inventory Intelligence**
- Pressure levels calculated
- Recommendations generated
- Tier-by-tier analysis

✓ **Customer Intelligence**
- RFM scores computed
- Segments identified
- Churn risks detected

✓ **Learning Systems**
- Channel attribution analyzed
- Patterns discovered
- Performance predicted

✓ **Autonomous Operations**
- Auto-onboarding triggered
- Artist research completed
- Marketing plans generated

---

## 🎯 Next Steps After Testing

Once tests pass:

1. **Deploy to production**
   ```bash
   # Set production env vars
   # Run migrations
   # Start server
   ```

2. **Enable proactive monitoring**
   ```python
   from app.services.proactive_monitor import schedule_proactive_monitoring
   schedule_proactive_monitoring()
   ```

3. **Configure webhooks for alerts**
   ```bash
   # Add webhook endpoint in settings
   ALERT_WEBHOOK_URL=https://your-webhook.com/alerts
   ```

4. **Test with real events**
   - Create actual events
   - Monitor intelligence systems
   - Verify autonomous actions

---

## 📞 Support

If tests fail or you need help:

1. Check logs: `tail -f logs/app.log`
2. Review test output for specific errors
3. Ensure all dependencies installed: `pip install -r requirements.txt`
4. Verify database schema: `alembic current`

---

**🚀 Your platform is now running at LEVEL 5 AUTONOMOUS!**
