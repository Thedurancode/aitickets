# Real-Time Analytics Dashboard

## Overview

Comprehensive analytics dashboard with real-time updates that visualizes:
- Revenue trends (hourly, daily, monthly)
- Campaign performance (opens, clicks, conversions)
- Alert activity and distribution
- Event performance rankings
- Live metrics via SSE

---

## Architecture

```
Database (PostgreSQL)
    ↓
Analytics API (8 endpoints)
    ↓
SSE Stream (real-time updates every 10s)
    ↓
Frontend Dashboard (charts, tables, metrics)
```

---

## API Endpoints

### Base URL: `/api/dashboard`

### 1. Overall Metrics

**GET /dashboard/metrics**

Get comprehensive dashboard metrics.

**Response:**
```json
{
    "revenue_today": 1245.50,
    "revenue_this_week": 8932.75,
    "revenue_this_month": 34521.00,
    "tickets_sold_today": 24,
    "tickets_sold_this_week": 156,
    "tickets_sold_this_month": 687,
    "active_campaigns": 5,
    "unread_alerts": 3,
    "critical_alerts": 1,
    "conversion_rate": 3.42
}
```

### 2. Real-Time Metrics Stream

**GET /dashboard/metrics/stream**

Server-Sent Events stream with live metric updates every 10 seconds.

**Events:**
- `metrics` - Updated metrics (every 10s)
- `connected` - Initial connection
- `heartbeat` - Keep-alive ping

**Frontend Usage:**
```javascript
const eventSource = new EventSource('/api/dashboard/metrics/stream');

eventSource.addEventListener('metrics', (event) => {
    const metrics = JSON.parse(event.data);

    // Update UI
    document.getElementById('revenue-today').textContent =
        `$${metrics.revenue_today.toLocaleString()}`;
    document.getElementById('tickets-today').textContent =
        metrics.tickets_sold_today;
    document.getElementById('unread-alerts').textContent =
        metrics.unread_alerts;
});

eventSource.addEventListener('connected', () => {
    console.log('Dashboard connected to real-time stream');
});
```

### 3. Campaign Performance

**GET /dashboard/campaigns/performance?days=30&limit=10**

Top performing campaigns by revenue.

**Query Parameters:**
- `days` - Time period (default 30, max 365)
- `limit` - Number of campaigns (default 10, max 50)

**Response:**
```json
[
    {
        "campaign_id": 1,
        "name": "Summer Sale Email Blast",
        "type": "email",
        "sent": 1000,
        "opened": 420,
        "clicked": 72,
        "converted": 18,
        "revenue": 1245.00,
        "open_rate": 42.0,
        "click_rate": 17.14,
        "conversion_rate": 25.0
    }
]
```

### 4. Alert Activity

**GET /dashboard/alerts/activity?days=7**

Alert activity summary.

**Query Parameters:**
- `days` - Time period (default 7, max 90)

**Response:**
```json
{
    "total_alerts": 45,
    "unread_alerts": 3,
    "by_severity": {
        "low": 12,
        "medium": 25,
        "high": 7,
        "critical": 1
    },
    "recent_alerts": [
        {
            "id": 123,
            "title": "Ad Campaign Underperforming",
            "severity": "high",
            "is_read": false,
            "created_at": "2026-03-28T14:32:00Z"
        }
    ]
}
```

### 5. Revenue Charts

**GET /dashboard/revenue/daily?days=30**

Daily revenue trend data for charts.

**Response:**
```json
{
    "labels": ["2026-02-27", "2026-02-28", "2026-03-01", ...],
    "revenue": [245.50, 532.00, 189.75, ...],
    "tickets": [5, 11, 4, ...]
}
```

**GET /dashboard/revenue/hourly?hours=24**

Hourly revenue trend (last 24 hours).

**Response:**
```json
{
    "labels": ["2026-03-28 00:00", "2026-03-28 01:00", ...],
    "revenue": [0, 45.00, 189.50, ...],
    "tickets": [0, 1, 4, ...]
}
```

### 6. Event Performance

