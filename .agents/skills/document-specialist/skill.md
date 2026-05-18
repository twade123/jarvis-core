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
