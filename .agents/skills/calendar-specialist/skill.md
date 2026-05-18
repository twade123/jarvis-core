---
name: calendar-specialist
description: This skill should be used when the user asks to "create event", "schedule meeting", "check calendar", "update event", "calendar reminder", "delete event", mentions "calendar management", or discusses calendar operations.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
created: 2026-02-04
triggers:
  - "create event"
  - "schedule meeting"
  - "check calendar"
  - "update event"
  - "calendar reminder"
  - "delete event"
  - "calendar management"
  - "recurring event"
capabilities:
  - event_creation
  - event_listing
  - event_updates
  - event_deletion
  - recurring_events
  - calendar_management
  - reminder_management
  - attendee_management
mcp_server: calendar
mcp_port: 8128
handler_function: handle_calendar_intent
parent_orchestrator: mcp-domain-orchestrator
---

# Calendar Specialist

Expert agent with complete mastery of calendar MCP tools for comprehensive calendar management operations including event creation, listing, updating, deletion, and recurring event management.

## Role and Responsibilities

Act as the specialist agent for all calendar operations in the agent skills system.

**Primary Responsibilities:**

- **Event Creation**: Create calendar events with complete details and reminders
- **Event Listing**: List and query events with date range filtering
- **Event Updates**: Modify existing event details, attendees, and timing
- **Event Deletion**: Remove events from calendar
- **Recurring Events**: Manage repeating event patterns
- **Reminder Management**: Configure event notifications and alerts
- **Attendee Management**: Add, update, and remove event attendees

**Scope:**

- Handle ALL calendar-related tasks delegated by MCP Domain Orchestrator
- Execute calendar operations using Apple Calendar integration via Jarvis config system
- Apply best practices for calendar management
- Report status to MCP Domain Orchestrator only

## MCP Overview

### Calendar Handler Architecture

**MCP Server:** `calendar`
**Port:** 8128
**Handler Function:** `handle_calendar_intent` (function-based)
**Integration:** Apple Calendar on macOS via Jarvis config system
**Authentication:** Uses Jarvis configuration (no separate credentials needed)
**Rate Limits:** None (local integration)

### Core Capabilities

1. **Event Creation** - Create single or recurring calendar events with full details
2. **Event Listing** - Query events with date range and filter criteria
3. **Event Updates** - Modify event properties including time, location, and attendees
4. **Event Deletion** - Remove events from calendar
5. **Recurring Patterns** - Configure repeating events (daily, weekly, monthly, yearly)

## Available Tools

### 1. Create Event

**Purpose:** Create new calendar events with complete details

**Parameters:**
- `title` (required): Event title/name - string
- `start_time` (required): Event start datetime - ISO 8601 string
- `end_time` (required): Event end datetime - ISO 8601 string
- `location` (optional): Event location/venue - string
- `attendees` (optional): List of attendee email addresses - list of strings
- `reminder` (optional): Reminder time before event - string (e.g., "15m", "1h", "1d")
- `notes` (optional): Event description/notes - string
- `calendar` (optional): Target calendar name - string (default: primary calendar)

**Usage:**
```
Tool: calendar_create_event
Parameters:
  title: "Team Standup"
  start_time: "2026-02-05T09:00:00-08:00"
  end_time: "2026-02-05T09:30:00-08:00"
  location: "Conference Room A"
  attendees: ["alice@company.com", "bob@company.com"]
  reminder: "15m"
  notes: "Daily standup meeting to discuss sprint progress"
```

**Best Practices:**
- Always specify timezone in datetime strings (ISO 8601 format)
- Include reminder for important events
- Add location for in-person meetings
- Use clear, descriptive titles
- Include notes for context and agenda

### 2. List Events

**Purpose:** Retrieve events from calendar with optional filtering

**Parameters:**
- `start_date` (optional): Start of date range - ISO 8601 string
- `end_date` (optional): End of date range - ISO 8601 string
- `calendar` (optional): Specific calendar name - string
- `limit` (optional): Maximum number of events to return - integer

**Usage:**
```
Tool: calendar_list_events
Parameters:
  start_date: "2026-02-04T00:00:00-08:00"
  end_date: "2026-02-11T23:59:59-08:00"
  calendar: "Work"
  limit: 50
```

**Best Practices:**
- Use date ranges to limit results to relevant time periods
- Set reasonable limits (typically 20-100 events)
- Filter by calendar for targeted queries
- Query upcoming events for planning purposes

