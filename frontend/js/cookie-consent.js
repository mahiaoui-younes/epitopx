/**
 * EpitopX AI — Cookie Consent Banner
 * GDPR-compliant cookie consent with granular category controls.
 * Include this script on every page BEFORE </body>.
 */
(function () {
  'use strict';

  // Skip if already consented
  var consent = localStorage.getItem('epitopx_cookie_consent');
  if (consent === 'all' || consent === 'essential' || consent === 'custom') return;

  // Build banner HTML
  var banner = document.createElement('div');
  banner.id = 'cookie-consent-banner';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Cookie consent');
  banner.innerHTML = [
    '<div class="ccb-inner">',
    '  <div class="ccb-icon">🍪</div>',
    '  <div class="ccb-text">',
    '    <p class="ccb-title">Nous utilisons des cookies</p>',
    '    <p class="ccb-desc">EpitopX AI utilise des cookies essentiels pour le fonctionnement du site et des cookies optionnels pour améliorer votre expérience. ',
    '    <a href="cookies.html" class="ccb-link">En savoir plus</a></p>',
    '  </div>',
    '  <div class="ccb-actions">',
    '    <button id="ccb-accept-all" class="ccb-btn ccb-btn-primary">Tout accepter</button>',
    '    <button id="ccb-essential" class="ccb-btn ccb-btn-secondary">Essentiels uniquement</button>',
    '    <a href="cookies.html" class="ccb-btn ccb-btn-ghost">Personnaliser</a>',
    '  </div>',
    '</div>'
  ].join('\n');

  // Styles
  var style = document.createElement('style');
  style.textContent = [
    '#cookie-consent-banner {',
    '  position: fixed; bottom: 0; left: 0; right: 0; z-index: 99999;',
    '  padding: 0 1rem 1rem;',
    '  animation: ccb-slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1);',
    '  pointer-events: none;',
    '}',
    '.ccb-inner {',
    '  max-width: 52rem; margin: 0 auto;',
    '  background: rgba(255,255,255,0.97); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);',
    '  border: 1px solid rgba(226,232,240,0.8);',
    '  border-radius: 1.25rem;',
    '  padding: 1.25rem 1.5rem;',
    '  box-shadow: 0 -4px 40px rgba(0,0,0,0.08), 0 0 0 1px rgba(59,130,246,0.04);',
    '  display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;',
    '  pointer-events: auto;',
    '}',
    '.ccb-icon { font-size: 2rem; flex-shrink: 0; animation: ccb-wobble 2s ease-in-out infinite; }',
    '.ccb-text { flex: 1; min-width: 200px; }',
    '.ccb-title { font-size: 0.95rem; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem; }',
    '.ccb-desc { font-size: 0.8rem; color: #64748b; margin: 0; line-height: 1.5; }',
    '.ccb-link { color: #3b82f6; text-decoration: underline; text-underline-offset: 2px; transition: color 0.2s; }',
    '.ccb-link:hover { color: #0d9488; }',
    '.ccb-actions { display: flex; gap: 0.5rem; flex-shrink: 0; flex-wrap: wrap; }',
    '.ccb-btn {',
    '  padding: 0.55rem 1.1rem; border-radius: 0.625rem; font-size: 0.8rem;',
    '  font-weight: 600; cursor: pointer; border: none; transition: all 0.2s;',
    '  text-decoration: none; text-align: center; white-space: nowrap;',
    '}',
    '.ccb-btn-primary {',
    '  background: linear-gradient(135deg, #3b82f6, #0d9488); color: #fff;',
    '  box-shadow: 0 2px 12px rgba(59,130,246,0.3);',
    '}',
    '.ccb-btn-primary:hover { box-shadow: 0 4px 20px rgba(59,130,246,0.4); transform: translateY(-1px); }',
    '.ccb-btn-secondary {',
    '  background: #f1f5f9; color: #334155;',
    '}',
    '.ccb-btn-secondary:hover { background: #e2e8f0; }',
    '.ccb-btn-ghost {',
    '  background: transparent; color: #94a3b8; display: inline-flex; align-items: center;',
    '}',
    '.ccb-btn-ghost:hover { color: #3b82f6; }',
    '@keyframes ccb-slide-up { from { transform: translateY(100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }',
    '@keyframes ccb-wobble { 0%,100% { transform: rotate(0deg); } 25% { transform: rotate(-8deg); } 75% { transform: rotate(8deg); } }',
    '@media (max-width: 640px) {',
    '  .ccb-inner { flex-direction: column; text-align: center; padding: 1rem; }',
    '  .ccb-actions { width: 100%; justify-content: center; }',
    '}'
  ].join('\n');

  document.head.appendChild(style);
  document.body.appendChild(banner);

  // Accept all
  document.getElementById('ccb-accept-all').addEventListener('click', function () {
    localStorage.setItem('epitopx_cookie_consent', 'all');
    localStorage.setItem('epitopx_cookie_prefs', JSON.stringify({
      functional: true, analytics: true, performance: true, timestamp: Date.now()
    }));
    closeBanner();
  });

  // Essential only
  document.getElementById('ccb-essential').addEventListener('click', function () {
    localStorage.setItem('epitopx_cookie_consent', 'essential');
    localStorage.setItem('epitopx_cookie_prefs', JSON.stringify({
      functional: false, analytics: false, performance: false, timestamp: Date.now()
    }));
    closeBanner();
  });

  function closeBanner() {
    banner.style.animation = 'ccb-slide-down 0.3s ease forwards';
    setTimeout(function () { banner.remove(); }, 350);
    // Add slide-down animation
    var downStyle = document.createElement('style');
    downStyle.textContent = '@keyframes ccb-slide-down { from { transform: translateY(0); opacity: 1; } to { transform: translateY(100%); opacity: 0; } }';
    document.head.appendChild(downStyle);
  }
})();
