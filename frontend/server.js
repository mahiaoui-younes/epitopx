/**
 * EpitopX AI � Local dev server (hardened + optimized)
 * Serves static files AND proxies /api/* to the remote API.
 * Same origin => no CORS issues.
 *
 * Features:
 *  - Response caching for external APIs (UniProt, NCBI)
 *  - Request throttling & concurrency limiting per host
 *  - Tiered rate limiting (general + API-specific)
 *  - Input validation & SSRF mitigation
 *  - Path-traversal protection & security headers
 *  - Structured logging
 *  - Diagnostic /api/_status endpoint
 *
 * Usage:  node server.js
 * Then open http://127.0.0.1:3333
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');

// Load .env file (LLM_API_KEY, PORT, REMOTE_API, etc.)
require('dotenv').config();

// -- Modules --------------------------------------------------------------
const { ResponseCache }     = require('./lib/cache');
const { RequestThrottle }   = require('./lib/throttle');
const { Logger }            = require('./lib/logger');
const { createProxyHandler } = require('./lib/proxy');
const validator              = require('./lib/validator');

// -- Configuration --------------------------------------------------------
const PORT        = process.env.PORT ? Number(process.env.PORT) : 3333;
const REMOTE_API  = process.env.REMOTE_API  || 'http://localhost:8000';
const EPITOPE_API = process.env.EPITOPE_API || 'http://localhost:8000';
const LOG_LEVEL   = process.env.LOG_LEVEL || 'info';

const MAX_BODY_SIZE = 10 * 1024 * 1024; // 10 MB

// -- LLM (OpenRouter) configuration ----------------------------------------
const LLM_API_KEY  = process.env.LLM_API_KEY  || '';
const LLM_MODEL    = process.env.LLM_MODEL    || 'openai/gpt-oss-120b:free';
const LLM_PROVIDER = process.env.LLM_PROVIDER || 'openrouter';

// -- Initialize shared services -------------------------------------------
const log      = new Logger({ level: LOG_LEVEL });
const cache    = new ResponseCache({ maxEntries: 500 });
const throttle = new RequestThrottle();
const { proxyRequest, collectBody } = createProxyHandler({ cache, throttle, log, maxBodySize: MAX_BODY_SIZE });

// Register dynamic backend hosts in validator
try { validator.addAllowedHost(new URL(REMOTE_API).hostname); } catch {}
try { validator.addAllowedHost(new URL(EPITOPE_API).hostname); } catch {}
// Add custom backend hosts here if needed (e.g. ngrok or remote API)

// -- Rate limiting (tiered: general + API proxy) --------------------------
const RATE_LIMITS = {
  general:   { windowMs: 60 * 1000, max: 300 },   // 300 req/min total
  apiProxy:  { windowMs: 60 * 1000, max: 150 },    // 150 external-proxy req/min
};
const rateLimitMaps = {
  general:  new Map(),
  apiProxy: new Map(),
};

function checkRateLimit(ip, tier) {
  const config = RATE_LIMITS[tier];
  const map = rateLimitMaps[tier];
  const now = Date.now();
  let entry = map.get(ip);
  if (!entry || now - entry.start > config.windowMs) {
    entry = { start: now, count: 0 };
    map.set(ip, entry);
  }
  entry.count++;
  return entry.count > config.max;
}

// Cleanup stale rate-limit entries every 2 minutes
setInterval(() => {
  const now = Date.now();
  for (const [tier, config] of Object.entries(RATE_LIMITS)) {
    const map = rateLimitMaps[tier];
    for (const [ip, entry] of map) {
      if (now - entry.start > config.windowMs) map.delete(ip);
    }
  }
}, 2 * 60 * 1000);

// -- MIME types -----------------------------------------------------------
const MIME_TYPES = {
  '.html': 'text/html',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
  '.pdb':  'text/plain',
};

// -- Security headers -----------------------------------------------------
function setSecurityHeaders(res) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
}

// -- Path traversal guard -------------------------------------------------
const DOCUMENT_ROOT = path.resolve(__dirname);

function safePath(requestPath) {
  const decoded = decodeURIComponent(requestPath);
  const resolved = path.resolve(DOCUMENT_ROOT, '.' + decoded);
  if (!resolved.startsWith(DOCUMENT_ROOT + path.sep) && resolved !== DOCUMENT_ROOT) {
    return null;
  }
  return resolved;
}

// -------------------------------------------------------------------------
// -- HTTP Server ----------------------------------------------------------
// -------------------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const clientIp = req.socket.remoteAddress || 'unknown';

  // -- General rate limiting ----------------------------------------------
  if (checkRateLimit(clientIp, 'general')) {
    log.warn('rate-limit', `General limit exceeded for ${clientIp}`);
    res.writeHead(429, { 'Content-Type': 'application/json', 'Retry-After': '60' });
    res.end(JSON.stringify({ error: 'Too many requests. Please try again later.' }));
    return;
  }

  setSecurityHeaders(res);

  const parsed = url.parse(req.url);
  const pathname = decodeURIComponent(parsed.pathname);

  // -- Block null bytes ---------------------------------------------------
  if (pathname.includes('\0')) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    res.end('Bad Request');
    return;
  }

  // -- CORS preflight -----------------------------------------------------
  if (req.method === 'OPTIONS' && pathname.startsWith('/api/')) {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, ngrok-skip-browser-warning',
      'Access-Control-Max-Age': '86400',
    });
    res.end();
    return;
  }

  // -- Diagnostic endpoint: /api/_status ----------------------------------
  if (pathname === '/api/_status' && req.method === 'GET') {
    const status = {
      uptime: Math.round(process.uptime()),
      cache: cache.stats(),
      throttle: throttle.stats(),
      memory: {
        rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
        heap: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
      },
    };
    res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
    res.end(JSON.stringify(status, null, 2));
    return;
  }

  // -----------------------------------------------------------------------
  // -- Proxy routes (with caching, throttling, validation) ----------------
  // -----------------------------------------------------------------------

  // -- Proxy /api/uniprot/* ? UniProt REST API ----------------------------
  if (pathname.startsWith('/api/uniprot/')) {
    // API-specific rate limiting for proxy routes
    if (checkRateLimit(clientIp, 'apiProxy')) {
      log.warn('rate-limit', `API proxy limit exceeded for ${clientIp}`);
      res.writeHead(429, { 'Content-Type': 'application/json', 'Retry-After': '30' });
      res.end(JSON.stringify({ error: 'Too many API requests. Please slow down.' }));
      return;
    }

    const uniprotPath = req.url.replace(/^\/api\/uniprot/, '');
    const check = validator.validateUniProtPath(uniprotPath);
    if (!check.valid) {
      log.warn('validator', `UniProt path rejected: ${check.reason}`);
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: check.reason }));
      return;
    }

    const target = 'https://rest.uniprot.org' + uniprotPath;

    proxyRequest({
      tag: 'uniprot-proxy',
      targetUrl: target,
      method: 'GET',
      headers: {
        'Accept': req.headers['accept'] || 'application/json',
        'User-Agent': 'EpitopX AI/1.0',
      },
      timeout: 30000,
      cacheable: true,  // Cache UniProt GET responses
      res,
    });
    return;
  }

  // -- Proxy /api/epitopes/* ? EPITOPE_API --------------------------------
  if (pathname.startsWith('/api/epitopes/')) {
    const target = EPITOPE_API + req.url;

    try {
      const bodyBuffer = await collectBody(req);
      proxyRequest({
        tag: 'epitope-proxy',
        targetUrl: target,
        method: req.method,
        headers: {
          ...req.headers,
          host: new URL(EPITOPE_API).host,
          'content-length': bodyBuffer.length,
          'ngrok-skip-browser-warning': 'true',
        },
        body: bodyBuffer,
        timeout: 60000,
        cacheable: false,  // Epitope analysis results are unique per request
        res,
      });
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // -- Proxy /api/ncbi/* ? NCBI E-utilities -------------------------------
  if (pathname.startsWith('/api/ncbi/')) {
    if (checkRateLimit(clientIp, 'apiProxy')) {
      log.warn('rate-limit', `API proxy limit exceeded for ${clientIp}`);
      res.writeHead(429, { 'Content-Type': 'application/json', 'Retry-After': '30' });
      res.end(JSON.stringify({ error: 'Too many API requests. Please slow down.' }));
      return;
    }

    const ncbiPath = req.url.replace(/^\/api\/ncbi/, '');
    const check = validator.validateNCBIPath(ncbiPath);
    if (!check.valid) {
      log.warn('validator', `NCBI path rejected: ${check.reason}`);
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: check.reason }));
      return;
    }

    const target = 'https://eutils.ncbi.nlm.nih.gov' + ncbiPath;

    try {
      const bodyBuffer = await collectBody(req);
      proxyRequest({
        tag: 'ncbi-proxy',
        targetUrl: target,
        method: req.method,
        headers: {
          'Accept': req.headers['accept'] || '*/*',
          'User-Agent': 'EpitopX AI/1.0 (bioinformatics research tool)',
          ...(bodyBuffer.length ? {
            'Content-Type': req.headers['content-type'] || 'application/x-www-form-urlencoded',
            'Content-Length': bodyBuffer.length,
          } : {}),
        },
        body: bodyBuffer.length ? bodyBuffer : undefined,
        timeout: 30000,
        cacheable: req.method === 'GET',  // Cache NCBI GET responses
        res,
      });
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // -- Proxy /api/msa/* ? MSA Alignment API (ngrok) ----------------------
  if (pathname.startsWith('/api/msa/')) {
    const ALIGNMENT_API = process.env.ALIGNMENT_API || 'http://localhost:8000';
    if (checkRateLimit(clientIp, 'apiProxy')) {
      res.writeHead(429, { 'Content-Type': 'application/json', 'Retry-After': '30' });
      res.end(JSON.stringify({ error: 'Too many API requests. Please slow down.' }));
      return;
    }
    const target = ALIGNMENT_API + req.url;  // forward full path: /api/msa/align/
    try {
      const bodyBuffer = await collectBody(req);
      proxyRequest({
        tag: 'msa-proxy',
        targetUrl: target,
        method: req.method,
        headers: {
          'Content-Type': req.headers['content-type'] || 'application/json',
          'Accept': req.headers['accept'] || 'application/json',
          'User-Agent': 'EpitopX AI/1.0',
          'ngrok-skip-browser-warning': 'true',
          ...(bodyBuffer.length ? { 'Content-Length': bodyBuffer.length } : {}),
        },
        body: bodyBuffer.length ? bodyBuffer : undefined,
        timeout: 120000,
        cacheable: false,
        res,
      });
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // -- Proxy /api/alignment/* ? MSA Alignment API (legacy alias) ---------
  if (pathname.startsWith('/api/alignment/')) {
    const ALIGNMENT_API = process.env.ALIGNMENT_API || 'http://localhost:8000';
    if (checkRateLimit(clientIp, 'apiProxy')) {
      res.writeHead(429, { 'Content-Type': 'application/json', 'Retry-After': '30' });
      res.end(JSON.stringify({ error: 'Too many API requests. Please slow down.' }));
      return;
    }
    const target = ALIGNMENT_API + req.url.replace(/^\/api\/alignment/, '');
    try {
      const bodyBuffer = await collectBody(req);
      proxyRequest({
        tag: 'alignment-proxy',
        targetUrl: target,
        method: req.method,
        headers: {
          'Content-Type': req.headers['content-type'] || 'application/json',
          'Accept': req.headers['accept'] || 'application/json',
          'User-Agent': 'EpitopX AI/1.0',
          'ngrok-skip-browser-warning': 'true',
          ...(bodyBuffer.length ? { 'Content-Length': bodyBuffer.length } : {}),
        },
        body: bodyBuffer.length ? bodyBuffer : undefined,
        timeout: 120000,
        cacheable: false,
        res,
      });
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // -- Proxy /api/blast/* ? NCBI BLAST ------------------------------------
  if (pathname.startsWith('/api/blast/')) {
    if (checkRateLimit(clientIp, 'apiProxy')) {
      res.writeHead(429, { 'Content-Type': 'application/json', 'Retry-After': '30' });
      res.end(JSON.stringify({ error: 'Too many API requests. Please slow down.' }));
      return;
    }

    const blastPath = req.url.replace(/^\/api\/blast/, '');
    const target = 'https://blast.ncbi.nlm.nih.gov' + blastPath;

    try {
      const bodyBuffer = await collectBody(req);
      proxyRequest({
        tag: 'blast-proxy',
        targetUrl: target,
        method: req.method,
        headers: {
          'Accept': req.headers['accept'] || '*/*',
          'User-Agent': 'EpitopX AI/1.0 (bioinformatics research tool)',
          ...(bodyBuffer.length ? {
            'Content-Type': req.headers['content-type'] || 'application/x-www-form-urlencoded',
            'Content-Length': bodyBuffer.length,
          } : {}),
        },
        body: bodyBuffer.length ? bodyBuffer : undefined,
        timeout: 120000,
        cacheable: req.method === 'GET',
        res,
      });
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // -- AI Agent: POST /api/analyze-protein/ --------------------------------
  if (pathname === '/api/analyze-protein/' && req.method === 'POST') {
    try {
      const bodyBuffer = await collectBody(req);
      const body = JSON.parse(bodyBuffer.toString('utf8'));
      // Accept {message} (general chat) or {name} (legacy protein-only)
      const userMessage = (body.message || body.name || '').trim().slice(0, 10000);

      if (!userMessage) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Missing message' }));
        return;
      }

      // Model override from client (validate it looks like a model id)
      const modelOverride = typeof body.model === 'string' && /^[\w\-./+:]{3,80}$/.test(body.model)
        ? body.model : null;

      // Multi-turn history (last 14 messages, only user/assistant roles)
      const rawHistory = Array.isArray(body.history) ? body.history.slice(-14) : [];
      const history = rawHistory
        .filter(m => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string')
        .map(m => ({ role: m.role, content: m.content.slice(0, 3000) }));

      // Optional persistent memory context from client
      const memoryContext = typeof body.memoryContext === 'string'
        ? body.memoryContext.slice(0, 2000) : '';

      // Optional auth token — DRF Token (40-char hex) or JWT (dot-separated)
      const rawAuthToken = typeof body.authToken === 'string' ? body.authToken.trim() : '';
      const authToken = /^[a-f0-9]{20,64}$/i.test(rawAuthToken) || /^[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+$/.test(rawAuthToken)
        ? rawAuthToken : null;

      // ── Helper: make an authenticated GET to the Django backend ──────────
      async function djangoGet(path) {
        return new Promise((resolve, reject) => {
          const r = http.get(
            `${REMOTE_API}${path}`,
            { headers: authToken ? { Authorization: `Token ${authToken}` } : {} },
            (res) => {
              let data = '';
              res.on('data', c => { data += c; });
              res.on('end', () => resolve({ status: res.statusCode, body: data }));
            }
          );
          r.on('error', reject);
          r.setTimeout(8000, () => r.destroy());
        });
      }

      async function djangoPost(path, payload, extraHeaders = {}) {
        const buf = Buffer.from(JSON.stringify(payload));
        return new Promise((resolve, reject) => {
          const urlObj = new URL(`${REMOTE_API}${path}`);
          const r = http.request({
            hostname: urlObj.hostname,
            port: urlObj.port || 80,
            path: urlObj.pathname + (urlObj.search || ''),
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Content-Length': buf.length,
              ...(authToken ? { Authorization: `Token ${authToken}` } : {}),
              ...extraHeaders,
            },
          }, (res) => {
            let data = '';
            res.on('data', c => { data += c; });
            res.on('end', () => resolve({ status: res.statusCode, body: data }));
          });
          r.on('error', reject);
          r.setTimeout(30000, () => r.destroy());
          r.write(buf);
          r.end();
        });
      }

      // ── Fetch a snapshot of the user's proteins for context ───────────────

      // ── Check agent message quota BEFORE processing ───────────────────────
      if (authToken) {
        try {
          const quotaRes = await djangoGet('/api/users/agent-quota/');
          if (quotaRes.status === 200) {
            const quota = JSON.parse(quotaRes.body);
            if (quota.exhausted) {
              res.writeHead(429, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({
                error: `🔒 **Limite mensuelle atteinte** (${quota.used}/${quota.limit} messages).\n\nPassez à un plan supérieur pour continuer à utiliser l'Agent IA.\n\n→ [Voir les offres](/pricing.html)`,
                quota,
              }));
              return;
            }
          }
        } catch (_) { /* quota check failed — allow request to proceed */ }
      }
      let dbContext = '';
      let proteinList = [];
      if (authToken) {
        try {
          const dbRes = await djangoGet('/api/proteins/?page_size=50');
          if (dbRes.status === 200) {
            const proteins = JSON.parse(dbRes.body);
            proteinList = (proteins.results || proteins || []).slice(0, 20);
            if (proteinList.length) {
              dbContext = '\n\n## Proteins in the user\'s local EpitopX database (id | name | organism | length | epitopes):\n'
                + proteinList.map(p =>
                    `- id=${p.id} **${p.name}** (${p.organism || 'unknown'}) — ${p.sequence ? p.sequence.length + ' aa' : '?'}`
                    + (p.epitope_count ? `, ${p.epitope_count} epitopes already predicted` : ', no epitopes yet')
                  ).join('\n');
            }
          }
        } catch (_) { /* continue without DB context */ }
      }

      // ─────────────────────────────────────────────────────────────────────
      // ── Offline bioinformatics engine (no LLM needed for these) ──────────
      // ─────────────────────────────────────────────────────────────────────
      function buildOfflineReply(msg, proteins) {
        if (/\b(h[eé]moglobine?|hemoglobin)\b/i.test(msg))
          return '## 🩸 Hémoglobine\n\n**Hémoglobine (Hb)** est une métalloprotéine transportant l\'oxygène dans le sang.\n\n| Propriété | Valeur |\n|---|---|\n| Gènes | HBA1/HBA2 (α), HBB (β) |\n| UniProt | P69905 (α), P68871 (β) |\n| Longueur | 141 aa (α), 146 aa (β) |\n| Structure | Tétramère α₂β₂ |\n\n→ [Rechercher sur UniProt](protein-search.html?q=hemoglobin) | [Rech. Épitopes](epitope-search.html)';
        if (/\b(insuline?|insulin)\b/i.test(msg))
          return '## 💉 Insuline\n\n**Insuline** est une hormone peptidique régulatrice de la glycémie.\n\n| Propriété | Valeur |\n|---|---|\n| Gène | INS |\n| UniProt | P01308 |\n| Longueur | 110 aa |\n| Chaînes | A (21 aa) + B (30 aa) |\n\n→ [UniProt](protein-search.html?q=insulin) | [Épitopes](epitope-search.html)';
        if (/\b(spike|sars|covid|corona)\b/i.test(msg))
          return '## 🦠 Protéine Spike (SARS-CoV-2)\n\n**Spike** est la glycoprotéine de surface du SARS-CoV-2 ciblée par les vaccins.\n\n| Propriété | Valeur |\n|---|---|\n| UniProt | P0DTC2 |\n| Longueur | 1273 aa |\n| Domaines | NTD, RBD, FP, HR1/HR2, TM |\n| Récepteur | ACE2 |\n\n**Épitopes neutralisants :** RBD (319–541), NTD (14–305)\n\n→ [Viewer 3D](viewer.html?protein=SPIKE) | [Épitopes](epitope-search.html)';
        if (/\b(albumine?|albumin)\b/i.test(msg))
          return '## 🔬 Albumine Sérique\n\n**Albumine** est la protéine plasmatique la plus abondante.\n\n| Propriété | Valeur |\n|---|---|\n| UniProt | P02768 |\n| Longueur | 609 aa |\n| Masse | ~66.5 kDa |\n| Fonction | Transport lipides, médicaments, hormones |\n\n→ [UniProt](protein-search.html?q=albumin) | [Épitopes](epitope-search.html)';
        if (/\bfasta\b/i.test(msg))
          return '## 📄 Format FASTA\n\nLe format **FASTA** est le standard pour les séquences biologiques.\n\n```\n>sp|P68871|HBB_HUMAN Hemoglobin beta OS=Homo sapiens\nMVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLS...\n```\n\n**Glissez** un fichier `.fasta` directement dans cette fenêtre pour l\'analyser !';
        if (/\b(?:adn|dna|arn|rna)\b/i.test(msg))
          return '## 🔗 Séquences Nucléotidiques\n\n- **ADN** : bases A, T, G, C\n- **ARN** : bases A, U, G, C\n\n**Outils EpitopX :**\n- 🔗 [Alignement ADN](dna-alignment.html)\n- 🧬 [Analyse MSA](msa-analysis.html)\n- 🔎 [NCBI](ncbi-search.html)\n\n> Dites *"traduis la séquence ATGGCTAGC..."* pour convertir ADN → protéine.';
        if (/\b(?:quel(?:le)?s?\s+outils?|que.*(?:peux|peut)|capabilities|fonctionnalit|aide|help|bonjour|hello|salut|hi\b)/i.test(msg))
          return '## 🤖 EpitopX AI Agent\n\nJe suis votre assistant bioinformatique. Voici mes capacités :\n\n| Action | Exemple |\n|---|---|\n| ✅ Créer une protéine | *"Crée une protéine nommée Spike..."* |\n| 📋 Lister mes protéines | *"Montre mes protéines"* |\n| 🔗 Traduire ADN | *"Traduis ATGGCTAGC..."* |\n| 🎯 Prédire épitopes | *"Prédit les épitopes de [nom]"* |\n| 🔍 Chercher protéine | *"Cherche Hémoglobine"* |\n\n> 💡 Ajoutez `LLM_API_KEY` dans `frontend/.env` pour l\'IA générative (OpenRouter.ai).';
        if (proteins.length)
          return `## 🤖 EpitopX AI Agent\n\nVous avez **${proteins.length} protéine(s)** dans votre base.\n\n${proteins.slice(0, 5).map(p => `- **${p.name}** (${p.organism || '?'}, ${p.sequence ? p.sequence.length + ' aa' : '?'})`).join('\n')}\n\n**Que puis-je faire ?**\n- 🎯 Prédire des épitopes\n- 🔗 Traduire une séquence ADN\n- ➕ Créer une nouvelle protéine\n\n> 💡 Configurez \`LLM_API_KEY\` dans \`frontend/.env\` pour l\'IA générative.`;
        return '## 🤖 EpitopX AI Agent\n\nJe suis votre assistant bioinformatique EpitopX.\n\n**Actions rapides :**\n- ✅ *"Crée une protéine nommée [nom] avec la séquence [AA]"*\n- 📋 *"Montre mes protéines"*\n- 🔗 *"Traduis la séquence ADN ATGGCT..."*\n- 🎯 *"Prédit les épitopes de [protéine]"*\n- 🔍 *"Cherche [nom protéine]"*\n\n> 💡 Ajoutez `LLM_API_KEY=sk-or-v1-...` dans `frontend/.env` pour l\'IA générative (OpenRouter.ai — gratuit).';
      }

      // ── Detect protein CREATION intent ───────────────────────────────────
      const msgLower = userMessage.toLowerCase();
      const wantsCreate = /(?:cr[ée]{1,2}[er]?|crée[r]?|ajoute[r]?|\badd\b|save|enregistre[r]?|nouvelle?\s+prot[ée]ine?|new\s+protein)/i.test(userMessage)
        && /\bprot[ée]ine?s?\b/i.test(userMessage);
      if (wantsCreate) {
        const nameMatch = userMessage.match(/(?:nom(?:mé[e]?)?|named?|appel[ée][e]?|called?)\s*[:\s«"`']+\s*([A-Za-z0-9_\-]{2,50})/i)
          || userMessage.match(/["«`'']([A-Za-z0-9_\-][A-Za-z0-9_\-\s]{0,48}?)["»`''"]/);
        const seqMatch = userMessage.match(/(?:s[ée]quence?)\s*[:\s]+([ACDEFGHIKLMNPQRSTVWY]{10,})/i)
          || userMessage.match(/\b([ACDEFGHIKLMNPQRSTVWY]{20,})\b/);
        const orgMatch = userMessage.match(/(?:organisme?|organism|esp[èe]ce|species)\s*[:\s]+([A-Za-z\s]{3,40})/i);
        if (nameMatch && seqMatch) {
          const protName = nameMatch[1].trim().replace(/\s+/g, ' ');
          const sequence = seqMatch[1].trim().toUpperCase();
          const organism = orgMatch ? orgMatch[1].trim() : '';
          if (!authToken) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ analysis: '⚠️ **Non connecté.** Veuillez vous connecter pour créer une protéine.' }));
            return;
          }
          try {
            const createRes = await djangoPost('/api/proteins/', {
              name: protName, sequence, organism,
              description: "Créée par l'Agent IA EpitopX", is_public: false,
            });
            if (createRes.status === 201) {
              const created = JSON.parse(createRes.body);
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ analysis: `## ✅ Protéine créée avec succès !\n\n| Champ | Valeur |\n|---|---|\n| **ID** | ${created.id} |\n| **Nom** | ${created.name} |\n| **Organisme** | ${created.organism || '—'} |\n| **Longueur** | ${sequence.length} aa |\n| **Visibilité** | Privée |\n\n🎯 Souhaitez-vous que je **prédise les épitopes** de cette protéine ?\n\n→ [Voir dans Mes Protéines](my-proteins.html)` }));
            } else {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ analysis: `⚠️ Erreur création (${createRes.status}): ${createRes.body.slice(0, 200)}` }));
            }
          } catch (e) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ analysis: `⚠️ Impossible de créer la protéine : ${e.message}` }));
          }
          return;
        }
        // Missing name or sequence — guide the user
        const missing = [];
        if (!nameMatch) missing.push('le **nom** (ex: `nommée Spike-COVID`)');
        if (!seqMatch) missing.push('la **séquence** acide aminée ≥ 20 AA (ex: `MFVFLVLLPLVSSQCVNL...`)');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis: `## 📝 Créer une protéine\n\nPour créer une protéine j\'ai besoin de :\n${missing.map(m => '- ' + m).join('\n')}\n\n**Exemple :**\n> *"Crée une protéine nommée \`Spike-SARS2\` avec la séquence \`MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFFSNVTWFHAIHVSGTNGTKRFDNP\`"*` }));
        return;
      }

      // ── Detect protein LIST intent ────────────────────────────────────────
      const wantsList = /(?:mes\s+prot[ée]ines?|my\s+proteins?|what\s+proteins?|liste[r]?\s+(?:mes\s+)?prot[ée]ines?|list\s+(?:my\s+)?proteins?|affiche[r]?\s+(?:mes\s+)?prot[ée]ines?|show\s+(?:my\s+)?proteins?|montre[r]?\s+(?:mes\s+)?prot[ée]ines?|quelles?\s+prot[ée]ines?|combien\s+de\s+prot[ée]ines?|how\s+many\s+proteins?|which\s+proteins?|get\s+(?:my\s+)?proteins?)/i.test(userMessage);
      if (wantsList) {
        if (!proteinList.length) {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ analysis: '## 📭 Aucune protéine trouvée\n\nVotre base de données est vide.\n\n**Pour commencer :**\n- Dites *"Crée une protéine nommée [nom] avec la séquence [AA]"*\n- Ou visitez [Mes Protéines](my-proteins.html)' }));
          return;
        }
        const rows = proteinList.map(p => `| ${p.id} | **${p.name}** | ${p.organism || '—'} | ${p.sequence ? p.sequence.length + ' aa' : '?'} | ${p.epitope_count || 0} |`).join('\n');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis: `## 🧬 Vos Protéines (${proteinList.length})\n\n| ID | Nom | Organisme | Longueur | Épitopes |\n|---|---|---|---|---|\n${rows}\n\n→ [Gérer dans Mes Protéines](my-proteins.html)` }));
        return;
      }

      // ── Detect protein DELETE intent ──────────────────────────────────────
      const wantsDelete = /(?:supprime[r]?|efface[r]?|suppression|retire[r]?|delete|remove)\b.*\bprot[ée]ine?\b|\bprot[ée]ine?\b.*(?:supprime[r]?|efface[r]?|delete|remove)\b/i.test(userMessage);
      if (wantsDelete && authToken) {
        let targetP = null;
        for (const p of proteinList) {
          if (msgLower.includes(p.name.toLowerCase())) { targetP = p; break; }
        }
        if (!targetP) {
          const idM = userMessage.match(/\b(?:id\s*[=:]?\s*|#)(\d+)\b/i);
          if (idM) targetP = proteinList.find(p => String(p.id) === idM[1]);
        }
        if (!targetP && proteinList.length === 1) targetP = proteinList[0];
        if (targetP) {
          try {
            const delRes = await new Promise((resolve, reject) => {
              const urlObj = new URL(`${REMOTE_API}/api/proteins/${targetP.id}/`);
              const r = http.request({
                hostname: urlObj.hostname, port: urlObj.port || 80,
                path: urlObj.pathname, method: 'DELETE',
                headers: { Authorization: `Token ${authToken}` },
              }, (res2) => { res2.resume(); resolve(res2.statusCode); });
              r.on('error', reject);
              r.setTimeout(8000, () => r.destroy());
              r.end();
            });
            if (delRes === 204 || delRes === 200) {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ analysis: `## 🗑️ Protéine supprimée\n\n**${targetP.name}** (ID: ${targetP.id}) a été supprimée avec succès.\n\n→ [Mes Protéines](my-proteins.html)` }));
            } else {
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ analysis: `⚠️ Impossible de supprimer **${targetP.name}** (erreur ${delRes}).` }));
            }
          } catch (e) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ analysis: `⚠️ Erreur lors de la suppression : ${e.message}` }));
          }
          return;
        }
        const names = proteinList.map(p => `- **${p.name}** (ID: ${p.id})`).join('\n');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis: `## 🗑️ Supprimer une protéine\n\nQuelle protéine souhaitez-vous supprimer ?\n\n${names || '*(aucune protéine enregistrée)*'}\n\n*Exemple : "Supprime la protéine Spike-SARS2"*` }));
        return;
      }

      // ── Detect COMPARE intent ─────────────────────────────────────────────
      const wantsCompare = /(?:compar[ei]|compare[r]?|similarit[ée]|homolog|identit[ée]|ressemble|diff[ée]rence|versus|\bvs\b)/i.test(userMessage)
        && /prot[ée]ine?s?\b/i.test(userMessage);
      if (wantsCompare && proteinList.length >= 2) {
        // Find the two proteins referenced by name
        let p1 = null, p2 = null;
        for (const p of proteinList) {
          const nl = p.name.toLowerCase();
          if (msgLower.includes(nl)) {
            if (!p1) p1 = p; else if (!p2 && p.id !== p1.id) { p2 = p; break; }
          }
        }
        if (!p1 && !p2) { p1 = proteinList[0]; p2 = proteinList[1]; }
        if (p1 && p2) {
          // Needleman-Wunsch alignment server-side
          const MATCH = 1, MISMATCH = -1, GAP = -2;
          const sA = p1.sequence || '', sB = p2.sequence || '';
          const m = sA.length, n = sB.length;
          // Capped at 500 aa to avoid huge O(m*n) allocations
          const capA = sA.slice(0, 500), capB = sB.slice(0, 500);
          const dp = Array.from({ length: capA.length + 1 }, (_, i) =>
            new Int32Array(capB.length + 1).fill(0).map((_, j) => i === 0 ? j * GAP : j === 0 ? i * GAP : 0)
          );
          for (let i = 0; i <= capA.length; i++) dp[i][0] = i * GAP;
          for (let j = 0; j <= capB.length; j++) dp[0][j] = j * GAP;
          for (let i = 1; i <= capA.length; i++) {
            for (let j = 1; j <= capB.length; j++) {
              const d = dp[i-1][j-1] + (capA[i-1] === capB[j-1] ? MATCH : MISMATCH);
              dp[i][j] = Math.max(d, dp[i-1][j] + GAP, dp[i][j-1] + GAP);
            }
          }
          let aA = '', aB = '', i = capA.length, j = capB.length;
          while (i > 0 && j > 0) {
            const s = dp[i][j];
            if (s === dp[i-1][j-1] + (capA[i-1] === capB[j-1] ? MATCH : MISMATCH)) { aA = capA[i-1]+aA; aB = capB[j-1]+aB; i--; j--; }
            else if (s === dp[i-1][j] + GAP) { aA = capA[i-1]+aA; aB = '-'+aB; i--; }
            else { aA = '-'+aA; aB = capB[j-1]+aB; j--; }
          }
          const aLen = aA.length;
          let matches = 0, gaps = 0;
          for (let k = 0; k < aLen; k++) { if (aA[k]===aB[k]) matches++; if (aA[k]==='-'||aB[k]==='-') gaps++; }
          const identity = aLen > 0 ? ((matches/aLen)*100).toFixed(1) : '0.0';
          const preview = aA.slice(0, 60);
          const previewB = aB.slice(0, 60);
          const idFrac = matches/aLen;
          const rmsd = idFrac > 0 ? (1.5 * Math.exp(-1.87*idFrac)).toFixed(2) : 'N/A';
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ analysis:
            `## 📊 Comparaison : **${p1.name}** vs **${p2.name}**\n\n`
            + `| Paramètre | Valeur |\n|---|---|\n`
            + `| **Identité** | **${identity}%** |\n`
            + `| Longueur alignement | ${aLen} positions |\n`
            + `| Positions identiques | ${matches} |\n`
            + `| Gaps | ${gaps} |\n`
            + `| Score NW | ${dp[capA.length][capB.length]} |\n`
            + `| RMSD estimé | ~${rmsd} Å |\n\n`
            + `**Aperçu de l'alignement (60 premiers aa) :**\n\`\`\`\n${p1.name.slice(0,12).padEnd(12)} ${preview}\n${p2.name.slice(0,12).padEnd(12)} ${previewB}\n\`\`\`\n\n`
            + `→ [Comparer en détail](compare.html)`
          }));
          return;
        }
      }

      // ── Detect MSA (Multiple Sequence Alignment) intent ───────────────────
      const wantsMSA = /\b(?:align|alignement|msa|multiple\s+sequence|clustal|muscle|mafft|phylo|phylog[eé]nie|arbre|tree)\b/i.test(userMessage);
      if (wantsMSA) {
        // Extract all FASTA sequences from the message
        const fastaBlocks = [];
        const fastaPattern = />([^\n]+)\n([ACDEFGHIKLMNPQRSTVWY\-\n\s]{10,})/gi;
        let fm;
        while ((fm = fastaPattern.exec(userMessage)) !== null) {
          fastaBlocks.push({ id: fm[1].trim(), seq: fm[2].replace(/[\s\n]/g, '').toUpperCase() });
        }

        // Also try to pick proteins from DB if names mentioned
        const seqsFromDB = [];
        for (const p of proteinList) {
          if (msgLower.includes(p.name.toLowerCase()) && p.sequence) {
            seqsFromDB.push({ id: p.name, seq: p.sequence.slice(0, 300) });
          }
        }

        const allSeqs = fastaBlocks.length >= 2 ? fastaBlocks
          : seqsFromDB.length >= 2 ? seqsFromDB
          : fastaBlocks.length === 1 && seqsFromDB.length >= 1 ? [...fastaBlocks, ...seqsFromDB]
          : null;

        if (allSeqs && allSeqs.length >= 2) {
          log.info('agent', `Running MSA for ${allSeqs.length} sequences`);
          // Detect if DNA or protein
          const isDNA = allSeqs.every(s => /^[ATCGU\-]{6,}$/i.test(s.seq));

          if (isDNA) {
            // Call Django MSA (DNA only)
            try {
              const msaRes = await djangoPost('/api/msa/align/', { sequences: allSeqs.map(s => s.seq) });
              if (msaRes.status === 200) {
                const msaData = JSON.parse(msaRes.body);
                if (msaData.success && msaData.alignment) {
                  const aligned = msaData.alignment;
                  const consensus = msaData.consensus || '';
                  const idScores = msaData.identity_scores || [];
                  const alignBlock = allSeqs.map((s, i) =>
                    `${s.id.slice(0,15).padEnd(15)} ${(aligned[i] || s.seq).slice(0,60)}`
                  ).join('\n') + (consensus ? `\n${'Consensus'.padEnd(15)} ${consensus.slice(0,60)}` : '');
                  res.writeHead(200, { 'Content-Type': 'application/json' });
                  res.end(JSON.stringify({ analysis:
                    `## 🧬 MSA ADN — ${allSeqs.length} séquences\n\n`
                    + `Longueur : ${aligned[0]?.length || '?'} col | Méthode : ${msaData.method || 'progressive_msa'}\n\n`
                    + (idScores.length ? `**Identités :** ${idScores.map((sc,i) => `${allSeqs[i]?.id || i+1}: ${Number(sc).toFixed(1)}%`).join(' | ')}\n\n` : '')
                    + `\`\`\`\n${alignBlock}\n\`\`\`\n\n→ [Analyse MSA complète](msa-analysis.html)`
                  }));
                  return;
                }
              }
            } catch (msaErr) { log.warn('agent', `MSA backend failed: ${msaErr.message}`); }
          } else {
            // Protein sequences — star NW alignment in JS
            const MATCH = 2, MISMATCH = -1, GAP = -2;
            function nwAlign(a, b) {
              const m = a.length, n = b.length;
              const dp = Array.from({length: m+1}, (_, i) => new Int32Array(n+1));
              for (let i = 0; i <= m; i++) dp[i][0] = i * GAP;
              for (let j = 0; j <= n; j++) dp[0][j] = j * GAP;
              for (let i = 1; i <= m; i++)
                for (let j = 1; j <= n; j++)
                  dp[i][j] = Math.max(
                    dp[i-1][j-1] + (a[i-1] === b[j-1] ? MATCH : MISMATCH),
                    dp[i-1][j] + GAP, dp[i][j-1] + GAP
                  );
              let aA = '', aB = '', i = m, j = n;
              while (i > 0 && j > 0) {
                if (dp[i][j] === dp[i-1][j-1] + (a[i-1] === b[j-1] ? MATCH : MISMATCH)) { aA=a[i-1]+aA; aB=b[j-1]+aB; i--; j--; }
                else if (dp[i][j] === dp[i-1][j] + GAP) { aA=a[i-1]+aA; aB='-'+aB; i--; }
                else { aA='-'+aA; aB=b[j-1]+aB; j--; }
              }
              while (i > 0) { aA=a[i-1]+aA; aB='-'+aB; i--; }
              while (j > 0) { aA='-'+aA; aB=b[j-1]+aB; j--; }
              return [aA, aB];
            }
            // Star strategy: pick center = longest sequence
            let cIdx = 0;
            for (let i = 1; i < allSeqs.length; i++)
              if (allSeqs[i].seq.length > allSeqs[cIdx].seq.length) cIdx = i;
            const center = allSeqs[cIdx].seq;
            // Align all others against center
            const pairAligns = allSeqs.map((s, i) => i === cIdx ? [center, center] : nwAlign(center, s.seq));
            const centerAligned = pairAligns.find((_, i) => i !== cIdx)?.[0] || center;
            const aligned = allSeqs.map((s, i) => i === cIdx ? centerAligned : pairAligns[i][1]);
            const aLen = aligned[0].length;
            const idScores = aligned.map(seq => {
              let m = 0;
              for (let k = 0; k < aLen; k++) if (seq[k] === aligned[cIdx][k]) m++;
              return ((m / aLen) * 100).toFixed(1);
            });
            // Consensus
            let consensus = '';
            for (let k = 0; k < aLen; k++) {
              const freq = {}; aligned.forEach(s => { const c = s[k]||'-'; freq[c]=(freq[c]||0)+1; });
              const best = Object.entries(freq).sort((a,b)=>b[1]-a[1])[0][0];
              consensus += best === '-' ? '·' : best;
            }
            const alignBlock = allSeqs.map((s, i) =>
              `${s.id.slice(0,15).padEnd(15)} ${aligned[i].slice(0,60)}`
            ).join('\n') + `\n${'Consensus'.padEnd(15)} ${consensus.slice(0,60)}`;
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ analysis:
              `## 🧬 MSA Protéines — ${allSeqs.length} séquences (Star NW)\n\n`
              + `Longueur : ${aLen} col | Méthode : star_needleman-wunsch\n\n`
              + `**Identités vs centre (${allSeqs[cIdx].id}) :** ${idScores.map((sc,i) => `${allSeqs[i].id}: ${sc}%`).join(' | ')}\n\n`
              + `\`\`\`\n${alignBlock}\n\`\`\`\n\n→ [Analyse MSA complète](msa-analysis.html)`
            }));
            return;
          }
        }
        // Not enough sequences → redirect
        if (!allSeqs || allSeqs.length < 2) {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ analysis: `## 🧬 Alignement Multiple de Séquences\n\nPour lancer un MSA, j'ai besoin d'au moins **2 séquences**.\n\n**Format FASTA :**\n\`\`\`\n>Séquence_1\nMKFFYLFVLF...\n>Séquence_2\nMKTYLFVLLF...\n\`\`\`\n\nOu mentionnez 2+ protéines de votre base, ex : *"Aligne HI et FCRL4"*\n\n→ [Outil MSA](msa-analysis.html)` }));
          return;
        }
      }

      // ── Detect VIEWER 3D intent ────────────────────────────────────────────
      const wantsViewer = /\b(?:3d|viewer|visuali[sz]|structure|mol[eé]cule|fold|repli|alph.?fold|pdb)\b/i.test(userMessage);
      if (wantsViewer) {
        let targetP3D = null;
        for (const p of proteinList) {
          if (msgLower.includes(p.name.toLowerCase())) { targetP3D = p; break; }
        }
        if (!targetP3D && proteinList.length === 1) targetP3D = proteinList[0];
        const pLink = targetP3D
          ? `[Ouvrir **${targetP3D.name}** dans le Viewer 3D](viewer.html?id=${targetP3D.id})`
          : `[Ouvrir le Viewer 3D](viewer.html)`;
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis:
          `## 🏗️ Visualisation 3D\n\n${pLink}\n\n`
          + `Le Viewer 3D charge automatiquement la structure depuis :\n`
          + `1. Votre fichier PDB enregistré\n`
          + `2. **AlphaFold EBI** (si la protéine est connue)\n`
          + `3. Modèle généré localement (fallback)\n\n`
          + `→ [Viewer 3D](viewer.html${targetP3D ? '?id=' + targetP3D.id : ''})`
        }));
        return;
      }

      // ── Detect UniProt SEARCH intent ──────────────────────────────────────
      const wantsUniProt = /(?:cherche[r]?|search|trouve[r]?|find|look\s+up|accès?|récupère[r]?|fetch)\b.*\b(?:uniprot|swiss.?prot|trembl)/i.test(userMessage)
        || /\buniprot\b.*(?:cherche[r]?|search|trouve[r]?|pour|for|protein|prot[ée]ine?)/i.test(userMessage);
      if (wantsUniProt) {
        const qMatch = userMessage.match(/(?:pour|for|la\s+prot[ée]ine?|the\s+protein|about|de\s+la?)\s+([A-Za-zÀ-ÿ0-9_\-\s]{2,40}?)(?:\s*(?:sur|on|in|dans|uniprot|$))/i)
          || userMessage.match(/(?:cherche[r]?|search|trouve[r]?|find)\s+([A-Za-zÀ-ÿ0-9_\-]{3,40})(?=\s|$)/i);
        const query = (qMatch ? qMatch[1].trim() : '').replace(/^(la|le|les|the|une|un)\s+/i, '').trim() || 'protein';
        try {
          const uniRes = await new Promise((resolve, reject) => {
            const urlObj = new URL(`https://rest.uniprot.org/uniprotkb/search?query=${encodeURIComponent(query)}&format=json&size=5&fields=accession,protein_name,gene_names,organism_name,length,reviewed`);
            const protocol = require('https');
            const r = protocol.get({ hostname: urlObj.hostname, path: urlObj.pathname + urlObj.search, headers: { Accept: 'application/json' } },
              (res2) => { let data = ''; res2.on('data', c => { data += c; }); res2.on('end', () => resolve({ status: res2.statusCode, body: data })); });
            r.on('error', reject); r.setTimeout(10000, () => r.destroy());
          });
          if (uniRes.status === 200) {
            const uniData = JSON.parse(uniRes.body);
            const results = (uniData.results || []).slice(0, 5);
            if (results.length) {
              const rows = results.map(r => {
                const acc = r.primaryAccession || '?';
                const pname = r.proteinDescription?.recommendedName?.fullName?.value || r.proteinDescription?.submittedName?.[0]?.fullName?.value || '?';
                const gene = (r.genes || []).map(g => g.geneName?.value).filter(Boolean).join(', ') || '—';
                const org = r.organism?.scientificName || '?';
                const len = r.sequence?.length || '?';
                const status = r.entryType?.includes('Swiss') ? '⭐' : '📄';
                return `| ${status} [${acc}](protein-search.html?q=${acc}) | ${pname.slice(0, 40)} | ${gene} | ${org.slice(0, 25)} | ${len} aa |`;
              }).join('\n');
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ analysis: `## 🔍 Résultats UniProt pour "${query}"\n\n| Accession | Protéine | Gène | Organisme | Taille |\n|---|---|---|---|---|\n${rows}\n\n→ [Voir tous les résultats](protein-search.html?q=${encodeURIComponent(query)})` }));
              return;
            }
          }
        } catch (e) { /* fall through to LLM */ }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis: `## 🔍 Recherche UniProt\n\n→ [Chercher "${query}" sur UniProt](protein-search.html?q=${encodeURIComponent(query)})` }));
        return;
      }

      // ── Detect NCBI SEARCH intent ─────────────────────────────────────────
      const wantsNCBI = /\bncbi\b|\bgenbank\b|\bpubmed\b|\bentrez\b|\bblast\b/i.test(userMessage)
        && /(?:cherche[r]?|search|trouve[r]?|find|accès?|récupère[r]?|look\s+up)/i.test(userMessage);
      if (wantsNCBI) {
        // Extract meaningful query by stripping stop words and tool names
        const q = (() => {
          const stripped = userMessage
            .replace(/\b(cherche[r]?|search|trouve[r]?|find|look\s*up|fetch|ncbi|genbank|pubmed|entrez|blast|sur|in|on|dans|for|pour|with|avec|the|la|le|les|un|une|des|prot[ée]ine?s?|proteins?|blast|me|please|moi|stp|svp)\b/gi, ' ')
            .replace(/[^\w\s\-\.]/g, ' ')
            .replace(/\s{2,}/g, ' ').trim();
          const words = stripped.split(/\s+/).filter(w => w.length >= 2);
          return words.slice(0, 5).join(' ') || 'protein';
        })();
        const db = /pubmed/i.test(userMessage) ? 'pubmed' : 'protein';
        try {
          // Step 1: esearch
          const srchRes = await new Promise((resolve, reject) => {
            const r = https.get(
              `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=${db}&term=${encodeURIComponent(q)}&retmax=5&retmode=json&usehistory=n`,
              { headers: { 'User-Agent': 'EpitopX AI/1.0' } },
              (resp) => { let d=''; resp.on('data',c=>{d+=c;}); resp.on('end',()=>resolve({status:resp.statusCode,body:d})); }
            );
            r.on('error', reject); r.setTimeout(8000, () => r.destroy());
          });
          if (srchRes.status === 200) {
            const srchData = JSON.parse(srchRes.body);
            const ids = (srchData.esearchresult?.idlist || []).slice(0, 5);
            if (ids.length) {
              // Step 2: esummary
              const sumRes = await new Promise((resolve, reject) => {
                const r = https.get(
                  `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=${db}&id=${ids.join(',')}&retmode=json`,
                  { headers: { 'User-Agent': 'EpitopX AI/1.0' } },
                  (resp) => { let d=''; resp.on('data',c=>{d+=c;}); resp.on('end',()=>resolve({status:resp.statusCode,body:d})); }
                );
                r.on('error', reject); r.setTimeout(8000, () => r.destroy());
              });
              if (sumRes.status === 200) {
                const sumData = JSON.parse(sumRes.body);
                const uids = sumData.result?.uids || ids;
                const rows = uids.map(id => {
                  const doc = sumData.result?.[id] || {};
                  if (db === 'pubmed') {
                    const title = (doc.title || 'N/A').slice(0, 80);
                    const authors = (doc.authors || []).slice(0,2).map(a=>a.name).join(', ');
                    const year = (doc.pubdate || '').slice(0,4);
                    return `| [${id}](https://pubmed.ncbi.nlm.nih.gov/${id}) | ${title} | ${authors} | ${year} |`;
                  } else {
                    const title = (doc.title || doc.defline || doc.name || 'N/A').slice(0, 60);
                    const org = (doc.organism || doc.taxname || '—').slice(0, 25);
                    const len = doc.slen || doc.length || '?';
                    return `| [${id}](https://www.ncbi.nlm.nih.gov/protein/${id}) | ${title} | ${org} | ${len} aa |`;
                  }
                }).join('\n');
                const header = db === 'pubmed'
                  ? `| PMID | Titre | Auteurs | Année |\n|---|---|---|---|`
                  : `| ID | Titre | Organisme | Taille |\n|---|---|---|---|`;
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ analysis: `## 🔎 NCBI ${db === 'pubmed' ? 'PubMed' : 'Protein'} — "${q}" (${srchData.esearchresult?.count || ids.length} résultats)\n\n${header}\n${rows}\n\n→ [Recherche NCBI complète](ncbi-search.html?q=${encodeURIComponent(q)})` }));
                return;
              }
            }
          }
        } catch (ncbiErr) {
          log.warn('agent', `NCBI search failed: ${ncbiErr.message}`);
        }
        // Fallback to links
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis: `## 🔎 NCBI — "${q}"\n\n**Liens directs :**\n- 🧬 [Protein](https://www.ncbi.nlm.nih.gov/protein/?term=${encodeURIComponent(q)}) — séquences protéiques\n- 📄 [PubMed](https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(q)}) — articles scientifiques\n- 🔗 [Nucleotide](https://www.ncbi.nlm.nih.gov/nucleotide/?term=${encodeURIComponent(q)}) — séquences ADN/ARN\n- 🏗️ [Structure](https://www.ncbi.nlm.nih.gov/structure/?term=${encodeURIComponent(q)}) — structures 3D\n\n→ [Rech. NCBI intégrée](ncbi-search.html?q=${encodeURIComponent(q)})` }));
        return;
      }

      // ── Detect raw AA SEQUENCE analysis (pasted sequence with no other intent) ─
      const rawSeqMatch = userMessage.match(/^[>\s]*(?:[^\n]+\n)?([ACDEFGHIKLMNPQRSTVWY\n\s]{20,})$/i);
      if (rawSeqMatch || (/^[ACDEFGHIKLMNPQRSTVWY]{20,}$/.test(userMessage.replace(/\s+/g, '')))) {
        const rawSeq = (rawSeqMatch ? rawSeqMatch[1] : userMessage).replace(/\s+/g, '').toUpperCase();
        if (rawSeq.length >= 20) {
          const aa = { A:0,R:0,N:0,D:0,C:0,Q:0,E:0,G:0,H:0,I:0,L:0,K:0,M:0,F:0,P:0,S:0,T:0,W:0,Y:0,V:0 };
          for (const c of rawSeq) { if (aa[c] !== undefined) aa[c]++; }
          const mwMap = {A:89,R:174,N:132,D:133,C:121,Q:146,E:147,G:75,H:155,I:131,L:131,K:146,M:149,F:165,P:115,S:105,T:119,W:204,Y:181,V:117};
          const mw = (Object.entries(aa).reduce((s,[k,v]) => s + (mwMap[k]||0)*v, 0) / 1000).toFixed(1);
          const top5 = Object.entries(aa).sort((a,b) => b[1]-a[1]).slice(0,5).map(([k,v]) => `${k}:${((v/rawSeq.length)*100).toFixed(1)}%`).join(', ');
          const hasSignalP = /^M[A-Z]{10,30}[LI]/i.test(rawSeq);
          const isCysPoor = ((aa.C||0)/rawSeq.length) < 0.01;
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ analysis: `## 🔬 Analyse de Séquence\n\n**Longueur :** ${rawSeq.length} acides aminés\n**Masse moléculaire estimée :** ~${mw} kDa\n**Top 5 AA :** ${top5}\n**Signal peptide possible :** ${hasSignalP ? '✅ Oui (début M suivi hydrophobe)' : '❌ Non détecté'}\n**Cystéines rares :** ${isCysPoor ? '⚠️ Pauvre en Cys (< 1%)' : 'Normal'}\n\n**Séquence (${rawSeq.length} aa) :**\n\`\`\`\n${rawSeq.match(/.{1,60}/g).join('\n')}\n\`\`\`\n\n**Actions suggérées :**\n- 🎯 *"Prédit les épitopes de cette séquence"*\n- 💾 *"Crée une protéine nommée [nom] avec la séquence [cette séquence]"*\n- 🔍 [BLAST](ncbi-search.html) — comparer avec des séquences connues\n\n→ [Alignement MSA](msa-analysis.html) | [Recherche UniProt](protein-search.html)` }));
          return;
        }
      }

      // ── Detect DNA/RNA TRANSLATION intent ────────────────────────────────
      const hasDnaSeq = userMessage.match(/\b([ACGTU]{12,})\b/i);
      const wantsTranslate = /(?:traduis?|traduire|translate|traduction|translation)\b/i.test(userMessage);
      if (hasDnaSeq && (wantsTranslate || /\b(?:adn|dna|arn|rna|s[ée]quence|codon)\b/i.test(userMessage))) {
        const dna = hasDnaSeq[1].toUpperCase().replace(/U/g, 'T');
        const CT = {
          TTT:'F',TTC:'F',TTA:'L',TTG:'L',CTT:'L',CTC:'L',CTA:'L',CTG:'L',
          ATT:'I',ATC:'I',ATA:'I',ATG:'M',GTT:'V',GTC:'V',GTA:'V',GTG:'V',
          TCT:'S',TCC:'S',TCA:'S',TCG:'S',CCT:'P',CCC:'P',CCA:'P',CCG:'P',
          ACT:'T',ACC:'T',ACA:'T',ACG:'T',GCT:'A',GCC:'A',GCA:'A',GCG:'A',
          TAT:'Y',TAC:'Y',TAA:'*',TAG:'*',CAT:'H',CAC:'H',CAA:'Q',CAG:'Q',
          AAT:'N',AAC:'N',AAA:'K',AAG:'K',GAT:'D',GAC:'D',GAA:'E',GAG:'E',
          TGT:'C',TGC:'C',TGA:'*',TGG:'W',CGT:'R',CGC:'R',CGA:'R',CGG:'R',
          AGT:'S',AGC:'S',AGA:'R',AGG:'R',GGT:'G',GGC:'G',GGA:'G',GGG:'G',
        };
        let protein = '', stopAt = dna.length;
        for (let i = 0; i + 2 < dna.length; i += 3) {
          const aa = CT[dna.slice(i, i + 3)];
          if (aa === '*') { stopAt = i; break; }
          protein += aa || 'X';
        }
        const gc = ((dna.split('').filter(c => c === 'G' || c === 'C').length / dna.length) * 100).toFixed(1);
        const comp = dna.split('').map(c => ({A:'T',T:'A',G:'C',C:'G'}[c] || c)).join('');
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis: `## 🔗 Traduction ADN → Protéine\n\n**Séquence ADN :** \`${dna}\`\n**Longueur :** ${dna.length} nt | **Codons :** ${Math.floor(dna.length / 3)} | **%GC :** ${gc}%\n**Brin complémentaire :** \`${comp}\`\n\n**Protéine traduite${stopAt < dna.length ? ' (codon stop @ pos ' + stopAt + ')' : ''} :**\n\`\`\`\n${protein || '(trop court)'}\n\`\`\`\n**Longueur protéique :** ${protein.length} aa\n\n> 💡 *"Crée une protéine nommée [nom] avec la séquence \`${protein}\`"* pour la sauvegarder.\n\n→ [Alignement ADN](dna-alignment.html) | [Analyse MSA](msa-analysis.html)` }));
        return;
      }

      // ── Offline fallback when no LLM API key ────────────────────────────
      if (!LLM_API_KEY) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ analysis: buildOfflineReply(userMessage, proteinList) }));
        return;
      }


      // ── Detect epitope-prediction intent and run the analysis ─────────────
      let epitopeResultContext = '';
      const wantsEpitope = /epitop|predict|pr[eé]dis?|best.*peptide|b.cell|t.cell|antigen|immunogen/i.test(userMessage);
      if (wantsEpitope) {
        // Find which protein the user is referring to — by name match first
        let targetProtein = null;
        let targetSequence = null;
        let targetLabel = null;

        for (const p of proteinList) {
          if (msgLower.includes(p.name.toLowerCase())) { targetProtein = p; break; }
        }
        // "my protein", "this protein", "the protein" → pick first/only one if DB has exactly 1
        if (!targetProtein && proteinList.length === 1) targetProtein = proteinList[0];

        if (targetProtein) {
          targetSequence = targetProtein.sequence;
          targetLabel = targetProtein.name;
        } else {
          // Helper: extract longest AA sequence from a text string
          const extractSeq = (text) => {
            const matches = text.match(/[ACDEFGHIKLMNPQRSTVWY]{20,}/gi);
            if (!matches) return null;
            return matches.sort((a, b) => b.length - a.length)[0].toUpperCase();
          };

          // 1. Try current message first
          let found = extractSeq(userMessage);

          // 2. If not found (e.g. user said "cette séquence"), search conversation history
          if (!found && history.length) {
            for (let i = history.length - 1; i >= 0; i--) {
              const hSeq = extractSeq(history[i].content || '');
              if (hSeq && hSeq.length >= 20) { found = hSeq; break; }
            }
          }

          if (found && found.length >= 20) {
            targetSequence = found;
            targetLabel = `séquence (${found.length} aa)`;
          }
        }

        if (targetSequence) {
          // ── 1. Local EpitopX backend prediction ──────────────────────────────
          let localEpitopes = [];
          try {
            log.info('agent', `Running EpitopX prediction for ${targetLabel}`);
            const epPayload = {
              sequence: targetSequence,
              method: 'core',
              min_length: 9,
              max_length: 20,
              min_score: 0.5,
              top_n: 20,
            };
            if (targetProtein) epPayload.protein_id = targetProtein.id;
            const epRes = await djangoPost('/api/epitopes/analyze/', epPayload);
            if (epRes.status === 200 || epRes.status === 201) {
              const epData = JSON.parse(epRes.body);
              localEpitopes = (epData.epitopes || epData.top_epitopes || []).slice(0, 20);
            }
          } catch (epErr) {
            log.warn('agent', `EpitopX prediction failed: ${epErr.message}`);
          }

          // ── 2. IEDB BepiPred-2.0 B-cell prediction (external online tool) ───
          let bepipredEpitopes = [];
          try {
            log.info('agent', `Running IEDB BepiPred-2.0 for ${targetLabel}`);
            const fasta = `>query\n${targetSequence}`;
            const formBody = `method=Bepipred-2.0&sequence_text=${encodeURIComponent(fasta)}`;
            const formBuf = Buffer.from(formBody);
            const iedbRes = await new Promise((resolve, reject) => {
              const r = http.request({
                hostname: 'tools.iedb.org',
                path: '/tools_api/bcell/',
                method: 'POST',
                headers: {
                  'Content-Type': 'application/x-www-form-urlencoded',
                  'Content-Length': formBuf.length,
                },
              }, (resp) => {
                let d = '';
                resp.on('data', c => { d += c; });
                resp.on('end', () => resolve({ status: resp.statusCode, body: d }));
              });
              r.on('error', reject);
              r.setTimeout(15000, () => r.destroy());
              r.write(formBuf);
              r.end();
            });
            if (iedbRes.status === 200 && iedbRes.body.includes('\t')) {
              const rows = iedbRes.body.trim().split('\n')
                .map(l => l.split('\t'))
                .filter(p => p.length >= 3 && /^\d+$/.test((p[0] || '').trim()));
              const scores = rows.map(p => ({
                pos: parseInt(p[0]),
                aa: (p[1] || '?').trim(),
                score: parseFloat(p[2]) || 0,
              }));
              // Collect consecutive windows with score >= 0.5 (BepiPred threshold), min 9 aa
              let wStart = -1, epBuf = '';
              for (let i = 0; i <= scores.length; i++) {
                const above = i < scores.length && scores[i].score >= 0.5;
                if (above) {
                  if (wStart < 0) { wStart = i; epBuf = ''; }
                  epBuf += scores[i].aa;
                } else if (wStart >= 0) {
                  if (epBuf.length >= 9) {
                    const sl = scores.slice(wStart, i);
                    const avg = sl.reduce((s, x) => s + x.score, 0) / sl.length;
                    bepipredEpitopes.push({ start: scores[wStart].pos, end: scores[i - 1].pos, seq: epBuf, avg });
                  }
                  wStart = -1; epBuf = '';
                }
              }
              bepipredEpitopes.sort((a, b) => b.avg - a.avg);
              log.info('agent', `BepiPred-2.0: found ${bepipredEpitopes.length} epitope regions`);
            }
          } catch (iedbErr) {
            log.warn('agent', `IEDB BepiPred-2.0 failed: ${iedbErr.message}`);
          }

          // ── 3. IEDB DB search — experimentally validated epitopes ────────────
          let iedbDbHits = [];
          try {
            const topPeps = localEpitopes.slice(0, 4)
              .map(e => (e.sequence || e.epitope_sequence || '').toUpperCase())
              .filter(p => p.length >= 9);
            for (const pep of topPeps) {
              const dbRes = await new Promise((resolve, reject) => {
                const r = https.get(
                  `https://query.iedb.org/search?format=json&q=linear_sequence_text:${encodeURIComponent(pep)}&size=3`,
                  { headers: { Accept: 'application/json' } },
                  (resp) => {
                    let d = '';
                    resp.on('data', c => { d += c; });
                    resp.on('end', () => resolve({ status: resp.statusCode, body: d }));
                  }
                );
                r.on('error', reject);
                r.setTimeout(8000, () => r.destroy());
              });
              if (dbRes.status === 200) {
                try {
                  const parsed = JSON.parse(dbRes.body);
                  const hits = Array.isArray(parsed.hits?.hits) ? parsed.hits.hits
                    : Array.isArray(parsed.results) ? parsed.results
                    : Array.isArray(parsed) ? parsed : [];
                  if (hits.length) {
                    const sample = hits[0]._source || hits[0];
                    iedbDbHits.push({ pep, count: hits.length, antigen: sample.antigen_name || sample.description || '' });
                  }
                } catch { /* ignore parse errors */ }
              }
            }
          } catch (dbErr) {
            log.warn('agent', `IEDB DB search failed: ${dbErr.message}`);
          }

          // ── Build combined context for the LLM ───────────────────────────────
          if (localEpitopes.length || bepipredEpitopes.length) {
            const bpSeqs = new Set(bepipredEpitopes.map(e => e.seq.toUpperCase()));
            const dbHitPeps = new Set(iedbDbHits.map(h => h.pep));
            epitopeResultContext = `\n\n## ✅ EpitopX backend prediction for **${targetLabel}**:\n`
              + `Method: core (Hopp-Woods, Kyte-Doolittle, Karplus-Schulz, Emini, Kolaskar)\n\n`
              + `| Rank | Position | Len | Score | Sequence | BepiPred-2.0? | In IEDB DB? |\n`
              + `|------|----------|-----|-------|----------|---------------|-------------|\n`
              + localEpitopes.map((e, i) => {
                  const seq = (e.sequence || e.epitope_sequence || '').toUpperCase();
                  const bpOk = bpSeqs.has(seq) || [...bpSeqs].some(s => s.includes(seq) || seq.includes(s));
                  const dbOk = dbHitPeps.has(seq);
                  return `| ${i+1} | ${e.start}–${e.end} | ${e.length || (e.end - e.start + 1)} | ${Number(e.score).toFixed(4)} | \`${seq}\` | ${bpOk ? '✅ YES' : '—'} | ${dbOk ? '🧪 YES' : '—'} |`;
                }).join('\n');

            if (bepipredEpitopes.length) {
              epitopeResultContext += `\n\n## 🌐 IEDB BepiPred-2.0 online prediction (external validation):\n`
                + `| Rank | Position | Len | Avg Score | Sequence |\n|------|----------|-----|-----------|----------|\n`
                + bepipredEpitopes.slice(0, 10).map((e, i) =>
                    `| ${i+1} | ${e.start}–${e.end} | ${e.seq.length} | ${e.avg.toFixed(4)} | \`${e.seq}\` |`
                  ).join('\n');
            }

            if (iedbDbHits.length) {
              epitopeResultContext += `\n\n## 🧪 Experimentally validated in IEDB database:\n`
                + iedbDbHits.map(h =>
                    `- \`${h.pep}\` — ${h.count} published experiment(s)${h.antigen ? ` · ${h.antigen}` : ''}`
                  ).join('\n');
            }

            epitopeResultContext += `\n\nINSTRUCTIONS FOR YOUR RESPONSE:\n`
              + `1. Briefly summarize how many epitopes were found by each method.\n`
              + `2. Highlight epitopes confirmed by BOTH EpitopX AND BepiPred-2.0 as the MOST RELIABLE (double-confirmed).\n`
              + `3. Rank experimentally validated IEDB epitopes HIGHEST of all.\n`
              + `4. Give a clear final TOP 5 list of best epitopes for experimental work.\n`
              + `5. Do NOT invent epitopes outside what is listed above.`;
          }
        }
      }

      const systemPrompt = `You are EpitopX AI, an expert bioinformatics assistant integrated into the EpitopX platform.
You have FULL access to the user's local EpitopX database (proteins, epitopes, sequences stored on this server).
You help researchers with questions about proteins, epitopes, DNA/RNA sequences, structural biology, immunology, and bioinformatics tools.

IMPORTANT INSTRUCTIONS:
- Respond in the SAME LANGUAGE as the user's message (French if French, English if English, etc.)
- When asked about proteins "in the dashboard" or "in my database", refer to the protein list provided below.
- When given a protein name or accession, provide a structured analysis: function, key domains, epitope regions, associated organisms/diseases, clinical significance.
- When given a FASTA sequence, identify the type, notable motifs, and suggest relevant analyses.
- For epitope questions: distinguish B-cell epitopes (linear + conformational), T-cell epitopes (MHC-I 8-10aa, MHC-II 13-25aa). When both EpitopX and IEDB BepiPred-2.0 results are provided, cross-reference them: epitopes confirmed by BOTH tools are the most reliable candidates. Epitopes found in the IEDB database (experimentally validated) rank highest.
- For bioinformatics tools: you have already RUN the following tools automatically when data was available: EpitopX epitope prediction (core method), IEDB BepiPred-2.0, IEDB DB search, MSA alignment, NW protein comparison, NCBI search. Present those results directly.
- Cite relevant databases (UniProt, IEDB, PDB, NCBI, AlphaFold) when appropriate.
- Format responses with markdown: use **bold**, ## headers, bullet lists, tables, and code blocks.
- Keep answers under 800 words and well-structured. Be precise and scientifically accurate.${dbContext}${epitopeResultContext}${memoryContext ? '\n\n' + memoryContext : ''}`;

      const messages = [
        { role: 'system', content: systemPrompt },
        ...history,
        { role: 'user', content: userMessage },
      ];

      const llmPayload = JSON.stringify({
        model: modelOverride || LLM_MODEL,
        messages,
        max_tokens: 1024,
        temperature: 0.3,
        stream: true,   // stream token-by-token
      });

      const llmBody = Buffer.from(llmPayload);
      const llmUrl  = new URL('https://openrouter.ai/api/v1/chat/completions');

      const llmReq = https.request({
        hostname: llmUrl.hostname,
        path:     llmUrl.pathname,
        method:   'POST',
        headers: {
          'Content-Type':   'application/json',
          'Authorization':  `Bearer ${LLM_API_KEY}`,
          'HTTP-Referer':   process.env.SITE_URL || 'https://epitopx-frontend.onrender.com',
          'X-Title':        'EpitopX AI',
          'Content-Length': llmBody.length,
        },
      }, (llmRes) => {
        if (llmRes.statusCode !== 200) {
          let errBody = '';
          llmRes.on('data', c => { errBody += c; });
          llmRes.on('end', () => {
            log.warn('llm', `OpenRouter ${llmRes.statusCode}: ${errBody.slice(0, 200)}`);
            if (!res.headersSent) {
              // If we have epitope/tool results, return them even if LLM fails
              if (epitopeResultContext) {
                const fallbackText = epitopeResultContext
                  .replace(/\n\nINSTRUCTIONS FOR YOUR RESPONSE:[\s\S]*$/, '')
                  + '\n\n> ⚠️ *Analyse IA temporairement indisponible (modèle LLM limité). Résultats bruts ci-dessus.*';
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ analysis: fallbackText.trim() }));
              } else {
                const offlineReply = buildOfflineReply(userMessage, proteinList);
                if (offlineReply) {
                  res.writeHead(200, { 'Content-Type': 'application/json' });
                  res.end(JSON.stringify({ analysis: offlineReply }));
                } else {
                  res.writeHead(200, { 'Content-Type': 'application/json' });
                  res.end(JSON.stringify({ analysis: '⚠️ Le modèle IA est temporairement limité. Veuillez réessayer dans quelques secondes, ou essayez une question précise (liste de protéines, prédiction d\'épitopes, recherche NCBI, etc.).' }));
                }
              }
            }
          });
          return;
        }
        // Pipe SSE stream directly to client — first token arrives in < 1 s
        res.writeHead(200, {
          'Content-Type':    'text/event-stream; charset=utf-8',
          'Cache-Control':   'no-cache',
          'X-Accel-Buffering': 'no',
        });
        llmRes.pipe(res);
        llmRes.on('end', () => log.info('llm', `Streamed reply to "${userMessage.slice(0,60)}"`));
      });

      const llmFallback = (label) => {
        if (res.headersSent) return;
        if (epitopeResultContext) {
          const ft = epitopeResultContext.replace(/\n\nINSTRUCTIONS FOR YOUR RESPONSE:[\s\S]*$/, '')
            + `\n\n> ⚠️ *${label}. Résultats bruts ci-dessus.*`;
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ analysis: ft.trim() }));
        } else {
          const offline = buildOfflineReply(userMessage, proteinList);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ analysis: offline || `⚠️ ${label}. Essayez une question précise comme "liste mes protéines" ou "prédit les épitopes de [nom]".` }));
        }
      };
      llmReq.on('error', (err) => {
        log.error('llm', `LLM request error: ${err.message}`);
        llmFallback(`Erreur LLM: ${err.message}`);
      });
      llmReq.setTimeout(30000, () => {
        llmReq.destroy();
        llmFallback('Délai LLM dépassé (30s)');
      });
      llmReq.write(llmBody);
      llmReq.end();
    } catch (err) {
      log.error('llm', `analyze-protein error: ${err.message}`);
      if (!res.headersSent) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // -- Proxy /api/* and /media/* → remote backend -------------------------
  if (pathname.startsWith('/api/') || pathname.startsWith('/media/')) {
    const target = REMOTE_API + req.url;

    try {
      const bodyBuffer = await collectBody(req);
      proxyRequest({
        tag: 'backend-proxy',
        targetUrl: target,
        method: req.method,
        headers: {
          ...req.headers,
          host: new URL(REMOTE_API).host,
          'ngrok-skip-browser-warning': 'true',
          ...(bodyBuffer.length ? { 'content-length': bodyBuffer.length } : {}),
        },
        body: bodyBuffer.length ? bodyBuffer : undefined,
        timeout: 60000,
        cacheable: req.method === 'GET' && pathname.startsWith('/media/'),
        res,
      });
    } catch (err) {
      if (!res.headersSent) {
        res.writeHead(413, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // -----------------------------------------------------------------------
  // -- Static file server (with path traversal protection) ----------------
  // -----------------------------------------------------------------------

  const requestedPath = parsed.pathname === '/' ? '/index.html' : parsed.pathname;
  const filePath = safePath(requestedPath);

  if (!filePath) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('403 Forbidden');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }

    const ext = path.extname(filePath);
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    const cacheControl = (ext === '.html' || ext === '.js' || ext === '.css')
      ? 'no-cache, no-store, must-revalidate'
      : 'public, max-age=86400';

    res.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': stats.size,
      'Cache-Control': cacheControl,
    });
    fs.createReadStream(filePath).pipe(res);
  });
});

