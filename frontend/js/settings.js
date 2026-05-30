/**
 * EpitopX AI — Settings page logic
 */

(function () {
  'use strict';

  const SERVER_URL = window.location.origin;

  // ── helpers ──────────────────────────────────────────────
  function getToken() { return (typeof Auth !== 'undefined' ? Auth.getAuthToken() : null) || ''; }

  function getUser() {
    try { return JSON.parse(localStorage.getItem('authUser')) || {}; } catch { return {}; }
  }

  function getInitials(username) {
    if (!username) return '?';
    const parts = username.split(/[_.\s-]/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return username.slice(0, 2).toUpperCase();
  }

  function setStatus(elId, message, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = message;
    el.className = `text-xs ${isError ? 'text-red-500' : 'text-emerald-600'}`;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 4000);
  }

  // ── init ──────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    populateFromCache();
    fetchProfile();
    initTokenDisplay();
    initAboutServer();
    initLangButtons();
    initTabFromHash();
  });

  // ── tabs ──────────────────────────────────────────────────
  window.switchTab = function (tab) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    document.querySelectorAll('.settings-tab').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.remove('hidden');
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    location.hash = tab;
  };

  function initTabFromHash() {
    const hash = location.hash.replace('#', '');
    if (['profile', 'security', 'prefs', 'danger'].includes(hash)) {
      switchTab(hash);
    }
  }

  // ── populate from localStorage ─────────────────────────
  function populateFromCache() {
    const user = getUser();
    if (!user.username) return;

    const initials = getInitials(user.username);
    document.getElementById('settings-avatar').textContent = initials;
    document.getElementById('settings-username-display').textContent = user.username;
    document.getElementById('settings-email-display').textContent = user.email || 'Email non renseigné';
    document.getElementById('pf-username').value = user.username;
    document.getElementById('pf-email').value = user.email || '';
    document.getElementById('session-username').textContent = user.username;
    document.getElementById('delete-confirm-username').textContent = user.username;
  }

  // ── fetch profile from API ─────────────────────────────
  async function fetchProfile() {
    const token = getToken();
    if (!token) return;
    try {
      const res = await fetch('/api/users/profile/', {
        headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' }
      });
      if (!res.ok) return;
      const data = await res.json();

      const username = data.username || getUser().username || '';
      const email    = data.email    || getUser().email    || '';
      const firstName = data.first_name || '';
      const lastName  = data.last_name  || '';

      document.getElementById('pf-username').value  = username;
      document.getElementById('pf-email').value     = email;
      document.getElementById('pf-firstname').value = firstName;
      document.getElementById('pf-lastname').value  = lastName;

      const initials = getInitials(username);
      document.getElementById('settings-avatar').textContent = initials;
      document.getElementById('settings-username-display').textContent = username;
      document.getElementById('settings-email-display').textContent = email || 'Email non renseigné';
      document.getElementById('session-username').textContent = username;
      document.getElementById('delete-confirm-username').textContent = username;

      // update localStorage
      localStorage.setItem('authUser', JSON.stringify({ username, email, first_name: firstName, last_name: lastName }));
    } catch (_) { /* fail silently — cached data shown */ }
  }

  // ── save profile ───────────────────────────────────────
  window.saveProfile = async function (e) {
    e.preventDefault();
    const btn = document.getElementById('profile-save-btn');
    const token = getToken();
    if (!token) { Utils.showToast('Non authentifié', 'error'); return; }

    const body = {
      email:      document.getElementById('pf-email').value.trim(),
      first_name: document.getElementById('pf-firstname').value.trim(),
      last_name:  document.getElementById('pf-lastname').value.trim(),
    };

    btn.disabled = true;
    btn.textContent = 'Enregistrement…';

    try {
      const res = await fetch('/api/users/profile/', {
        method: 'PATCH',
        headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = data.detail || data.email?.[0] || 'Erreur inconnue';
        setStatus('profile-status', msg, true);
        Utils.showToast(msg, 'error');
      } else {
        // update cache
        const current = getUser();
        localStorage.setItem('authUser', JSON.stringify({ ...current, ...body, email: body.email }));
        document.getElementById('settings-email-display').textContent = body.email || 'Email non renseigné';
        setStatus('profile-status', 'Modifications enregistrées', false);
        Utils.showToast('Profil mis à jour', 'success');
      }
    } catch (err) {
      setStatus('profile-status', 'Erreur réseau', true);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Enregistrer les modifications';
    }
  };

  // ── change password ───────────────────────────────────
  window.changePassword = async function (e) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;

    const current = document.getElementById('pw-current').value;
    const newPw   = document.getElementById('pw-new').value;
    const confirm = document.getElementById('pw-confirm').value;
    const btn     = document.getElementById('pw-save-btn');

    if (newPw !== confirm) {
      setStatus('pw-status', 'Les mots de passe ne correspondent pas', true);
      return;
    }
    if (newPw.length < 8) {
      setStatus('pw-status', 'Le mot de passe doit faire au moins 8 caractères', true);
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Modification…';

    try {
      const res = await fetch('/api/users/change-password/', {
        method: 'POST',
        headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password: current, new_password: newPw, confirm_password: confirm })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = data.detail || data.old_password?.[0] || data.new_password?.[0] || 'Erreur inconnue';
        setStatus('pw-status', msg, true);
        Utils.showToast(msg, 'error');
      } else {
        setStatus('pw-status', 'Mot de passe modifié avec succès', false);
        Utils.showToast('Mot de passe changé', 'success');
        document.getElementById('password-form').reset();
        resetPasswordStrength();
      }
    } catch (_) {
      setStatus('pw-status', 'Erreur réseau', true);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Changer le mot de passe';
    }
  };

  // ── password strength ─────────────────────────────────
  window.checkPasswordStrength = function () {
    const pw = document.getElementById('pw-new').value;
    let score = 0;
    if (pw.length >= 8)  score++;
    if (pw.length >= 12) score++;
    if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
    if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) score++;

    const colors  = ['#ef4444', '#f97316', '#eab308', '#22c55e'];
    const labels  = ['Très faible', 'Faible', 'Moyen', 'Fort'];
    for (let i = 1; i <= 4; i++) {
      const bar = document.getElementById(`pw-str-${i}`);
      bar.style.background = i <= score ? colors[score - 1] : '#e5e7eb';
      bar.style.width = i <= score ? '100%' : '0%';
    }
    const label = document.getElementById('pw-str-label');
    label.textContent = pw.length ? labels[score - 1] || '' : '';
    label.style.color = pw.length ? colors[score - 1] : '#9ca3af';
  };

  function resetPasswordStrength() {
    for (let i = 1; i <= 4; i++) {
      const bar = document.getElementById(`pw-str-${i}`);
      bar.style.background = '#e5e7eb';
      bar.style.width = '0%';
    }
    document.getElementById('pw-str-label').textContent = '';
  }

  // ── toggle password visibility ────────────────────────
  window.togglePw = function (id) {
    const input = document.getElementById(id);
    input.type = input.type === 'password' ? 'text' : 'password';
  };

  // ── token display ─────────────────────────────────────
  function initTokenDisplay() {
    const token = getToken();
    const el = document.getElementById('token-display');
    if (el) el.textContent = token ? `${token.slice(0, 10)}••••••••••••••••••••••••${token.slice(-6)}` : 'Aucun token';
  }

  window.copyToken = function () {
    const token = getToken();
    if (!token) return;
    navigator.clipboard.writeText(token).then(() => {
      Utils.showToast('Token copié dans le presse-papiers', 'success');
    }).catch(() => {
      Utils.showToast('Impossible de copier', 'error');
    });
  };

  // ── about server ──────────────────────────────────────
  function initAboutServer() {
    const el = document.getElementById('about-server');
    if (el) el.textContent = SERVER_URL;
  }

  // ── language preferences ───────────────────────────────
  function initLangButtons() {
    const currentLang = localStorage.getItem('lang') || 'fr';
    highlightLang(currentLang);
  }

  function highlightLang(lang) {
    document.querySelectorAll('.lang-pref-btn').forEach(b => b.classList.remove('selected'));
    const btn = document.getElementById(`lang-${lang}`);
    if (btn) btn.classList.add('selected');
  }

  window.setLangAndSave = function (lang) {
    if (typeof setLang === 'function') setLang(lang);
    highlightLang(lang);
    Utils.showToast('Langue mise à jour', 'success');
  };

  // ── logout ─────────────────────────────────────────────
  window.doLogout = function () {
    if (typeof sbLogout === 'function') sbLogout();
    else {
      if (typeof Auth !== 'undefined') Auth.clearAuthToken();
      localStorage.removeItem('authUser');
      location.replace('login.html');
    }
  };

  // ── delete account ─────────────────────────────────────
  window.openDeleteAccountModal = function () {
    document.getElementById('delete-account-confirm-input').value = '';
    const modal = document.getElementById('delete-account-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  };

  window.closeDeleteAccountModal = function () {
    const modal = document.getElementById('delete-account-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  };

  // ══════════════════════════════════════════════════════
  // SUBSCRIPTION TAB
  // ══════════════════════════════════════════════════════
  const PLAN_COLORS = {
    free:       { border: 'border-gray-200',  btn: 'bg-gray-800 hover:bg-gray-900 text-white' },
    starter:    { border: 'border-teal-200',   btn: 'bg-teal-600 hover:bg-teal-700 text-white' },
    pro:        { border: 'border-blue-400',   btn: 'bg-blue-600 hover:bg-blue-700 text-white' },
    team:       { border: 'border-violet-300', btn: 'bg-violet-600 hover:bg-violet-700 text-white' },
    enterprise: { border: 'border-amber-300',  btn: 'bg-amber-500 hover:bg-amber-600 text-white' },
  };

  let _subPlans = [];
  let _subCurrentPlan = null;

  async function loadSubscriptionTab() {
    // Fetch plans
    try {
      const res = await fetch('/api/users/plans/');
      if (res.ok) _subPlans = (await res.json()).plans || [];
    } catch { /* ignore */ }

    // Fetch current subscription
    const token = getToken();
    if (token) {
      try {
        const res = await fetch('/api/users/profile/', { headers: { 'Authorization': `Token ${token}` } });
        if (res.ok) {
          const data = await res.json();
          const sub = data.subscription;
          _subCurrentPlan = sub?.plan || 'free';

          const plan = _subPlans.find(p => p.id === _subCurrentPlan);
          document.getElementById('sub-plan-name').textContent = plan?.name || _subCurrentPlan;
          document.getElementById('sub-plan-price').textContent = plan
            ? (plan.price === 0 ? 'Free forever' : `$${plan.price} / month`)
            : '—';

          if (sub) {
            const proteinsUsed   = sub.proteins_used   || 0;
            const analysesUsed   = sub.analyses_month  || 0;
            const limits         = sub.plan_limits     || {};
            const proteinLimit   = limits.proteins     || plan?.proteins   || 0;
            const analysisLimit  = limits.analyses_month || plan?.analyses_month || 0;

            document.getElementById('sub-proteins-used').textContent  = proteinsUsed;
            document.getElementById('sub-proteins-limit').textContent = proteinLimit >= 9999 ? '∞' : proteinLimit;
            document.getElementById('sub-analyses-used').textContent  = analysesUsed;
            document.getElementById('sub-analyses-limit').textContent = analysisLimit >= 99999 ? '∞' : analysisLimit;

            const proteinPct  = proteinLimit  >= 9999 ? 5  : Math.min(100, Math.round(proteinsUsed  / proteinLimit  * 100));
            const analysisPct = analysisLimit >= 99999 ? 5 : Math.min(100, Math.round(analysesUsed / analysisLimit * 100));
            document.getElementById('sub-proteins-bar').style.width  = proteinPct  + '%';
            document.getElementById('sub-analyses-bar').style.width  = analysisPct + '%';
          }
        }
      } catch { /* ignore */ }
    }

    renderSettingsPlanGrid();
  }

  function renderSettingsPlanGrid() {
    const grid = document.getElementById('settings-plans-grid');
    if (!grid || !_subPlans.length) return;
    grid.innerHTML = '';
    _subPlans.forEach(plan => {
      const style    = PLAN_COLORS[plan.id] || PLAN_COLORS.free;
      const isCurrent = plan.id === _subCurrentPlan;
      const card = document.createElement('div');
      card.className = `border-2 ${isCurrent ? 'border-blue-400 ring-2 ring-blue-100' : style.border} rounded-xl p-4 flex flex-col gap-2`;
      const priceLabel = plan.price === 0 ? 'Free' : `$${plan.price}/mo`;
      let btnHtml;
      if (isCurrent) {
        btnHtml = `<button disabled class="mt-auto w-full py-1.5 rounded-lg bg-emerald-100 text-emerald-700 text-xs font-semibold cursor-default">✓ Current</button>`;
      } else {
        const isDown = _subPlans.findIndex(p => p.id === plan.id) < _subPlans.findIndex(p => p.id === _subCurrentPlan);
        btnHtml = `<button onclick="settingsUpgradePlan('${plan.id}')" class="mt-auto w-full py-1.5 rounded-lg ${style.btn} text-xs font-semibold transition-colors">${isDown ? 'Downgrade' : 'Upgrade'}</button>`;
      }
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-semibold text-sm text-gray-900">${plan.name}</span>
          <span class="text-xs font-bold text-gray-500">${priceLabel}</span>
        </div>
        <p class="text-xs text-gray-400">${plan.description}</p>
        ${btnHtml}
      `;
      grid.appendChild(card);
    });
  }

  window.settingsUpgradePlan = async function (planId) {
    const token = getToken();
    if (!token) { Utils.showToast('Non authentifié', 'error'); return; }
    const plan = _subPlans.find(p => p.id === planId);
    if (!confirm(`Switch to ${plan?.name} plan ($${plan?.price}/mo)?`)) return;
    const statusEl = document.getElementById('sub-upgrade-status');
    statusEl.textContent = 'Processing…';
    statusEl.classList.remove('hidden');
    try {
      const res = await fetch('/api/users/upgrade-plan/', {
        method: 'POST',
        headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: planId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        Utils.showToast(data.error || 'Upgrade failed', 'error');
        statusEl.textContent = data.error || 'Error';
      } else {
        _subCurrentPlan = planId;
        document.getElementById('sub-plan-name').textContent  = plan?.name || planId;
        document.getElementById('sub-plan-price').textContent = plan?.price === 0 ? 'Free forever' : `$${plan?.price} / month`;
        renderSettingsPlanGrid();
        Utils.showToast(data.message || 'Plan updated!', 'success');
        statusEl.classList.add('hidden');
      }
    } catch {
      Utils.showToast('Erreur réseau', 'error');
      statusEl.textContent = 'Network error';
    }
  };

  // Hook subscription tab load
  const _origSwitchTab = window.switchTab;
  window.switchTab = function (tab) {
    _origSwitchTab(tab);
    if (tab === 'subscription' && _subPlans.length === 0) {
      loadSubscriptionTab();
    }
  };

  // Also update initTabFromHash to allow 'subscription'
  function initTabFromHash() {
    const hash = location.hash.replace('#', '');
    if (['profile', 'security', 'prefs', 'danger', 'subscription'].includes(hash)) {
      window.switchTab(hash);
    }
  }

  window.confirmDeleteAccount = async function () {
    const inputVal = document.getElementById('delete-account-confirm-input').value.trim();
    const username = getUser().username || '';
    if (inputVal !== username) {
      Utils.showToast('Nom d\'utilisateur incorrect', 'error');
      return;
    }

    const btn = document.getElementById('delete-account-btn');
    btn.disabled = true;
    btn.textContent = 'Suppression…';

    try {
      const token = getToken();
      const res = await fetch('/api/users/delete/', {
        method: 'DELETE',
        headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' }
      });
      if (res.ok || res.status === 204) {
        if (typeof Auth !== 'undefined') Auth.clearAuthToken();
        localStorage.removeItem('authUser');
        Utils.showToast('Compte supprimé avec succès', 'success');
        setTimeout(() => location.replace('index.html'), 1500);
      } else {
        const data = await res.json().catch(() => ({}));
        Utils.showToast(data.detail || 'Erreur lors de la suppression', 'error');
        btn.disabled = false;
        btn.textContent = 'Supprimer définitivement';
      }
    } catch (_) {
      Utils.showToast('Erreur réseau', 'error');
      btn.disabled = false;
      btn.textContent = 'Supprimer définitivement';
    }
  };

  // Close modal on backdrop click
  document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('delete-account-modal');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === this) closeDeleteAccountModal();
      });
    }
  });

})();
