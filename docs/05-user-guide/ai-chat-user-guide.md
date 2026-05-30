# AI Chat User Guide

**Version:** 1.1.0
**Last Updated:** 2026-05-30
**Audience:** End Users

---

## Overview

The Backcast AI Chat is an intelligent assistant that helps you manage projects, WBS Elements, cost elements, change orders, and perform earned value analysis using natural language. Simply ask questions in plain English, and the AI will use the appropriate tools to retrieve and analyze your data.

### What Can AI Chat Do?

- **Project Management**: List, search, and get details about projects
- **WBS Element Management**: Query work breakdown structures and their hierarchies
- **Cost Analysis**: Access cost elements and perform variance analysis
- **Change Orders**: Generate drafts and manage change order workflows
- **EVM Analysis**: Calculate earned value metrics, performance indices, and forecasts
- **Natural Conversations**: Maintain context across multiple questions in a session

---

## Getting Started

### Accessing AI Chat

1. Navigate to the AI Chat section in the Backcast application
2. Select or create an AI assistant configuration
3. Start a new conversation or continue an existing one
4. Type your question and press Enter or click Send

### Real-Time Streaming

AI Chat responses are streamed in real time via WebSocket, so you see the assistant's output as it is generated rather than waiting for the full response.

### Session Context

When starting a conversation, you can select a project and branch context. This allows the AI to focus on the relevant data for that project and branch (including change order branches), providing more accurate and scoped responses.

### Multimodal Input

You can attach images and files to your messages using drag-and-drop or the upload button. The AI supports:

- **Image uploads**: Attach screenshots, photos, or diagrams for the AI to analyze (e.g., a Gantt chart screenshot for discussion)
- **File uploads**: Attach documents for context or analysis

### First Time Setup

Before using AI Chat, ensure:
- You have the appropriate RBAC permissions for the data you want to access. AI operations are governed by your assigned role, and different assistant configurations may have different permission levels and tool access.
- An AI assistant has been configured with the tools you need
- Your user account has been granted access to the AI Chat feature

---

## Entity Hierarchy

Understanding the entity hierarchy in Backcast is important for asking effective questions:

```
Project
  └── WBS Element (Work Breakdown Structure)
        └── Control Account (WBS Element x Organizational Unit intersection)
              └── Work Package (PMI budget holder where EVM is calculated)
                    ├── Cost Element (allocated budget line item, typed by Cost Element Type)
                    ├── Schedule Baseline (defines the planned value curve)
                    └── Forecast (EAC with approval workflow)
```

Key entities the AI can work with:

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| **Project** | Top-level project container | code, name, contract_value, start_date, end_date, status |
| **WBS Element** | Work breakdown hierarchy node | code (e.g., 1.2.3), name, revenue_allocation, level |
| **Control Account** | Intersection of WBS Element and Organizational Unit | name, code, wbs_element_id, organizational_unit_id |
| **Work Package** | Budget holder under a Control Account | name, code, budget_amount, status |
| **Cost Element** | Budget line item within a Work Package | amount, cost_element_type_id |
| **Cost Element Type** | Categorization for cost elements (e.g., Labor, Materials) | code, name |
| **Cost Registration** | Actual cost tracked against a Cost Element | amount, registration_date, invoice_number |
| **Change Order** | Formal change request with impact analysis | code, title, impact_level, impact_score, status |
| **Forecast** | Estimate at Complete with approval | eac_amount, basis_of_estimate, approved_date |
| **Schedule Baseline** | Planned value curve definition | name, start_date, end_date, progression_type |
| **Progress Entry** | Progress percentage for a Work Package | progress_percentage, notes |

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
What's the contract value for the warehouse automation project?
```

**Example Conversation:**
```
You: Show me all active projects
AI: I found 5 active projects:
    - PRJ-001: Warehouse Automation (Status: Active, Contract Value: $500,000)
    - PRJ-002: Conveyor Line Upgrade (Status: Active, Contract Value: $250,000)
    ...

You: What's the status of PRJ-001?
AI: PRJ-001 (Warehouse Automation) is currently Active.
    Start Date: 2026-01-15
    End Date: 2026-06-30
