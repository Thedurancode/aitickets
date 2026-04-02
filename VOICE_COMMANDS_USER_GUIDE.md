## 🎤 Voice Commands User Guide

Welcome to AI-Tickets Voice Control! Manage your event platform hands-free using natural language commands.

---

## Getting Started

### Browser Requirements

Voice commands work best in:
- ✅ Google Chrome (recommended)
- ✅ Microsoft Edge
- ✅ Safari (iOS/macOS)
- ⚠️ Firefox (limited support)

### Microphone Setup

1. **Grant Permission**: Click "Allow" when your browser requests microphone access
2. **Check Settings**: Ensure your microphone is working in browser settings
3. **Reduce Noise**: Use in a quiet environment for best recognition

---

## How to Use Voice Commands

### Basic Usage

1. **Click the microphone button** or say "Hey AI-Tickets" (if wake word enabled)
2. **Speak clearly** - say your command naturally
3. **Listen to response** - AI-Tickets will speak back to you
4. **View transcript** - see what you said and the response

### Tips for Best Results

✅ **DO:**
- Speak clearly and at normal pace
- Use natural language ("Show me today's revenue")
- Wait for the listening indicator before speaking
- Speak complete sentences

❌ **DON'T:**
- Rush or speak too fast
- Use technical jargon
- Interrupt while AI-Tickets is speaking
- Expect exact keyword matching

---

## Voice Command Reference

### 🔔 Alert Commands

#### Show Alerts
**Say:** "Show alerts" | "What alerts do I have?" | "Any alerts?"

**Response:** List of unread alerts with severity and details

**Example:**
```
You: "Show alerts"
AI: "You have 3 unread alerts. Critical Alert 5: Refund spike detected.
     High priority Alert 6: Low inventory warning. Alert 7: Sales milestone reached."
```

---

#### Check Critical Alerts
**Say:** "Any critical alerts?" | "Show urgent alerts" | "Do I have any urgent alerts?"

**Response:** Only critical and high-priority unread alerts

**Example:**
```
You: "Any critical alerts?"
AI: "You have 2 urgent alerts: Critical alert: Refund spike detected.
     High alert: Low inventory warning."
```

---

#### Dismiss Alert
**Say:** "Dismiss alert 5" | "Mark alert 5 as read" | "Clear alert 5"

**Response:** Confirmation that alert was dismissed

**Example:**
```
You: "Dismiss alert 5"
AI: "Alert 5 dismissed."
```

---

#### Clear All Alerts
**Say:** "Clear all alerts" | "Dismiss all alerts" | "Mark all as read"

**Response:** Confirmation with count of cleared alerts

**Example:**
```
You: "Clear all alerts"
AI: "Cleared 7 alerts."
```

---

### 📊 Dashboard Commands

#### Status Check
**Say:** "Status" | "How are we doing?" | "Give me an update" | "What's the status?"

**Response:** Today's key metrics plus critical alerts

**Example:**
```
You: "Status"
AI: "Today's status: $3,245.50 in revenue from 42 tickets.
     No urgent alerts. Everything looks good!"
```

---

#### Today's Revenue
**Say:** "What's today's revenue?" | "How much did we make today?" | "Revenue today"

**Response:** Today's total revenue and ticket count

**Example:**
```
You: "What's today's revenue?"
AI: "Today's revenue is $3,245.50 from 42 tickets."
```

---

#### Top Events
**Say:** "Top events" | "Best events" | "Show me top events" | "Which events are performing best?"

**Response:** Top 5 events by revenue (last 30 days)

**Example:**
```
You: "Top events"
AI: "Your top 5 events: Number 1: Summer Music Festival with $12,450.
     Number 2: Comedy Night with $8,900. Number 3: Wine Tasting with $6,200."
```

---

### 📧 Campaign Commands

#### Show Campaigns
**Say:** "Show campaigns" | "What campaigns are running?" | "List campaigns"

**Response:** Recent campaigns with performance summary

**Example:**
```
You: "Show campaigns"
AI: "You have 5 recent campaigns. Summer Sale Email: $2,450 revenue, 18 conversions.
     Back to School SMS: $1,890 revenue, 12 conversions."
```

---

#### Campaign Performance
**Say:** "How did campaign 3 do?" | "Campaign 3 performance" | "Stats for campaign 3"

**Response:** Detailed performance stats for specific campaign

**Example:**
```
You: "How did campaign 3 do?"
AI: "Campaign 3: Sent to 1,000 people. 420 opened it, that's 42 percent.
     85 clicked, 18 purchased. Total revenue: $2,450."
```

---

#### Top Campaigns
**Say:** "Top campaigns" | "Best performing campaigns" | "Show best campaigns"

**Response:** Top 5 campaigns by revenue

**Example:**
```
You: "Top campaigns"
AI: "Your top 5 campaigns: Number 1: Summer Sale Email with $2,450 in revenue.
     Number 2: Back to School SMS with $1,890. Number 3: Flash Sale with $1,200."
```

---

## Advanced Features

### Continuous Listening

**Enable:** Check "Continuous listening" in voice settings

**Behavior:**
- Microphone stays active after each command
- No need to click button repeatedly
- Automatically listens for next command
- Great for hands-free operation

**Disable:** Uncheck the option to return to push-to-talk mode

---

### Voice Settings

