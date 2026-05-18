import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, X, Maximize2, MessageCircle, Settings, Send, Upload, File, Trash2, Terminal, FolderOpen, ChevronDown, Code } from 'lucide-react';

// File Explorer Component
const FileExplorer = ({ onFileSelect, expandedFolders, setExpandedFolders }) => {
  // Mock file structure based on the screenshot
  const fileStructure = {
    'JARVIS': {
      type: 'folder',
      children: {
        'Create': {
          type: 'folder',
          children: {}
        },
        'Data': {
          type: 'folder',
          children: {}
        },
        'Database': {
          type: 'folder',
          children: {
            '_pycache_': { type: 'folder', children: {} },
            'backups': { type: 'folder', children: {} },
            '_init_.py': { type: 'file', ext: 'py' },
            'database_interaction.py': { type: 'file', ext: 'py' },
            'database_user.py': { type: 'file', ext: 'py' },
            'db_manager.py': { type: 'file', ext: 'py' },
            'handler_user_manager.py': { type: 'file', ext: 'py' },
            'inspect_blob.py': { type: 'file', ext: 'py' },
            'task_manager.py': { type: 'file', ext: 'py' },
            'training_data.py': { type: 'file', ext: 'py' },
            'trevor_database.py': { type: 'file', ext: 'py' }
          }
        },
        'Handler': {
          type: 'folder',
          children: {
            '_pycache_': { type: 'folder', children: {} },
            'agents': { type: 'folder', children: {} },
            'configs': { type: 'folder', children: {} },
            'utils': { type: 'folder', children: {} }
          }
        }
      }
    }
  };

  const getFileIcon = (file) => {
    if (file.type === 'folder') {
      return <FolderOpen className="h-4 w-4 text-blue-400" />;
    }
    switch (file.ext) {
      case 'py':
        return <Code className="h-4 w-4 text-green-400" />;
      case 'db':
        return <File className="h-4 w-4 text-yellow-400" />;
      default:
        return <File className="h-4 w-4 text-gray-400" />;
    }
  };

  const renderTree = (structure, path = '') => {
    return Object.entries(structure).map(([name, file]) => {
      const currentPath = path ? `${path}/${name}` : name;
      const isExpanded = expandedFolders[currentPath];

      if (file.type === 'folder') {
        return (
          <div key={currentPath}>
            <button
              className="w-full flex items-center gap-2 px-2 py-1 hover:bg-gray-800 text-sm group"
              onClick={() => setExpandedFolders(prev => ({ ...prev, [currentPath]: !prev[currentPath] }))}
            >
              <ChevronDown className={`h-3 w-3 transition-transform ${isExpanded ? 'rotate-0' : '-rotate-90'}`} />
              {getFileIcon(file)}
              <span className="truncate">{name}</span>
            </button>
            {isExpanded && file.children && (
              <div className="ml-4">
                {renderTree(file.children, currentPath)}
              </div>
            )}
          </div>
        );
      }

      return (
        <button
          key={currentPath}
          className="w-full flex items-center gap-2 px-2 py-1 hover:bg-gray-800 text-sm group"
          onClick={() => onFileSelect(currentPath, file)}
        >
          {getFileIcon(file)}
          <span className="truncate">{name}</span>
        </button>
      );
    });
  };

  return (
    <div className="w-64 overflow-auto text-gray-300">
      {renderTree(fileStructure)}
    </div>
  );
};

// Terminal Component
const TerminalView = ({ output }) => {
  return (
    <div className="bg-black text-green-400 font-mono text-sm p-2 h-48 overflow-auto">
      <div className="whitespace-pre-wrap">{output}</div>
    </div>
  );
};

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const sampleMessages = [
  { role: 'assistant', content: "Hello! I'm Trevor. How can I help you today?" },
  { role: 'user', content: "Can you help me understand how databases work?" },
  { 
    role: 'assistant', 
    content: "I'll explain databases using a simple analogy and create a diagram to help visualize the concepts.",
    artifacts: [
      {
        id: 'db-diagram',
        type: 'code',
        title: 'Database Concepts',
        content: '// Example database schema\nconst UserSchema = {\n  id: "uuid",\n  name: "string",\n  email: "string",\n  created_at: "timestamp"\n};',
        error: null,
        corrections: []
      }
    ]
  }
];

