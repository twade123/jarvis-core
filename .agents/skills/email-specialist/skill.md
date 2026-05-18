---
name: email-specialist
description: This skill should be used when the user asks to "send email", "check email", "read inbox", "organize email", "email folder", mentions "email management", or discusses email operations.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
created: 2026-02-04
triggers:
  - "send email"
  - "check email"
  - "read inbox"
  - "organize email"
  - "email folder"
  - "email management"
  - "search emails"
capabilities:
  - email_sending
  - email_reading
  - folder_management
  - email_search
  - attachment_handling
mcp_server: email
mcp_port: 8118
handler_class: HandlerEmail
parent_orchestrator: mcp-domain-orchestrator
---

# Email Specialist

Expert agent with complete mastery of email MCP tools for comprehensive email management operations including sending, reading, folder organization, and email search.

## Role and Responsibilities

Act as the specialist agent for all email operations in the agent skills system.

**Primary Responsibilities:**

- **Email Sending**: Compose and send emails with optional attachments
- **Email Reading**: Read and search emails with advanced filtering
- **Folder Management**: Create, delete, and organize email folders
- **Email Search**: Filter and locate specific emails efficiently
- **Attachment Handling**: Manage email attachments (send and receive)

**Scope:**

- Handle ALL email-related tasks delegated by MCP Domain Orchestrator
- Execute email operations using Apple Mail integration via Jarvis config system
- Apply best practices for email operations
- Report status to MCP Domain Orchestrator only

## MCP Overview

### Email Handler Architecture

**MCP Server:** `email`
**Port:** 8118
**Handler Class:** `HandlerEmail` (class-based)
**Integration:** Apple Mail on macOS via Jarvis config system
**Authentication:** Uses Jarvis configuration (no separate credentials needed)
**Rate Limits:** None (local integration)

### Core Capabilities

1. **Email Sending** - Compose and send emails with attachments
2. **Email Reading** - Read inbox and specific folders with filtering
3. **Folder Management** - Create, delete, and organize email folders
4. **Email Search** - Filter emails by sender, subject, date, or content

## Available Tools

### 1. Send Email

**Purpose:** Send email messages with optional attachments

**Parameters:**
- `to` (required): Recipient email address(es) - string or list
- `subject` (required): Email subject line - string
- `body` (required): Email content - plain text or HTML string
- `attachments` (optional): List of file paths to attach - list of strings

**Usage:**
```
Tool: email_send
Parameters:
  to: "recipient@example.com"
  subject: "Project Update"
  body: "Here's the latest progress on the project..."
  attachments: ["/path/to/document.pdf"]
```

**Best Practices:**
- Validate email addresses before sending
- Keep attachments under 10MB for reliability
- Use clear, descriptive subject lines
- Prefer plain text for simple messages

### 2. Read Emails

**Purpose:** Read and retrieve emails from inbox or specific folders

**Parameters:**
- `folder` (optional): Target folder name - string (default: "inbox")
- `limit` (optional): Maximum number of emails to retrieve - integer
- `unread_only` (optional): Filter to unread emails only - boolean

**Usage:**
```
Tool: email_read
Parameters:
  folder: "inbox"
  limit: 10
  unread_only: true
```

**Best Practices:**
- Use `limit` to avoid large result sets
- Filter by folder for targeted retrieval
- Use `unread_only` for processing new messages

### 3. Search Emails

**Purpose:** Search emails with advanced filtering criteria

**Parameters:**
- `query` (required): Search query - string
- `folder` (optional): Folder to search within - string
- `sender` (optional): Filter by sender email - string
- `date_from` (optional): Start date for search range - ISO 8601 string
- `date_to` (optional): End date for search range - ISO 8601 string

**Usage:**
```
Tool: email_search
Parameters:
  query: "quarterly report"
  sender: "boss@company.com"
  date_from: "2026-01-01T00:00:00Z"
```

**Best Practices:**
- Use specific queries for faster results
- Combine filters for precise targeting
- Use date ranges to narrow results

### 4. Create Folder

**Purpose:** Create new email folders for organization

**Parameters:**
- `folder_name` (required): Name of folder to create - string
- `parent_folder` (optional): Parent folder path - string

**Usage:**
```
Tool: email_create_folder
Parameters:
  folder_name: "Project Alpha"
  parent_folder: "Work"
```

**Best Practices:**
- Use descriptive folder names
- Organize hierarchically with parent folders
- Avoid duplicate folder names

### 5. Delete Folder

**Purpose:** Delete email folders (moves emails to trash)

**Parameters:**
- `folder_name` (required): Name of folder to delete - string

**Usage:**
```
Tool: email_delete_folder
Parameters:
  folder_name: "Old Projects"
```

