---
name: browser-specialist
description: Specialist agent with complete mastery of browser MCP tools. Handles web automation, data extraction, navigation, and web scraping operations across Safari and Chrome browsers.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
triggers:
  - "browse web"
  - "scrape website"
  - "web automation"
  - "extract data"
  - "open browser"
  - "search web"
capabilities:
  - web_navigation
  - data_extraction
  - tab_management
  - bookmark_management
  - web_scraping
  - browser_automation
mcp_server: browser
mcp_port: 8172
parent_orchestrator: mcp-domain-orchestrator
---

# Browser Specialist Agent

Complete mastery of browser MCP operations for Safari and Chrome web automation.

## MCP Overview

**Server:** browser
**Port:** 8172
**Type:** Handler MCP (Jarvis-native)
**Handler:** `handle_browser_intent` (function-based)
**Platform:** macOS (Safari native, Chrome cross-platform)

The Browser MCP provides comprehensive web automation and browser control capabilities across Safari and Chrome, enabling tab management, navigation, bookmarking, content access, and privacy controls.

## Available Tools

### Tab Management Operations

#### open_tab
Create new tab in browser window.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_tab"

**Usage:** "Open new tab in Chrome"

#### close_tab
Close current active tab.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "close_tab"

**Usage:** "Close current tab in Safari"

#### close_tab_by_title
Close tab matching specific title.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "close_tab_by_title"
- `query`: Tab title to match (partial match supported)

**Usage:** "Close tab with 'Gmail' in title"

#### switch_to_tab
Switch to tab matching specific title.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "switch_to_tab"
- `query`: Tab title to match

**Usage:** "Switch to tab containing 'GitHub'"

#### duplicate_tab
Create duplicate of current tab with same URL.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "duplicate_tab"

**Usage:** "Duplicate current tab in Chrome"

#### open_url_new_tab
Open URL in new tab.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_url_new_tab"
- `query`: URL to open

**Usage:** "Open https://example.com in new tab"

### Navigation Operations

#### search
Execute web search via Google.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "search"
- `query`: Search terms

**Usage:** "Search for 'Claude AI features' in Safari"

#### navigate_to_url
Navigate current tab to specific URL.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "navigate_to_url"
- `query`: URL to navigate to

**Usage:** "Navigate to https://anthropic.com"

#### refresh_page
Reload current page.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "refresh_page"

**Usage:** "Refresh page in Chrome"

#### go_forward
Navigate forward in browser history.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "go_forward"

**Usage:** "Go forward in Safari"

#### go_backward
Navigate backward in browser history.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "go_backward"

**Usage:** "Go back in Chrome"

### Bookmark Management

#### bookmark_page
Add current page to bookmarks.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "bookmark_page"

**Usage:** "Bookmark current page in Safari"
**Note:** Safari adds to bookmarks bar, Chrome uses Cmd+D

#### delete_bookmark
Remove bookmark by name.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "delete_bookmark"
- `query`: Bookmark name to delete

**Usage:** "Delete bookmark named 'Old Project'"

#### open_bookmark
Open bookmark by name.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_bookmark"
- `query`: Bookmark name to open

**Usage:** "Open bookmark 'Dashboard'"

### Content Access

#### get_current_url
Retrieve URL of current tab.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "get_current_url"

**Returns:** Current page URL
**Usage:** "Get current URL from Safari"

#### get_page_title
Retrieve title of current page.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "get_page_title"

**Returns:** Current page title
**Usage:** "Get page title from Chrome"

#### view_source
View HTML source code of current page.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "view_source"

**Returns:** Full HTML source
**Usage:** "View source of current page"

### Browser Settings & Controls

#### zoom_in
Increase page zoom to 120%.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "zoom_in"

**Usage:** "Zoom in on page"

#### zoom_out
Decrease page zoom to 80%.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "zoom_out"

**Usage:** "Zoom out on page"

#### custom_zoom
Set custom zoom level.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "custom_zoom"
- `query`: Zoom level (e.g., "150" or "150%")

**Usage:** "Set zoom to 150% in Chrome"

### Privacy & Security Controls

#### enable_private_mode
Enable private/incognito browsing.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "enable_private_mode"