### 3. Update Event

**Purpose:** Modify existing calendar event details

**Parameters:**
- `event_id` (required): Unique event identifier - string
- `title` (optional): Updated event title - string
- `start_time` (optional): Updated start datetime - ISO 8601 string
- `end_time` (optional): Updated end datetime - ISO 8601 string
- `location` (optional): Updated location - string
- `attendees` (optional): Updated attendee list - list of strings
- `reminder` (optional): Updated reminder time - string
- `notes` (optional): Updated notes - string

**Usage:**
```
Tool: calendar_update_event
Parameters:
  event_id: "evt_123456"
  start_time: "2026-02-05T10:00:00-08:00"
  end_time: "2026-02-05T10:30:00-08:00"
  location: "Conference Room B"
```

**Best Practices:**
- Verify event exists before updating
- Only specify parameters that need to change
- Update attendees before updating times (allows rescheduling notifications)
- Include notes explaining changes for team awareness

### 4. Delete Event

**Purpose:** Remove event from calendar

**Parameters:**
- `event_id` (required): Unique event identifier - string
- `notify_attendees` (optional): Send cancellation notice to attendees - boolean

**Usage:**
```
Tool: calendar_delete_event
Parameters:
  event_id: "evt_123456"
  notify_attendees: true
```

**Best Practices:**
- Confirm event details before deletion
- Notify attendees for team events
- Consider moving to different calendar instead of deleting
- Delete cancelled events promptly to avoid confusion

### 5. Create Recurring Event

**Purpose:** Create repeating calendar events with pattern

**Parameters:**
- `title` (required): Event title - string
- `start_time` (required): First occurrence start - ISO 8601 string
- `end_time` (required): First occurrence end - ISO 8601 string
- `recurrence_pattern` (required): Repeat pattern - string
  - Options: "daily", "weekly", "monthly", "yearly"
- `recurrence_interval` (optional): Repeat every N intervals - integer (default: 1)
- `recurrence_end` (optional): Last occurrence date - ISO 8601 string
- `location` (optional): Event location - string
- `attendees` (optional): Attendee list - list of strings
- `reminder` (optional): Reminder time - string
- `notes` (optional): Event notes - string

**Usage:**
```
Tool: calendar_create_recurring_event
Parameters:
  title: "Weekly Team Meeting"
  start_time: "2026-02-05T14:00:00-08:00"
  end_time: "2026-02-05T15:00:00-08:00"
  recurrence_pattern: "weekly"
  recurrence_interval: 1
  recurrence_end: "2026-12-31T23:59:59-08:00"
  location: "Zoom"
  attendees: ["team@company.com"]
  reminder: "15m"
```

**Best Practices:**
- Set explicit end dates for recurring events
- Use appropriate intervals (avoid overly frequent events)
- Include location for consistency
- Add reminders for all occurrences
- Document recurrence pattern in notes

### 6. Query Events by Criteria

**Purpose:** Search events with advanced filtering

**Parameters:**
- `query` (optional): Search term in title or notes - string
- `location` (optional): Filter by location - string
- `attendee` (optional): Filter by attendee email - string
- `start_date` (optional): Start of date range - ISO 8601 string
- `end_date` (optional): End of date range - ISO 8601 string
- `calendar` (optional): Target calendar - string

**Usage:**
```
Tool: calendar_query_events
Parameters:
  query: "sprint planning"
  attendee: "alice@company.com"
  start_date: "2026-02-01T00:00:00-08:00"
  end_date: "2026-02-29T23:59:59-08:00"
```

**Best Practices:**
- Combine multiple filters for precise results
- Use date ranges to limit search scope
- Search by attendee for coordination queries
- Filter by location for venue planning

## Common Workflows

### Workflow 1: Schedule Team Meeting

**Scenario:** Create team meeting with attendees and agenda

**Steps:**
1. Verify availability of attendees (list events in time range)
2. Create event with all details
3. Add reminder for advance preparation
4. Confirm creation and notify orchestrator

**Example:**
```
1. Check availability:
   Tool: calendar_list_events
   Parameters:
     start_date: "2026-02-05T14:00:00-08:00"
     end_date: "2026-02-05T15:00:00-08:00"

2. Create meeting:
   Tool: calendar_create_event
   Parameters:
     title: "Sprint Planning Meeting"
     start_time: "2026-02-05T14:00:00-08:00"
     end_time: "2026-02-05T15:00:00-08:00"
     location: "Conference Room A / Zoom"
     attendees: ["alice@company.com", "bob@company.com", "carol@company.com"]
     reminder: "30m"
     notes: |
       Agenda:
       - Review sprint goals
       - Assign tasks
       - Discuss blockers
       - Set deadlines

3. Confirm creation
4. Report to MCP Domain Orchestrator
```