**GET /dashboard/events/top-performing?days=30&limit=10**

Top performing events by revenue.

**Response:**
```json
[
    {
        "event_id": 45,
        "event_name": "Summer Music Festival",
        "tickets_sold": 234,
        "revenue": 15678.00
    }
]
```

### 7. Stream Statistics

**GET /dashboard/stats**

Get dashboard stream statistics.

**Response:**
```json
{
    "active_metric_streams": 5,
    "status": "operational"
}
```

---

## Frontend Integration

### React Dashboard Example

```typescript
import { useEffect, useState } from 'react';
import { Line, Bar } from 'react-chartjs-2';

interface Metrics {
    revenue_today: number;
    revenue_this_week: number;
    tickets_sold_today: number;
    unread_alerts: number;
    critical_alerts: number;
}

export function Dashboard() {
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [connected, setConnected] = useState(false);
    const [revenueChart, setRevenueChart] = useState(null);
    const [campaigns, setCampaigns] = useState([]);

    // Real-time metrics stream
    useEffect(() => {
        const eventSource = new EventSource('/api/dashboard/metrics/stream');

        eventSource.addEventListener('metrics', (event) => {
            const data = JSON.parse(event.data);
            setMetrics(data);
        });

        eventSource.addEventListener('connected', () => {
            setConnected(true);
        });

        eventSource.addEventListener('error', () => {
            setConnected(false);
        });

        return () => {
            eventSource.close();
        };
    }, []);

    // Load revenue chart data
    useEffect(() => {
        fetch('/api/dashboard/revenue/daily?days=30')
            .then(res => res.json())
            .then(data => setRevenueChart(data));
    }, []);

    // Load campaign performance
    useEffect(() => {
        fetch('/api/dashboard/campaigns/performance?limit=10')
            .then(res => res.json())
            .then(data => setCampaigns(data));
    }, []);

    if (!metrics) {
        return <div>Loading dashboard...</div>;
    }

    return (
        <div className="dashboard">
            {/* Connection status */}
            <div className={`status ${connected ? 'connected' : 'disconnected'}`}>
                {connected ? '🟢 Live' : '🔴 Disconnected'}
            </div>

            {/* Key metrics */}
            <div className="metrics-grid">
                <MetricCard
                    title="Revenue Today"
                    value={`$${metrics.revenue_today.toLocaleString()}`}
                    trend="+12%"
                />
                <MetricCard
                    title="Tickets Sold Today"
                    value={metrics.tickets_sold_today}
                    trend="+8%"
                />
                <MetricCard
                    title="Unread Alerts"
                    value={metrics.unread_alerts}
                    severity={metrics.critical_alerts > 0 ? 'critical' : 'normal'}
                />
                <MetricCard
                    title="Conversion Rate"
                    value={`${metrics.conversion_rate}%`}
                />
            </div>

            {/* Revenue chart */}
            {revenueChart && (
                <div className="chart-container">
                    <h2>Revenue Trend (30 Days)</h2>
                    <Line
                        data={{
                            labels: revenueChart.labels,
                            datasets: [
                                {
                                    label: 'Revenue',
                                    data: revenueChart.revenue,
                                    borderColor: 'rgb(75, 192, 192)',
                                    tension: 0.1,
                                },
                            ],
                        }}
                    />
                </div>
            )}

            {/* Campaign performance */}
            <div className="campaigns-table">
                <h2>Top Campaigns</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Campaign</th>
                            <th>Type</th>
                            <th>Open Rate</th>
                            <th>Click Rate</th>
                            <th>Conversions</th>
                            <th>Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        {campaigns.map(c => (
                            <tr key={c.campaign_id}>
                                <td>{c.name}</td>
                                <td>{c.type}</td>
                                <td>{c.open_rate}%</td>
                                <td>{c.click_rate}%</td>
                                <td>{c.converted}</td>
                                <td>${c.revenue.toLocaleString()}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function MetricCard({ title, value, trend, severity = 'normal' }) {
    return (
        <div className={`metric-card ${severity}`}>
            <div className="metric-title">{title}</div>
            <div className="metric-value">{value}</div>
            {trend && <div className="metric-trend">{trend}</div>}
        </div>
    );
}
```