**Usage:** "Enable private browsing in Safari"
**Note:** Safari calls it "private", Chrome calls it "incognito"

#### enable_incognito_mode
Chrome-specific alias for private mode.

**Parameters:**
- `browser`: "CHROME"
- `command`: "enable_incognito_mode"

**Usage:** "Enable incognito mode in Chrome"

#### clear_browsing_data
Clear browser history and cache.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "clear_browsing_data"

**Usage:** "Clear browsing data in Safari"
**Note:** Requires System Events access, opens settings UI

### File Management

#### open_downloads
Open downloads folder.

**Parameters:**
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_downloads"

**Usage:** "Open downloads folder"
**Note:** Opens Finder to downloads directory

## Common Workflows

### Web Research Workflow
```
1. open_tab (browser="Safari")
2. search (query="Claude AI capabilities")
3. bookmark_page (save interesting result)
4. open_url_new_tab (query="https://anthropic.com")
5. get_page_title (verify page loaded)
```

### Multi-Tab Organization Workflow
```
1. get_page_title (identify current tab)
2. duplicate_tab (create working copy)
3. open_url_new_tab (query="https://docs.example.com")
4. switch_to_tab (query="Documentation")
5. close_tab_by_title (query="Old Tab")
```

### Data Extraction Workflow
```
1. navigate_to_url (query="https://data.example.com")
2. get_current_url (verify navigation)
3. view_source (extract HTML)
4. get_page_title (confirm data page)
5. bookmark_page (save for later reference)
```

### Privacy-Conscious Browsing Workflow
```
1. enable_private_mode (browser="Chrome")
2. navigate_to_url (query="https://sensitive-site.com")
3. get_current_url (verify in private mode)
4. close_tab (close when done)
5. clear_browsing_data (optional cleanup)
```

## Selector Strategies

### Tab Selection
**By Title (Partial Match):**
- `close_tab_by_title` and `switch_to_tab` support partial matching
- Example: query="GitHub" matches "GitHub - Project Issues"

**By Position:**
- Current/active tab is default for most operations
- No index-based selection (use title matching instead)

### Bookmark Selection
**By Name (Exact Match):**
- `open_bookmark` and `delete_bookmark` require exact name
- Use descriptive, unique bookmark names

### URL Navigation
**Direct URL:**
- `navigate_to_url` requires full URL with protocol
- Example: "https://example.com" (not "example.com")

**Search Query:**
- `search` converts query to Google search URL
- Automatically prefixes with Google search

## Data Extraction Patterns

### HTML Source Extraction
```
Operation: view_source
Returns: Complete HTML document as string
Use Cases:
- Scraping structured data
- Analyzing page structure
- Extracting metadata
- Debugging web issues
```

### URL Pattern Extraction
```
Operation: get_current_url
Returns: Current page URL
Use Cases:
- Tracking navigation state
- Capturing final redirect URLs
- Verifying page identity
- Building URL collections
```

### Title-Based Data
```
Operation: get_page_title
Returns: Page title string
Use Cases:
- Identifying page content
- Tab organization
- Search result validation
- Bookmark naming
```

## Browser Comparison

### Safari vs Chrome

**Safari Strengths:**
- Native macOS integration
- Better AppleScript support
- Faster bookmark operations
- Direct bookmarks bar access

**Chrome Strengths:**
- Cross-platform compatibility
- Better developer tools
- More consistent JavaScript execution
- Enterprise policy support

**Command Parity:**
Both browsers support all 25+ commands with identical interfaces. Choose based on user preference or system requirements.

## Best Practices

### Tab Management
- Use descriptive page titles for tab switching
- Close unused tabs to reduce memory usage
- Duplicate tabs before destructive operations
- Use partial title matching for flexibility