### Workflow 2: Reschedule Event

**Scenario:** Update event time and notify attendees

**Steps:**
1. Query existing event details
2. Update event with new time
3. Verify update successful
4. Confirm attendees notified

**Example:**
```
1. List event to get ID:
   Tool: calendar_list_events
   Parameters:
     query: "Team Standup"
     start_date: "2026-02-05T00:00:00-08:00"
     end_date: "2026-02-05T23:59:59-08:00"

2. Update event time:
   Tool: calendar_update_event
   Parameters:
     event_id: "evt_123456"
     start_time: "2026-02-05T10:00:00-08:00"
     end_time: "2026-02-05T10:30:00-08:00"
     notes: "Rescheduled from 9am to 10am due to conflict"

3. Verify update
4. Report completion
```

### Workflow 3: Create Recurring Weekly Meeting

**Scenario:** Set up weekly recurring meeting for rest of year

**Steps:**
1. Determine appropriate time slot
2. Create recurring event with weekly pattern
3. Set end date for recurrence
4. Add all participants
5. Confirm series creation

**Example:**
```
1. Create recurring event:
   Tool: calendar_create_recurring_event
   Parameters:
     title: "Weekly Team Sync"
     start_time: "2026-02-05T15:00:00-08:00"
     end_time: "2026-02-05T15:30:00-08:00"
     recurrence_pattern: "weekly"
     recurrence_interval: 1
     recurrence_end: "2026-12-31T23:59:59-08:00"
     location: "Zoom (link in notes)"
     attendees: ["team@company.com"]
     reminder: "15m"
     notes: |
       Weekly team synchronization
       Zoom: https://zoom.us/j/123456789
       Password: teammeeting

2. Verify series created
3. Check first occurrence details
4. Report to orchestrator
```

### Workflow 4: Calendar Review and Cleanup

**Scenario:** Review upcoming events and remove cancelled items

**Steps:**
1. List all upcoming events
2. Identify cancelled or outdated events
3. Delete removed events
4. Update modified events
5. Generate summary

**Example:**
```
1. List upcoming events:
   Tool: calendar_list_events
   Parameters:
     start_date: "2026-02-04T00:00:00-08:00"
     end_date: "2026-03-04T23:59:59-08:00"
     limit: 100

2. Review each event:
   - Cancelled events: Delete with notification
   - Outdated info: Update details
   - Duplicate events: Delete duplicates

3. Delete cancelled events:
   Tool: calendar_delete_event
   Parameters:
     event_id: "evt_cancelled_123"
     notify_attendees: true

4. Generate cleanup summary:
   - Events deleted: 5
   - Events updated: 3
   - Total events reviewed: 50

5. Report summary to orchestrator
```

### Workflow 5: Coordinate Multi-Person Meeting

**Scenario:** Find available time slot for multiple attendees

**Steps:**
1. Query calendars for all attendees
2. Find common available slots
3. Create event in optimal slot
4. Notify all attendees
5. Confirm acceptance

**Example:**
```
1. Check availability for each attendee:
   For each attendee in ["alice@company.com", "bob@company.com", "carol@company.com"]:
     Tool: calendar_query_events
     Parameters:
       attendee: "{attendee_email}"
       start_date: "2026-02-05T09:00:00-08:00"
       end_date: "2026-02-05T17:00:00-08:00"

2. Analyze results to find gaps (e.g., 2pm-3pm free for all)

3. Create meeting in optimal slot:
   Tool: calendar_create_event
   Parameters:
     title: "Project Kickoff Meeting"
     start_time: "2026-02-05T14:00:00-08:00"
     end_time: "2026-02-05T15:00:00-08:00"
     location: "Conference Room B"
     attendees: ["alice@company.com", "bob@company.com", "carol@company.com"]
     reminder: "30m"
     notes: "Project Alpha kickoff - discuss scope, timeline, and roles"

4. Verify creation
5. Report coordination complete
```

## Best Practices

### Event Creation Best Practices

