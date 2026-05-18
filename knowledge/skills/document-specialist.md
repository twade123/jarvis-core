---
name: document-specialist
description: Specialist agent with complete mastery of document MCP tools. Handles document operations including reading, writing, format conversion, and content extraction across Pages and Microsoft Word.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
triggers:
  - "read document"
  - "create document"
  - "pdf"
  - "word document"
  - "pages document"
  - "export document"
capabilities:
  - document_reading
  - document_writing
  - format_conversion
  - content_extraction
  - document_collaboration
mcp_server: document
mcp_port: 8140
parent_orchestrator: mcp-domain-orchestrator
---

# Document Specialist Agent

Complete mastery of document MCP operations for Pages and Microsoft Word.

## MCP Overview

**Server:** document
**Port:** 8140
**Type:** Handler MCP (Jarvis-native)
**Handler:** `handle_document_creation_intent` (function-based)
**Platform:** macOS (Pages native, Word cross-platform)

The Document MCP provides comprehensive document management capabilities across Apple Pages and Microsoft Word, enabling document creation, editing, formatting, and export operations.

## Available Tools

### Document Lifecycle Management

#### create_document
Create new document in specified application.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "create_document"

**Usage:** "Create new document in Pages"

#### open_document
Open existing document by search query or file path.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "open_document"
- `search_query`: Document name to search
- `file_path`: Direct path to document

**Usage:** "Open document 'report.pages' in Pages"

#### save_document
Save current document.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "save_document"

**Usage:** "Save current document in Word"

#### close_document
Close current document with save option.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "close_document"

**Usage:** "Close document in Pages"

### Format Conversion & Export

#### export_pdf
Export document to PDF format.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "export_pdf"
- `file_path`: Export destination path

**Usage:** "Export document to PDF at '/path/to/file.pdf' in Word"

### Content Operations

#### insert_image
Insert image into document from file path.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "insert_image"
- `search_query`: Image name to search
- `file_path`: Direct path to image file

**Usage:** "Insert image '/path/to/photo.png' in document"

#### insert_table
Insert table into document.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "insert_table"

**Usage:** "Insert 3x3 table in Pages document"
**Note:** Default creates 3 rows × 3 columns table

### Document Properties Management

#### set_document_title
Set document title/name.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "set_document_title"
- `search_query`: New document title

**Usage:** "Set document title to 'Q4 Report' in Word"

#### get_document_properties
Retrieve document metadata (name, path).

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "get_document_properties"

**Returns:** Document name and file path
**Usage:** "Get document properties from Pages"

### Search & Navigation

#### search_document
Search for text within document.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "search_document"
- `search_query`: Text to search for

**Usage:** "Search for 'revenue' in document"
**Note:** Opens find dialog in Pages, executes find in Word

### Collaboration Features

#### add_comment
Add comment at current selection.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "add_comment"
- `search_query`: Comment text

**Usage:** "Add comment 'Review this section' in document"

#### enable_track_changes
Enable track changes mode for collaborative editing.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "enable_track_changes"

**Usage:** "Enable track changes in Word"

#### disable_track_changes
Disable track changes mode.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "disable_track_changes"

**Usage:** "Disable track changes in Pages"

### Document Actions

#### print_document
Print current document.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "print_document"

**Usage:** "Print document in Pages"

#### duplicate_document
Create duplicate of current document.

**Parameters:**
- `app`: "Pages" or "Microsoft Word"
- `command`: "duplicate_document"

**Usage:** "Duplicate document in Word"

## Common Workflows

### Create and Export Workflow
```
1. create_document (app="Pages")
2. insert_image (file_path="/path/to/logo.png")
3. insert_table (3x3 table)
4. set_document_title (title="Report")
5. save_document
6. export_pdf (file_path="/path/to/report.pdf")
```

### Collaborative Editing Workflow
```
1. open_document (search_query="proposal.docx")
2. enable_track_changes
3. add_comment (text="Review pricing section")
4. search_document (query="pricing")
5. save_document
```

### Document Review Workflow
```
1. open_document (file_path="/path/to/draft.pages")
2. get_document_properties (check metadata)
3. search_document (query="TODO")
4. add_comment (text="Address TODOs before final")
5. duplicate_document (create backup)
6. close_document
```

## Supported Formats

### Input Formats
- **Pages:** .pages (native)
- **Word:** .docx, .doc
- **Search:** Filename-based search via Finder integration

