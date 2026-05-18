# Jarvis Workspace UI Brand Guide

Extracted from Trevor Desktop and Forex Trading Team dashboard — the two production
interfaces that define the Jarvis visual language.

## Table of Contents
- [Color System](#color-system)
- [Typography](#typography)
- [Layout System](#layout-system)
- [Component Library](#component-library)
- [State Management](#state-management)
- [SSE Real-Time Updates](#sse-real-time-updates)
- [View Architecture](#view-architecture)
- [Customization](#customization)

---

## Color System

All colors defined as CSS custom properties on `:root`. Override any value to theme a workspace.

```css
:root {
  /* Backgrounds */
  --bg:        #0d1117;    /* Page background */
  --surface:   #161b22;    /* Cards, sidebar, header */
  --surface-2: #1c2128;    /* Hover states, secondary surfaces */

  /* Borders */
  --border:    #21262d;    /* Primary borders */
  --border-2:  #30363d;    /* Secondary/hover borders */

  /* Text */
  --text:      #c9d1d9;    /* Body text */
  --text-h:    #f0f6fc;    /* Headings, emphasis */
  --muted:     #7d8590;    /* Labels, secondary text */

  /* Semantic Colors */
  --accent:    #58a6ff;    /* Links, active states, primary actions */
  --green:     #3fb950;    /* Success, live indicators, positive values */
  --green-d:   #238636;    /* Primary buttons, confirmed actions */
  --amber:     #d29922;    /* Warnings, demo mode, caution states */
  --red:       #f85149;    /* Errors, destructive actions, negative values */
  --purple:    #bc8cff;    /* Special highlights, agent indicators */

  /* Layout */
  --sidebar-w: 248px;
  --header-h:  44px;
  --radius:    6px;

  /* Fonts */
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
```

### Color Usage Rules
- **Backgrounds**: Always layer `--bg` < `--surface` < `--surface-2` (darkest to lightest)
- **Borders**: Use `--border` for structural, `--border-2` for interactive/hover
- **Semantic**: Green = positive/success, Red = negative/error, Amber = warning/caution
- **Accent**: Blue (`--accent`) is the primary interactive color — links, active nav, focus rings

---

## Typography

```css
body {
  font-family: var(--font);
  font-size: 14px;
  line-height: 1.5;
  color: var(--text);
}

/* Headings */
h1 { color: var(--text-h); font-size: 1.5rem; font-weight: 600; }
h2 { color: var(--text-h); font-size: 1.25rem; font-weight: 600; }

/* Monospace for code, data, agent output */
.mono, code, pre { font-family: var(--mono); }

/* Labels and section headers */
.section-label {
  font-size: .7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--muted);
}

/* Small text */
.small { font-size: .8rem; }
.muted { color: var(--muted); }
```

---

## Layout System

### App Shell
```
+--sidebar--+--------main-content--------+
|  logo     |  header bar                |
|  nav      |  +---------------------+   |
|  items    |  | content panels      |   |
|           |  |                     |   |
|           |  +---------------------+   |
|  user     |  status bar                |
+-----------+----------------------------+
```

### Core Layout CSS
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }

#app-view { display: flex; flex-direction: row; height: 100vh; }

#sidebar {
  width: var(--sidebar-w);
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100vh;
}

#main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
```

### Scrollbars
```css
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 2px; }
```

---

## Component Library

### Buttons
```css
/* Primary action (green) */
.btn-primary {
  background: var(--green-d);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  padding: .65rem 1rem;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
}
.btn-primary:hover { background: #2ea043; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }

/* Secondary action (surface) */
.btn-secondary {
  background: var(--surface-2);
  border: 1px solid var(--border-2);
  border-radius: var(--radius);
  color: var(--text);
  padding: .5rem .75rem;
  font-size: .85rem;
  cursor: pointer;
  transition: border-color .15s;
}
.btn-secondary:hover { border-color: var(--accent); color: var(--text-h); }
```

### Form Inputs
```css
.form-group input, .form-group textarea, .form-group select {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: .6rem .75rem;
  color: var(--text-h);
  font-size: .875rem;
  outline: none;
  transition: border-color .15s;
}
.form-group input:focus { border-color: var(--accent); }
.form-group label {
  font-size: .8rem;
  color: var(--muted);
  display: block;
  margin-bottom: .3rem;
}
```

### Cards
```css
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem;
}
```

### Auth Card (Login/Setup)
```css
.auth-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 2rem;
  width: 100%;
  max-width: 420px;
  margin: 1rem;
}
```

### Navigation Items
```css
.nav-item {
  display: flex;
  align-items: center;
  gap: .6rem;
  padding: .45rem .875rem;
  color: var(--muted);
  font-size: .85rem;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: all .12s;
}
.nav-item:hover { color: var(--text); background: rgba(255,255,255,.03); }
.nav-item.active {
  color: var(--text-h);
  background: rgba(88,166,255,.08);
  border-left-color: var(--accent);
}
```

### Tabs
```css
.tabs { display: flex; border-bottom: 1px solid var(--border); }
.tab {
  flex: 1;
  padding: .65rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  font-size: .9rem;
  cursor: pointer;
  transition: all .15s;
}
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab:hover:not(.active) { color: var(--text); }
```

### Badges
```css
.badge {
  padding: .1rem .35rem;
  border-radius: 8px;
  font-size: .65rem;
  font-weight: 600;
}
.badge-success { background: rgba(63,185,80,.15); color: var(--green); }
.badge-warning { background: rgba(210,153,34,.15); color: var(--amber); }
.badge-error   { background: rgba(248,81,73,.15); color: var(--red); }
.badge-info    { background: rgba(88,166,255,.15); color: var(--accent); }
```

### Status Indicators
```css
/* Connection dot */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--muted);
  transition: background .3s;
}
.status-dot.live {
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
}

/* Spinner */
.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

### Pulse Animations (for live/active states)
```css
@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 4px rgba(35,134,54,.3); }
  50% { box-shadow: 0 0 12px rgba(35,134,54,.7); }
}
@keyframes pulse-blue {
  0%, 100% { box-shadow: 0 0 4px rgba(88,166,255,.3); }
  50% { box-shadow: 0 0 16px rgba(88,166,255,.8); }
}
@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 4px rgba(248,81,73,.3); }
  50% { box-shadow: 0 0 12px rgba(248,81,73,.7); }
}
```

---

## State Management

### Global State Object
Every workspace UI uses a single global state object:

```javascript
const S = {
  // Auth
  token:      localStorage.getItem('ws_token'),
  user:       JSON.parse(localStorage.getItem('ws_user') || 'null'),

  // Workspace
  workspaceId:   null,
  workspaceName: null,

  // UI State
  currentView:   'loading',
  activePanel:   null,

  // Data
  agents:        {},
  tasks:         [],
  conversations: [],

  // SSE
  eventSource:   null,
  connected:     false,
};
```

### localStorage Persistence
```javascript
// Save auth state
function saveAuth(token, user) {
  S.token = token;
  S.user = user;
  localStorage.setItem('ws_token', token);
  localStorage.setItem('ws_user', JSON.stringify(user));
}

// Auto-login on localhost
if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
  // Skip login, auto-authenticate as local user
  saveAuth('local-dev-token', { name: 'Tim', role: 'admin' });
}
```

---

## SSE Real-Time Updates

### Client Setup
```javascript
function connectSSE() {
  if (S.eventSource) S.eventSource.close();

  S.eventSource = new EventSource(`/api/stream?token=${S.token}`);

  S.eventSource.onopen = () => {
    S.connected = true;
    document.querySelector('.status-dot').classList.add('live');
  };

  S.eventSource.onerror = () => {
    S.connected = false;
    document.querySelector('.status-dot').classList.remove('live');
    // Auto-reconnect after 3s
    setTimeout(connectSSE, 3000);
  };

  // Standard workspace events
  S.eventSource.addEventListener('agent_activity', (e) => {
    const data = JSON.parse(e.data);
    handleAgentActivity(data);
  });

  S.eventSource.addEventListener('task_update', (e) => {
    const data = JSON.parse(e.data);
    handleTaskUpdate(data);
  });

  S.eventSource.addEventListener('conversation', (e) => {
    const data = JSON.parse(e.data);
    handleConversation(data);
  });
}
```

### Server-Side SSE (Flask)
```python
from flask import Response, stream_with_context
import queue
import threading

# Per-client event queues
_sse_clients = []

def broadcast_event(event_type, data):
    """Send event to all connected SSE clients."""
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    dead = []
    for q in _sse_clients:
        try:
            q.put_nowait(msg)
        except:
            dead.append(q)
    for q in dead:
        _sse_clients.remove(q)

@app.route('/api/stream')
def sse_stream():
    q = queue.Queue(maxsize=100)
    _sse_clients.append(q)

    def generate():
        try:
            while True:
                msg = q.get(timeout=30)
                yield msg
        except queue.Empty:
            yield ": keepalive\n\n"
        finally:
            if q in _sse_clients:
                _sse_clients.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )
```

---

## View Architecture

### View Switching Pattern
```html
<!-- All views use .view class, only one has .active -->
<div id="loading-view" class="view active">...</div>
<div id="login-view" class="view">...</div>
<div id="setup-view" class="view">...</div>
<div id="app-view" class="view">...</div>
```

```javascript
function showView(viewId) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(viewId).classList.add('active');
  S.currentView = viewId;
}

// Boot sequence
async function boot() {
  showView('loading-view');
  if (!S.token) return showView('login-view');

  try {
    const config = await fetch('/api/config').then(r => r.json());
    S.workspaceId = config.workspace_id;
    S.workspaceName = config.workspace_name;
    connectSSE();
    showView('app-view');
  } catch (err) {
    showView('login-view');
  }
}

document.addEventListener('DOMContentLoaded', boot);
```

---

## Customization

### Theming a Workspace
Override CSS variables to create a workspace-specific theme:

```css
/* Example: Warm theme for a finance workspace */
:root {
  --accent: #d29922;    /* Gold instead of blue */
  --green: #2ea043;     /* Darker green */
}
```

### Adding Workspace-Specific Panels
```html
<!-- Add inside #main-content -->
<div id="panel-custom" class="panel" style="display:none">
  <h2>My Custom Panel</h2>
  <!-- Workspace-specific content -->
</div>
```

```javascript
// Register in navigation
const panels = {
  'dashboard': 'Dashboard',
  'agents': 'Agent Team',
  'tasks': 'Tasks',
  'custom': 'My Custom Panel',
};
```

### Mobile Responsiveness
The base template includes responsive breakpoints:
```css
@media (max-width: 768px) {
  #sidebar { display: none; }
  :root { --sidebar-w: 0px; }
}
```
