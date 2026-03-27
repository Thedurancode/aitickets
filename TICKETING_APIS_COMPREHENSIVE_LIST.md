# Complete Ticketing & Event Discovery APIs for Integration

Comprehensive list of ticketing platform APIs you can integrate with your AI Tickets system in 2025.

---

## 🎫 Primary Ticketing Platforms (Event Creation)

These platforms let you **create and sell tickets** directly on their marketplace.

### 1. **Eventbrite** ⭐⭐⭐⭐⭐
**Status:** ✅ Already integrated in your codebase
**API Quality:** Excellent
**Best For:** Community events, workshops, fundraisers, conferences

**Features:**
- Create events programmatically
- Manage ticket tiers and pricing
- Track attendees and check-ins
- Payment processing included
- Email notifications
- Analytics and reporting

**API Details:**
- **Docs:** https://www.eventbrite.com/platform/api
- **Auth:** OAuth 2.0
- **Rate Limits:** 1000 calls/day (free), more on paid plans
- **Cost:** Free API, 3.7% + $1.79 per ticket sold

**Integration Effort:** ⏱️ Low (already built)

---

### 2. **Universe (by Ticketmaster)** ⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Good
**Best For:** Small to mid-size events, DIY promoters

**Features:**
- Modern mobile-first interface
- Lower fees than Ticketmaster
- Part of Ticketmaster infrastructure
- Better for indie/local events
- Customizable event pages

**API Details:**
- **Docs:** https://developers.universe.com (via Ticketmaster)
- **Auth:** API key
- **Integration:** Via Ticketmaster API
- **Cost:** ~2-3% per ticket

**Integration Effort:** ⏱️ Medium

---

### 3. **Dice** ⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Limited public API
**Best For:** Music events, nightlife, indie artists

**Features:**
- No hidden fees (transparent pricing)
- Fan-first mobile app
- Discovery-focused platform
- Waitlist management
- Social features

**API Details:**
- **Docs:** Limited public API (partner access)
- **Auth:** Partner agreement required
- **Notes:** Owned by Fever (acquired June 2024)
- **Cost:** Lower fees than competitors

**Integration Effort:** ⏱️ High (requires partnership)

---

### 4. **See Tickets** ⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Partner-only
**Best For:** Larger venues, established promoters

**Features:**
- White-label ticketing
- Advanced seat mapping
- Box office integration
- Multi-venue support

**API Details:**
- **Docs:** Partner access only
- **Auth:** Partnership required
- **Notes:** Owned by CTS Eventim (acquired 2024)
- **Cost:** Negotiated per partnership

**Integration Effort:** ⏱️ Very High (enterprise partnership)

---

### 5. **Ticketmaster** ⭐⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Excellent
**Best For:** Large events, venues, concert tours

**Features:**
- Largest event inventory (230K+ events)
- Global reach (US, Canada, Europe, Australia)
- Advanced seat selection
- Resale marketplace
- Verified tickets

**API Details:**
- **Docs:** https://developer.ticketmaster.com
- **Auth:** API key (free)
- **Rate Limits:** 5,000 calls/day, 5 req/sec
- **Coverage:** US, CA, MX, AU, NZ, UK, IE, Europe
- **Cost:** Free API (read-only), partnership for sales

**Important:** Discovery API is read-only. Creating events requires partnership.

**Integration Effort:** ⏱️ Low for discovery, Very High for sales

---

## 🔍 Secondary Ticketing (Resale Marketplaces)

These platforms buy/sell **already-issued tickets** (resale market).

### 6. **StubHub** ⭐⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Excellent
**Best For:** Secondary ticket market, resale

**Features:**
- World's largest ticket resale marketplace
- FanProtect guarantee
- Last-minute ticket deals
- Mobile ticket delivery
- Price alerts

**API Details:**
- **Docs:** https://developer.stubhub.com
- **Auth:** OAuth 2.0 / API key
- **Endpoints:** Search, inventory, purchase, sell
- **Cost:** Free API

**Integration Effort:** ⏱️ Medium

---

### 7. **Vivid Seats** ⭐⭐⭐⭐
**Status:** 🔶 No public API (use TicketsData)
**API Quality:** Via aggregator only
**Best For:** Ticket resale, price comparison

**Features:**
- 100% buyer guarantee
- Rewards program
- Mobile tickets
- Last-minute deals

**API Details:**
- **Docs:** No public API
- **Access:** Via TicketsData.com (unified API)
- **Cost:** Free via aggregator

**Integration Effort:** ⏱️ Low via TicketsData

---

### 8. **SeatGeek** ⭐⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Excellent
**Best For:** Ticket aggregation, price comparison

**Features:**
- Aggregates tickets from 100+ sites
- Deal Score algorithm
- Interactive seat maps
- Price predictions
- SeatGeek Swaps (ticket exchange)

**API Details:**
- **Docs:** https://platform.seatgeek.com
- **Auth:** API key
- **Endpoints:** Events, performers, venues, tickets
- **Cost:** Free API