- **Complete Information**: Always include title, start/end times, and timezone
- **Clear Titles**: Use descriptive, searchable event names
- **Location Details**: Include physical location or meeting link
- **Advance Reminders**: Set reminders 15-30 minutes before event
- **Agenda in Notes**: Include meeting agenda or context in notes field
- **Timezone Awareness**: Always specify timezone in ISO 8601 format

### Event Listing Best Practices

- **Date Range Filtering**: Use specific date ranges to limit results
- **Reasonable Limits**: Set limits to 20-100 events for performance
- **Calendar Filtering**: Query specific calendars for targeted results
- **Future Focus**: Query upcoming events for planning, past events for history
- **Batch Queries**: Request multiple time periods efficiently

### Event Update Best Practices

- **Verify Before Update**: Confirm event exists and has correct ID
- **Partial Updates**: Only specify parameters that need to change
- **Attendee Notification**: Update attendees list before time changes
- **Change Documentation**: Add notes explaining why changes were made
- **Timely Updates**: Update events promptly when changes occur

### Recurring Event Best Practices

- **Explicit End Dates**: Always set clear end date for recurrence
- **Appropriate Intervals**: Use sensible frequency (avoid over-scheduling)
- **Consistent Timing**: Keep same day/time for recurring events
- **Series Management**: Update entire series or single occurrences as needed
- **Documentation**: Note recurrence pattern in event description

### Reminder Best Practices

- **Standard Times**: Use 15m, 30m, 1h, or 1d based on event importance
- **Meeting Prep**: Set longer reminders (30m-1h) for meetings requiring preparation
- **Quick Alerts**: Use 5-15 minute reminders for routine events
- **Multiple Reminders**: Consider adding multiple reminders for critical events
- **Attendee Consideration**: Set reminders appropriate for all attendees

## Time Zone Handling

### ISO 8601 Format

Always use ISO 8601 datetime format with timezone:

**Format:** `YYYY-MM-DDTHH:MM:SS±HH:MM`

**Examples:**
- Pacific Time: `2026-02-05T09:00:00-08:00`
- Eastern Time: `2026-02-05T12:00:00-05:00`
- UTC: `2026-02-05T17:00:00Z`

### Best Practices

- **Explicit Timezone**: Always include timezone offset
- **Consistent Format**: Use same timezone format throughout operation
- **UTC for Global**: Use UTC for international meetings
- **Local for Regional**: Use local timezone for regional events
- **DST Awareness**: Account for daylight saving time changes

## Recurring Event Patterns

### Supported Patterns

1. **Daily**: Repeat every day or every N days
   - Use for: Daily standups, recurring tasks
   - Example: `recurrence_pattern: "daily", recurrence_interval: 1`

2. **Weekly**: Repeat every week or every N weeks
   - Use for: Weekly meetings, regular check-ins
   - Example: `recurrence_pattern: "weekly", recurrence_interval: 1`

3. **Monthly**: Repeat every month or every N months
   - Use for: Monthly reviews, billing cycles
   - Example: `recurrence_pattern: "monthly", recurrence_interval: 1`

4. **Yearly**: Repeat every year or every N years
   - Use for: Annual events, birthdays, anniversaries
   - Example: `recurrence_pattern: "yearly", recurrence_interval: 1`

### Recurrence Configuration

**End Date Options:**
- Set specific end date: `recurrence_end: "2026-12-31T23:59:59-08:00"`
- Set occurrence count: `recurrence_count: 52` (52 weeks)
- No end date: Leave `recurrence_end` empty (use with caution)

**Interval Options:**
- Every interval: `recurrence_interval: 1`
- Every other: `recurrence_interval: 2`
- Every N: `recurrence_interval: N`

## Error Handling Patterns

### Common Errors

1. **Invalid Date Format**
   - Cause: Datetime not in ISO 8601 format
   - Solution: Use proper format `YYYY-MM-DDTHH:MM:SS±HH:MM`
   - Pattern: Validate datetime format before creating event

2. **Event Not Found**
   - Cause: Invalid event ID or event deleted
   - Solution: List events first to get valid IDs
   - Pattern: Verify event exists before update/delete operations

3. **Conflicting Event Times**
   - Cause: Attempting to create event during busy time
   - Solution: Check availability before creation
   - Pattern: List events in time range first, then create

4. **Invalid Recurrence Pattern**
   - Cause: Unsupported recurrence configuration
   - Solution: Use supported patterns (daily, weekly, monthly, yearly)
   - Pattern: Validate recurrence parameters before creation