### Output Formats
- **PDF:** Full export capability with formatting preservation
- **Native:** .pages (Pages), .docx (Word)

### Image Formats
- PNG, JPEG, TIFF, GIF (standard image formats)
- File path or search query based insertion

## Content Extraction

### Metadata Extraction
Use `get_document_properties` to retrieve:
- Document name
- File path
- Application-specific metadata

### Text Search
Use `search_document` to locate:
- Specific terms
- Section headers
- Content markers (TODO, FIXME, etc.)

## Best Practices

### File Path Management
- Use absolute paths for reliability
- Validate file existence before operations
- Use search_query for user-friendly filename lookup
- Leverage Finder integration for file discovery

### Application Selection
- **Pages:** Native macOS, best for Apple ecosystem
- **Word:** Cross-platform compatibility, enterprise standard
- Both support same core operations (create, save, export, insert)

### Collaboration
- Enable track changes before collaborative editing
- Add comments for review points
- Use descriptive comment text for clarity
- Disable track changes after collaboration complete

### Export Operations
- Specify explicit file paths for exports
- Use PDF for universal compatibility
- Verify export path is writable
- Consider filename conflicts

### Error Handling
- Validate app parameter ("Pages" or "Microsoft Word")
- Check file_path exists for open operations
- Provide search_query or file_path for file operations
- Handle missing required parameters gracefully

### Performance
- Search operations may take time with large document sets
- PDF export depends on document complexity
- Use duplicate_document before destructive operations

## Usage Examples

### Example 1: Quick Document Creation
```
Task: "Create a new report in Pages with a table"
Operations:
1. create_document (app="Pages")
2. set_document_title (search_query="Q4 Report")
3. insert_table (creates 3x3 table)
4. save_document
```

### Example 2: Document Review and Export
```
Task: "Open proposal, add comments, export to PDF"
Operations:
1. open_document (app="Word", search_query="proposal.docx")
2. enable_track_changes
3. search_document (search_query="budget")
4. add_comment (search_query="Verify budget numbers")
5. save_document
6. export_pdf (file_path="/Documents/proposal.pdf")
```

### Example 3: Image Insertion
```
Task: "Insert logo into current document"
Operations:
1. insert_image (app="Pages", file_path="/path/to/logo.png")
   OR
1. insert_image (app="Pages", search_query="company_logo")
```

## Troubleshooting

### Common Issues

**Issue:** Document not found
**Solution:** Use file_path with absolute path instead of search_query

**Issue:** Export fails
**Solution:** Verify export path exists and is writable

**Issue:** Track changes not visible
**Solution:** Ensure application supports track changes (both do)

**Issue:** Search not working
**Solution:** Provide search_query parameter with text to find

### Platform Limitations
- macOS only (AppleScript-based implementation)
- Requires Pages or Microsoft Word installed
- Finder integration required for search operations
- System Events access required for some operations

## Integration Points

### MCP Domain Orchestrator
Reports to MCP Domain Orchestrator for:
- Task routing and assignment
- Resource allocation
- Performance monitoring

### File System Integration
- Finder search integration
- Document folder access
- Downloads folder management
- Absolute path resolution

### Collaboration Integration
- Track changes system
- Comment management
- Version control support (via duplicates)

---

**Skill Version:** 1.0.0
**Last Updated:** 2026-02-04
**MCP Server:** document (port 8140)
**Parent:** mcp-domain-orchestrator

<!-- merged from skills/browser-specialist.md -->
name: browser-specialist
description: Specialist agent with complete mastery of browser MCP tools. Handles web automation, data extraction, navigation, and web scraping operations across Safari and Chrome browsers.
  - "browse web"
  - "scrape website"
  - "web automation"
  - "extract data"
  - "open browser"
  - "search web"
  - web_navigation
  - data_extraction
  - tab_management
  - bookmark_management
  - web_scraping
  - browser_automation
