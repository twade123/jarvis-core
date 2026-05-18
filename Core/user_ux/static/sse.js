/**
 * Trevor Desktop EventSource Connection Manager
 * 
 * Single consolidated EventSource (SSE) connection for Trevor Desktop UI
 * - Uses Server-Sent Events instead of Socket.IO
 * - No ping/pong mechanism (pure real-time)
 * - Single initialization point
 * - Unified error handling
 * - Maintains the same event structure as the Socket.IO implementation
 */

// Single global EventSource instance
let eventSource = null;

// Connection state tracking
let connectionState = {
    connected: false,
    connectedAt: null,
    disconnectedAt: null,
    reconnectAttempts: 0,
    serverConfirmed: false,
    lastError: null
};

// Message handlers by event type
const eventHandlers = {
    'boardroom_update': [],
    'message': [],
    'connection_confirmed': [],
    'ready_confirmed': [],
    'connection_status': [],
    'authentication_result': [],
    'workspace_list': [],
    'conversation_list': [],
    'feedback_response': []
};

/**
 * Initialize EventSource connection
 * @param {string} serverUrl - Server URL to connect to
 * @returns {EventSource} EventSource instance
 */
function initializeEventSource(serverUrl) {
    console.log("Initializing Trevor Desktop EventSource connection to:", serverUrl);
    
    // Close any existing connection
    if (eventSource) {
        try {
            eventSource.close();
            console.log("Closed existing EventSource connection");
        } catch (e) {
            console.warn("Error closing existing EventSource:", e);
        }
    }
    
    // Generate a session ID if not already available
    let session_id = localStorage.getItem('trevor_session_id');
    if (!session_id) {
        session_id = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('trevor_session_id', session_id);
    }
    
    // Create the EventSource URL with session ID
    const eventsUrl = `${serverUrl}/events?session_id=${session_id}`;
    console.log("Connecting to EventSource URL:", eventsUrl);
    
    try {
        // Create EventSource connection with session ID
        eventSource = new EventSource(eventsUrl);
        console.log("EventSource connection initiated");
        
        // Set up basic event handlers
        setupEventSourceHandlers();
        
        // Store eventSource globally for debugging
        window.eventSource = eventSource;
        window.trevorEventSource = eventSource;
        
        return eventSource;
    } catch (error) {
        console.error("Error creating EventSource connection:", error);
        return null;
    }
}

/**
 * Set up basic EventSource event handlers
 */