// -------------------------------------------------------------------------
// -- Startup --------------------------------------------------------------
// -------------------------------------------------------------------------

server.listen(PORT, '0.0.0.0', () => {
  log.info('server', `EpitopX AI dev server running at http://0.0.0.0:${PORT}`);
  log.info('server', `API proxy: /api/* ? ${REMOTE_API}/api/*`);
  log.info('server', `UniProt proxy: /api/uniprot/* ? rest.uniprot.org (cached, throttled)`);
  log.info('server', `NCBI proxy: /api/ncbi/* ? eutils.ncbi.nlm.nih.gov (cached, throttled)`);
  log.info('server', `BLAST proxy: /api/blast/* ? blast.ncbi.nlm.nih.gov (throttled)`);
  log.info('server', `Alignment proxy: /api/alignment/* ? ${process.env.ALIGNMENT_API || 'http://localhost:8000'}/msa/align/`);
  log.info('server', `Epitope proxy: /api/epitopes/* ? ${EPITOPE_API}`);
  log.info('server', `Rate limits: ${RATE_LIMITS.general.max} req/min (general), ${RATE_LIMITS.apiProxy.max} req/min (API proxy)`);
  log.info('server', `Cache: max ${cache.maxEntries} entries | Throttle: 2-3 concurrent/host`);
  log.info('server', `Status endpoint: /api/_status`);

  // Startup health-check
  try {
    const _remoteHost = new URL(REMOTE_API);
    const _checkReq = https.request({
      hostname: _remoteHost.hostname,
      path: '/api/proteins/',
      method: 'HEAD',
      headers: { 'ngrok-skip-browser-warning': 'true' },
      timeout: 6000,
    }, (_res) => {
      if (_res.statusCode >= 500) {
        log.warn('health', `Remote API returned HTTP ${_res.statusCode} � backend may be down`);
      } else {
        log.info('health', `Remote API reachable (HTTP ${_res.statusCode})`);
      }
      _res.resume();
    });
    _checkReq.on('timeout', () => {
      _checkReq.destroy();
      log.warn('health', 'Remote API health-check timed out � update REMOTE_API if using ngrok');
    });
    _checkReq.on('error', (_err) => {
      log.error('health', `Remote API UNREACHABLE: ${_err.message}`);
    });
    _checkReq.end();
  } catch (_) { /* malformed REMOTE_API URL � skip check */ }
});

// -- Graceful shutdown ----------------------------------------------------
function shutdown() {
  log.info('server', 'Shutting down�');
  cache.destroy();
  server.close(() => process.exit(0));
  // Force exit after 5s if connections are still open
  setTimeout(() => process.exit(1), 5000);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
