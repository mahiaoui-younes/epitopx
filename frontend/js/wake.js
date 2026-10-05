/**
 * wake.js — wakes the Render free-tier backend from ANY device.
 *
 * The Node server already pings the backend on startup / page visits, but that
 * depends on in-memory state and can give up too early. This script makes the
 * browser itself wake the backend on every page load (phone or PC): it polls
 * /api/health/?db=1 (proxied to the Django backend) until it answers, and shows
 * a small "waking up" notice only if it takes more than a moment.
 */
(function () {
  'use strict';

  if (window.__epitopxWakeStarted) return;
  window.__epitopxWakeStarted = true;

  var MAX_TOTAL_MS = 4 * 60 * 1000; // give up after 4 minutes
  var RETRY_DELAY_MS = 4000;
  var SHOW_NOTICE_AFTER_MS = 2500;

  var notice = null;
  var noticeTimer = null;

  function showNotice() {
    if (notice || !document.body) return;
    notice = document.createElement('div');
    notice.id = 'backend-wake-notice';
    notice.setAttribute('role', 'status');
    notice.style.cssText =
      'position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:99999;' +
      'padding:10px 18px;border-radius:999px;font:500 13px/1.3 system-ui,sans-serif;' +
      'color:#e2e8f0;background:rgba(15,23,42,.92);border:1px solid rgba(99,102,241,.5);' +
      'box-shadow:0 8px 30px rgba(0,0,0,.4);max-width:90vw;text-align:center;';
    notice.textContent = 'Waking up the server\u2026 this can take up to a minute.';
    document.body.appendChild(notice);
  }

  function hideNotice() {
    clearTimeout(noticeTimer);
    if (notice && notice.parentNode) notice.parentNode.removeChild(notice);
    notice = null;
  }

  function healthOk() {
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var t = controller ? setTimeout(function () { controller.abort(); }, 100000) : null;
    return fetch('/api/health/', { cache: 'no-store', signal: controller ? controller.signal : undefined })
      .then(function (res) { return res.ok; })
      .catch(function () { return false; })
      .then(function (ok) { if (t) clearTimeout(t); return ok; });
  }

  function wake() {
    var startedAt = Date.now();
    noticeTimer = setTimeout(showNotice, SHOW_NOTICE_AFTER_MS);

    (function attempt() {
      healthOk().then(function (ok) {
        if (ok) {
          hideNotice();
          window.dispatchEvent(new CustomEvent('backend-ready'));
          return;
        }
        if (Date.now() - startedAt >= MAX_TOTAL_MS) {
          hideNotice();
          return;
        }
        setTimeout(attempt, RETRY_DELAY_MS);
      });
    })();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wake);
  } else {
    wake();
  }
})();
