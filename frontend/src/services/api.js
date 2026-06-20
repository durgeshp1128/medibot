const API_BASE = 'http://127.0.0.1:8000';

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const data = await res.json();
  if (res.ok) {
    localStorage.setItem('jwt', data.access_token);
    const payload = JSON.parse(atob(data.access_token.split('.')[1]));
    localStorage.setItem('role', payload.role);
  }
  return data;
}

export async function fetchChat(question) {
  const token = localStorage.getItem('jwt');
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ question })
  });
  return await res.json();
}

export async function fetchCollections() {
  const token = localStorage.getItem('jwt');
  const role = localStorage.getItem('role');
  const res = await fetch(`${API_BASE}/collections/${role}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` }
  });
  return await res.json();
}
