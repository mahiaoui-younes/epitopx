/**
 * EpitopX AI — Shared Sidebar Logic
 * Handles: active page detection, collapse toggle, mobile open/close, auth profile
 */
(function () {
  'use strict';

  /* ── route guard ─────────────────────────────────────────── */
  const PUBLIC_PAGES = ['index.html', 'login.html', 'signup.html', 'pricing.html', 'viewer.html', 'privacy.html', 'cookies.html', 'welcome.html', ''];
  const currentPage  = location.pathname.split('/').pop() || 'index.html';

  if (!PUBLIC_PAGES.includes(currentPage) &&
      (typeof Auth === 'undefined' || !Auth.isAuthenticated())) {
    window.location.replace('login.html');
  }

  /* ── AI Agent pinned button + grouped nav ────────────────── */
  function enhanceSidebar() {
    const sbNav = document.querySelector('#sidebar .sb-nav');
    if (!sbNav) return;

    // 1. Inject pinned AI Agent button before the nav
    if (!document.getElementById('sb-agent-pin')) {
      const pin = document.createElement('div');
      pin.id = 'sb-agent-pin';
      pin.innerHTML = `
        <a href="agent.html" id="sb-agent-link"
          style="display:flex;align-items:center;gap:.625rem;
                 margin:.625rem .75rem .5rem;
                 padding:.65rem .875rem;
                 border-radius:.875rem;
                 background:linear-gradient(135deg,rgba(99,102,241,.12),rgba(59,130,246,.12));
                 border:1px solid rgba(99,102,241,.35);
                 text-decoration:none;
                 position:relative;overflow:hidden;
                 transition:all .2s ease;
                 box-shadow:0 0 0 0 rgba(99,102,241,.3);
                 animation:sb-agent-pulse 3s ease-in-out infinite;"
          onmouseover="this.style.background='linear-gradient(135deg,rgba(99,102,241,.2),rgba(59,130,246,.2))';this.style.borderColor='rgba(99,102,241,.6)';"
          onmouseout="this.style.background='linear-gradient(135deg,rgba(99,102,241,.12),rgba(59,130,246,.12))';this.style.borderColor='rgba(99,102,241,.35)';"
        >
          <div style="width:30px;height:30px;border-radius:.5rem;flex-shrink:0;
                      background:linear-gradient(135deg,#6366f1,#3b82f6);
                      display:flex;align-items:center;justify-content:center;
                      font-size:.95rem;box-shadow:0 3px 10px rgba(99,102,241,.4);">🤖</div>
          <div class="sb-item-label" style="flex:1;min-width:0;">
            <div style="font-size:.8125rem;font-weight:700;color:#4f46e5;line-height:1.2;">AI Assistant</div>
            <div style="font-size:.67rem;color:#94a3b8;margin-top:.1rem;">Ask anything in natural language</div>
          </div>
          <span class="sb-item-label" style="font-size:.58rem;font-weight:700;letter-spacing:.05em;
            background:linear-gradient(135deg,#6366f1,#3b82f6);color:#fff;
            padding:.15rem .45rem;border-radius:.3rem;flex-shrink:0;">AI</span>
        </a>
      `;
      sbNav.parentNode.insertBefore(pin, sbNav);
    }

    // 2. Group the existing nav items with labels
    const groups = [
      {
        label: 'MAIN',
        pages: ['index.html', 'dashboard.html'],
      },
      {
        label: 'PROTEIN TOOLS',
        pages: ['protein-search.html', 'ncbi-search.html', 'my-proteins.html'],
      },
      {
        label: 'EPITOPE TOOLS',
        pages: ['epitope-search.html', 'epitope-details.html'],
      },
      {
        label: 'ANALYSIS',
        pages: ['viewer.html', 'compare.html', 'dna-alignment.html', 'msa-analysis.html'],
      },
    ];

    // Remove the generic single group label if present
    const genericLabel = sbNav.querySelector('.sb-group-label');
    if (genericLabel) genericLabel.remove();

    // Collect all sb-items
    const items = Array.from(sbNav.querySelectorAll('a.sb-item'));
    if (!items.length) return;

    // Clear nav, re-inject grouped
    sbNav.innerHTML = '';

    groups.forEach(group => {
      const groupItems = items.filter(el => {
        const href = (el.getAttribute('href') || '').split('/').pop();
        return group.pages.includes(href);
      });
      if (!groupItems.length) return;

      const lbl = document.createElement('span');
      lbl.className = 'sb-group-label';
      lbl.style.cssText = 'font-size:.6rem;font-weight:700;letter-spacing:.12em;color:#94a3b8;text-transform:uppercase;padding:.75rem .875rem .25rem;display:block;';
      lbl.textContent = group.label;
      sbNav.appendChild(lbl);

      groupItems.forEach(el => sbNav.appendChild(el));
    });

    // Remaining items (settings, agent — exclude agent since it's pinned)
    const groupedPages = groups.flatMap(g => g.pages);
    const remaining = items.filter(el => {
      const href = (el.getAttribute('href') || '').split('/').pop();
      return !groupedPages.includes(href) && href !== 'agent.html';
    });
    if (remaining.length) {
      const sep = document.createElement('div');
      sep.style.cssText = 'height:1px;background:#f1f5f9;margin:.5rem .75rem;';
      sbNav.appendChild(sep);
      remaining.forEach(el => sbNav.appendChild(el));
    }

    // Highlight active agent link
    if (currentPage === 'agent.html') {
      const agentLink = document.getElementById('sb-agent-link');
      if (agentLink) {
        agentLink.style.background = 'linear-gradient(135deg,rgba(99,102,241,.22),rgba(59,130,246,.22))';
        agentLink.style.borderColor = 'rgba(99,102,241,.6)';
      }
    }
  }

  /* ── helpers ─────────────────────────────────────────────── */
  const esc = Utils.escapeHTML;

  function getInitials(username) {
    if (!username) return '?';
    const parts = username.split(/[_.\s-]/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return username.slice(0, 2).toUpperCase();
  }

  function getAuthUser() {
    try { return JSON.parse(localStorage.getItem('authUser')); } catch { return null; }
  }

  /* ── sidebar auth panel ───────────────────────────────────── */
  function renderSidebarAuth() {
    const sbBottom = document.querySelector('#sidebar .sb-bottom');
    if (!sbBottom) return;

    const existing = document.getElementById('sb-auth-panel');
    if (existing) existing.remove();

    const token = (typeof Auth !== 'undefined' ? Auth.getAuthToken() : null)
                || sessionStorage.getItem('_authSession'); // treat session flag as "logged in"
    const user  = getAuthUser();
    const panel = document.createElement('div');
    panel.id = 'sb-auth-panel';
    panel.style.cssText = 'padding:0.5rem 0.75rem 0.25rem;';

    if (token && user) {
      const initials = esc(getInitials(user.username));
      panel.innerHTML = `
        <div id="sb-profile-btn"
          style="display:flex;align-items:center;gap:0.625rem;padding:0.5rem 0.625rem;
                 border-radius:0.75rem;cursor:pointer;transition:background 0.15s;
                 background:rgba(37,99,235,0.06);border:1px solid rgba(37,99,235,0.12);"
          onmouseover="this.style.background='rgba(37,99,235,0.11)'"
          onmouseout="this.style.background='rgba(37,99,235,0.06)'">
          <div style="width:2rem;height:2rem;border-radius:50%;
                      background:linear-gradient(135deg,#2563eb,#0d9488);
                      display:flex;align-items:center;justify-content:center;
                      color:#fff;font-weight:700;font-size:0.7rem;flex-shrink:0;letter-spacing:0.03em;">
            ${initials}
          </div>
          <div class="sb-item-label" style="flex:1;overflow:hidden;min-width:0;">
            <div style="font-size:0.8125rem;font-weight:600;color:#1e293b;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              ${esc(user.username)}
            </div>
            <div style="font-size:0.6875rem;color:#10b981;">● Connecté</div>
          </div>
          <svg class="sb-item-label" style="width:1rem;height:1rem;color:#94a3b8;flex-shrink:0;
               transition:transform 0.2s;" id="sb-profile-chevron"
               fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
          </svg>
        </div>
        <div id="sb-profile-dropdown"
          style="display:none;margin-top:0.25rem;background:#fff;
                 border:1px solid #e2e8f0;border-radius:0.75rem;
                 box-shadow:0 4px 16px rgba(0,0,0,0.08);overflow:hidden;">
          <div style="padding:0.75rem 0.875rem;border-bottom:1px solid #f1f5f9;
                      display:flex;align-items:center;gap:0.625rem;">
            <div style="width:2.5rem;height:2.5rem;border-radius:50%;flex-shrink:0;
                        background:linear-gradient(135deg,#2563eb,#0d9488);
                        display:flex;align-items:center;justify-content:center;
                        color:#fff;font-weight:700;font-size:0.8rem;">
              ${initials}
            </div>
            <div>
              <div style="font-size:0.875rem;font-weight:700;color:#1e293b;">${esc(user.username)}</div>
              ${user.email ? `<div style="font-size:0.7rem;color:#64748b;">${esc(user.email)}</div>` : ''}
            </div>
          </div>
          <a href="settings.html"
            style="display:flex;align-items:center;gap:0.5rem;
                   padding:0.6rem 0.875rem;font-size:0.8125rem;color:#374151;
                   text-decoration:none;transition:background 0.15s;"
            onmouseover="this.style.background='#f8fafc'"
            onmouseout="this.style.background='none'">
            <svg style="width:0.875rem;height:0.875rem;color:#64748b;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            Param\u00e8tres
          </a>
          <button onclick="sbLogout()"
            style="width:100%;display:flex;align-items:center;gap:0.5rem;
                   padding:0.6rem 0.875rem;font-size:0.8125rem;color:#ef4444;
                   background:none;border:none;cursor:pointer;transition:background 0.15s;font-family:inherit;"
            onmouseover="this.style.background='#fef2f2'"
            onmouseout="this.style.background='none'">
            <svg style="width:0.875rem;height:0.875rem;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
            Se d\u00e9connecter
          </button>
        </div>`;

      panel.querySelector('#sb-profile-btn').addEventListener('click', function () {
        const dd = document.getElementById('sb-profile-dropdown');
        const ch = document.getElementById('sb-profile-chevron');
        const open = dd.style.display === 'block';
        dd.style.display = open ? 'none' : 'block';
        if (ch) ch.style.transform = open ? '' : 'rotate(180deg)';
      });

    } else {
      panel.innerHTML = `
        <div style="display:flex;gap:0.4rem;">
          <a href="login.html" class="btn-secondary sb-item-label"
             style="flex:1;text-align:center;padding:0.4rem 0;font-size:0.78rem;
                    border-radius:0.5rem;display:block;">Connexion</a>
          <a href="signup.html" class="btn-primary sb-item-label"
             style="flex:1;text-align:center;padding:0.4rem 0;font-size:0.78rem;
                    border-radius:0.5rem;display:block;">S'inscrire</a>
        </div>`;
    }

    sbBottom.before(panel);
  }

  /* ── mobile menu auth (index.html only) ─────────────────── */
  function renderMobileMenuAuth() {
    const wrap = document.getElementById('mobile-auth-wrap');
    if (!wrap) return;
    const token = sessionStorage.getItem('_authSession');
    const user  = getAuthUser();
    if (token && user) {
      const initials = esc(getInitials(user.username));
      wrap.innerHTML = `
        <div style="display:flex;align-items:center;gap:0.625rem;padding:0.5rem 0.625rem;
                    border-radius:0.75rem;background:rgba(37,99,235,0.06);
                    border:1px solid rgba(37,99,235,0.12);flex:1;">
          <div style="width:2rem;height:2rem;border-radius:50%;flex-shrink:0;
                      background:linear-gradient(135deg,#2563eb,#0d9488);
                      display:flex;align-items:center;justify-content:center;
                      color:#fff;font-weight:700;font-size:0.7rem;">${initials}</div>
          <div style="flex:1;overflow:hidden;min-width:0;">
            <div style="font-size:0.8125rem;font-weight:600;color:#1e293b;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(user.username)}</div>
            <div style="font-size:0.6875rem;color:#10b981;">● Connecté</div>
          </div>
          <button onclick="sbLogout()"
            style="display:flex;align-items:center;gap:0.25rem;font-size:0.75rem;
                   color:#ef4444;background:none;border:none;cursor:pointer;font-family:inherit;flex-shrink:0;">
            <svg style="width:0.875rem;height:0.875rem;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
            Quitter
          </button>
        </div>`;
    }
  }

  /* ── float-nav auth (index.html only) ───────────────────── */
  function renderFloatNavAuth() {
    const navAuthWrap = document.getElementById('nav-auth-wrap');
    if (!navAuthWrap) return;

    const token = sessionStorage.getItem('_authSession');
    const user  = getAuthUser();

    if (token && user) {
      const initials = esc(getInitials(user.username));
      navAuthWrap.innerHTML = `
        <div style="position:relative;">
          <button id="nav-profile-btn"
            style="display:flex;align-items:center;gap:0.5rem;padding:0.35rem 0.75rem 0.35rem 0.35rem;
                   border-radius:2rem;border:1px solid rgba(37,99,235,0.2);background:rgba(37,99,235,0.06);
                   cursor:pointer;transition:background 0.15s;font-family:inherit;"
            onmouseover="this.style.background='rgba(37,99,235,0.12)'"
            onmouseout="this.style.background='rgba(37,99,235,0.06)'">
            <div style="width:1.75rem;height:1.75rem;border-radius:50%;
                        background:linear-gradient(135deg,#2563eb,#0d9488);
                        display:flex;align-items:center;justify-content:center;
                        color:#fff;font-weight:700;font-size:0.65rem;">
              ${initials}
            </div>
            <span style="font-size:0.8rem;font-weight:600;color:#1e293b;">${esc(user.username)}</span>
            <svg style="width:0.75rem;height:0.75rem;color:#94a3b8;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>
          <div id="nav-profile-dd"
            style="display:none;position:absolute;right:0;top:calc(100% + 0.375rem);
                   background:#fff;border:1px solid #e2e8f0;border-radius:0.875rem;
                   box-shadow:0 8px 24px rgba(0,0,0,0.1);min-width:13rem;z-index:999;overflow:hidden;">
            <div style="padding:0.75rem 1rem;border-bottom:1px solid #f1f5f9;
                        display:flex;align-items:center;gap:0.625rem;">
              <div style="width:2.25rem;height:2.25rem;border-radius:50%;flex-shrink:0;
                          background:linear-gradient(135deg,#2563eb,#0d9488);
                          display:flex;align-items:center;justify-content:center;
                          color:#fff;font-weight:700;font-size:0.75rem;">
                ${initials}
              </div>
              <div>
                <div style="font-size:0.875rem;font-weight:700;color:#1e293b;">${esc(user.username)}</div>
                ${user.email ? `<div style="font-size:0.7rem;color:#64748b;">${esc(user.email)}</div>` : '<div style="font-size:0.7rem;color:#10b981;">● Connecté</div>'}
              </div>
            </div>
            <a href="settings.html"
              style="display:flex;align-items:center;gap:0.5rem;
                     padding:0.6rem 1rem;font-size:0.8125rem;color:#374151;
                     text-decoration:none;transition:background 0.15s;"
              onmouseover="this.style.background='#f8fafc'"
              onmouseout="this.style.background='none'">
              <svg style="width:0.875rem;height:0.875rem;color:#64748b;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Param\u00e8tres
            </a>
            <button onclick="sbLogout()"
              style="width:100%;display:flex;align-items:center;gap:0.5rem;
                     padding:0.6rem 1rem;font-size:0.8125rem;color:#ef4444;
                     background:none;border:none;cursor:pointer;transition:background 0.15s;font-family:inherit;"
              onmouseover="this.style.background='#fef2f2'"
              onmouseout="this.style.background='none'">
              <svg style="width:0.875rem;height:0.875rem;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
              Se d\u00e9connecter
            </button>
          </div>
        </div>`;

      document.getElementById('nav-profile-btn').addEventListener('click', function (e) {
        e.stopPropagation();
        const dd = document.getElementById('nav-profile-dd');
        dd.style.display = dd.style.display === 'block' ? 'none' : 'block';
      });
      document.addEventListener('click', function () {
        const dd = document.getElementById('nav-profile-dd');
        if (dd) dd.style.display = 'none';
      });
    } else {
      navAuthWrap.innerHTML = `
        <a href="login.html" class="btn-secondary" style="padding:0.45rem 1rem;font-size:0.8rem;">Connexion</a>
        <a href="signup.html" class="btn-primary"  style="padding:0.45rem 1rem;font-size:0.8rem;">S'inscrire</a>`;
    }
  }

  /* ── logout ──────────────────────────────────────────────── */
  window.sbLogout = function () {
    if (typeof Auth !== 'undefined') Auth.clearAuthToken();
    localStorage.removeItem('authUser');
    window.location.href = 'login.html';
  };

  /* ── collapse helpers ────────────────────────────────────── */
  function _toggleIcons(collapsed) {
    var collapseIcon = document.getElementById('sb-collapse-icon');
    var expandIcon = document.getElementById('sb-expand-icon');
    if (collapseIcon) collapseIcon.classList.toggle('hidden', collapsed);
    if (expandIcon) expandIcon.classList.toggle('hidden', !collapsed);
  }

  window.toggleSidebar = function () {
    var sb = document.getElementById('sidebar');
    var main = document.getElementById('page-main');
    sb.classList.toggle('collapsed');
    if (main) main.classList.toggle('sidebar-collapsed');
    var collapsed = sb.classList.contains('collapsed');
    _toggleIcons(collapsed);
    localStorage.setItem('sb-collapsed', collapsed ? '1' : '0');
  };

  window.openSidebarMobile = function () {
    document.getElementById('sidebar').classList.add('open');
    document.getElementById('sidebar-overlay').classList.add('visible');
    document.body.style.overflow = 'hidden';
  };

  window.closeSidebarMobile = function () {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('visible');
    document.body.style.overflow = '';
  };

  /* ── init ────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    const page = location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('#sidebar .sb-item').forEach(function (el) {
      el.classList.toggle('sb-item--active', el.getAttribute('href') === page);
    });

    if (window.innerWidth >= 1024 && localStorage.getItem('sb-collapsed') === '1') {
      var sb = document.getElementById('sidebar');
      var main = document.getElementById('page-main');
      if (sb) sb.classList.add('collapsed');
      if (main) main.classList.add('sidebar-collapsed');
      _toggleIcons(true);
    }

    enhanceSidebar();
    renderSidebarAuth();
    renderFloatNavAuth();
    renderMobileMenuAuth();
  });

  /* ── Keyframe for agent pin pulse ────────────────────────── */
  (function injectAgentStyle() {
    if (document.getElementById('sb-agent-style')) return;
    const s = document.createElement('style');
    s.id = 'sb-agent-style';
    s.textContent = `
      @keyframes sb-agent-pulse {
        0%,100% { box-shadow: 0 0 0 0 rgba(99,102,241,0); }
        50%      { box-shadow: 0 0 12px 3px rgba(99,102,241,0.18); }
      }
    `;
    document.head.appendChild(s);
  })();
})();