**Integration Effort:** ⏱️ Low

---

### 9. **TickPick** ⭐⭐⭐⭐
**Status:** 🔶 No public API (use TicketsData)
**API Quality:** Via aggregator
**Best For:** No-fee tickets, value pricing

**Features:**
- No buyer fees (transparent pricing)
- BestPrice Guarantee
- Mobile-first experience
- Last-minute deals

**API Details:**
- **Docs:** No public API
- **Access:** Via TicketsData.com
- **Cost:** Free via aggregator

**Integration Effort:** ⏱️ Low via TicketsData

---

### 10. **Gametime** ⭐⭐⭐⭐
**Status:** 🔶 No public API (use TicketsData)
**API Quality:** Via aggregator
**Best For:** Last-minute tickets, mobile-first

**Features:**
- Last-minute ticket deals
- Zone seating (instant delivery)
- Gametime Guarantee
- Panoramic seat views
- Price drop alerts

**API Details:**
- **Docs:** No public API
- **Access:** Via TicketsData.com
- **Cost:** Free via aggregator

**Integration Effort:** ⏱️ Low via TicketsData

---

### 11. **Viagogo** ⭐⭐⭐
**Status:** 🔶 No public API (use TicketsData)
**API Quality:** Via aggregator
**Best For:** International events, global coverage

**Features:**
- Global marketplace (70+ countries)
- Multi-currency support
- Viagogo Guarantee
- Wide event coverage

**API Details:**
- **Docs:** No public API
- **Access:** Via TicketsData.com
- **Cost:** Free via aggregator

**Integration Effort:** ⏱️ Low via TicketsData

---

## 🎵 Event Discovery & Artist Platforms

These help users **discover events** and track artists.

### 12. **Bandsintown** ⭐⭐⭐⭐⭐
**Status:** ✅ Already integrated in your codebase
**API Quality:** Excellent
**Best For:** Music events, artist tracking

**Features:**
- Artist event listings
- Fan tracking ("Track" button)
- Tour announcements
- Ticket links
- 50M+ users

**API Details:**
- **Docs:** https://artists.bandsintown.com/support/api
- **Auth:** App ID
- **Endpoints:** Artists, events, venues
- **Cost:** Free

**Integration Effort:** ⏱️ Low (already built)

---

### 13. **Songkick** ⭐⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Excellent
**Best For:** Concert discovery, artist tracking

**Features:**
- Track favorite artists
- Concert notifications
- Personalized recommendations
- Calendar integration
- Metro area searches

**API Details:**
- **Docs:** https://www.songkick.com/developer
- **Auth:** API key (free)
- **Endpoints:** Events, artists, venues, metro areas
- **Cost:** Free API

**Integration Effort:** ⏱️ Low

---

### 14. **Meetup** ⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Good (GraphQL)
**Best For:** Community events, networking, groups

**Features:**
- Group management
- Event RSVPs
- Member directory
- Discussion forums
- Photo sharing

**API Details:**
- **Docs:** https://www.meetup.com/graphql/guide
- **Auth:** OAuth 2.0 (Pro customers only)
- **Type:** GraphQL API
- **Cost:** Pro membership required for API access
- **Changes:** New GraphQL API released Feb 2025

**Integration Effort:** ⏱️ Medium (requires Pro subscription)

---

### 15. **Resident Advisor (RA)** ⭐⭐⭐⭐
**Status:** 🔶 Limited/no public API
**API Quality:** Unknown
**Best For:** Electronic music, nightlife, club events

**Features:**
- Electronic music focus
- Global event listings
- DJ/artist profiles
- Ticketing via RA Tickets
- Magazine/editorial content

**API Details:**
- **Docs:** RA Pro for listing events (no public API)
- **Access:** https://pro.ra.co/listing
- **Notes:** World's largest electronic music platform
- **Cost:** Listing fees apply

**Integration Effort:** ⏱️ Very High (may require scraping or partnership)

---

### 16. **Allevents** ⭐⭐⭐
**Status:** 🔶 Unknown API availability
**API Quality:** Unknown
**Best For:** Event aggregation, discovery

**Features:**
- Event aggregator
- Local event discovery
- Multiple categories
- Calendar export

**API Details:**
- **Docs:** No public API documentation found
- **Notes:** May require partnership or custom integration

**Integration Effort:** ⏱️ Unknown

---

## 🔗 Unified Aggregator APIs

One API to access multiple platforms.

### 17. **TicketsData** ⭐⭐⭐⭐⭐
**Status:** 🔶 Needs integration
**API Quality:** Excellent
**Best For:** Multi-platform ticket aggregation

**Platforms Covered:**
- ✅ Ticketmaster
- ✅ SeatGeek
- ✅ StubHub
- ✅ Vivid Seats
- ✅ Gametime
- ✅ TickPick
- ✅ Viagogo

**Features:**
- Unified JSON format across all platforms
- Real-time ticket pricing
- Event data normalization
- Single API key for all sources
- Developer-friendly responses

