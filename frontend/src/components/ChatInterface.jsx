import React, { useState, useEffect, useRef } from 'react';
import './ChatInterface.css';
import { fetchChat, fetchCollections } from '../services/api';

export default function ChatInterface() {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: 'Welcome to MediBot AI! I can assist you with clinical guidelines, billing queries, and maintenance manual lookups. How can I help you today?',
      retrieval_type: 'system',
      sources: []
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState('');
  const [collections, setCollections] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const storedRole = localStorage.getItem('role');
    if (storedRole) setRole(storedRole);
    
    const loadCollections = async () => {
      try {
        const data = await fetchCollections();
        setCollections(data.collections || []);
      } catch (e) {
        console.error('Failed to load collections', e);
      }
    };
    loadCollections();
  }, []);

  useEffect(() => {
    // Auto scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!prompt.trim()) return;
    const userPrompt = prompt.trim();
    setPrompt('');
    
    // Add user message to state
    setMessages(prev => [...prev, { sender: 'user', text: userPrompt }]);
    setLoading(true);
    
    try {
      const data = await fetchChat(userPrompt);
      setMessages(prev => [...prev, {
        sender: 'bot',
        text: data.answer || data.response || 'No response generated.',
        sources: data.sources || [],
        retrieval_type: data.retrieval_type || 'hybrid_rag',
        blocked: data.blocked,
        error: data.error
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        sender: 'bot',
        text: 'Error communicating with the medical brain.',
        error: 'Network Error'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('jwt');
    localStorage.removeItem('role');
    window.location.href = '/login';
  };

  return (
    <div className="chat-container">
      {/* Left Sidebar */}
      <div className="chat-sidebar">
        <div className="brand-section">
          <svg className="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2v20M2 12h20" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="brand-name">MediBot AI</span>
        </div>
        
        <div className="profile-section">
          <div className="avatar">
            {role ? role[0].toUpperCase() : 'G'}
          </div>
          <div className="profile-info">
            <div className="profile-role">{role ? role.replace('_', ' ').toUpperCase() : 'GUEST'}</div>
            <div className="profile-status">Authorized Access</div>
          </div>
        </div>

        <div className="sidebar-menu">
          <div className="menu-header">Accessible Collections</div>
          <ul className="collections-list">
            {collections.map((c, i) => (
              <li key={i} className="collection-item">
                <svg className="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {c.charAt(0).toUpperCase() + c.slice(1)} Collection
              </li>
            ))}
            {collections.length === 0 && <li className="no-collections">No collections found</li>}
          </ul>
        </div>

        <button onClick={handleLogout} className="logout-btn">
          <svg className="logout-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Log Out
        </button>
      </div>

      {/* Right Chat Section */}
      <div className="chat-main">
        <header className="chat-main-header">
          <div className="header-info">
            <h2>Clinical Knowledge Assistant</h2>
            <p>MediAssist Health Network Secure RAG Pipeline</p>
          </div>
          <div className="status-indicator">
            <span className="pulse-dot"></span>
            System Online
          </div>
        </header>

        <div className="messages-container">
          {messages.map((msg, index) => (
            <div key={index} className={`message-wrapper ${msg.sender}-wrapper`}>
              <div className={`message-bubble ${msg.sender}-bubble`}>
                <div className="message-text">{msg.text}</div>
                
                {msg.sender === 'bot' && (
                  <>
                    {msg.retrieval_type && (
                      <div className={`retrieval-badge badge-${msg.retrieval_type}`}>
                        {msg.retrieval_type.toUpperCase().replace('_', ' ')}
                      </div>
                    )}
                    
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="sources-container">
                        <div className="sources-header">
                          <svg className="source-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                          </svg>
                          Citations:
                        </div>
                        <ul className="sources-list">
                          {msg.sources.map((src, idx) => (
                            <li key={idx} className="source-item">
                              <span className="doc-name">{src.source_document || src.source_document}</span>
                              {src.section_title && (
                                <span className="doc-section"> - {src.section_title}</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message-wrapper bot-wrapper">
              <div className="message-bubble bot-bubble loading-bubble">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <div className="input-wrapper">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask MediBot clinical, policy, or hardware manual questions..."
              rows={1}
            />
            <button onClick={handleSend} disabled={loading || !prompt.trim()} className="send-button">
              <svg className="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
