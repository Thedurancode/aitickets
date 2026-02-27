# AI Tickets - Complete User Guide for Moltenclaw

## 🎯 Welcome to AI Tickets

AI Tickets is a comprehensive event management and ticketing platform with AI-powered voice agent integration, customer intelligence, marketing automation, and multi-channel communication capabilities.

### What You Can Do

- 🎪 **Manage Events**: Create, promote, and sell tickets for events
- 🎫 **Sell Tickets**: Multi-tier pricing with Stripe payment processing
- 🤖 **Voice Integration**: Natural language voice agent with 150+ tools
- 📊 **Customer Intelligence**: Deep insights into customer behavior and preferences
- 📧 **Marketing Automation**: Email, SMS, and social media campaigns
- 📈 **Analytics**: Real-time sales data, attendance tracking, and revenue reports
- 🎨 **AI Flyers**: Generate event flyers using AI style transfer
- 📱 **Mobile Wallet**: Apple Wallet integration for tickets
- 🔔 **Notifications**: Automated reminders and updates
- 📸 **Photo Galleries**: User-generated content with moderation

---

## 🚀 Getting Started

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/ai-tickets.git
cd ai-tickets

# Install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Set up environment
cp .env.development .env
# Edit .env with your API keys and configuration

# Initialize database
python -c "from app.database import init_db; init_db()"

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Configuration

Edit your `.env` file with essential settings:

```env
# Organization
ORG_NAME=Your Organization Name
ORG_COLOR=#CE1141
ORG_LOGO_URL=https://your-logo.com/logo.png

# Database
database_url=sqlite:///./tickets.db

# Stripe (Payments)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Email (Resend)
RESEND_API_KEY=re_...
FROM_EMAIL=tickets@yourdomain.com

# SMS (Twilio)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# LLM (for voice agent)
OPENROUTER_API_KEY=sk-or-...
LLM_ROUTER_MODEL=openai/gpt-4o-mini
```

### 3. First Steps

1. **Create a Venue**:
```bash
curl -X POST "http://localhost:8000/api/venues" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Grand Theater",
    "address": "123 Main St, City, State",
    "phone": "+1-555-0100",
    "description": "Premier event venue"
  }'
```

2. **Create an Event**:
```bash
curl -X POST "http://localhost:8000/api/events" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "venue_id": 1,
    "name": "Summer Music Festival",
    "description": "An amazing evening of live music",
    "event_date": "2026-07-15",
    "event_time": "19:00",
    "image_url": "https://example.com/image.jpg"
  }'
```

3. **Add Ticket Tiers**:
```bash
curl -X POST "http://localhost:8000/api/events/1/tiers" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "General Admission",
    "description": "Standard entry",
    "price": 5000,
    "quantity_available": 500
  }'
```

---

## 🎪 Core Features

### Event Management

#### Creating Events

**Basic Event**:
```python
import requests

event_data = {
    "venue_id": 1,
    "name": "Tech Conference 2026",
    "description": "Annual technology conference",
    "event_date": "2026-09-20",
    "event_time": "09:00",
    "doors_open_time": "08:00",
    "image_url": "https://example.com/tech-conf.jpg",
    "promo_video_url": "https://youtube.com/watch?v=...",
    "is_visible": True
}

response = requests.post(
    "http://localhost:8000/api/events",
    json=event_data,
    headers={"Authorization": f"Bearer {API_KEY}"}
)
event = response.json()
print(f"Event created: {event['id']}")
```