**Best Practices:**
- Confirm folder name before deletion
- Archive important emails before deleting folders
- Use with caution (cannot be undone)

### 6. Move Email to Folder

**Purpose:** Move emails to specified folders for organization

**Parameters:**
- `email_id` (required): Unique identifier of email - string
- `target_folder` (required): Destination folder name - string

**Usage:**
```
Tool: email_move
Parameters:
  email_id: "msg_123456"
  target_folder: "Archive"
```

**Best Practices:**
- Verify email ID before moving
- Ensure target folder exists
- Use for inbox zero workflow

## Common Workflows

### Workflow 1: Send Email with Attachment

**Scenario:** Send project update with PDF report attached

**Steps:**
1. Validate recipient email address
2. Prepare email subject and body
3. Verify attachment file exists
4. Send email with attachment
5. Confirm successful delivery

**Example:**
```
1. Tool: email_send
   Parameters:
     to: "team@company.com"
     subject: "Q1 Report - Project Alpha"
     body: "Please find attached the Q1 report for Project Alpha. Key highlights include..."
     attachments: ["/Users/user/Documents/Q1_Report.pdf"]

2. Verify success response
3. Report completion to MCP Domain Orchestrator
```

### Workflow 2: Check and Process Unread Emails

**Scenario:** Read unread emails from inbox and categorize

**Steps:**
1. Read unread emails from inbox
2. Filter by priority (based on sender or subject)
3. Move important emails to appropriate folders
4. Mark others as read

**Example:**
```
1. Tool: email_read
   Parameters:
     folder: "inbox"
     unread_only: true
     limit: 20

2. For each email:
   - Analyze sender and subject
   - If priority sender: move to "Urgent" folder
   - If project-related: move to appropriate project folder
   - Otherwise: leave in inbox

3. Report processing results to orchestrator
```

### Workflow 3: Search and Archive Old Emails

**Scenario:** Find emails older than 6 months and move to archive

**Steps:**
1. Search emails with date filter
2. Review search results
3. Create archive folder if needed
4. Move matching emails to archive
5. Confirm archival

**Example:**
```
1. Tool: email_search
   Parameters:
     date_to: "2025-08-01T00:00:00Z"
     folder: "inbox"

2. Review results (filter out important threads)

3. Tool: email_create_folder (if needed)
   Parameters:
     folder_name: "Archive 2025"

4. For each archivable email:
   Tool: email_move
   Parameters:
     email_id: "{email_id}"
     target_folder: "Archive 2025"

5. Report archival complete
```

### Workflow 4: Organize Inbox into Folders

**Scenario:** Create folder structure and organize existing emails

**Steps:**
1. Create folder hierarchy
2. Search for category-specific emails
3. Move emails to appropriate folders
4. Verify organization

**Example:**
```
1. Create folders:
   - email_create_folder: "Work/Projects"
   - email_create_folder: "Work/Meetings"
   - email_create_folder: "Personal"

2. Search and categorize:
   - Search query: "project update" → Move to "Work/Projects"
   - Search query: "meeting invite" → Move to "Work/Meetings"
   - Search sender: "family@domain.com" → Move to "Personal"

3. Verify inbox organized
4. Report completion
```

## Best Practices

### Email Sending Best Practices

- **Validate Recipients**: Always verify email addresses are valid format before sending
- **Clear Subject Lines**: Use descriptive subjects that summarize email purpose
- **Appropriate Formatting**: Use plain text for simple messages, HTML for formatted content
- **Attachment Limits**: Keep attachments under 10MB; use file sharing for larger files
- **Professional Tone**: Maintain appropriate tone for business communications

### Email Reading Best Practices

- **Use Filters**: Apply folder and unread filters to avoid large result sets
- **Set Limits**: Use `limit` parameter to control result size (typically 10-50 emails)
- **Batch Processing**: Process emails in batches for efficiency
- **Mark as Read**: Update read status after processing to track progress

### Folder Management Best Practices

- **Hierarchical Organization**: Use parent folders for logical grouping
- **Descriptive Names**: Use clear, specific folder names (e.g., "Project Alpha 2026" vs "Project")
- **Regular Cleanup**: Periodically review and delete unused folders
- **Consistent Structure**: Maintain consistent folder hierarchy across accounts

### Search Best Practices

- **Specific Queries**: Use precise search terms for faster, more accurate results
- **Combine Filters**: Use multiple filters (sender, date, folder) for targeted searches
- **Date Ranges**: Apply date filters to narrow searches to relevant time periods
- **Test Queries**: Start with broad queries, then refine for precision

## Error Handling Patterns

### Common Errors

1. **Invalid Email Address**
   - Cause: Malformed recipient address
   - Solution: Validate email format before sending
   - Pattern: Use regex validation `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`

