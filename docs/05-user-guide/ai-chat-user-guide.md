# AI Chat User Guide

**Version:** 1.0.0
**Last Updated:** 2026-03-10
**Audience:** End Users

---

## Overview

The Backcast  AI Chat is an intelligent assistant that helps you manage projects, work breakdown structures (WBEs), cost elements, change orders, and perform earned value analysis using natural language. Simply ask questions in plain English, and the AI will use the appropriate tools to retrieve and analyze your data.

### What Can AI Chat Do?

- **Project Management**: List, search, and get details about projects
- **WBE Management**: Query work breakdown structures and their hierarchies
- **Cost Analysis**: Access cost elements and perform variance analysis
- **Change Orders**: Generate drafts and manage change order workflows
- **EVM Analysis**: Calculate earned value metrics, performance indices, and forecasts
- **Natural Conversations**: Maintain context across multiple questions in a session

---

## Getting Started

### Accessing AI Chat

1. Navigate to the AI Chat section in the Backcast  application
2. Select or create an AI assistant configuration
3. Start a new conversation or continue an existing one
4. Type your question and press Enter or click Send

### First Time Setup

Before using AI Chat, ensure:
- You have the appropriate permissions for the data you want to access
- An AI assistant has been configured with the tools you need
- Your user account has been granted access to the AI Chat feature

---

## Common Use Cases

### 1. Project Information

**List all projects:**
```
Show me all projects
```
```
What projects do I have access to?
```

**Filter projects by status:**
```
Show me active projects
```
```
List all completed projects
```

**Search for a specific project:**
```
Find the automation line project
```
```
Search for projects containing "conveyor"
```

**Get project details:**
```
Tell me about project PRJ-001
```
```
What's the budget for the warehouse automation project?
```

**Example Conversation:**
```
You: Show me all active projects
AI: I found 5 active projects:
    - PRJ-001: Warehouse Automation (Status: Active, Budget: $500,000)
    - PRJ-002: Conveyor Line Upgrade (Status: Active, Budget: $250,000)
    ...

You: What's the status of PRJ-001?
AI: PRJ-001 (Warehouse Automation) is currently Active.
    Start Date: 2026-01-15
    Planned End: 2026-06-30
    Progress: 45% complete
```

---

### 2. Work Breakdown Structure (WBE)

**List WBEs for a project:**
```
Show me the work breakdown for PRJ-001
```
```
What WBEs are in the warehouse automation project?
```

**Get WBE details:**
```
Tell me about WBE WBE-001
```
```
What's the budget for the electrical installation WBE?
```

**Navigate WBE hierarchy:**
```
Show me the top-level WBEs for PRJ-001
```
```
What are the child WBEs under mechanical installation?
```

**Example Conversation:**
```
You: Show me the WBE structure for PRJ-001
AI: Here's the WBE hierarchy for PRJ-001 (Warehouse Automation):

    1. WBE-001: Site Preparation ($50,000)
       ├── WBE-002: Grading & Leveling ($20,000)
       └── WBE-003: Foundation Work ($30,000)

    2. WBE-004: Structural Steel ($150,000)
       ├── WBE-005: Steel Columns ($80,000)
       └── WBE-006: Steel Beams ($70,000)
    ...

You: What's the budget for WBE-005?
AI: WBE-005 (Steel Columns) has a budget of $80,000.
    Current actual cost: $75,000
    Variance: -$5,000 (under budget)
```

---

### 3. Cost Elements

**List cost elements:**
```
Show me cost elements for PRJ-001
```
```
What cost categories are in the conveyor project?
```

**Filter cost elements:**
```
Show me labor costs for PRJ-001
```
```
What material costs are in WBE-005?
```

**Cost analysis:**
```
What's the total actual cost for PRJ-001?
```
```
Compare budget vs actual for WBE-004
```

**Example Conversation:**
```
You: What are the labor costs for PRJ-001?
AI: Here are the labor costs for PRJ-001:

    WBE-005 (Steel Columns):
    - Electricians: $40,000 (budget: $45,000)
    - Welders: $25,000 (budget: $25,000)
    - Laborers: $10,000 (budget: $8,000)

    Total Labor: $75,000 / $78,000 budget
    Variance: -$3,000 (under budget)
```

---

### 4. Change Orders

**Generate a change order draft:**
```
Create a change order for additional conveyor length
```
```
Draft a change order to add safety equipment
```

**Check change order status:**
```
What's the status of change order CO-001?
```
```
Show me pending change orders
```

**Change order workflow:**
```
Submit CO-001 for approval
```
```
Approve change order CO-002
```

**Example Conversation:**
```
You: I need to add 50 meters of conveyor to PRJ-001
AI: I can help create a change order for that. Let me gather some details:

    Current conveyor length: 200m
    Additional length requested: 50m
    Unit cost: $500/meter
    Estimated impact: $25,000

    Would you like me to create a change order draft with these details?

You: Yes, create it
AI: Change Order CO-003 has been created:
    - Project: PRJ-001 (Warehouse Automation)
    - Description: Add 50m conveyor extension
    - Cost Impact: +$25,000
    - Status: Draft

    Would you like me to submit it for approval?
```

