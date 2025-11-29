# Contact Summary Example

## Sample Interaction Summary Response

Here's what a contact summary with recommendations looks like:

### Example Summary

**Contact:** Sarah Johnson (sarah.johnson@techcorp.com)  
**Company:** TechCorp Solutions  
**Tags:** VIP, Lead

**Summary:**
Sarah has been an engaged contact over the past 3 months, with 12 total interactions. Her communication style is professional yet friendly, typically responding within 24 hours. The primary topics of discussion have centered around enterprise pricing, integration capabilities, and custom workflow requirements. 

She's shown strong buying signals, including asking detailed technical questions, requesting demos, and mentioning budget approval timelines. The relationship status appears to be a high-value lead transitioning toward a potential enterprise customer. There's a notable pattern of urgency in her recent messages, suggesting she may be evaluating multiple vendors.

Overall sentiment is positive, with Sarah expressing appreciation for quick responses and detailed information. However, there's one pending task from 5 days ago that hasn't been addressed, which could impact the sales cycle.

**Recommendations:**
1. **Prioritize the pending task immediately** - The 5-day-old pending task may be blocking her decision-making process. A quick resolution could accelerate the sales cycle.
2. **Schedule a personalized demo** - Given her technical questions and enterprise focus, a custom demo showcasing integration capabilities would be highly valuable.
3. **Send a follow-up with pricing tier comparison** - She's shown interest in enterprise features; providing a clear breakdown of pricing tiers with ROI calculations could help move her to the next stage.

---

### Technical Implementation

The summary is generated using the LLM (Ollama phi3 or OpenAI) with:
- **Input:** Contact details, recent message history (last 10 messages), task statistics
- **Output:** JSON with `summary` (2-3 paragraphs) and `recommendations` (2-3 actionable items)
- **Display:** Formatted in the contact detail page with numbered recommendations

### Features

✅ **Insightful Analysis:** Covers communication style, topics, relationship status, patterns, and sentiment  
✅ **Actionable Recommendations:** 2-3 specific, data-driven recommendations  
✅ **Context-Aware:** Based on actual message history and task data  
✅ **Natural Language:** Written in a conversational, human-like tone


