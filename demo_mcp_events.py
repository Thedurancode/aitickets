#!/usr/bin/env python3
"""
MCP Event Intelligence Demo

Demonstrates everything MCP can do for events:
- Create events from natural language
- Research market and competitors
- Analyze event performance
- Optimize pricing dynamically
- Compare multiple events
- Search cross-session memory
"""
import json


print("=" * 80)
print("🎯 MCP EVENT INTELLIGENCE - COMPLETE CAPABILITIES")
print("=" * 80)

# ==================== 1. CREATE EVENT FROM NATURAL LANGUAGE ====================

print("\n\n📝 1. CREATE EVENT FROM NATURAL LANGUAGE")
print("─" * 80)

natural_language_input = """
Create a tech conference called 'AI Summit 2026' on June 15th at the Convention
Center with 500 tickets: 400 general admission at $99 and 100 VIP at $299
"""

print(f"🎤 Input: {natural_language_input.strip()}")
print("\n🔧 MCP Processing:")
print("   → Parse natural language with GPT-4")
print("   → Extract: name, date, venue, capacity, pricing tiers")
print("   → Validate parameters")
print("   → Create database records")

print("\n✅ Result:")
result = {
    "success": True,
    "event_id": 42,
    "event_name": "AI Summit 2026",
    "parsed_params": {
        "name": "AI Summit 2026",
        "date": "2026-06-15",
        "venue": "Convention Center",
        "category": "technology",
        "ticket_tiers": [
            {"name": "General Admission", "price": 9900, "quantity": 400},
            {"name": "VIP", "price": 29900, "quantity": 100}
        ]
    },
    "tiers_created": 2
}
print(json.dumps(result, indent=2))

# ==================== 2. MARKET RESEARCH ====================

print("\n\n🔍 2. MARKET RESEARCH & COMPETITIVE ANALYSIS")
print("─" * 80)

research_query = "What are the top trending tech conferences in San Francisco and average pricing?"

print(f"🎤 Query: {research_query}")
print("\n🔧 MCP Actions:")
print("   → WebSearch for 'tech conferences San Francisco 2026 pricing'")
print("   → Analyze 50+ competitor events")
print("   → Extract pricing patterns")
print("   → Identify market trends")
print("   → Generate recommendations")

print("\n✅ Research Results:")
research = {
    "query": research_query,
    "insights": [
        "Tech conferences in SF average $150-300 per ticket",
        "Virtual hybrid events growing 40% YoY",
        "Best months: September, October, March",
        "Networking sessions highly valued (86% satisfaction impact)"
    ],
    "pricing_recommendations": {
        "average_market_price": "$150.00",
        "recommended_range": "$99-$199 for 500-person tech event",
        "your_position": "Competitive at $99",
        "premium_tier_sweet_spot": "$250-$350 for VIP"
    },
    "top_venues": [
        {"name": "Convention Center", "capacity": 800, "rating": 4.5, "avg_cost": "$5,000"},
        {"name": "Tech Hub SF", "capacity": 500, "rating": 4.7, "avg_cost": "$3,500"}
    ],
    "competitors": [
        {"name": "DevCon 2026", "price": "$125", "capacity": 600, "sellout_time": "3 weeks"},
        {"name": "Cloud Summit", "price": "$199", "capacity": 400, "sellout_time": "6 weeks"}
    ],
    "market_trends": [
        "Hybrid (in-person + virtual) attendance models increasing",
        "Interactive workshops command 30% premium",
        "Food quality impacts NPS by 15 points",
        "Early bird discounts drive 40% of ticket sales"
    ]
}
print(json.dumps(research, indent=2))

# ==================== 3. EVENT PERFORMANCE ANALYSIS ====================

print("\n\n📊 3. DEEP EVENT PERFORMANCE ANALYSIS")
print("─" * 80)

print("🎤 Analyzing: AI Summit 2026 (Event ID: 42)")
print("\n🔧 MCP Analytics:")
print("   → Query ticket sales data")
print("   → Calculate sales velocity")
print("   → Project final attendance")
print("   → Analyze pricing tier performance")
print("   → Find similar historical events")
print("   → Generate recommendations")

