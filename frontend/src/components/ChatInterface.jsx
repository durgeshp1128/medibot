import React, { useState, useEffect } from 'react';
//import './ChatInterface.css';
import { fetchChat, fetchCollections } from '../services/api';

export default function ChatInterface() {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState('');
  const [collections, setCollections] = useState([]);

  useEffect(() => {
    const storedRole = localStorage.getItem('role');
    if (storedRole) setRole(storedRole);
    // fetch allowed collections for the role
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

  const handleSend = async () => {
    if (!prompt) return;
    setLoading(true);
    try {
      const data = await fetchChat(prompt);
      setResponse(data);
    } catch (e) {
      setResponse({ error: 'Network error' });
    } finally {
      setLoading(false);
    }
  };

  const renderSources = (sources) => (
    <ul className="sources-list">
      {sources.map((src, idx) => (
        <li key={idx}>
          <strong>{src.document_name || src.source_document}</strong> – {src.section_title || src.collection}
        </li>
      ))}
    </ul>
  );

  return (
    <div className="chat-interface">
      <header className="chat-header">
        <div className="role-badge">Role: {role || 'guest'}</div>
        <div className="collections-sidebar">
          <h4>Accessible Collections</h4>
          <ul>
            {collections.map((c, i) => (<li key={i}>{c}</li>))}
          </ul>
        </div>
      </header>
      <section className="chat-body">
        {response && response.error && (
          <div className="error-msg">{response.error}</div>
        )}
        {response && response.blocked && (
          <div className="blocked-msg">{response.blocked}</div>
        )}
        {response && response.answer && (
          <div className="answer-card">
            <p>{response.answer}</p>
            {response.retrieval_type && (
              <span className="retrieval-label">{response.retrieval_type}</span>
            )}
            {response.sources && renderSources(response.sources)}
          </div>
        )}
      </section>
      <footer className="chat-footer">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask MediBot..."
          rows={3}
        />
        <button onClick={handleSend} disabled={loading} className="send-btn">
          {loading ? 'Thinking…' : 'Send'}
        </button>
      </footer>
    </div>
  );
}