```

---

### 2. Work Breakdown Structure (WBS Elements)

**List WBS Elements for a project:**
```
Show me the work breakdown for PRJ-001
```
```
What WBS Elements are in the warehouse automation project?
```

**Get WBS Element details:**
```
Tell me about WBS Element 1.2
```
```
What's the revenue allocation for the electrical installation WBS Element?
```

**Navigate WBS Element hierarchy:**
```
Show me the top-level WBS Elements for PRJ-001
```
```
What are the child WBS Elements under mechanical installation?
```

**Example Conversation:**
```
You: Show me the WBS structure for PRJ-001
AI: Here's the WBS hierarchy for PRJ-001 (Warehouse Automation):

    1. 1.0: Site Preparation (Revenue Allocation: $50,000)
       ├── 1.1: Grading & Leveling (Revenue Allocation: $20,000)
       └── 1.2: Foundation Work (Revenue Allocation: $30,000)

    2. 2.0: Structural Steel (Revenue Allocation: $150,000)
       ├── 2.1: Steel Columns (Revenue Allocation: $80,000)
       └── 2.2: Steel Beams (Revenue Allocation: $70,000)
    ...

You: What's the revenue allocation for WBS Element 2.1?
AI: WBS Element 2.1 (Steel Columns) has a revenue allocation of $80,000.
    This WBS Element is at level 2 and belongs to 2.0 (Structural Steel).
```

---

### 3. Control Accounts and Work Packages

**List control accounts:**
```
Show me control accounts for PRJ-001
```
```
What control accounts exist for the conveyor project?
```

**Work package details:**
```
Show me work packages for control account CA-001
```
```
What's the budget amount for work package WP-Conveyor-Install?
```

**Example Conversation:**
```
You: Show me work packages for PRJ-001
AI: Here are the work packages for PRJ-001 (Warehouse Automation):

    Control Account: CA-001 (Site Work / Engineering Dept)
    ├── WP-001: Site Grading (Budget: $20,000, Status: Open)
    └── WP-002: Foundation Pour (Budget: $30,000, Status: Open)

    Control Account: CA-002 (Structural / Fabrication Dept)
    ├── WP-003: Column Erection (Budget: $80,000, Status: In Progress)
    └── WP-004: Beam Installation (Budget: $70,000, Status: Open)
```

---

### 4. Cost Elements and Cost Registrations

**List cost elements:**
```
Show me cost elements for work package WP-001
```
```
What cost element types are in the conveyor project?
```

**Filter cost elements by type:**
```
Show me cost elements of type Labor for WP-003
```
```
What material cost elements are in work package WP-004?
```

**Cost analysis:**
```
What's the total actual cost (cost registrations) for PRJ-001?
```
```
Compare budget amount vs cost registrations for work package WP-003
```

**Example Conversation:**
```
You: What are the labor cost elements for WP-003?
AI: Here are the cost elements of type Labor for WP-003 (Column Erection):

    - Electricians: $45,000 (allocated amount)
    - Welders: $25,000 (allocated amount)
    - Laborers: $8,000 (allocated amount)

    Total Allocated (Labor): $78,000
    Total Cost Registrations against these: $75,000

    Note: Actual costs are tracked via Cost Registrations linked to each Cost Element.
```

---

### 5. Change Orders

**Generate a change order draft:**
```
Create a change order for additional conveyor length
```
```
Draft a change order to add safety equipment
```

**Check change order status:**
```
What's the status of change order CO-2026-001?
```
```
Show me pending change orders
```

**Change order workflow:**
```
Submit CO-2026-001 for approval
```
```
Approve change order CO-2026-002
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
AI: Change Order CO-2026-003 has been created:
    - Project: PRJ-001 (Warehouse Automation)
    - Title: Add 50m conveyor extension
    - Impact Level: MEDIUM
    - Impact Score: 3.50
    - Status: Draft

    Would you like me to submit it for approval?
```

---

### 6. Earned Value Management (EVM)

EVM metrics (PV, EV, AC, SPI, CPI, etc.) are computed dynamically by the EVM service, not stored as project fields. You can request them for any entity level: Project, WBS Element, Control Account, Work Package, or Cost Element.

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
What's the cost variance for WBS Element 2.1?
```
```
Why is PRJ-001 over budget?
```