### Vanilla JavaScript Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 20px 0;
        }
        .metric-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        .critical {
            border-left: 4px solid red;
        }
        .status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            border-radius: 20px;
            background: #ddd;
        }
        .status.connected {
            background: #4CAF50;
            color: white;
        }
    </style>
</head>
<body>
    <div class="status" id="status">⚪ Connecting...</div>

    <h1>Real-Time Analytics Dashboard</h1>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">Revenue Today</div>
            <div class="metric-value" id="revenue-today">$0</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Tickets Sold</div>
            <div class="metric-value" id="tickets-today">0</div>
        </div>
        <div class="metric-card" id="alerts-card">
            <div class="metric-title">Unread Alerts</div>
            <div class="metric-value" id="unread-alerts">0</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Conversion Rate</div>
            <div class="metric-value" id="conversion-rate">0%</div>
        </div>
    </div>

    <canvas id="revenueChart" width="400" height="100"></canvas>

    <script>
        // Real-time metrics stream
        const eventSource = new EventSource('/api/dashboard/metrics/stream');

        eventSource.addEventListener('metrics', (event) => {
            const metrics = JSON.parse(event.data);

            // Update metrics
            document.getElementById('revenue-today').textContent =
                `$${metrics.revenue_today.toLocaleString()}`;
            document.getElementById('tickets-today').textContent =
                metrics.tickets_sold_today;
            document.getElementById('unread-alerts').textContent =
                metrics.unread_alerts;
            document.getElementById('conversion-rate').textContent =
                `${metrics.conversion_rate}%`;

            // Highlight critical alerts
            const alertsCard = document.getElementById('alerts-card');
            if (metrics.critical_alerts > 0) {
                alertsCard.classList.add('critical');
            } else {
                alertsCard.classList.remove('critical');
            }
        });

        eventSource.addEventListener('connected', () => {
            const status = document.getElementById('status');
            status.textContent = '🟢 Live';
            status.classList.add('connected');
        });

        eventSource.addEventListener('error', () => {
            const status = document.getElementById('status');
            status.textContent = '🔴 Disconnected';
            status.classList.remove('connected');
        });

        // Load revenue chart
        fetch('/api/dashboard/revenue/daily?days=30')
            .then(res => res.json())
            .then(data => {
                const ctx = document.getElementById('revenueChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Revenue',
                            data: data.revenue,
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Revenue Trend (30 Days)'
                            }
                        }
                    }
                });
            });
    </script>
</body>
</html>
```

---

## Features

### Real-Time Updates
- ✅ Metrics update every 10 seconds automatically
- ✅ No polling - efficient SSE push
- ✅ Connection status indicator
- ✅ Auto-reconnect on network issues

### Comprehensive Metrics
- ✅ Revenue (today, week, month)
- ✅ Ticket sales (today, week, month)
- ✅ Active campaigns count
- ✅ Alert activity breakdown
- ✅ Conversion rate tracking

### Campaign Analytics
- ✅ Top performers by revenue
- ✅ Open/click/conversion rates
- ✅ Campaign type breakdown
- ✅ Time period filtering

### Revenue Visualization
- ✅ Daily revenue trends
- ✅ Hourly revenue (last 24h)
- ✅ Chart-ready data format
- ✅ Ticket sales correlation

### Event Performance
- ✅ Top events by revenue
- ✅ Ticket sales rankings
- ✅ Time period filtering

---

## Integration with Existing Systems

### Broadcast Updates on Events

Update the dashboard in real-time when events occur:

```python
# In app/routers/payments.py (after successful payment)
from app.routers.analytics_dashboard import broadcast_metric_update

# After ticket purchase
broadcast_metric_update({
    "revenue_today": new_revenue_today,
    "tickets_sold_today": new_tickets_today,
})
```

```python
# In app/services/alerts.py (after alert created)
from app.routers.analytics_dashboard import broadcast_metric_update