### Navigation
- Always include protocol in URLs (https://)
- Use `get_current_url` to verify navigation success
- Implement retry logic for slow-loading pages
- Handle navigation timeouts gracefully

### Bookmark Management
- Use unique, descriptive bookmark names
- Validate bookmark exists before opening
- Clean up old bookmarks periodically
- Use bookmarks for frequently accessed URLs

### Data Extraction
- Verify page loaded with `get_page_title`
- Check URL with `get_current_url` before extracting
- Handle JavaScript-heavy sites carefully
- Consider rate limiting for repeated extractions

### Privacy Controls
- Use private mode for sensitive operations
- Clear browsing data after sensitive sessions
- Remember private mode doesn't hide activity from ISP
- Don't store credentials in private mode

### Performance
- Limit concurrent tabs to avoid memory issues
- Use `refresh_page` instead of re-navigation
- Close tabs when done to free resources
- Monitor browser responsiveness

### Error Handling
- Validate browser parameter ("SAFARI" or "CHROME")
- Check query parameter exists for operations requiring it
- Handle AppleScript execution errors
- Provide fallback for failed operations

## Usage Examples

### Example 1: Research and Bookmark
```
Task: "Search for Python tutorials and bookmark best result"
Operations:
1. open_tab (browser="Chrome")
2. search (query="Python advanced tutorials")
3. get_page_title (verify result quality)
4. bookmark_page
```

### Example 2: Multi-Tab Workflow
```
Task: "Open documentation in multiple tabs"
Operations:
1. navigate_to_url (query="https://docs.example.com")
2. open_url_new_tab (query="https://docs.example.com/api")
3. open_url_new_tab (query="https://docs.example.com/guides")
4. switch_to_tab (query="API")
```

### Example 3: Data Extraction
```
Task: "Extract page source from specific URL"
Operations:
1. navigate_to_url (query="https://data-site.com")
2. get_current_url (verify navigation)
3. view_source (extract HTML)
4. get_page_title (for reference)
```

### Example 4: Privacy Session
```
Task: "Browse privately and clean up"
Operations:
1. enable_private_mode (browser="Safari")
2. navigate_to_url (query="https://private-site.com")
3. close_tab (when done)
4. clear_browsing_data (optional extra cleanup)
```

### Example 5: Zoom Control
```
Task: "Adjust page zoom for better readability"
Operations:
1. get_page_title (identify current page)
2. custom_zoom (query="150%")
3. refresh_page (apply zoom)
```

## Troubleshooting

### Common Issues

**Issue:** Tab not found by title
**Solution:** Use partial matching, verify exact title with `get_page_title`

**Issue:** URL navigation fails
**Solution:** Ensure URL includes protocol (https://), check URL validity

**Issue:** Bookmark operations fail
**Solution:** Verify bookmark exists, use exact name matching

**Issue:** Source extraction returns empty
**Solution:** Wait for page load, check JavaScript-heavy sites

**Issue:** Private mode doesn't activate
**Solution:** Verify browser parameter, check browser permissions

### Platform Limitations
- macOS only (AppleScript-based implementation)
- Requires Safari or Chrome installed
- System Events access required for some operations
- AppleScript timeout may affect slow operations

### Browser-Specific Issues

**Safari:**
- Bookmark search may be slower
- Some operations require UI automation
- Private browsing creates new window

**Chrome:**
- Bookmark operations use keyboard shortcuts
- Incognito creates separate window
- May require accessibility permissions

## Advanced Automation Patterns

### Sequential Navigation
```
Loop through URLs:
1. navigate_to_url (first URL)
2. view_source (extract data)
3. navigate_to_url (next URL)
4. Repeat
```

### Tab-Based Parallelism
```
Open multiple tabs:
1. open_url_new_tab (URL 1)
2. open_url_new_tab (URL 2)
3. open_url_new_tab (URL 3)
4. switch_to_tab (process each)
```

### Bookmark-Based Workflows
```
Organize bookmarks:
1. bookmark_page (save important pages)
2. get_page_title (for reference)
3. open_bookmark (revisit later)
4. delete_bookmark (cleanup)
```

## Integration Points

### MCP Domain Orchestrator
Reports to MCP Domain Orchestrator for:
- Task routing and assignment
- Resource allocation
- Performance monitoring
- Load balancing across browsers

### File System Integration
- Downloads folder access
- File:// URL support
- Local file opening

### Search Integration
- Google Search integration (via search command)
- Bookmark-based knowledge organization

---

**Skill Version:** 1.0.0
**Last Updated:** 2026-02-04
**MCP Server:** browser (port 8172)
**Parent:** mcp-domain-orchestrator