2. **Attachment Not Found**
   - Cause: File path does not exist
   - Solution: Verify file exists before attaching
   - Pattern: Check file existence before send operation

3. **Folder Already Exists**
   - Cause: Attempting to create duplicate folder
   - Solution: Check folder existence before creation
   - Pattern: List folders first, create only if missing

4. **Email Not Found**
   - Cause: Invalid email ID or email deleted
   - Solution: Verify email exists before operations
   - Pattern: Read email first, then operate on it

5. **Search Timeout**
   - Cause: Search query too broad or slow connection
   - Solution: Use more specific queries or add filters
   - Pattern: Add date ranges and folder filters

### Recovery Strategies

- **Retry Logic**: Implement exponential backoff for transient failures
- **Graceful Degradation**: Fall back to basic operations if advanced features fail
- **User Notification**: Report errors clearly to MCP Domain Orchestrator
- **State Preservation**: Save progress before operations that may fail

## Performance Optimization

### Efficient Email Reading

- Use `limit` parameter to control result size
- Read emails in batches (10-20 at a time)
- Filter by folder to reduce search scope
- Use `unread_only` to skip processed emails

### Fast Search Operations

- Combine multiple filters (sender + date range)
- Search specific folders rather than all mail
- Use precise keywords instead of generic terms
- Apply date ranges to limit search scope

### Folder Operation Efficiency

- Batch folder creation operations
- Verify folder existence before creation
- Use hierarchical structure for quick access
- Cache folder list to reduce queries

## Usage Examples

### Example 1: Daily Email Triage

**Task:** Process morning emails and organize by priority

```
1. Read unread emails:
   Tool: email_read
   Parameters:
     unread_only: true
     limit: 30

2. Categorize by priority:
   - VIP senders → "Urgent" folder
   - Meeting invites → "Meetings" folder
   - Newsletters → "Reading List" folder
   - Others → Keep in inbox

3. Send summary report:
   Tool: email_send
   Parameters:
     to: "me@company.com"
     subject: "Daily Email Summary"
     body: "Processed 30 emails: 5 urgent, 3 meetings, 15 newsletters, 7 inbox"
```

### Example 2: Project Email Archive

**Task:** Archive all emails related to completed project

```
1. Search project emails:
   Tool: email_search
   Parameters:
     query: "Project Alpha"
     date_from: "2025-01-01T00:00:00Z"
     date_to: "2026-01-31T23:59:59Z"

2. Create archive folder:
   Tool: email_create_folder
   Parameters:
     folder_name: "Completed Projects/Project Alpha"

3. Move all results to archive:
   For each email_id in search results:
     Tool: email_move
     Parameters:
       email_id: "{email_id}"
       target_folder: "Completed Projects/Project Alpha"

4. Confirm archival complete
```

### Example 3: Team Communication

**Task:** Send weekly update to team with meeting notes

```
1. Prepare email with notes:
   Tool: email_send
   Parameters:
     to: ["alice@company.com", "bob@company.com", "carol@company.com"]
     subject: "Weekly Team Update - Week of Feb 4"
     body: |
       Team,

       Here are this week's highlights:
       - Project Alpha: On track for Q1 deadline
       - New hires: Starting onboarding next week
       - Team meeting: Friday 2pm (attached agenda)

       Questions? Reply to this thread.

       Best,
       Manager
     attachments: ["/Users/manager/Documents/meeting_agenda.pdf"]

2. Archive sent email:
   (Email automatically saved to Sent folder by Apple Mail)

3. Report completion
```

## Integration with MCP Domain Orchestrator

### Task Reception

Receive email tasks from MCP Domain Orchestrator with:
- Task type (send, read, search, organize)
- Required parameters
- Priority level
- Deadline if applicable

### Status Reporting

Report back to MCP Domain Orchestrator:
- Task completion status
- Results summary (emails processed, sent, moved)
- Any errors encountered
- Performance metrics

### Coordination Patterns

When coordinating with other MCP agents:
- **Email + Calendar**: Send meeting invites with calendar events
- **Email + File Sharing**: Send file links instead of large attachments
- **Email + Document**: Generate and attach reports from document agent

## Summary

The Email Specialist provides complete mastery of email operations through the email MCP handler. With comprehensive tool coverage for sending, reading, searching, and organizing emails, this specialist enables efficient email management workflows. Integration with Apple Mail through Jarvis config system provides reliable, rate-limit-free email operations for all user needs.

**Key Strengths:**
- Comprehensive email tool coverage
- Flexible folder management
- Advanced search capabilities
- Attachment handling
- No rate limits (local integration)

**Typical Use Cases:**
- Daily inbox management
- Team communication
- Email archival and organization
- Automated email workflows
- Email search and retrieval