mcp_server: browser
mcp_port: 8172
# Browser Specialist Agent
Complete mastery of browser MCP operations for Safari and Chrome web automation.
**Server:** browser
**Port:** 8172
**Handler:** `handle_browser_intent` (function-based)
**Platform:** macOS (Safari native, Chrome cross-platform)
The Browser MCP provides comprehensive web automation and browser control capabilities across Safari and Chrome, enabling tab management, navigation, bookmarking, content access, and privacy controls.
### Tab Management Operations
#### open_tab
Create new tab in browser window.
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_tab"
**Usage:** "Open new tab in Chrome"
#### close_tab
Close current active tab.
- `browser`: "SAFARI" or "CHROME"
- `command`: "close_tab"
**Usage:** "Close current tab in Safari"
#### close_tab_by_title
Close tab matching specific title.
- `browser`: "SAFARI" or "CHROME"
- `command`: "close_tab_by_title"
- `query`: Tab title to match (partial match supported)
**Usage:** "Close tab with 'Gmail' in title"
#### switch_to_tab
Switch to tab matching specific title.
- `browser`: "SAFARI" or "CHROME"
- `command`: "switch_to_tab"
- `query`: Tab title to match
**Usage:** "Switch to tab containing 'GitHub'"
#### duplicate_tab
Create duplicate of current tab with same URL.
- `browser`: "SAFARI" or "CHROME"
- `command`: "duplicate_tab"
**Usage:** "Duplicate current tab in Chrome"
#### open_url_new_tab
Open URL in new tab.
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_url_new_tab"
- `query`: URL to open
**Usage:** "Open https://example.com in new tab"
### Navigation Operations
#### search
Execute web search via Google.
- `browser`: "SAFARI" or "CHROME"
- `command`: "search"
- `query`: Search terms
**Usage:** "Search for 'Claude AI features' in Safari"
#### navigate_to_url
Navigate current tab to specific URL.
- `browser`: "SAFARI" or "CHROME"
- `command`: "navigate_to_url"
- `query`: URL to navigate to
**Usage:** "Navigate to https://anthropic.com"
#### refresh_page
Reload current page.
- `browser`: "SAFARI" or "CHROME"
- `command`: "refresh_page"
**Usage:** "Refresh page in Chrome"
#### go_forward
Navigate forward in browser history.
- `browser`: "SAFARI" or "CHROME"
- `command`: "go_forward"
**Usage:** "Go forward in Safari"
#### go_backward
Navigate backward in browser history.
- `browser`: "SAFARI" or "CHROME"
- `command`: "go_backward"
**Usage:** "Go back in Chrome"
### Bookmark Management
#### bookmark_page
Add current page to bookmarks.
- `browser`: "SAFARI" or "CHROME"
- `command`: "bookmark_page"
**Usage:** "Bookmark current page in Safari"
**Note:** Safari adds to bookmarks bar, Chrome uses Cmd+D
#### delete_bookmark
Remove bookmark by name.
- `browser`: "SAFARI" or "CHROME"
- `command`: "delete_bookmark"
- `query`: Bookmark name to delete
**Usage:** "Delete bookmark named 'Old Project'"
#### open_bookmark
Open bookmark by name.
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_bookmark"
- `query`: Bookmark name to open
**Usage:** "Open bookmark 'Dashboard'"
### Content Access
#### get_current_url
Retrieve URL of current tab.
- `browser`: "SAFARI" or "CHROME"
- `command`: "get_current_url"
**Returns:** Current page URL
**Usage:** "Get current URL from Safari"
#### get_page_title
Retrieve title of current page.
- `browser`: "SAFARI" or "CHROME"
- `command`: "get_page_title"
**Returns:** Current page title
**Usage:** "Get page title from Chrome"
#### view_source
View HTML source code of current page.
- `browser`: "SAFARI" or "CHROME"
- `command`: "view_source"
**Returns:** Full HTML source
**Usage:** "View source of current page"
### Browser Settings & Controls
#### zoom_in
Increase page zoom to 120%.
- `browser`: "SAFARI" or "CHROME"
- `command`: "zoom_in"
**Usage:** "Zoom in on page"
#### zoom_out
Decrease page zoom to 80%.
- `browser`: "SAFARI" or "CHROME"
- `command`: "zoom_out"
**Usage:** "Zoom out on page"
#### custom_zoom
Set custom zoom level.
- `browser`: "SAFARI" or "CHROME"
- `command`: "custom_zoom"
- `query`: Zoom level (e.g., "150" or "150%")
**Usage:** "Set zoom to 150% in Chrome"
### Privacy & Security Controls
#### enable_private_mode
Enable private/incognito browsing.
- `browser`: "SAFARI" or "CHROME"
- `command`: "enable_private_mode"
**Usage:** "Enable private browsing in Safari"
**Note:** Safari calls it "private", Chrome calls it "incognito"
#### enable_incognito_mode
Chrome-specific alias for private mode.
- `browser`: "CHROME"
- `command`: "enable_incognito_mode"
**Usage:** "Enable incognito mode in Chrome"
#### clear_browsing_data
Clear browser history and cache.
- `browser`: "SAFARI" or "CHROME"
- `command`: "clear_browsing_data"
**Usage:** "Clear browsing data in Safari"
**Note:** Requires System Events access, opens settings UI
### File Management
#### open_downloads
Open downloads folder.
- `browser`: "SAFARI" or "CHROME"
- `command`: "open_downloads"
**Usage:** "Open downloads folder"
**Note:** Opens Finder to downloads directory
### Web Research Workflow
1. open_tab (browser="Safari")
2. search (query="Claude AI capabilities")
3. bookmark_page (save interesting result)
4. open_url_new_tab (query="https://anthropic.com")
5. get_page_title (verify page loaded)
### Multi-Tab Organization Workflow
1. get_page_title (identify current tab)
2. duplicate_tab (create working copy)
3. open_url_new_tab (query="https://docs.example.com")
4. switch_to_tab (query="Documentation")
5. close_tab_by_title (query="Old Tab")
### Data Extraction Workflow
1. navigate_to_url (query="https://data.example.com")
2. get_current_url (verify navigation)
3. view_source (extract HTML)
4. get_page_title (confirm data page)
5. bookmark_page (save for later reference)
### Privacy-Conscious Browsing Workflow
1. enable_private_mode (browser="Chrome")
2. navigate_to_url (query="https://sensitive-site.com")
3. get_current_url (verify in private mode)
4. close_tab (close when done)
5. clear_browsing_data (optional cleanup)
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
Operation: view_source
Returns: Complete HTML document as string
Use Cases:
- Scraping structured data
- Analyzing page structure
- Extracting metadata
- Debugging web issues
### URL Pattern Extraction
Operation: get_current_url
Returns: Current page URL
Use Cases:
- Tracking navigation state
- Capturing final redirect URLs
- Verifying page identity
- Building URL collections
### Title-Based Data
Operation: get_page_title
Returns: Page title string
Use Cases:
- Identifying page content
- Tab organization
- Search result validation
- Bookmark naming
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
- Limit concurrent tabs to avoid memory issues
- Use `refresh_page` instead of re-navigation
- Close tabs when done to free resources
- Monitor browser responsiveness
- Validate browser parameter ("SAFARI" or "CHROME")
- Check query parameter exists for operations requiring it
- Handle AppleScript execution errors
- Provide fallback for failed operations
### Example 1: Research and Bookmark
Task: "Search for Python tutorials and bookmark best result"
1. open_tab (browser="Chrome")
2. search (query="Python advanced tutorials")
3. get_page_title (verify result quality)
4. bookmark_page
### Example 2: Multi-Tab Workflow
Task: "Open documentation in multiple tabs"
1. navigate_to_url (query="https://docs.example.com")
2. open_url_new_tab (query="https://docs.example.com/api")
3. open_url_new_tab (query="https://docs.example.com/guides")
4. switch_to_tab (query="API")
### Example 3: Data Extraction
Task: "Extract page source from specific URL"
1. navigate_to_url (query="https://data-site.com")
2. get_current_url (verify navigation)
3. view_source (extract HTML)
4. get_page_title (for reference)
### Example 4: Privacy Session
Task: "Browse privately and clean up"
1. enable_private_mode (browser="Safari")
2. navigate_to_url (query="https://private-site.com")
3. close_tab (when done)
4. clear_browsing_data (optional extra cleanup)
### Example 5: Zoom Control
Task: "Adjust page zoom for better readability"
1. get_page_title (identify current page)
2. custom_zoom (query="150%")
3. refresh_page (apply zoom)
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
- Requires Safari or Chrome installed
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
Loop through URLs:
1. navigate_to_url (first URL)
2. view_source (extract data)
3. navigate_to_url (next URL)
4. Repeat
### Tab-Based Parallelism
Open multiple tabs:
1. open_url_new_tab (URL 1)
2. open_url_new_tab (URL 2)
3. open_url_new_tab (URL 3)
4. switch_to_tab (process each)
### Bookmark-Based Workflows
Organize bookmarks:
1. bookmark_page (save important pages)
2. get_page_title (for reference)
3. open_bookmark (revisit later)
4. delete_bookmark (cleanup)
- Load balancing across browsers
- Downloads folder access
- File:// URL support
- Local file opening
### Search Integration
- Google Search integration (via search command)
- Bookmark-based knowledge organization
**MCP Server:** browser (port 8172)
