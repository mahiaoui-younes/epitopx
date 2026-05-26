# 🎨 GUIDE FRONTEND - Intégration des 4 Endpoints

## 📋 Table des matières

1. [Installation & Configuration](#installation)
2. [Endpoint 1: Lister proteins publics](#endpoint-1)
3. [Endpoint 2: Analyser epitopes](#endpoint-2)
4. [Endpoint 3: Dashboard personnel](#endpoint-3)
5. [Endpoint 4: Admin panel](#endpoint-4)
6. [Examples complets](#examples)

---

## 🔧 Installation & Configuration {#installation}

### Base URL
```javascript
const API_BASE = 'http://localhost:8000/api';
```

### Helper Function - Requête avec Token
```javascript
async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('userToken');
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Token ${token}` }),
    ...options.headers
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
```

---

## 📚 Endpoint 1: Lister Proteins Publics {#endpoint-1}

### Public List - Afficher tous les proteins publics (SANS TOKEN)

```javascript
// ✅ PUBLIQUE - Aucune authentification requise
async function loadPublicProteins() {
  try {
    const data = await fetch(`${API_BASE}/proteins/public_list/`)
      .then(r => r.json());
    
    console.log(`Found ${data.count} public proteins`);
    
    // Afficher les proteins
    displayProteins(data.results);
    
    return data.results;
  } catch (error) {
    console.error('Error loading proteins:', error);
  }
}

function displayProteins(proteins) {
  const container = document.getElementById('proteins-list');
  
  proteins.forEach(protein => {
    const card = document.createElement('div');
    card.className = 'protein-card';
    card.innerHTML = `
      <h3>${protein.name}</h3>
      <p>By: ${protein.created_by}</p>
      <p>Length: ${protein.sequence.length} aa</p>
      <p class="status">Public ✅</p>
      <button onclick="viewProteinDetails(${protein.id})">View</button>
    `;
    container.appendChild(card);
  });
}
```

### React Component:
```jsx
import { useState, useEffect } from 'react';

export function PublicProteins() {
  const [proteins, setProteins] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/proteins/public_list/')
      .then(r => r.json())
      .then(data => {
        setProteins(data.results);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="proteins-grid">
      {proteins.map(p => (
        <div key={p.id} className="protein-card">
          <h3>{p.name}</h3>
          <p>By: {p.created_by}</p>
          <p>Public ✅</p>
        </div>
      ))}
    </div>
  );
}
```

---

## 🧬 Endpoint 2: Analyser Epitopes {#endpoint-2}

### Epitope Analysis Tool (SANS TOKEN)

```javascript
// ✅ PUBLIQUE - Aucune authentification requise
async function analyzeProtein(sequence) {
  try {
    const response = await fetch(`${API_BASE}/epitopes/analyze/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sequence: sequence,
        method: 'core',
        min_length: 9,
        max_length: 20,
        min_score: 0.5,
        top_n: 20
      })
    });

    const result = await response.json();
    
    console.log(`Found ${result.epitopes.length} epitopes`);
    displayEpitopes(result.epitopes);
    
    return result;
  } catch (error) {
    console.error('Analysis error:', error);
  }
}

function displayEpitopes(epitopes) {
  const container = document.getElementById('epitopes-results');
  
  epitopes.forEach((epi, idx) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${idx + 1}</td>
      <td>${epi.start}-${epi.end}</td>
      <td>${epi.length}</td>
      <td>${epi.score.toFixed(4)}</td>
      <td>${epi.sequence}</td>
    `;
    container.appendChild(row);
  });
}
```

### Vue Component:
```vue
<template>
  <div class="analysis-tool">
    <textarea v-model="sequence" placeholder="Enter protein sequence..."></textarea>
    <button @click="analyze">Analyze</button>
    
    <table v-if="results.length">
      <tr v-for="(epi, idx) in results" :key="idx">
        <td>{{ idx + 1 }}</td>
        <td>{{ epi.start }}-{{ epi.end }}</td>
        <td>{{ epi.length }}</td>
        <td>{{ epi.score.toFixed(4) }}</td>
        <td>{{ epi.sequence }}</td>
      </tr>
    </table>
  </div>
</template>

<script>
export default {
  data() {
    return {
      sequence: '',
      results: []
    }
  },
  methods: {
    async analyze() {
      const response = await fetch('http://localhost:8000/api/epitopes/analyze/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sequence: this.sequence,
          method: 'core'
        })
      });
      const data = await response.json();
      this.results = data.epitopes;
    }
  }
}
</script>
```

---

## 👤 Endpoint 3: Dashboard Personnel {#endpoint-3}

### User - Voir ses proteins (AVEC TOKEN)

```javascript
// 🔐 PROTECTION - Token requis
async function loadMyProteins() {
  try {
    const data = await apiCall('/proteins/my_proteins/');
    
    console.log(`${data.username} voit ${data.count} proteins`);
    console.log('Is Admin:', data.is_admin);
    
    displayMyProteins(data.results);
    return data.results;
  } catch (error) {
    console.error('Error:', error);
    // Si 401, rediriger vers login
    if (error.status === 401) {
      window.location.href = '/login';
    }
  }
}

function displayMyProteins(proteins) {
  const personal = proteins.filter(p => p.created_by === getCurrentUser());
  const public_only = proteins.filter(p => p.is_public);
  
  console.log(`Your proteins: ${personal.length}`);
  console.log(`Public proteins: ${public_only.length}`);
  
  // Afficher dans différentes sections
  document.getElementById('my-proteins').innerHTML = 
    personal.map(p => renderProteinCard(p, true)).join('');
  
  document.getElementById('public-proteins').innerHTML = 
    public_only.map(p => renderProteinCard(p, false)).join('');
}

function renderProteinCard(protein, isOwned) {
  return `
    <div class="protein-card ${isOwned ? 'owned' : 'public'}">
      <h3>${protein.name}</h3>
      <p>Status: ${protein.is_public ? '🌍 Public' : '🔒 Private'}</p>
      <p>Created: ${new Date(protein.created_at).toLocaleDateString()}</p>
      ${isOwned ? `
        <button onclick="editProtein(${protein.id})">Edit</button>
        <button onclick="deleteProtein(${protein.id})">Delete</button>
      ` : ''}
    </div>
  `;
}
```

### React Hook:
```jsx
import { useEffect, useState } from 'react';

export function MyProteins() {
  const [proteins, setProteins] = useState([]);
  const [user, setUser] = useState(null);
  const token = localStorage.getItem('userToken');

  useEffect(() => {
    if (!token) {
      window.location.href = '/login';
      return;
    }

    fetch('http://localhost:8000/api/proteins/my_proteins/', {
      headers: { 'Authorization': `Token ${token}` }
    })
      .then(r => r.json())
      .then(data => {
        setProteins(data.results);
        setUser({
          username: data.username,
          is_admin: data.is_admin
        });
      });
  }, []);

  return (
    <div>
      <h2>Welcome {user?.username}!</h2>
      <p>You can see {proteins.length} proteins</p>
      
      <div className="proteins-owned">
        <h3>Your Proteins</h3>
        {proteins
          .filter(p => p.created_by === user?.username)
          .map(p => (
            <ProteinCard key={p.id} protein={p} owned />
          ))}
      </div>
      
      <div className="proteins-public">
        <h3>Public Proteins</h3>
        {proteins
          .filter(p => p.is_public)
          .map(p => (
            <ProteinCard key={p.id} protein={p} />
          ))}
      </div>
    </div>
  );
}
```

---

## 👨‍💼 Endpoint 4: Admin Panel {#endpoint-4}

### Admin - Voir TOUS les proteins (ADMIN SEULEMENT)

```javascript
// 🔐 PROTECTION - Token Admin requis
async function loadAllProteins() {
  try {
    const data = await apiCall('/proteins/all_proteins/');
    
    console.log(`Admin ${data.admin} accède à ${data.count} proteins`);
    
    displayAdminStats(data.results);
    return data.results;
  } catch (error) {
    if (error.status === 403) {
      alert('You must be an admin to access this');
      window.location.href = '/';
    }
  }
}

function displayAdminStats(proteins) {
  const stats = {
    total: proteins.length,
    public: proteins.filter(p => p.is_public).length,
    private: proteins.filter(p => !p.is_public).length,
    creators: new Set(proteins.map(p => p.created_by)).size
  };
  
  console.log(`
    📊 ADMIN STATS
    Total: ${stats.total}
    Public: ${stats.public}
    Private: ${stats.private}
    Creators: ${stats.creators}
  `);
  
  // Afficher dashbo
  document.getElementById('admin-stats').innerHTML = `
    <div class="stat">Total: <strong>${stats.total}</strong></div>
    <div class="stat">Public: <strong>${stats.public}</strong></div>
    <div class="stat">Private: <strong>${stats.private}</strong></div>
    <div class="stat">Creators: <strong>${stats.creators}</strong></div>
  `;
}
```

### Vue Admin Component:
```vue
<template>
  <div class="admin-panel">
    <h2>Admin Dashboard</h2>
    
    <div class="stats">
      <div>Total Proteins: {{ proteins.length }}</div>
      <div>Public: {{ publicCount }}</div>
      <div>Private: {{ privateCount }}</div>
    </div>
    
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Creator</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in proteins" :key="p.id">
          <td>{{ p.id }}</td>
          <td>{{ p.name }}</td>
          <td>{{ p.created_by }}</td>
          <td>
            <span v-if="p.is_public" class="badge success">Public</span>
            <span v-else class="badge warning">Private</span>
          </td>
          <td>
            <button @click="editProtein(p.id)">Edit</button>
            <button @click="deleteProtein(p.id)">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  data() {
    return {
      proteins: []
    };
  },
  computed: {
    publicCount() {
      return this.proteins.filter(p => p.is_public).length;
    },
    privateCount() {
      return this.proteins.filter(p => !p.is_public).length;
    }
  },
  mounted() {
    const token = localStorage.getItem('userToken');
    fetch('http://localhost:8000/api/proteins/all_proteins/', {
      headers: { 'Authorization': `Token ${token}` }
    })
      .then(r => r.json())
      .then(data => {
        this.proteins = data.results;
      })
      .catch(e => {
        alert('Admin access required');
        window.location.href = '/';
      });
  }
};
</script>
```

---

## 💻 Exemples Complets {#examples}

### Single Page Application
```html
<!DOCTYPE html>
<html>
<head>
  <title>EpiTop1 API</title>
</head>
<body>
  <div id="app">
    <nav>
      <button onclick="showPublic()">Public Proteins</button>
      <button onclick="showAnalyzer()">Analyzer</button>
      <button onclick="showDashboard()">Dashboard</button>
      <button onclick="admin() && showAdmin()">Admin</button>
      <button onclick="logout()">Logout</button>
    </nav>
    
    <div id="public" class="section">
      <h2>Public Proteins</h2>
      <div id="proteins-list"></div>
    </div>
    
    <div id="analyzer" class="section">
      <h2>Epitope Analyzer</h2>
      <textarea id="seq-input" placeholder="Enter sequence..."></textarea>
      <button onclick="analyzeProtein()">Analyze</button>
      <table id="epitopes-results"></table>
    </div>
    
    <div id="dashboard" class="section">
      <h2>My Proteins</h2>
      <div id="my-proteins"></div>
    </div>
    
    <div id="admin" class="section">
      <h2>Admin Panel</h2>
      <div id="admin-stats"></div>
      <table id="all-proteins"></table>
    </div>
  </div>

  <script>
    const API = 'http://localhost:8000/api';
    
    // Sections Management
    function showPublic() { show('public'); loadPublicProteins(); }
    function showAnalyzer() { show('analyzer'); }
    function showDashboard() { show('dashboard'); loadMyProteins(); }
    function showAdmin() { show('admin'); loadAllProteins(); }
    
    function show(id) {
      document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
      document.getElementById(id).style.display = 'block';
    }
    
    // Load Data
    async function loadPublicProteins() {
      const data = await fetch(`${API}/proteins/public_list/`).then(r => r.json());
      document.getElementById('proteins-list').innerHTML = 
        data.results.map(p => `<div class="card">${p.name}</div>`).join('');
    }
    
    async function analyzeProtein() {
      const seq = document.getElementById('seq-input').value;
      const data = await fetch(`${API}/epitopes/analyze/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({sequence: seq, method: 'core'})
      }).then(r => r.json());
      
      document.getElementById('epitopes-results').innerHTML = data.epitopes
        .map(e => `<tr><td>${e.sequence}</td><td>${e.score}</td></tr>`)
        .join('');
    }
    
    async function loadMyProteins() {
      const token = localStorage.getItem('userToken');
      if (!token) return window.location = '/login';
      
      const data = await fetch(`${API}/proteins/my_proteins/`, {
        headers: {'Authorization': `Token ${token}`}
      }).then(r => r.json());
      
      document.getElementById('my-proteins').innerHTML = 
        data.results.map(p => `<div>${p.name} (${p.is_public ? 'Public' : 'Private'})</div>`).join('');
    }
    
    async function loadAllProteins() {
      const token = localStorage.getItem('userToken');
      const data = await fetch(`${API}/proteins/all_proteins/`, {
        headers: {'Authorization': `Token ${token}`}
      }).then(r => r.json()).catch(() => {
        alert('Admin only'); return {results: []};
      });
      
      document.getElementById('all-proteins').innerHTML = 
        data.results.map(p => `<tr><td>${p.name}</td><td>${p.created_by}</td></tr>`).join('');
    }
    
    function logout() {
      localStorage.removeItem('userToken');
      window.location = '/login';
    }
  </script>
</body>
</html>
```

---

## 🚨 Gestion des Erreurs

```javascript
// Common error responses
const errors = {
  401: 'Please login first',
  403: 'You do not have permission',
  404: 'Protein not found',
  500: 'Server error'
};

async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(endpoint, options);
    
    if (!response.ok) {
      const error = new Error(errors[response.status] || 'Unknown error');
      error.status = response.status;
      throw error;
    }
    
    return response.json();
  } catch (error) {
    console.error(`API Error (${error.status}):`, error.message);
    throw error;
  }
}
```

---

## 🎊 Résumé de l'Intégration

- ✅ **Public List**: Affiche proteins publics sans login
- ✅ **Analyzer**: Tool gratuit d'analyse d'epitopes
- ✅ **Dashboard**: Users voient leurs propres proteins
- ✅ **Admin**: Admins gèrent tout

**Tous les endpoints intégrables en frontend!** 🚀