print("\n✅ Performance Analysis:")
analysis = {
    "event_name": "AI Summit 2026",
    "current_stats": {
        "tickets_sold": 234,
        "revenue": "$23,166.00",
        "capacity_used": "46.8%",
        "days_active": 12,
        "tickets_remaining": 266
    },
    "velocity_analysis": {
        "tickets_per_day": "19.5",
        "days_until_event": 45,
        "projected_final_tickets": 465,
        "projected_sellout_date": "2026-06-10",
        "sellout_likelihood": "93%"
    },
    "pricing_tier_performance": {
        "General Admission ($99)": {
            "sold": 190,
            "available": 210,
            "contribution": "81.2%",
            "performance": "Strong"
        },
        "VIP ($299)": {
            "sold": 44,
            "available": 56,
            "contribution": "18.8%",
            "performance": "Moderate"
        }
    },
    "recommendations": [
        "✅ Trending well - continue current marketing strategy",
        "💡 VIP tier underperforming - highlight exclusive perks",
        "📢 Increase LinkedIn ad spend - tech audience responds well",
        "🎯 Launch early bird extension to drive urgency"
    ],
    "similar_events_comparison": [
        {"name": "DevWeek 2025", "final_attendance": 487, "similarity": 0.89},
        {"name": "AI Conference SF 2025", "final_attendance": 512, "similarity": 0.85}
    ]
}
print(json.dumps(analysis, indent=2))

# ==================== 4. DYNAMIC PRICING OPTIMIZATION ====================

print("\n\n💰 4. AI-POWERED PRICING OPTIMIZATION")
print("─" * 80)

print("🎤 Request: Optimize pricing for AI Summit 2026")
print("\n🔧 MCP Intelligence:")
print("   → Analyze current sell-through rates")
print("   → Compare to market averages")
print("   → Calculate elasticity of demand")
print("   → Factor in days until event")
print("   → Generate tier-specific recommendations")

print("\n✅ Pricing Optimization:")
pricing_opt = {
    "event_name": "AI Summit 2026",
    "market_context": {
        "average_market_price": "$125.00",
        "your_current_average": "$135.00",
        "position": "Slightly above market",
        "analyzed_events": 50
    },
    "tier_recommendations": [
        {
            "tier": "General Admission",
            "current_price": "$99.00",
            "sold": 190,
            "available": 210,
            "sell_through_rate": "47.5%",
            "recommendation": "MAINTAIN",
            "suggested_price": "$99.00",
            "reasoning": "Moderate sell-through with 45 days remaining. Current pricing effective.",
            "expected_impact": "Continue steady sales velocity"
        },
        {
            "tier": "VIP",
            "current_price": "$299.00",
            "sold": 44,
            "available": 56,
            "sell_through_rate": "44.0%",
            "recommendation": "DECREASE",
            "suggested_price": "$249.00",
            "reasoning": "VIP tier lagging. Market analysis shows $250-280 is sweet spot for tech VIP.",
            "expected_impact": "+15-20 VIP tickets, +$4,200 revenue"
        }
    ],
    "overall_strategy": {
        "action": "Strategic VIP price reduction",
        "timing": "Implement immediately (45 days out)",
        "expected_outcomes": [
            "Improve VIP sell-through from 44% to 65%",
            "Maintain general admission momentum",
            "Net revenue impact: +$2,100",
            "Increase total attendance by 4%"
        ],
        "risk_factors": [
            "Price drop may signal desperation (mitigate with 'exclusive tier expansion' messaging)",
            "General admission may feel overpriced relative to VIP (monitor closely)"
        ]
    }
}
print(json.dumps(pricing_opt, indent=2))

# ==================== 5. MULTI-EVENT COMPARISON ====================

print("\n\n📈 5. COMPARE MULTIPLE EVENTS SIDE-BY-SIDE")
print("─" * 80)

print("🎤 Request: Compare my last 3 tech conferences")
print("\n🔧 MCP Analysis:")
print("   → Query events by category and date")
print("   → Aggregate performance metrics")
print("   → Identify success patterns")
print("   → Highlight best performers")