**Recurring Event Series**:
```python
# Create events every Tuesday for 3 months
from datetime import datetime, timedelta

import requests

response = requests.post(
    "http://localhost:8000/api/events/recurring",
    json={
        "venue_id": 1,
        "name": "Weekly Comedy Night",
        "description": "Every Tuesday night comedy",
        "start_date": "2026-03-01",
        "end_date": "2026-05-31",
        "days_of_week": ["tuesday"],
        "event_time": "20:00",
        "ticket_tiers": [
            {
                "name": "Admission",
                "price": 2500,
                "quantity_available": 100
            }
        ]
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

#### Updating Events

```python
# Update event details
requests.put(
    f"http://localhost:8000/api/events/{event_id}",
    json={
        "name": "Updated Event Name",
        "description": "New description",
        "image_url": "https://example.com/new-image.jpg"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Set post-event recap video
requests.post(
    f"http://localhost:8000/api/events/{event_id}/recap-video",
    json={"video_url": "https://youtube.com/watch?v=..."},
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Postpone event
requests.post(
    f"http://localhost:8000/api/events/{event_id}/postpone",
    json={
        "new_date": "2026-08-15",
        "new_time": "19:00",
        "notify_attendees": True
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Cancel event
requests.post(
    f"http://localhost:8000/api/events/{event_id}/cancel",
    json={
        "reason": "Due to unforeseen circumstances",
        "notify_attendees": True
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Ticket Management

#### Creating Ticket Tiers

```python
# Create multiple pricing tiers
tiers = [
    {
        "name": "VIP",
        "description": "Front row + meet & greet",
        "price": 15000,  # $150.00
        "quantity_available": 50
    },
    {
        "name": "Premium",
        "description": "Premium seating",
        "price": 7500,   # $75.00
        "quantity_available": 200
    },
    {
        "name": "General Admission",
        "description": "Standard entry",
        "price": 3500,   # $35.00
        "quantity_available": 500
    }
]

for tier_data in tiers:
    requests.post(
        f"http://localhost:8000/api/events/{event_id}/tiers",
        json=tier_data,
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
```

#### Managing Ticket Availability

```python
# Update tier
requests.put(
    f"http://localhost:8000/api/tiers/{tier_id}",
    json={
        "status": "paused",  # Options: active, paused, sold_out
        "quantity_available": 600
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Check availability
response = requests.get(
    f"http://localhost:8000/api/events/{event_id}/tiers"
)
availability = response.json()
for tier in availability:
    print(f"{tier['name']}: {tier['remaining']} remaining")
```

#### Processing Purchases

```python
# Purchase tickets
response = requests.post(
    f"http://localhost:8000/api/tickets/events/{event_id}/purchase",
    json={
        "ticket_tier_id": tier_id,
        "quantity": 2,
        "name": "John Doe",
        "email": "john@example.com"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

result = response.json()
if result.get("checkout_url"):
    print(f"Redirect to: {result['checkout_url']}")
```

#### Check-In Management

```python
# Validate and check in ticket
response = requests.post(
    "http://localhost:8000/api/tickets/validate",
    json={"qr_token": "abc123xyz"},
    headers={"Authorization": f"Bearer {API_KEY}"}
)

if response.json().get("valid"):
    # Check in guest
    requests.post(
        f"http://localhost:8000/api/tickets/{ticket_id}/check-in",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )

# Undo check-in
requests.post(
    f"http://localhost:8000/api/tickets/{ticket_id}/undo-check-in",
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

---

## 🤖 Voice Agent Integration

### Overview

The voice agent provides natural language access to 150+ tools for event management, customer service, and marketing automation.

### Voice Agent Endpoint

**POST** `/voice/action`

```bash
curl -X POST "http://localhost:8000/voice/action" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_MCP_API_KEY" \
  -d '{
    "text": "How many tickets have we sold for the Summer Music Festival?",
    "session_id": "optional-session-id"
  }'
```

### Example Conversations

#### Event Management

```
User: "Create a new event at the Grand Theater called Jazz Night"
Agent: "I'll create Jazz Night at Grand Theater. What date and time?"

User: "Next Friday at 8 PM"
Agent: "Got it. How much should tickets cost and how many available?"

User: "$50 general admission, 200 tickets"
Agent: "Perfect! I've created Jazz Night for next Friday at 8 PM with 200 $50 tickets at Grand Theater."
```

#### Customer Lookup

```
User: "Find customer John Smith"
Agent: "I found John Smith (john@example.com, +1-555-0100). He's attended 5 events and spent $450 total."

User: "What events has he attended?"
Agent: "John has attended Summer Music Festival, Tech Conference, Jazz Night, Comedy Show, and Wine Tasting."
```

#### Marketing

```
User: "Send a reminder to all Summer Music Festival attendees"
Agent: "I'll send event reminders to all 127 attendees of Summer Music Festival. Sending now..."

User: "Create a 20% off promo code for VIP customers"
Agent: "I've created promo code VIP20 for 20% off. It's valid for all events and can be used 100 times."
```

### Session Context

The voice agent remembers context across conversations:

```python
# First request
response = requests.post(
    "http://localhost:8000/voice/action",
    json={
        "text": "Find the Jazz Night event",
        "session_id": "user-123"
    },
    headers={"X-API-Key": MCP_API_KEY}
)
# Agent now has context about Jazz Night event

# Follow-up request
response = requests.post(
    "http://localhost:8000/voice/action",
    json={
        "text": "How many tickets are left?",  # Refers to Jazz Night from context
        "session_id": "user-123"
    },
    headers={"X-API-Key": MCP_API_KEY}
)
```

### Available MCP Tools

The system exposes 150+ tools organized into categories:

**Event Management**: `create_event`, `update_event`, `postpone_event`, `cancel_event`, `list_events`
**Ticket Operations**: `purchase_tickets`, `validate_ticket`, `check_in_guest`, `list_tickets`
**Customer Management**: `find_customer`, `create_customer`, `update_customer`, `get_customer_stats`
**Marketing**: `send_marketing_email`, `send_marketing_sms`, `create_promo_code`
**Analytics**: `get_event_sales`, `get_revenue_report`, `get_attendance_stats`
**Notifications**: `send_ticket_confirmation`, `send_reminder`, `send_event_update`

---

## 👥 Customer Intelligence

### Customer Search

```python
# Find by name (fuzzy search)
response = requests.get(
    "http://localhost:8000/api/customers/search",
    params={"name": "john"},
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Find by email
response = requests.get(
    "http://localhost:8000/api/customers/search",
    params={"email": "john@example.com"},
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Find by phone
response = requests.get(
    "http://localhost:8000/api/customers/search",
    params={"phone": "+1-555-0100"},
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Customer Profiles

```python
# Get customer details
response = requests.get(
    f"http://localhost:8000/api/customers/{customer_id}",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

customer = response.json()
print(f"Name: {customer['name']}")
print(f"Email: {customer['email']}")
print(f"Phone: {customer['phone']}")
print(f"Total Spend: ${customer['preferences']['total_spent_cents']/100:.2f}")
print(f"Events Attended: {customer['preferences']['total_events_attended']}")
print(f"VIP Status: {customer['preferences']['is_vip']}")
```

### Customer Segmentation

```python
# Get RFM segments
response = requests.get(
    "http://localhost:8000/api/analytics/customer-segments",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

segments = response.json()
# Returns: champions, loyal, potential_loyalists, at_risk, hibernating, lost

# Target specific segment
champions = segments['champions']
print(f"Champions: {len(champions)} customers")

# Send campaign to champions
for customer in champions:
    send_vip_offer(customer['email'])
```

### Customer Notes

```python
# Add AI-captured note
requests.post(
    f"http://localhost:8000/api/customers/{customer_id}/notes",
    json={
        "note_type": "preference",
        "note": "Prefers front-row seats, attends jazz events regularly"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Get customer notes
response = requests.get(
    f"http://localhost:8000/api/customers/{customer_id}/notes",
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

---

## 📧 Marketing Automation

### Email Campaigns

```python
# Send marketing email
requests.post(
    "http://localhost:8000/api/notifications/campaigns",
    json={
        "name": "Summer Festival Promo",
        "subject": "Early Bird Tickets Now Available!",
        "content": "Join us for the biggest event of the summer...",
        "target_segments": {
            "min_events": 2,
            "min_spent_cents": 10000
        },
        "channel": "email"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### SMS Campaigns

```python
# Send SMS blast
requests.post(
    "http://localhost:8000/api/notifications/campaigns",
    json={
        "name": "Event Reminder",
        "message": "Don't forget! Event starts in 24 hours.",
        "target_event_id": event_id,
        "channel": "sms"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Promo Codes

```python
# Create promo code
requests.post(
    "http://localhost:8000/api/promo-codes",
    json={
        "code": "SUMMER2026",
        "discount_type": "percent",
        "discount_value": 20,  # 20%
        "max_uses": 100,
        "valid_until": "2026-07-01",
        "event_id": event_id  # Event-specific, or omit for all events
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Validate promo code
response = requests.post(
    "http://localhost:8000/api/promo-codes/validate",
    json={
        "code": "SUMMER2026",
        "ticket_tier_id": tier_id
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

result = response.json()
if result['valid']:
    print(f"Discount: {result['message']}")
```

### Event Reminders

```python
# Send reminders to all attendees
requests.post(
    f"http://localhost:8000/api/events/{event_id}/reminders",
    json={
        "hours_before": 24,
        "channels": ["email", "sms"]
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

---

## 📊 Analytics & Reporting

### Event Analytics

```python
# Get event sales
response = requests.get(
    f"http://localhost:8000/api/analytics/events/{event_id}",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

analytics = response.json()
print(f"Total Revenue: ${analytics['revenue_cents']/100:.2f}")
print(f"Tickets Sold: {analytics['tickets_sold']}")
print(f"Attendance Rate: {analytics['attendance_rate']}%")
print(f"Page Views: {analytics['page_views']}")
```

### Revenue Reports

```python
# Get revenue by date range
response = requests.get(
    "http://localhost:8000/api/analytics/revenue",
    params={
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "group_by": "month"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

monthly_revenue = response.json()
for month in monthly_revenue:
    print(f"{month['month']}: ${month['revenue']:.2f}")
```

### Conversion Tracking

```python
# Get conversion funnel
response = requests.get(
    f"http://localhost:8000/api/analytics/events/{event_id}/conversion",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

funnel = response.json()
print(f"Page Views: {funnel['page_views']}")
print(f"Started Checkout: {funnel['checkout_started']}")
print(f"Purchased: {funnel['purchased']}")
print(f"Conversion Rate: {funnel['conversion_rate']}%")
```

---

## 🎨 AI Flyer Generation

### Template-Based Flyers

```python
# List available templates
response = requests.get(
    "http://localhost:8000/api/flyer-templates",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

templates = response.json()
for template in templates:
    print(f"{template['name']}: {template['description']}")

# Generate flyer from template
response = requests.post(
    f"http://localhost:8000/api/flyer-templates/events/{event_id}/generate/{template_id}",
    json={
        "event_name_override": "Special Edition Jazz Night",
        "highlight_text": "Limited Seating Available"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

flyer = response.json()
print(f"Flyer URL: {flyer['image_url']}")
```

### SMS Template Selection

```python
# Generate magic link for template selection
response = requests.post(
    "http://localhost:8000/api/flyer-templates/generate-token",
    json={
        "event_id": event_id,
        "phone": "+1-555-0100"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

token = response.json()['token']
selection_link = f"http://yourdomain.com/flyer-templates/select/{token}"

# Send link via SMS
import requests
from twilio.rest import Client

client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
client.messages.create(
    body=f"Choose a flyer template: {selection_link}",
    from_=settings.twilio_phone_number,
    to="+1-555-0100"
)
```

---

## 📱 Apple Wallet Integration

### Generate Wallet Pass

```python
# Configure Apple Wallet in .env:
# APPLE_WALLET_TEAM_ID=...
# APPLE_WALLET_PASS_TYPE_ID=pass.com.yourorg.event
# APPLE_WALLET_CERT_PATH=/path/to/cert.pem
# APPLE_WALLET_KEY_PATH=/path/to/key.pem
# APPLE_WALLET_WWDR_CERT_PATH=/path/to/wwdr.pem

# Generate .pkpass file
response = requests.get(
    f"http://localhost:8000/api/tickets/{ticket_id}/wallet-pass",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

with open("ticket.pkpass", "wb") as f:
    f.write(response.content)

# Send .pkpass file as email attachment or download link
```

---

## 🔔 Notification System

### Ticket Confirmation

```python
# Send ticket confirmation via email
requests.post(
    f"http://localhost:8000/api/tickets/{ticket_id}/confirm",
    json={
        "channel": "email",
        "include_qr": True
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Send via SMS
requests.post(
    f"http://localhost:8000/api/tickets/{ticket_id}/confirm",
    json={
        "channel": "sms",
        "include_qr": False
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Event Updates

```python
# Notify attendees of event changes
requests.post(
    f"http://localhost:8000/api/events/{event_id}/notify",
    json={
        "subject": "Event Time Changed",
        "message": "The event has been moved to 8:30 PM.",
        "channels": ["email", "sms"]
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Birthday Greetings

```python
# Send birthday wishes (for customers with birthday_opt_in=True)
requests.post(
    "http://localhost:8000/api/notifications/birthdays",
    json={
        "message": "Happy Birthday! Enjoy 20% off your next event.",
        "promo_code": "BIRTHDAY20",
        "channels": ["email"]
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

---

## 📸 Photo Galleries & User Content

### Event Photos

```python
# Get event photos
response = requests.get(
    f"http://localhost:8000/api/events/{event_id}/photos",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

photos = response.json()
for photo in photos:
    print(f"{photo['photo_url']} (moderation: {photo['moderation_status']})")
```

### Content Moderation

```python
# Review moderated content
response = requests.get(
    "http://localhost:8000/api/photos/pending-review",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

pending = response.json()
for photo in pending:
    # Approve
    requests.put(
        f"http://localhost:8000/api/photos/{photo['id']}/moderate",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {API_KEY}"}
    )

    # Or reject
    requests.put(
        f"http://localhost:8000/api/photos/{photo['id']}/moderate",
        json={"action": "reject", "reason": "Inappropriate content"},
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
```

---

## 🔌 Webhook Integration

### Register Webhook

```python
# Register webhook endpoint
requests.post(
    "http://localhost:8000/api/webhooks/outbound",
    json={
        "url": "https://your-app.com/webhooks",
        "secret": "your-webhook-secret",
        "description": "Ticket purchase notifications",
        "event_types": ["ticket.purchased", "ticket.checked_in"]
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Handle Webhook Payload

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

WEBHOOK_SECRET = "your-webhook-secret"

@app.route('/webhooks', methods=['POST'])
def handle_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Webhook-Signature')

    # Verify signature
    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return jsonify({"error": "Invalid signature"}), 401

    event = request.json
    event_type = event['type']
    data = event['data']

    if event_type == 'ticket.purchased':
        # Handle ticket purchase
        customer_id = data['customer_id']
        ticket_id = data['ticket_id']
        # Your logic here

    elif event_type == 'ticket.checked_in':
        # Handle check-in
        ticket_id = data['ticket_id']
        # Your logic here

    return jsonify({"status": "ok"}), 200
```

---

## 🔑 Authentication & Security

### API Keys

The system uses two levels of API keys:

**MCP API Key** (for voice/voice endpoints):
```env
MCP_API_KEY=your-mcp-key-here
```

**Admin API Key** (for REST API endpoints):
```env
ADMIN_API_KEY=your-admin-key-here
```

Usage:
```python
headers = {
    "X-API-Key": "your-api-key",
    "Authorization": f"Bearer {your-api-key}"
}
```

### Magic Link Authentication

```python
# Generate magic link for event admin
response = requests.post(
    f"http://localhost:8000/api/events/{event_id}/admin-link",
    json={
        "phone": "+1-555-0100"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

token = response.json()['token']
admin_link = f"http://yourdomain.com/events/{event_id}/admin?token={token}"

# Send link via SMS
# User can access admin dashboard without password
```

---

## 🎯 Best Practices

### 1. Event Setup

**Always create venues first**:
```python
# Create venue, then create event with venue_id
venue = create_venue(...)
event = create_event(venue_id=venue['id'], ...)
```

**Use recurring events for series**:
```python
# Instead of creating 10 separate events
create_recurring_event(
    days_of_week=["friday"],
    start_date="2026-06-01",
    end_date="2026-08-31"
)
```

### 2. Ticket Management

**Set up tier pricing strategically**:
```python
tiers = [
    {"name": "VIP", "price": 15000, "quantity": 50},      # High margin
    {"name": "Premium", "price": 7500, "quantity": 200},  # Mid tier
    {"name": "General", "price": 3500, "quantity": 500}    # Volume
]
```

**Use inventory alerts**:
```python
{
    "alert_thresholds": "80,90,95",  # Alert at 80%, 90%, 95% sold
}
```

### 3. Customer Communication

**Always send confirmations**:
```python
send_ticket_confirmation(ticket_id, channels=["email", "sms"])
```

**Use reminders strategically**:
```python
# 24 hours before
send_reminder(event_id, hours_before=24)

# 1 hour before (for timely events)
send_reminder(event_id, hours_before=1)
```

### 4. Marketing Automation

**Segment your audience**:
```python
# Target VIP customers
campaign = {
    "target_segments": {
        "is_vip": True,
        "min_events": 5
    }
}
```

**Use progressive discounts**:
```python
# Early bird pricing
create_promo_code(
    code="EARLYBIRD",
    discount_value=30,
    valid_until="2026-06-01"
)

# Regular pricing
create_promo_code(
    code="SUMMER20",
    discount_value=20,
    valid_until="2026-07-01"
)

# Last minute
create_promo_code(
    code="LASTCHANCE",
    discount_value=10,
    valid_until="2026-07-15"
)
```

### 5. Analytics

**Monitor conversion funnels**:
```python
funnel = get_conversion_funnel(event_id)
if funnel['conversion_rate'] < 5:
    # Optimize event page or pricing
```

**Track customer lifetime value**:
```python
customer = get_customer(customer_id)
clv = customer['preferences']['total_spent_cents']
if clv > 50000:  # $500+
    # Offer VIP treatment
```

---

## 🐛 Troubleshooting

### Common Issues

#### Stripe Payment Fails

**Problem**: Payments not processing
**Solution**:
- Check Stripe API keys in `.env`
- Verify webhook endpoint is accessible
- Test webhook signing: `stripe listen --forward-to localhost:8000/api/webhooks/stripe`

#### SMS Not Sending

**Problem**: Twilio SMS not delivered
**Solution**:
- Verify Twilio credentials
- Check phone number format (E.164: +1...)
- Ensure account has sufficient credits

#### Email Bounces

**Problem**: Resend email delivery fails
**Solution**:
- Verify API key
- Check sender domain is verified
- Review email content for spam triggers

#### Database Locks

**Problem**: SQLite database locked
**Solution**:
- For production, use PostgreSQL: `database_url=postgresql://...`
- For development, ensure only one server instance running

#### Voice Agent Not Responding

**Problem**: Voice agent returns errors
**Solution**:
- Verify `MCP_API_KEY` is set
- Check `OPENROUTER_API_KEY` is valid
- Review server logs: `tail -f logs/app.log`

---

## 📚 Additional Resources

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Database Schema

```bash
# Generate schema diagram
python -c "from app.database import Base; from sqlalchemy_schemadisplay import create_schema_graph; create_schema_graph(Base).write_png('schema.png')"
```

### Testing

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=app tests/
```

### Monitoring

```bash
# Check health status
curl http://localhost:8000/health

# View server logs
tail -f logs/app.log

# Monitor database
sqlite3 tickets.db ".tables"
```

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `ENV=production`
- [ ] Use PostgreSQL database
- [ ] Configure proper CORS origins
- [ ] Set up SSL/HTTPS
- [ ] Configure rate limiting
- [ ] Set up logging (structured format)
- [ ] Configure webhook endpoints
- [ ] Test payment flow
- [ ] Set up backup strategy
- [ ] Configure monitoring/alerting

### Environment Configuration

```env
ENV=production
database_url=postgresql://user:pass@localhost/tickets
LOG_LEVEL=INFO
LOG_FORMAT=structured
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t ai-tickets .
docker run -p 8000:8000 --env-file .env.production ai-tickets
```

---

## 💡 Tips & Tricks

### Quick Event Creation

```python
# One-liner event creation
import requests
requests.post("http://localhost:8000/api/events", json={
    "venue_id": 1,
    "name": "Tonight's Show",
    "event_date": "2026-02-27",
    "event_time": "20:00",
    "ticket_tiers": [{"name": "Admission", "price": 2500, "quantity": 100}]
}, headers={"Authorization": f"Bearer {API_KEY}"})
```

### Bulk Customer Import

```python
# Import from CSV
import csv

with open('customers.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        requests.post(
            "http://localhost:8000/api/event-goers",
            json={
                "email": row['email'],
                "name": row['name'],
                "phone": row.get('phone'),
                "email_opt_in": row.get('email_opt_in', 'true').lower() == 'true'
            },
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
```

### Quick Analytics

```python
# Get today's revenue
from datetime import date
requests.get(
    "http://localhost:8000/api/analytics/revenue",
    params={"start_date": date.today().isoformat(), "end_date": date.today().isoformat()},
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

---

## 🎓 Advanced Features

### Voice Calling Campaigns

```python
# Start automated voice campaign
requests.post(
    "http://localhost:8000/api/voice/campaigns",
    json={
        "name": "Event Reminder Calls",
        "goal": "event_reminder",
        "target_event_id": event_id,
        "start_calling_after": "10:00",
        "stop_calling_before": "21:00",
        "timezone": "America/New_York"
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Meta Ads Integration

```python
# Create Facebook/Instagram ad
requests.post(
    "http://localhost:8000/api/meta-ads/campaigns",
    json={
        "event_id": event_id,
        "budget_cents": 50000,  # $500 budget
        "targeting_radius_miles": 25,
        "age_min": 21,
        "age_max": 55
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### Knowledge Base (RAG)

```python
# Upload venue FAQ
requests.post(
    "http://localhost:8000/api/knowledge/upload",
    files={
        "file": open("venue-faq.pdf", "rb"),
        "venue_id": 1
    },
    headers={"Authorization": f"Bearer {API_KEY}"}
)

# Search knowledge base
requests.get(
    "http://localhost:8000/api/knowledge/search",
    params={"query": "parking availability", "venue_id": 1},
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

---

## 📞 Support

For issues, questions, or feature requests:
- 📧 Email: support@moltenclaw.com
- 📚 Documentation: https://docs.moltenclaw.com
- 💬 Community: https://community.moltenclaw.com

---

**Version**: 1.0.0
**Last Updated**: 2026-02-27
**Maintained By**: Moltenclaw Team