**Example Conversation:**
```
You: How is PRJ-001 performing?
AI: Here are the EVM metrics calculated for PRJ-001 (Warehouse Automation):

    **Overall Metrics (computed by EVM service):**
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

    The project is both behind schedule and over budget. Would you like me to analyze specific WBS Elements causing this?
```

---

## Tips for Better Results

### Be Specific

Instead of: "Show me projects"
Try: "Show me active projects with contract value over $100,000"

### Provide Context

Instead of: "What's the status?"
Try: "What's the status of PRJ-001's steel installation?"

### Use Entity Codes

Refer to projects, WBS Elements, and work packages by their codes (e.g., PRJ-001, WBS code 1.2.3, CO-2026-001) for more accurate results.

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
- "Which WBS Element has the largest revenue allocation?"
- "What's causing the cost overrun?"

---

## Approval Workflow for AI Actions

When the AI assistant needs to execute a tool that modifies data (such as creating a change order or updating a cost element), the action may require your approval depending on the execution mode:

- **Standard mode**: The AI will request your approval before executing high-risk operations. You will see the proposed action and can approve or reject it.
- **Expert mode**: The AI executes actions directly without requiring approval for each step.

The approval workflow uses the `/approve` endpoint. When an action is pending approval, you will be prompted in the chat interface to review and confirm.

---

## Limitations

### What AI Chat Cannot Do

- **Modify Data**: In Standard mode, AI Chat can create and update data with approval for high-risk operations. Critical operations like deletion require Expert mode.
- **Access Unauthorized Data**: You can only see data you have RBAC permissions to access. The AI tools respect your assigned role's permission boundaries.
- **Perform Calculations Beyond Tools**: Calculations are limited to the available EVM and forecasting tools
- **Real-time Data**: Data is based on the last database update, not real-time

### Known Limitations

- Complex multi-project analysis may require breaking into smaller questions
- Very large projects may take longer to process
- Historical data prior to system migration may not be available

---

## Troubleshooting

### "I don't have access to this information"

This means your account lacks the required RBAC permissions for the operation. AI Chat operations are governed by role-based access control. Contact your administrator to request the appropriate role assignment.

### "Tool not found"

This means the requested tool is not configured for your AI assistant. Check with your administrator about available tools and assistant configuration.

### "No results found"

- Check your spelling of project codes, WBS codes (e.g., 1.2.3), and change order codes (e.g., CO-2026-001)
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
2. **Drill Down**: Follow up with specific WBS Element, work package, or cost element questions
3. **Check Status Regularly**: Use "What's the status of PRJ-XXX?" for quick updates
4. **Monitor EVM**: Ask "How is PRJ-XXX performing?" weekly

### For Cost Engineers

1. **Use Variance Questions**: "What's the cost variance for...?"
2. **Compare Allocated vs Actual**: "Compare budget amount and cost registrations for work package WP-XXX"
3. **Analyze Trends**: "Show me cost trends for PRJ-XXX"

### For Change Managers

1. **Generate Drafts**: "Create a change order for..." to start the workflow
2. **Check Status**: "What's the status of CO-2026-XXX?" to track progress
3. **Review Impact**: "What's the impact level of CO-2026-XXX?" before approving

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
| Show WBS Elements | "Show WBS Elements for PRJ-001" |
| EVM metrics | "How is PRJ-001 performing?" |
| Create change order | "Create a change order for..." |
| Check status | "What's the status of PRJ-001?" |
| Cost analysis | "What's the cost variance for WBS Element 2.1?" |
| Upload image | Drag and drop an image into the chat |
| Upload file | Drag and drop a file into the chat |

---

**Version History**

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-10 | Initial release |
| 1.1.0 | 2026-05-30 | Correct entity names and field names to match codebase; add entity hierarchy with Control Accounts, Work Packages, Cost Registrations; add multimodal input, streaming, approval workflow, and RBAC permissions documentation; update EVM section to reflect computed metrics; update Change Order examples with correct fields (title, impact_level, impact_score) |