print("\n✅ Event Comparison:")
comparison = {
    "total_events": 3,
    "comparisons": [
        {
            "event_name": "AI Summit 2026",
            "date": "2026-06-15",
            "tickets_sold": 234,
            "revenue": "$23,166.00",
            "capacity_used": "46.8%",
            "avg_ticket_price": "$99.00"
        },
        {
            "event_name": "DevWeek 2025",
            "date": "2025-10-20",
            "tickets_sold": 487,
            "revenue": "$58,440.00",
            "capacity_used": "97.4%",
            "avg_ticket_price": "$120.00"
        },
        {
            "event_name": "Cloud Conference 2025",
            "date": "2025-03-15",
            "tickets_sold": 412,
            "revenue": "$49,440.00",
            "capacity_used": "82.4%",
            "avg_ticket_price": "$120.00"
        }
    ],
    "insights": {
        "highest_revenue": {"event": "DevWeek 2025", "amount": "$58,440.00"},
        "highest_capacity": {"event": "DevWeek 2025", "utilization": "97.4%"},
        "best_avg_price": {"event": "DevWeek 2025", "price": "$120.00"},
        "total_revenue_all_events": "$131,046.00",
        "total_tickets_all_events": 1133,
        "overall_avg_capacity": "75.5%"
    },
    "learnings": [
        "Fall events (Sept-Oct) perform 20% better than spring",
        "DevWeek's workshop-heavy format drove premium pricing",
        "Hybrid events had 15% higher satisfaction but lower per-ticket revenue",
        "LinkedIn ads ROI 3x better than Facebook for tech audience"
    ]
}
print(json.dumps(comparison, indent=2))

# ==================== 6. CROSS-SESSION MEMORY SEARCH ====================

print("\n\n🧠 6. SEARCH CROSS-SESSION MEMORY (MCP)")
print("─" * 80)

memory_query = "How did we price tech conferences in the past and what worked best?"

print(f"🎤 Query: {memory_query}")
print("\n🔧 MCP Memory Search:")
print("   → search_memory(query='tech conference pricing strategy')")
print("   → timeline(query='successful tech events')")
print("   → Filter by relevance score > 0.80")
print("   → Aggregate learnings across sessions")

print("\n✅ Memory Search Results:")
memory = {
    "query": memory_query,
    "sessions_searched": 47,
    "relevant_sessions": 8,
    "results": [
        {
            "session_date": "2025-10-15",
            "context": "DevWeek 2025 pricing strategy",
            "relevance": 0.95,
            "key_insight": "Two-tier pricing ($99/$249) with early bird ($79) drove 60% pre-sales",
            "outcome": "Sold out 2 weeks before event, $58k revenue"
        },
        {
            "session_date": "2025-03-10",
            "context": "Cloud Conference pricing analysis",
            "relevance": 0.89,
            "key_insight": "Single $120 price point simplified messaging, 82% capacity",
            "outcome": "Strong performance but left money on table (no VIP tier)"
        },
        {
            "session_date": "2024-11-20",
            "context": "AI Conference post-mortem",
            "relevance": 0.87,
            "key_insight": "$150 general was too high, $99 sweet spot for tech audience",
            "outcome": "Only reached 65% capacity, had to discount last minute"
        }
    ],
    "aggregated_learnings": [
        "✅ $99 is sweet spot for general admission tech conferences",
        "✅ VIP tier at $249-299 captures 15-20% of audience",
        "✅ Early bird discount (20% off) drives urgency and pre-sales",
        "✅ Two-tier structure works better than single price",
        "❌ Avoid pricing above $150 for general admission",
        "❌ Three+ tiers creates decision paralysis"
    ],
    "recommendations": {
        "optimal_structure": "Two-tier: $99 general + $249 VIP",
        "early_bird_strategy": "$79 early bird (first 100 tickets)",
        "expected_performance": "85-95% capacity, $48-55k revenue for 500-person event",
        "confidence": "High (based on 3 successful implementations)"
    }
}
print(json.dumps(memory, indent=2))

# ==================== 7. VOICE COMMAND INTEGRATION ====================

print("\n\n🎤 7. NATURAL LANGUAGE EVENT QUERIES")
print("─" * 80)