function setupEventSourceHandlers() {
    // Connection opened
    eventSource.onopen = function() {
        console.log("🟢 EventSource connected successfully!");
        
        // Update connection state
        connectionState.connected = true;
        connectionState.connectedAt = new Date();
        connectionState.reconnectAttempts = 0;
        
        // Update UI status
        updateConnectionStatus('connected', 'Connected to server');
        
        // Dispatch custom event for connection
        try {
            document.dispatchEvent(new CustomEvent('sseConnected', { 
                detail: { 
                    sessionId: localStorage.getItem('trevor_session_id'),
                    timestamp: Date.now()
                }
            }));
            console.log("🔔 Dispatched sseConnected event");
        } catch (e) {
            console.error("Error dispatching sseConnected event:", e);
        }
    };
    
    // Connection error with enhanced handling and exponential backoff
    eventSource.onerror = function(error) {
        console.error("🔴 EventSource error:", error);
        
        // Update connection state
        connectionState.connected = false;
        connectionState.disconnectedAt = new Date();
        connectionState.lastError = {
            time: new Date(),
            message: 'Connection error',
            type: 'event_source_error'
        };
        
        // First check if the EventSource is closed (readyState === 2)
        if (eventSource.readyState === 2) {
            console.warn("EventSource connection closed permanently");
            connectionState.reconnectAttempts++;
            
            // Update UI status
            updateConnectionStatus('error', 'Connection closed');
            
            // Immediate reconnection attempt for permanent closure
            console.log("Attempting immediate reconnection for closed connection");
            reconnectEventSource();
        } 
        // Check if it's in connecting state (readyState === 0)
        else if (eventSource.readyState === 0) {
            console.warn("EventSource is still trying to connect...");
            
            // Update UI status but maintain "connecting" state
            updateConnectionStatus('connecting', 'Connecting to server...');
            
            // Let the browser handle reconnection for connecting state
            // But set a timeout to force reconnection if it takes too long
            setTimeout(function() {
                if (eventSource.readyState !== 1) { // If not OPEN after timeout
                    console.warn("Connection attempt timed out, forcing reconnection");
                    connectionState.reconnectAttempts++;
                    reconnectEventSource();
                }
            }, 10000); // 10 second timeout for connection attempts
        }
        // Otherwise it's a temporary error during an open connection
        else {
            connectionState.reconnectAttempts++;
            
            // Update UI status
            updateConnectionStatus('error', 'Connection error - reconnecting...');
            
            // Dispatch custom event for disconnection
            try {
                document.dispatchEvent(new CustomEvent('sseDisconnected', { 
                    detail: { 
                        reason: 'Connection error',
                        timestamp: Date.now(),
                        reconnectAttempt: connectionState.reconnectAttempts
                    }
                }));
                console.log("🔔 Dispatched sseDisconnected event");
            } catch (e) {
                console.error("Error dispatching sseDisconnected event:", e);
            }
            
            // Implement exponential backoff for reconnection attempts
            const backoffTime = Math.min(1000 * Math.pow(1.5, connectionState.reconnectAttempts), 30000);
            console.log(`Reconnection attempt ${connectionState.reconnectAttempts} scheduled in ${backoffTime}ms`);
            
            // Schedule reconnection with backoff
            setTimeout(function() {
                reconnectEventSource();
            }, backoffTime);
        }
    };
    
    // Set up event listeners for specific event types
    eventSource.addEventListener('connection', function(event) {
        console.log("Received connection event:", event.data);
        const data = JSON.parse(event.data);
        
        // Update connection state
        connectionState.serverConfirmed = true;
        
        // Update session ID if provided
        if (data.session_id) {
            localStorage.setItem('trevor_session_id', data.session_id);
        }
        
        // Dispatch handlers for this event
        dispatchEventToHandlers('connection_confirmed', data);
    });
    
    // Set up event listeners for other event types
    setupEventListeners();
}

/**
 * Set up event listeners for specific event types
 */
function setupEventListeners() {
    // Set up event listeners for all known event types
    for (const eventType in eventHandlers) {
        eventSource.addEventListener(eventType, function(event) {
            // Enhanced debug logging with different icons for different event types
            if (eventType === 'boardroom_update') {
                console.log(`🔵 BOARDROOM UPDATE RECEIVED at ${new Date().toISOString()}:`, event.data);
                console.log(`🔍 Number of registered handlers: ${eventHandlers[eventType].length}`);
                try {
                    console.log("🔍 Parsed data:", JSON.parse(event.data));
                } catch (e) {
                    console.log("⚠️ Could not parse event data as JSON");
                }
            } else {
                console.log(`Received ${eventType} event:`, event.data);
            }
            
            try {
                const data = JSON.parse(event.data);
                
                // Super detailed debug for boardroom updates
                if (eventType === 'boardroom_update') {
                    console.log(`📦 SSE EVENT RECEIVED [${eventType}] (${new Date().toISOString()}):`, {
                        role: data.role || 'unknown',
                        content_preview: (data.content || '').slice(0, 50) + '...',
                        debug_info: data.debug_info || 'No debug info',
                        timestamp: data.timestamp ? new Date(data.timestamp * 1000).toISOString() : 'No timestamp',
                        message_id: data.message_id || 'No message ID'
                    });
                }
                
                dispatchEventToHandlers(eventType, data);
                
                // Special handling for boardroom messages to ensure proper UI routing
                if (eventType === 'boardroom_update') {
                    console.log("🔄 BOARDROOM_UPDATE EVENT BEING ROUTED:", JSON.stringify(data, null, 2));
                    console.debug("boardroom_update event details:", {
                        timestamp: new Date().toISOString(),
                        data: data,
                        handlers: eventHandlers[eventType].length
                    });
                    
                    // Check UI containers before routing
                    const boardroomMessages = document.querySelector('.boardroom-messages');
                    const boardroomContainer = document.querySelector('#boardroom-container');
                    const planningContainer = document.querySelector('.planning-container');
                    
                    console.log("🔍 UI CONTAINERS:", {
                        '.boardroom-messages': boardroomMessages ? 'Found' : 'Not Found',
                        '#boardroom-container': boardroomContainer ? 'Found' : 'Not Found',
                        '.planning-container': planningContainer ? 'Found' : 'Not Found'
                    });
                    
                    // Log message role for debugging
                    console.log("📝 Message role:", data.role || 'unknown');
                    
                    // Route message to container
                    routeBoardroomMessageToContainer(data);
                } else if (eventType === 'message') {
                    routeChatMessageToContainer(data);
                }
            } catch (e) {
                console.error(`Error parsing ${eventType} event data:`, e);
            }
        });
    }
}

