import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import LoginScreen from './components/LoginScreen.jsx';
import ChatInterface from './components/ChatInterface.jsx';

import './App.css'

// Simple auth helper
const getToken = () => localStorage.getItem('jwt');
const getUserRole = () => {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role || null;
  } catch { return null; }
};

// Protected route component
const ProtectedRoute = ({ children }) => {
  const token = getToken();
  return token ? children : <Navigate to="/login" replace />;
};

// ----- Pages -----


const Dashboard = () => {
  const role = getUserRole();
  return (
    <div className="dashboard">
      <h1>Welcome{role ? `, ${role}` : ''}!</h1>
      <nav className="nav-menu">
        <a href="/dashboard/chat">Chat</a>
        <a href="/dashboard/sql-rag">SQL RAG</a>
      </nav>
    </div>
  );
};

const ChatPage = () => {
  const [prompt, setPrompt] = React.useState('');
  const [response, setResponse] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  const handleSend = async () => {
    if (!prompt) return;
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ message: prompt }),
      });
      const data = await res.json();
      setResponse(data.response || '');
    } catch {
      setResponse('Error contacting backend');
    }
    setLoading(false);
  };

  return (
    <div className="page chat-page">
      <h2>Chat with Medibot</h2>
      <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Ask a medical question..." rows={4} />
      <button onClick={handleSend} disabled={loading} className="primary-button">{loading ? 'Thinking...' : 'Send'}</button>
      {response && <div className="response-card"><p>{response}</p></div>}
    </div>
  );
};

const SqlRagPage = () => {
  const [question, setQuestion] = React.useState('');
  const [result, setResult] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  const handleSubmit = async () => {
    if (!question) return;
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/sql_rag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ query: question }),
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setResult({ error: 'Network error' });
    }
    setLoading(false);
  };

  return (
    <div className="page sql-rag-page">
      <h2>SQL Retrieval‑Augmented Generation</h2>
      <input type="text" value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask about patient data..." />
      <button onClick={handleSubmit} disabled={loading} className="primary-button">{loading ? 'Fetching...' : 'Run'}</button>
      {result && (
        <div className="result-card">
          {result.error ? <p className="error-msg">{result.error}</p> : (
            <>
              <p><strong>SQL:</strong> {result.sql}</p>
              <p><strong>Result:</strong> {JSON.stringify(result.rows)}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
};


export default function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginScreen />} />
          <Route path="/dashboard" element={<ProtectedRoute><ChatInterface /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </>
  )
}