voice_examples = [
    {
        "input": "Create an AI conference on June 15th with 500 tickets at $99",
        "mcp_action": "parse_natural_language() → create_event()",
        "result": "✅ Created 'AI Conference' with 500 tickets @ $99"
    },
    {
        "input": "How is my AI Summit performing compared to last year's DevWeek?",
        "mcp_action": "analyze_event(42) + compare_events([42, 38])",
        "result": "📊 AI Summit: 47% capacity | DevWeek: 97% capacity\n    Your event trending 20% slower - consider price adjustment"
    },
    {
        "input": "What's the best price for VIP tickets at tech conferences?",
        "mcp_action": "search_memory('VIP pricing') + market_research('tech VIP pricing')",
        "result": "💰 Optimal VIP: $249-299 based on 8 past events\n    Market average: $275 | Your positioning: Competitive"
    },
    {
        "input": "Should I increase or decrease prices for my event?",
        "mcp_action": "optimize_pricing(event_id=42)",
        "result": "💡 RECOMMENDATION: Decrease VIP from $299 → $249\n    Expected impact: +15 VIP tickets, +$4,200 revenue"
    },
    {
        "input": "Find similar events to mine and show their pricing",
        "mcp_action": "find_similar_events() + market_research()",
        "result": "🔍 Found 3 similar: DevCon ($125), Cloud Summit ($199), AI Expo ($89)\n    Your price ($99) competitive, slightly below market"
    }
]

print("Voice Command Examples:")
for i, example in enumerate(voice_examples, 1):
    print(f"\n[Example {i}]")
    print(f"🎤 \"{example['input']}\"")
    print(f"   🔧 MCP: {example['mcp_action']}")
    print(f"   ✅ {example['result']}")

# ==================== SUMMARY ====================

print("\n\n" + "=" * 80)
print("🏆 MCP EVENT CAPABILITIES SUMMARY")
print("=" * 80)

capabilities = {
    "Event Creation": {
        "natural_language": "✅ Parse descriptions → Create events",
        "api": "POST /api/mcp/events/create-from-text",
        "example": "Create tech conference on June 15th..."
    },
    "Market Research": {
        "competitive_analysis": "✅ Find competitors, analyze pricing",
        "api": "POST /api/mcp/events/research",
        "example": "What are top tech conferences in SF?"
    },
    "Performance Analytics": {
        "deep_analysis": "✅ Sales velocity, projections, recommendations",
        "api": "GET /api/mcp/events/analyze/{event_id}",
        "example": "How is my event performing?"
    },
    "Pricing Optimization": {
        "ai_powered": "✅ Dynamic pricing based on demand + market",
        "api": "POST /api/mcp/events/optimize-pricing",
        "example": "Should I increase prices?"
    },
    "Event Comparison": {
        "multi_event": "✅ Side-by-side performance comparison",
        "api": "POST /api/mcp/events/compare-events",
        "example": "Compare my last 3 events"
    },
    "Memory Search": {
        "cross_session": "✅ Recall past events, learnings, strategies",
        "api": "GET /api/mcp/events/memory/search",
        "example": "What pricing worked best historically?"
    },
    "Voice Integration": {
        "natural_language": "✅ All features accessible via voice commands",
        "api": "POST /api/voice/command",
        "example": "How many tickets sold today?"
    }
}

print("\n📋 Available Capabilities:")
for category, details in capabilities.items():
    print(f"\n{category}:")
    for key, value in details.items():
        print(f"  {key}: {value}")

print("\n\n" + "=" * 80)
print("🚀 READY TO USE")
print("=" * 80)
print("\n1. Start server: uvicorn app.main:app --reload")
print("2. Get JWT token: POST /api/auth/login")
print("3. Try MCP endpoints:")
print("   - Create event: POST /api/mcp/events/create-from-text")
print("   - Research market: POST /api/mcp/events/research")
print("   - Analyze performance: GET /api/mcp/events/analyze/42")
print("   - Optimize pricing: POST /api/mcp/events/optimize-pricing")
print("   - Compare events: POST /api/mcp/events/compare-events")
print("   - Search memory: GET /api/mcp/events/memory/search")
print("\n4. Or use voice: POST /api/voice/command?text=YOUR_QUESTION")
print("=" * 80 + "\n")
