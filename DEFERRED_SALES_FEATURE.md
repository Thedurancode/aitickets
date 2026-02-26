# Deferred Ticket Sales with Countdown Timer

## Overview

This feature allows event organizers to schedule when tickets go on sale for an event, with a visual countdown timer displayed to visitors before sales begin.

## What Was Added

### 1. Database Schema Changes

Two new columns were added to the `events` table:

- `sale_start_date` (VARCHAR(20)): The date when tickets go on sale (YYYY-MM-DD format)
- `sale_start_time` (VARCHAR(10)): The time when tickets go on sale (HH:MM format)

### 2. Model Changes

Updated `app/models.py`:
```python
sale_start_date = Column(String(20), nullable=True)  # YYYY-MM-DD format
sale_start_time = Column(String(10), nullable=True)  # HH:MM format
```

### 3. Template Changes

Updated `app/templates/public/event_detail.html`:
- Added a countdown section that displays when `sale_start_date` and `sale_start_time` are set
- Countdown timer shows days, hours, minutes, and seconds until sale start
- Purchase buttons are disabled with message "Tickets Not Yet On Sale" until sale begins
- JavaScript automatically enables purchase buttons and hides countdown when sale starts

### 4. JavaScript Functionality

The countdown timer:
- Updates every second
- Automatically hides the countdown section and enables purchase buttons when the sale starts
- Disables all "Get Tickets" buttons until the sale start time is reached

## How to Use

### Setting Sale Start Date/Time

You can set the sale start date and time when creating or updating an event:

```python
from datetime import datetime, timedelta

# Set sale start to 3 days from now at 10:00 AM
sale_start = datetime.now() + timedelta(days=3)
event.sale_start_date = sale_start.strftime("%Y-%m-%d")  # e.g., "2026-03-01"
event.sale_start_time = "10:00"
```

### Leaving Empty for Immediate Sale

If you want tickets to be available immediately, simply leave both fields as `None`:

```python
event.sale_start_date = None
event.sale_start_time = None
```

### Testing the Feature

You can populate an event with a countdown using the provided script:

```bash
python3 populate_event.py
```

This will create an event with tickets going on sale 3 days from now at 10:00 AM.

## Database Migration

If you're upgrading from a previous version, run the migration script:

```bash
python3 migrate_add_sale_start.py
```

This will add the required columns to your existing `events` table.

## Example Display

When tickets aren't on sale yet, visitors see:

```
Tickets Go On Sale Soon
Starting March 1, 2026 at 10:00

[Days:Hours:Minutes:Seconds countdown]
```

All purchase buttons show "Tickets Not Yet On Sale" and are disabled until the countdown reaches zero.

## Technical Details

- **Timezone**: The countdown uses the visitor's local browser time for comparison
- **Auto-refresh**: The countdown updates every second without page refresh
- **Progressive enhancement**: If JavaScript is disabled, the countdown section still shows the sale start date/time
- **Performance**: The countdown stops automatically when it reaches zero to prevent unnecessary updates

## Files Modified

1. `app/models.py` - Added sale_start_date and sale_start_time columns
2. `app/templates/public/event_detail.html` - Added countdown UI and JavaScript
3. `populate_event.py` - Updated to demonstrate the feature
4. `migrate_add_sale_start.py` - Database migration script (new file)