const ClaudeInterface = () => {
  // All state declarations in one place
  const [messages, setMessages] = useState(sampleMessages);
  const [input, setInput] = useState('');
  const [showSidebar, setShowSidebar] = useState(true);
  const [showArtifact, setShowArtifact] = useState(true);
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [corrections, setCorrections] = useState([]);
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [showTerminal, setShowTerminal] = useState(true);
  const [terminalOutput, setTerminalOutput] = useState('$ ');
  const [expandedFolders, setExpandedFolders] = useState({
    'JARVIS': true,
    'Database': false,
    'Handler': false
  });

  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (input.trim() || uploadedFiles.length > 0) {
      setMessages([...messages, { role: 'user', content: input.trim() }]);
      setInput('');
      setUploadedFiles([]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files || event.dataTransfer.files);
    setUploadedFiles(prev => [...prev, ...files.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      name: file.name,
      size: file.size,
      type: file.type
    }))]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileUpload(e);
  };

  const removeFile = (fileId) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleArtifactClick = (artifact) => {
    setSelectedArtifact(artifact);
    setShowArtifact(true);
  };

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* File Explorer Column */}
      {showFileExplorer && (
        <div className="w-64 border-r border-gray-800 flex flex-col">
          <div className="flex items-center justify-between p-2 border-b border-gray-800">
            <h2 className="text-sm font-medium">Explorer</h2>
            <button
              onClick={() => setShowFileExplorer(false)}
              className="p-1 hover:bg-gray-800 rounded"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-auto">
            <FileExplorer
              onFileSelect={(path, file) => {
                setTerminalOutput(prev => `${prev}\n> Opening ${path}...\n`);
              }}
              expandedFolders={expandedFolders}
              setExpandedFolders={setExpandedFolders}
            />
          </div>
          {showTerminal && (
            <div className="border-t border-gray-800">
              <div className="flex items-center justify-between p-2 border-b border-gray-800">
                <h3 className="text-sm font-medium">Terminal</h3>
                <button
                  onClick={() => setShowTerminal(false)}
                  className="p-1 hover:bg-gray-800 rounded"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <TerminalView output={terminalOutput} />
            </div>
          )}
        </div>
      )}

      {/* Sidebar */}
      {showSidebar && (
        <div className="w-64 border-r border-gray-800 flex flex-col">
          <div className="p-4 border-b border-gray-800">
            <button className="w-full bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-sm font-medium">
              New Chat
            </button>
          </div>

          <nav className="flex-1 p-4 space-y-2">
            <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-800 text-sm">
              <MessageCircle className="h-4 w-4" />
              All Chats
            </button>
            <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-800 text-sm">
              <Settings className="h-4 w-4" />
              Settings
            </button>
          </nav>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex">
        <div className={`flex flex-col ${showArtifact ? 'w-1/2' : 'w-full'} transition-all duration-300`}>
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-3/4 rounded-lg p-3 ${
                    message.role === 'user' ? 'bg-blue-600' : 'bg-gray-800'
                  }`}
                >
                  <p className="text-sm">{message.content}</p>
                  {message.artifacts?.map((artifact) => (
                    <div
                      key={artifact.id}
                      onClick={() => handleArtifactClick(artifact)}
                      className="mt-2 p-2 bg-gray-700 rounded cursor-pointer hover:bg-gray-600"
                    >
                      <p className="text-xs font-medium">{artifact.title}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Input Area */}
          <div
            className={`border-t border-gray-800 p-4 ${
              isDragging ? 'bg-gray-800' : ''
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {uploadedFiles.length > 0 && (
              <div className="mb-2 space-y-1">
                {uploadedFiles.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between bg-gray-800 p-2 rounded text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <File className="h-4 w-4" />
                      <span>{file.name}</span>
                      <span className="text-gray-400">({formatFileSize(file.size)})</span>
                    </div>
                    <button
                      onClick={() => removeFile(file.id)}
                      className="p-1 hover:bg-gray-700 rounded"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-end gap-2">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message Trevor..."
                className="flex-1 bg-gray-800 rounded-lg p-3 min-h-[2.5rem] max-h-32 resize-none text-sm"
                style={{ height: 'auto' }}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2 hover:bg-gray-800 rounded"
                >
                  <Upload className="h-5 w-5" />
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() && uploadedFiles.length === 0}
                  className="p-2 bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Artifact Panel */}
        {showArtifact && (
          <div className="w-1/2 border-l border-gray-800 flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <h2 className="text-sm font-medium">
                {selectedArtifact?.title || 'Artifact View'}
              </h2>
              <button
                onClick={() => setShowArtifact(false)}
                className="p-1 hover:bg-gray-800 rounded"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 p-4 overflow-auto">
              {selectedArtifact && (
                <pre className="text-sm">
                  <code>{selectedArtifact.content}</code>
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ClaudeInterface;