/**
 * Route boardroom message to appropriate UI container
 * @param {object} data - Message data
 */
function routeBoardroomMessageToContainer(data) {
    try {
        // Enhanced debug logging to track message processing
        console.log("🔵 BOARDROOM MESSAGE RECEIVED:", data);
        console.debug("🔎 Processing boardroom message:", {
            messageId: data.message_id || 'unknown',
            conversationId: data.conversation_id || 'unknown',
            role: data.role || 'unknown',
            contentLength: data.content ? data.content.length : 0,
            timestamp: new Date().toISOString()
        });
        
        // Extract message properties
        const role = data.role || 'system';
        const content = data.content || '';
        const messageId = data.message_id || `msg_${Date.now()}`;
        const conversationId = data.conversation_id || 'default';
        
        // Get or create conversation container
        let container = document.querySelector('.boardroom-messages');
        if (!container) {
            // Fallback to boardroom-container
            container = document.querySelector('#boardroom-container');
            if (!container) {
                // Second fallback to planning-container
                container = document.querySelector('.planning-container');
                if (!container) {
                    console.warn("Boardroom container not found in DOM, message may not display properly");
                    return;
                }
            }
        }
        
        // Create message element
        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = `boardroom-message ${role}-message`;
        
        // Handle different role types
        let roleDisplay = role;
        if (role.toLowerCase().includes('claude')) {
            roleDisplay = 'Claude';
            messageElement.classList.add('claude-message');
        } else if (role.toLowerCase().includes('gpt')) {
            roleDisplay = 'GPT';
            messageElement.classList.add('gpt-message');
        } else if (role === 'system') {
            roleDisplay = 'System';
            messageElement.classList.add('system-message');
        } else if (role === 'user') {
            roleDisplay = 'You';
            messageElement.classList.add('user-message');
        } else if (role === 'assistant') {
            roleDisplay = 'Trevor';
            messageElement.classList.add('trevor-message');
        }
        
        // Set message content
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="message-role">${roleDisplay}</span>
                <span class="message-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="message-content">${formatMessageContent(content)}</div>
        `;
        
        // Add to container
        container.appendChild(messageElement);
        
        // Debug log for successful message addition
        console.log(`🟢 Added ${role} message to container:`, container.className || container.id);
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        
        console.log(`✅ Routed boardroom message to planning container: ${messageId}`);
        console.debug("🏁 Completed boardroom message rendering:", {
            messageId: messageId,
            container: container.className || container.id,
            role: role,
            success: true,
            timestamp: new Date().toISOString()
        });
    } catch (e) {
        console.error("Error routing boardroom message to container:", e);
    }
}

/**
 * Route chat message to appropriate UI container
 * @param {object} data - Message data
 */
function routeChatMessageToContainer(data) {
    try {
        // Extract message properties
        const role = data.role || 'system';
        const content = data.content || '';
        const messageId = data.message_id || `msg_${Date.now()}`;
        
        // Get message container
        let container = document.querySelector('.message-container');
        if (!container) {
            console.warn("Message container not found in DOM, message may not display properly");
            return;
        }
        
        // Create message element
        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = `message ${role}-message`;
        
        // Handle different role types
        let roleDisplay = role;
        if (role === 'user') {
            roleDisplay = 'You';
        } else if (role === 'assistant') {
            roleDisplay = 'Trevor';
        } else if (role === 'system') {
            roleDisplay = 'System';
        }
        
        // Set message content
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="message-role">${roleDisplay}</span>
                <span class="message-time">${new Date().toLocaleTimeString()}</span>
            </div>
            <div class="message-content">${formatMessageContent(content)}</div>
        `;
        
        // Add to container
        container.appendChild(messageElement);
        
        // Debug log for successful message addition
        console.log(`🟢 Added ${role} message to container:`, container.className || container.id);
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        
        console.log(`✅ Routed chat message to message container: ${messageId}`);
    } catch (e) {
        console.error("Error routing chat message to container:", e);
    }
}