#### Speech Rate
- **Range:** 0.5x to 2.0x (default: 1.0x)
- **Slow (0.5x):** Clear pronunciation, easier to understand
- **Normal (1.0x):** Natural speaking pace
- **Fast (2.0x):** Quick responses, harder to follow

**Adjust:** Use the "Speech Rate" slider in settings

---

#### Speech Pitch
- **Range:** 0.5 to 2.0 (default: 1.0)
- **Low (0.5):** Deeper voice
- **Normal (1.0):** Natural pitch
- **High (2.0):** Higher pitched voice

**Adjust:** Use the "Speech Pitch" slider in settings

---

### Interrupting Responses

**Press "Stop Speaking"** button or click microphone while AI is speaking

**When to use:**
- Response is too long
- You already understand
- Need to issue urgent command
- Want to ask follow-up immediately

---

## Troubleshooting

### "Voice commands not supported"

**Fix:**
1. Use Chrome, Edge, or Safari
2. Update browser to latest version
3. Enable JavaScript
4. Check browser compatibility

---

### "Microphone permission denied"

**Fix:**
1. Click padlock icon in address bar
2. Allow microphone access
3. Refresh page
4. Click microphone button again

---

### Commands not recognized

**Fix:**
1. Speak more clearly
2. Reduce background noise
3. Check microphone is working (test in OS settings)
4. Try rephrasing command naturally
5. Use command examples above

---

### AI-Tickets not responding

**Fix:**
1. Check internet connection
2. Verify MCP server is running
3. Look for error messages
4. Try refreshing page
5. Check browser console for errors

---

### Response is cut off or garbled

**Fix:**
1. Adjust speech rate to slower (0.8x or 0.7x)
2. Ensure good internet connection
3. Close other audio-playing tabs
4. Check system volume isn't muted
5. Try different voice in browser settings

---

## Keyboard Shortcuts

- **Space:** Toggle listening (when microphone button focused)
- **Esc:** Stop speaking
- **Enter:** Replay last response

---

## Privacy & Security

### What's Recorded
- Voice commands are processed by your browser's speech recognition
- Commands sent to AI-Tickets MCP server for execution
- No audio is stored on servers
- Transcripts kept locally in browser session only

### Data Handling
- Voice data doesn't leave your browser
- Only text transcripts sent to server
- No permanent logging of voice commands
- Clear history anytime with "Clear History" button

### Permissions
- Microphone access: Required for voice recognition
- Local storage: Saves voice preferences only
- No account linking to voice data
- No third-party voice data sharing

---

## Best Practices

### For Quick Checks
1. **Use "Status"** - fastest way to get overview
2. **Ask "Any critical alerts?"** - check urgent items only
3. **Say "Top events"** - see what's working best

### For Detailed Review
1. **Use Web UI** for extensive data review
2. **Voice for quick queries** during meetings
3. **Export data** for deep analysis

### During Events
1. **Enable continuous listening** for hands-free
2. **Check status regularly** during event day
3. **Monitor alerts** for issues
4. **Quick revenue checks** between tasks

### Multitasking
1. **Voice while working** on other tasks
2. **Continuous mode** for ongoing monitoring
3. **Lower speech rate** if distracted
4. **Use during commute** (hands-free safely!)

---

## Example Workflows

### Morning Check-In
```
You: "Status"
AI: [Gives today's revenue, tickets, alerts]

You: "Any critical alerts?"
AI: [Shows urgent issues or "All clear"]

You: "Top events"
AI: [Lists best performing events]
```

**Time: 30 seconds**

---

### Campaign Review
```
You: "Show campaigns"
AI: [Lists recent campaigns]

You: "Top campaigns"
AI: [Shows 5 best by revenue]

You: "How did campaign 3 do?"
AI: [Detailed stats for campaign 3]
```

**Time: 1 minute**

---

### Alert Management
```
You: "Show alerts"
AI: [Lists all unread alerts]

You: "Dismiss alert 5"
AI: [Confirms dismissal]

You: "Dismiss alert 6"
AI: [Confirms dismissal]

You: "Clear all alerts"
AI: [Clears remaining alerts]
```

**Time: 45 seconds**

---

## Command Variations

Voice recognition understands natural variations:

### Status Commands
- "Status" = "How are we doing?" = "Give me an update" = "What's up?"

### Alert Commands
- "Show alerts" = "What alerts do I have?" = "Any alerts?" = "Check alerts"

### Revenue Commands
- "Today's revenue" = "How much did we make today?" = "Revenue today" = "Sales today"

### Campaign Commands
- "Top campaigns" = "Best campaigns" = "Show best campaigns" = "Which campaigns performed well?"

**Tip:** Speak naturally - the system understands context!

---

## Getting Help

### In-App Help
- Click "?" icon for quick command reference
- Hover over buttons for tooltips
- Check conversation history for examples

### Support
- Documentation: `docs.ai-tickets.com/voice`
- Issues: GitHub Issues or support email
- Community: Discord server for tips

---

## What's Next?

### Coming Soon
- Multi-language support (Spanish, French, German)
- Custom wake words ("Hey AI-Tickets")
- Voice macros (save command sequences)
- Proactive notifications ("You have a new alert")
- Voice-controlled workflows

### Request Features
Found a command you wish existed? Let us know!
- GitHub: Open feature request
- Email: voice-feedback@ai-tickets.com
- Discord: #voice-features channel

---

**Happy voice commanding! 🎤✨**

Manage your events faster and easier with AI-Tickets Voice Control.