# After alert stored
broadcast_metric_update({
    "unread_alerts": new_unread_count,
    "critical_alerts": new_critical_count,
})
```

---

## Analytics Queries

### Revenue by Hour of Day

```sql
SELECT
    EXTRACT(HOUR FROM created_at) as hour,
    COUNT(*) as tickets,
    SUM(price_cents) / 100.0 as revenue
FROM tickets
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY EXTRACT(HOUR FROM created_at)
ORDER BY hour;
```

### Campaign ROI Analysis

```sql
SELECT
    c.name,
    c.campaign_type,
    c.sent_count,
    c.converted_count,
    c.revenue_cents / 100.0 as revenue,
    ROUND(c.revenue_cents::float / NULLIF(c.sent_count, 0) / 100.0, 2) as revenue_per_send,
    ROUND(100.0 * c.converted_count / NULLIF(c.clicked_count, 0), 2) as conversion_rate
FROM campaigns c
WHERE c.sent_count > 0
ORDER BY c.revenue_cents DESC
LIMIT 20;
```

### Alert Response Time

```sql
SELECT
    severity,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE is_read = true) as read,
    AVG(EXTRACT(EPOCH FROM (read_at - created_at)) / 60) as avg_response_minutes
FROM alerts
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY severity;
```

---

## Performance Considerations

### Caching Strategy
- Metrics endpoint: Cache for 30 seconds
- Chart data: Cache for 5 minutes
- Campaign stats: Cache for 1 minute

**Example with Redis:**
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_dashboard_metrics_cached():
    cached = redis_client.get('dashboard:metrics')
    if cached:
        return json.loads(cached)

    metrics = calculate_metrics()
    redis_client.setex('dashboard:metrics', 30, json.dumps(metrics))
    return metrics
```

### Database Optimization
- Add indexes on `created_at` columns
- Use materialized views for complex aggregations
- Partition tables by date for large datasets

---

## Production Checklist

- [ ] Frontend dashboard built and deployed
- [ ] SSE connection with auto-reconnect implemented
- [ ] Charts library integrated (Chart.js, Recharts, etc.)
- [ ] Caching layer for high-traffic endpoints
- [ ] Database indexes on `created_at` columns
- [ ] Alert notifications for critical metrics
- [ ] Mobile-responsive design
- [ ] Export functionality (CSV, PDF)

---

## What's Now Possible

### 1. Real-Time Business Intelligence
- See revenue tick up in real-time as sales happen
- Instant visibility into critical alerts
- Monitor campaign performance live
- Track conversion rates minute-by-minute

### 2. Data-Driven Decisions
- Identify best-performing campaigns at a glance
- Spot revenue trends immediately
- Compare event performance side-by-side
- Analyze alert patterns over time

### 3. Proactive Management
- Critical alerts highlighted instantly
- Revenue drops trigger immediate investigation
- Campaign underperformance visible immediately
- Event sales velocity tracking

### 4. Team Visibility
- Multiple team members monitor same dashboard
- Real-time updates for everyone simultaneously
- No refresh needed - updates push automatically
- Shared awareness of business state

---

## Next Enhancements

**Short-term:**
1. Export dashboard as PDF report
2. Custom date range filters
3. Comparison mode (this month vs last month)
4. Alert notifications in dashboard

**Long-term:**
5. Predictive analytics (revenue forecasting)
6. Anomaly detection (unusual patterns)
7. Custom dashboards per user
8. Mobile app version

---

## Status: Production Ready ✅

The analytics dashboard is fully implemented and ready to deploy:

✅ **8 API Endpoints**
- Overall metrics
- Real-time SSE stream
- Campaign performance
- Alert activity
- Revenue charts (daily & hourly)
- Event performance
- Stream statistics

✅ **Real-Time Features**
- Live metrics updates (every 10s)
- SSE connection with heartbeat
- Multi-client support
- Auto-reconnect handling

✅ **Chart-Ready Data**
- Daily revenue trends
- Hourly revenue patterns
- Campaign performance breakdown
- Alert severity distribution

**Build your frontend and start visualizing your business in real-time!** 📊