/**
 * Format message content with proper styling
 * @param {string} content - Message content
 * @returns {string} Formatted content
 */
function formatMessageContent(content) {
    // Simple formatting for code blocks
    let formattedContent = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Convert newlines to <br> tags
    formattedContent = formattedContent.replace(/\n/g, '<br>');
    
    return formattedContent;
}

/**
 * Dispatch event data to registered handlers for a specific event type
 * @param {string} eventType - Event type
 * @param {object} data - Event data
 */
function dispatchEventToHandlers(eventType, data) {
    if (eventHandlers[eventType]) {
        for (const handler of eventHandlers[eventType]) {
            try {
                handler(data);
            } catch (e) {
                console.error(`Error in ${eventType} handler:`, e);
            }
        }
    }
}

/**
 * Reconnect EventSource with enhanced error handling
 */
function reconnectEventSource() {
    // Update UI to show reconnection attempt
    updateConnectionStatus('connecting', `Reconnecting (attempt ${connectionState.reconnectAttempts})...`);
    
    // Close existing connection if any
    if (eventSource) {
        try {
            // Check if it's not already closed
            if (eventSource.readyState !== 2) {
                console.log("Closing existing EventSource connection before reconnecting");
                eventSource.close();
            }
        } catch (e) {
            console.warn("Error closing EventSource:", e);
        }
    }
    
    // Reset event handlers to prevent duplicate handlers
    eventSource = null;
    
    // Log reconnection attempt
    console.log(`Reconnection attempt ${connectionState.reconnectAttempts} starting...`);
    
    try {
        // Create new EventSource connection
        const serverUrl = window.location.origin;
        console.log(`Reconnecting to ${serverUrl}`);
        
        // Create new EventSource with different timestamp to avoid caching
        const newEventSource = initializeEventSource(serverUrl);
        
        // Add special one-time handler to confirm successful reconnection
        if (newEventSource) {
            // Set a timeout to check if connection succeeded
            setTimeout(function() {
                if (eventSource && eventSource.readyState === 1) {
                    console.log("✅ Reconnection successful!");
                    // Reset reconnect attempts on successful connection
                    connectionState.reconnectAttempts = 0;
                } else if (connectionState.reconnectAttempts < 10) {
                    console.warn("❌ Reconnection attempt failed, will retry");
                    // The onerror handler will schedule another reconnection attempt
                } else {
                    console.error("⛔ Maximum reconnection attempts reached");
                    updateConnectionStatus('error', 'Failed to reconnect - please refresh the page');
                    
                    // Show a manual reconnect button
                    const reconnectButton = document.getElementById('reconnect');
                    if (reconnectButton) {
                        reconnectButton.style.display = 'inline-block';
                    }
                }
            }, 3000);
        } else {
            console.error("Failed to create new EventSource connection");
            updateConnectionStatus('error', 'Connection failed');
        }
    } catch (error) {
        console.error("Error during reconnection:", error);
        updateConnectionStatus('error', 'Connection failed');
        
        // Schedule another attempt with exponential backoff if under max attempts
        if (connectionState.reconnectAttempts < 10) {
            const backoffTime = Math.min(1000 * Math.pow(2, connectionState.reconnectAttempts), 30000);
            console.log(`Scheduling another reconnection attempt in ${backoffTime}ms`);
            
            setTimeout(function() {
                reconnectEventSource();
            }, backoffTime);
        }
    }
}