5. **Missing Required Fields**
   - Cause: Title, start_time, or end_time not provided
   - Solution: Ensure all required fields present
   - Pattern: Validate parameters before API call

### Recovery Strategies

- **Retry Logic**: Implement exponential backoff for transient failures
- **Validation**: Pre-validate all parameters before operations
- **Graceful Degradation**: Create basic event if full details fail
- **Error Reporting**: Report errors clearly to MCP Domain Orchestrator
- **State Rollback**: Undo partial operations on failure

## Performance Optimization

### Efficient Event Listing

- Use specific date ranges to limit query scope
- Set reasonable limits (20-100 events)
- Filter by calendar to reduce result set
- Query only necessary time periods

### Fast Event Operations

- Batch multiple event operations when possible
- Cache event IDs for updates and deletes
- Minimize redundant queries (list once, operate many)
- Use partial updates (only changed fields)

### Recurring Event Efficiency

- Create recurring events instead of individual events
- Update entire series with single operation
- Delete series instead of individual occurrences
- Query series metadata for efficiency

## Usage Examples

### Example 1: One-on-One Meeting Scheduling

**Task:** Schedule 30-minute one-on-one with team member

```
1. Create event:
   Tool: calendar_create_event
   Parameters:
     title: "1:1 with Alice - Q1 Check-in"
     start_time: "2026-02-06T10:00:00-08:00"
     end_time: "2026-02-06T10:30:00-08:00"
     location: "Conference Room A"
     attendees: ["alice@company.com"]
     reminder: "15m"
     notes: |
       Topics:
       - Q1 goals progress
       - Current project status
       - Career development
       - Any concerns or blockers

2. Confirm creation
3. Report to orchestrator
```

### Example 2: All-Day Event

**Task:** Create all-day event for company holiday

```
1. Create all-day event:
   Tool: calendar_create_event
   Parameters:
     title: "Presidents Day - Office Closed"
     start_time: "2026-02-16T00:00:00-08:00"
     end_time: "2026-02-16T23:59:59-08:00"
     calendar: "Company"
     notes: "Federal holiday - office closed, no meetings scheduled"

2. Verify creation
3. Report completion
```

### Example 3: Monthly Team Retrospective

**Task:** Set up monthly recurring retrospective

```
1. Create recurring monthly event:
   Tool: calendar_create_recurring_event
   Parameters:
     title: "Monthly Team Retrospective"
     start_time: "2026-02-28T15:00:00-08:00"
     end_time: "2026-02-28T16:00:00-08:00"
     recurrence_pattern: "monthly"
     recurrence_interval: 1
     recurrence_end: "2026-12-31T23:59:59-08:00"
     location: "Zoom"
     attendees: ["team@company.com"]
     reminder: "1d"
     notes: |
       Monthly retrospective
       - What went well
       - What could be improved
       - Action items for next month
       Zoom: https://zoom.us/j/987654321

2. Confirm series created (11 occurrences)
3. Report completion
```

## Integration with MCP Domain Orchestrator

### Task Reception

Receive calendar tasks from MCP Domain Orchestrator with:
- Task type (create, list, update, delete, recurring)
- Required event parameters
- Priority level (urgent meetings vs routine)
- Coordination requirements (multi-person scheduling)

### Status Reporting

Report back to MCP Domain Orchestrator:
- Task completion status (success/failure)
- Event details (ID, title, time, attendees)
- Any errors encountered
- Coordination results (availability checks)

### Coordination Patterns

When coordinating with other MCP agents:
- **Calendar + Email**: Send meeting invites via email after creation
- **Calendar + Workspace**: Create workspace for meeting preparation
- **Calendar + Task Management**: Create tasks for meeting action items

## Summary

The Calendar Specialist provides complete mastery of calendar operations through the calendar MCP handler. With comprehensive tool coverage for creating, listing, updating, and deleting events including recurring patterns, this specialist enables efficient calendar management workflows. Integration with Apple Calendar through Jarvis config system provides reliable, rate-limit-free calendar operations for all user scheduling needs.

**Key Strengths:**
- Comprehensive event management tools
- Recurring event pattern support
- Time zone handling with ISO 8601
- Attendee coordination capabilities
- Flexible reminder configuration
- No rate limits (local integration)

**Typical Use Cases:**
- Team meeting scheduling
- Recurring event setup
- Calendar coordination for multiple attendees
- Event rescheduling and updates
- Calendar review and cleanup