**API Details:**
- **Docs:** https://ticketsdata.com/docs
- **Auth:** API key
- **Cost:** Paid tiers based on usage
- **Benefit:** Avoid building 7 separate integrations

**Integration Effort:** ⏱️ Low (one integration = 7 platforms)

---

## 📊 Comparison Table

| Platform | Type | API Quality | Cost | Integration Effort | Recommended |
|----------|------|-------------|------|-------------------|-------------|
| **Eventbrite** | Primary | ⭐⭐⭐⭐⭐ | 3.7% + $1.79 | ✅ Done | ✅ Yes |
| **Bandsintown** | Discovery | ⭐⭐⭐⭐⭐ | Free | ✅ Done | ✅ Yes |
| **Songkick** | Discovery | ⭐⭐⭐⭐⭐ | Free | Low | ✅ Yes |
| **SeatGeek** | Resale | ⭐⭐⭐⭐⭐ | Free | Low | ✅ Yes |
| **StubHub** | Resale | ⭐⭐⭐⭐⭐ | Free | Medium | ✅ Yes |
| **Ticketmaster** | Primary | ⭐⭐⭐⭐⭐ | Free (read) | Low (read only) | ⚠️ Read-only |
| **TicketsData** | Aggregator | ⭐⭐⭐⭐⭐ | Paid | Low | ✅ Yes (covers 7 platforms) |
| **Universe** | Primary | ⭐⭐⭐⭐ | 2-3% | Medium | ✅ Yes |
| **Meetup** | Discovery | ⭐⭐⭐⭐ | Pro required | Medium | ⚠️ If you target community events |
| **Dice** | Primary | ⭐⭐⭐⭐ | Low fees | High (partnership) | ⚠️ If music-focused |
| **Resident Advisor** | Discovery | ⭐⭐⭐⭐ | Unknown | Very High | ⚠️ If electronic music |

---

## 🚀 Recommended Integration Priority

### **Phase 1: Quick Wins (Already Done + Easy)** ✅
1. ✅ Eventbrite (done)
2. ✅ Bandsintown (done)
3. ✅ Social Media via Postiz (done)
4. ✅ Meta Ads (done)
5. 🔶 Songkick (add next - free, easy)
6. 🔶 SeatGeek (add next - free, easy)

### **Phase 2: Aggregator (One API = Many Platforms)** 💰
7. 🔶 TicketsData (paid but covers 7 platforms at once)
   - Ticketmaster, SeatGeek, StubHub, Vivid Seats, Gametime, TickPick, Viagogo

### **Phase 3: Secondary Markets** 🎫
8. 🔶 StubHub (if not using TicketsData)
9. 🔶 Ticketmaster Discovery API (read-only event data)

### **Phase 4: Niche Platforms** 🎵
10. 🔶 Universe (Ticketmaster's DIY platform)
11. 🔶 Meetup (if targeting community events)
12. 🔶 Resident Advisor (if electronic music focus)

---

## 💡 Integration Strategies

### **Strategy A: Maximum Coverage (Recommended)**
```
✅ Eventbrite (creating events)
✅ Social Media (promotion)
✅ Songkick (discovery)
✅ TicketsData (aggregation - covers 7 resale platforms)
```
**Result:** 10+ platforms with 4 integrations

### **Strategy B: Free APIs Only**
```
✅ Eventbrite
✅ Bandsintown
✅ Songkick
✅ SeatGeek
✅ StubHub
✅ Ticketmaster (read-only)
```
**Result:** 6 platforms, $0/month

### **Strategy C: Premium (Maximum Reach)**
```
✅ All free APIs
✅ TicketsData (paid aggregator)
✅ Universe (low fees)
✅ Meetup Pro (community events)
```
**Result:** 15+ platforms

---

## 📝 Next Steps

1. **Add Songkick integration** (free, easy, high ROI)
2. **Add SeatGeek integration** (free, price comparison data)
3. **Evaluate TicketsData** (one integration = 7 resale platforms)
4. **Consider Universe** (mid-size events, lower fees than Ticketmaster)
5. **Add Meetup if needed** (requires Pro subscription)

---

## 🔑 Environment Variables to Add

```env
# Discovery & Tracking
SONGKICK_API_KEY=your_key
SEATGEEK_API_KEY=your_key

# Aggregator (optional but powerful)
TICKETSDATA_API_KEY=your_key

# Ticketmaster (read-only discovery)
TICKETMASTER_API_KEY=your_key

# Community Events (requires Pro)
MEETUP_OAUTH_KEY=your_key
MEETUP_OAUTH_SECRET=your_secret

# DIY Ticketing
UNIVERSE_API_KEY=your_key

# Resale Markets
STUBHUB_API_KEY=your_key
```

---

**Bottom Line:** You already have 4 major integrations. Add Songkick + SeatGeek (both free, easy) for maximum discovery. Consider TicketsData to access 7 resale marketplaces with one integration.