/**
 * Update connection status in UI
 * @param {string} status - Connection status
 * @param {string} message - Status message
 */
function updateConnectionStatus(status, message) {
    const statusTextElement = document.querySelector('.connection-indicator .status-text');
    const dotElement = document.querySelector('.connection-indicator .dot');
    
    if (statusTextElement) {
        statusTextElement.textContent = message || status;
    }
    
    if (dotElement) {
        // Remove all status classes
        dotElement.classList.remove('connected', 'disconnected', 'error');
        
        // Add the current status class
        dotElement.classList.add(status);
    }
    
    // Update connection indicator container
    const indicatorElement = document.querySelector('.connection-indicator');
    if (indicatorElement) {
        // Remove all status classes
        indicatorElement.classList.remove('connected', 'disconnected', 'error');
        
        // Add the current status class
        indicatorElement.classList.add(status);
    }
}

/**
 * Add event listener for a specific event type
 * @param {string} eventType - Event type
 * @param {function} callback - Event handler
 */
function on(eventType, callback) {
    if (!eventHandlers[eventType]) {
        eventHandlers[eventType] = [];
    }
    
    eventHandlers[eventType].push(callback);
}

/**
 * Send a message to the server
 * @param {string} eventType - Event type
 * @param {object} data - Message data
 */
function emit(eventType, data) {
    // Get session ID and auth token
    const session_id = localStorage.getItem('trevor_session_id');
    const auth_token = localStorage.getItem('trevor_session_id') || localStorage.getItem('trevor_auth_token');
    
    // Add session ID to data
    const payload = {
        ...data,
        session_id,
        timestamp: Date.now()
    };
    
    // Prepare headers with authentication
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // Add authorization header if we have an auth token
    if (auth_token) {
        headers['Authorization'] = `Bearer ${auth_token}`;
    }
    
    // Send via HTTP POST to /api/send
    fetch('/api/send', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
            event_type: eventType,
            data: payload
        })
    })
    .then(response => response.json())
    .then(result => {
        console.log(`Sent ${eventType} event:`, result);
    })
    .catch(error => {
        console.error(`Error sending ${eventType} event:`, error);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log("Initializing Trevor Desktop EventSource connection");
    
    // Short delay to ensure page is fully loaded
    setTimeout(function() {
        initializeEventSource(window.location.origin);
        
        // Update UI with connection status
        const statusTextElement = document.querySelector('.connection-indicator .status-text');
        if (statusTextElement) {
            statusTextElement.textContent = 'Connecting to server...';
        }
        
        console.log("EventSource initialization triggered with delay");
    }, 500);
    
    // Define the setupSSEHandlers function that's called in HTML
    window.setupSSEHandlers = function() {
        console.log("Setting up SSE event handlers from HTML");
        
        // If eventSource is not yet initialized, initialize it
        if (!eventSource) {
            console.log("EventSource not initialized yet, initializing from setupSSEHandlers");
            initializeEventSource(window.location.origin);
        }
    };
    
    // Socket.io handler backward compatibility removed
});

// Create a full SSE API
window.trevorSSE = {
    // Core functions
    initialize: initializeEventSource,
    reconnect: reconnectEventSource,
    
    // Event handling
    on: on,
    emit: emit,
    
    // Connection management
    disconnect: function() {
        if (eventSource) {
            eventSource.close();
        }
    },
    
    // Status information
    getStatus: function() {
        return {
            connected: eventSource && eventSource.readyState === 1,
            readyState: eventSource ? eventSource.readyState : -1,
            connectionState: connectionState
        };
    },
    
    // Session ID
    sessionId: localStorage.getItem('trevor_session_id')
};

// Socket.io compatibility layer has been removed

// Make functions available globally
window.initializeEventSource = initializeEventSource;
window.reconnectEventSource = reconnectEventSource;