---

### 5. Earned Value Management (EVM)

**Calculate EVM metrics:**
```
What's the earned value for PRJ-001?
```
```
Show me EVM metrics for the conveyor project
```

**Performance analysis:**
```
What's the CPI for PRJ-001?
```
```
Is the project ahead or behind schedule?
```

**Forecasting:**
```
What's the forecasted final cost for PRJ-001?
```
```
When will PRJ-001 complete based on current performance?
```

**Variance analysis:**
```
What's the cost variance for WBE-005?
```
```
Why is PRJ-001 over budget?
```

**Example Conversation:**
```
You: How is PRJ-001 performing?
AI: Here's the EVM performance summary for PRJ-001:

    **Overall Metrics:**
    - Planned Value (PV): $225,000
    - Earned Value (EV): $202,500
    - Actual Cost (AC): $215,000

    **Performance Indices:**
    - Schedule Performance Index (SPI): 0.90 (behind schedule)
    - Cost Performance Index (CPI): 0.94 (over budget)

    **Variances:**
    - Schedule Variance (SV): -$22,500 (2 weeks behind)
    - Cost Variance (CV): -$12,500 (over budget)

    **Forecast:**
    - Estimate at Completion (EAC): $531,915
    - Estimate to Complete (ETC): $316,915
    - Variance at Completion (VAC): -$31,915

    The project is both behind schedule and over budget. Would you like me to analyze specific WBEs causing this?
```

---

## Tips for Better Results

### Be Specific

Instead of: "Show me projects"
Try: "Show me active projects with budget over $100,000"

### Provide Context

Instead of: "What's the status?"
Try: "What's the status of PRJ-001's steel installation?"

### Use Project Codes

Refer to projects by their codes (PRJ-001, PRJ-002) for more accurate results

### Ask Follow-up Questions

The AI maintains conversation context, so you can ask natural follow-up questions:

```
You: Show me projects over budget
AI: [Lists projects]

You: What about PRJ-003?
AI: [Provides details for PRJ-003 specifically]
```

### Use Natural Language

You don't need to use technical terms. Ask questions the way you would to a colleague:

- "Are any projects running late?"
- "Which WBE is costing the most?"
- "What's causing the cost overrun?"

---

## Limitations

### What AI Chat Cannot Do

- **Modify Data**: AI Chat is read-only. It cannot create, update, or delete projects, WBEs, or cost elements
- **Access Unauthorized Data**: You can only see data you have permissions to access
- **Perform Calculations Beyond Tools**: Calculations are limited to the available EVM and forecasting tools
- **Real-time Data**: Data is based on the last database update, not real-time

### Known Limitations

- Complex multi-project analysis may require breaking into smaller questions
- Very large projects may take longer to process
- Historical data prior to system migration may not be available

---

## Troubleshooting

### "I don't have access to this information"

This means your account lacks the required permissions. Contact your administrator to request access.

### "Tool not found"

This means the requested tool is not configured for your AI assistant. Check with your administrator about available tools.

### "No results found"

- Check your spelling of project/WBE codes
- Verify the item exists in the system
- Try using broader search terms

### Slow Response

- Large projects or complex queries may take longer
- Try breaking complex questions into smaller parts
- Check your internet connection

---

## Best Practices

### For Project Managers

1. **Start with Overview**: Begin with "Show me project summary" to get context
2. **Drill Down**: Follow up with specific WBE or cost element questions
3. **Check Status Regularly**: Use "What's the status of PRJ-XXX?" for quick updates
4. **Monitor EVM**: Ask "How is PRJ-XXX performing?" weekly

### For Cost Engineers

1. **Use Variance Questions**: "What's the cost variance for...?"
2. **Compare Budget vs Actual**: "Compare budget and actual for WBE-XXX"
3. **Analyze Trends**: "Show me cost trends for PRJ-XXX"

### For Change Managers

1. **Generate Drafts**: "Create a change order for..." to start the workflow
2. **Check Status**: "What's the status of CO-XXX?" to track progress
3. **Review Impact**: "What's the cost impact of CO-XXX?" before approving

---

## Support

If you encounter issues or have questions:

1. Check the troubleshooting section above
2. Review the [AI Architecture Documentation](../02-architecture/ai/)
3. Contact your system administrator
4. Submit a support ticket with:
   - Your question or the exact message you sent
   - The AI's response (if any)
   - Screenshots if applicable

---

**Quick Reference**

| Task | Example Query |
|------|---------------|
| List projects | "Show me all projects" |
| Get project details | "Tell me about PRJ-001" |
| Show WBEs | "Show WBEs for PRJ-001" |
| EVM metrics | "How is PRJ-001 performing?" |
| Create change order | "Create a change order for..." |
| Check status | "What's the status of PRJ-001?" |
| Cost analysis | "What's the cost variance for WBE-005?" |

---

**Version History**

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-10 | Initial release |
