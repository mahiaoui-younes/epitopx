/**
 * EpitopX AI — Guided Onboarding System
 *
 * Shows a 3-step modal on first visit.
 * Controlled by: localStorage['epitopx_onboarded']
 * - Not set → show modal
 * - '1'     → skip (already completed or skipped)
 *
 * API:
 *   window.EpitopXOnboarding.show()    — force-show (e.g. from "How It Works")
 *   window.EpitopXOnboarding.reset()   — clear flag + show (for Settings page)
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'epitopx_onboarded';
  const STEPS = [
    {
      icon: '🧬',
      iconBg: 'linear-gradient(135deg,#3b82f6,#6366f1)',
      title: 'Welcome to EpitopX AI',
      subtitle: 'The AI-powered bioinformatics platform',
      body: `
        <p style="color:#64748b;font-size:.9rem;line-height:1.7;margin-bottom:1.25rem;">
          EpitopX is a complete platform for protein research — designed for scientists,
          students, and researchers who want powerful tools without the complexity.
        </p>
        <div class="ob-grid">
          <div class="ob-feat-card">
            <span class="ob-feat-icon" style="background:rgba(59,130,246,.1);color:#3b82f6">🔍</span>
            <div>
              <div class="ob-feat-title">Protein Search</div>
              <div class="ob-feat-desc">Search UniProt &amp; NCBI databases</div>
            </div>
          </div>
          <div class="ob-feat-card">
            <span class="ob-feat-icon" style="background:rgba(13,148,136,.1);color:#0d9488">🎯</span>
            <div>
              <div class="ob-feat-title">Epitope Prediction</div>
              <div class="ob-feat-desc">B-cell &amp; T-cell epitope analysis</div>
            </div>
          </div>
          <div class="ob-feat-card">
            <span class="ob-feat-icon" style="background:rgba(139,92,246,.1);color:#7c3aed">🧪</span>
            <div>
              <div class="ob-feat-title">3D Visualization</div>
              <div class="ob-feat-desc">Interactive protein structure viewer</div>
            </div>
          </div>
          <div class="ob-feat-card">
            <span class="ob-feat-icon" style="background:rgba(99,102,241,.1);color:#6366f1">🤖</span>
            <div>
              <div class="ob-feat-title">AI Agent</div>
              <div class="ob-feat-desc">Run workflows with natural language</div>
            </div>
          </div>
        </div>
      `,
    },
    {
      icon: '⚡',
      iconBg: 'linear-gradient(135deg,#f59e0b,#f97316)',
      title: 'Example Workflows',
      subtitle: 'See what you can do in minutes',
      body: `
        <div class="ob-workflows">
          <div class="ob-workflow">
            <div class="ob-workflow-header">
              <span class="ob-workflow-num">01</span>
              <span class="ob-workflow-title">Protein Discovery</span>
            </div>
            <div class="ob-workflow-steps">
              <span class="ob-ws">Search NCBI or UniProt</span>
              <span class="ob-ws-arrow">→</span>
              <span class="ob-ws">View structure in 3D</span>
              <span class="ob-ws-arrow">→</span>
              <span class="ob-ws">Predict epitopes</span>
            </div>
          </div>
          <div class="ob-workflow">
            <div class="ob-workflow-header">
              <span class="ob-workflow-num">02</span>
              <span class="ob-workflow-title">Epitope Comparison</span>
            </div>
            <div class="ob-workflow-steps">
              <span class="ob-ws">Load two proteins</span>
              <span class="ob-ws-arrow">→</span>
              <span class="ob-ws">Run comparison</span>
              <span class="ob-ws-arrow">→</span>
              <span class="ob-ws">View RMSD &amp; similarity</span>
            </div>
          </div>
          <div class="ob-workflow ob-workflow-ai">
            <div class="ob-workflow-header">
              <span class="ob-workflow-num" style="color:#6366f1">AI</span>
              <span class="ob-workflow-title" style="color:#1e293b">Do it all with AI Agent</span>
            </div>
            <div style="font-size:.82rem;color:#64748b;margin-top:.5rem;line-height:1.5;">
              Just type: <em style="color:#6366f1">"Analyze the spike protein of SARS-CoV-2 and predict its B-cell epitopes"</em>
              — and the AI runs the entire workflow for you.
            </div>
          </div>
        </div>
      `,
    },
    {
      icon: '🤖',
      iconBg: 'linear-gradient(135deg,#6366f1,#3b82f6)',
      title: 'Meet Your AI Assistant',
      subtitle: 'The most powerful feature in EpitopX',
      body: `
        <p style="color:#64748b;font-size:.875rem;line-height:1.7;margin-bottom:1.25rem;">
          The EpitopX AI Agent understands bioinformatics. Just describe what you want —
          it handles searching, analysis, and interpretation automatically.
        </p>
        <div class="ob-prompts">
          <div class="ob-prompt-label">✦ Try these prompts</div>
          <div class="ob-prompt-item" onclick="setAgentPrompt(this.dataset.prompt)" data-prompt="Analyze SARS-CoV-2 spike protein and predict B-cell epitopes">
            <span class="ob-prompt-chip">→</span>
            Analyze SARS-CoV-2 spike protein and predict B-cell epitopes
          </div>
          <div class="ob-prompt-item" onclick="setAgentPrompt(this.dataset.prompt)" data-prompt="Find a malaria-related protein and summarize its structure">
            <span class="ob-prompt-chip">→</span>
            Find a malaria-related protein and summarize its structure
          </div>
          <div class="ob-prompt-item" onclick="setAgentPrompt(this.dataset.prompt)" data-prompt="Compare two proteins and show their epitope similarities">
            <span class="ob-prompt-chip">→</span>
            Compare two proteins and show their epitope similarities
          </div>
        </div>
        <p style="font-size:.75rem;color:#94a3b8;margin-top:1rem;text-align:center;">
          Click a prompt above, then finish the tour to use it directly
        </p>
      `,
    },
  ];

  let currentStep = 0;
  let selectedPrompt = null;
  let overlay = null;

  function isOnboarded() {
    try { return localStorage.getItem(STORAGE_KEY) === '1'; } catch(_) { return false; }
  }

  function markOnboarded() {
    try { localStorage.setItem(STORAGE_KEY, '1'); } catch(_) {}
  }

  function build() {
    if (document.getElementById('ob-overlay')) return; // already built

    overlay = document.createElement('div');
    overlay.id = 'ob-overlay';
    overlay.innerHTML = `
      <div id="ob-modal">
        <button id="ob-close" onclick="window.EpitopXOnboarding.skip()" title="Skip onboarding">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
        <div id="ob-body"></div>
        <div id="ob-footer">
          <div id="ob-dots"></div>
          <div id="ob-actions">
            <button id="ob-skip-btn" onclick="window.EpitopXOnboarding.skip()">Skip tour</button>
            <div style="display:flex;gap:.5rem;">
              <button id="ob-back-btn" onclick="window.EpitopXOnboarding.back()" style="display:none;">← Back</button>
              <button id="ob-next-btn" onclick="window.EpitopXOnboarding.next()">Next →</button>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  function render() {
    const step = STEPS[currentStep];

    // Body
    document.getElementById('ob-body').innerHTML = `
      <div style="text-align:center;margin-bottom:1.5rem;">
        <div style="width:54px;height:54px;border-radius:1rem;background:${step.iconBg};
          display:flex;align-items:center;justify-content:center;font-size:1.5rem;
          margin:0 auto 1rem;box-shadow:0 8px 24px rgba(0,0,0,0.12);">${step.icon}</div>
        <h2 style="font-size:1.3rem;font-weight:800;color:#0f172a;margin-bottom:.35rem;">${step.title}</h2>
        <p style="font-size:.8rem;color:#94a3b8;font-weight:500;">${step.subtitle}</p>
      </div>
      ${step.body}
    `;

    // Dots
    document.getElementById('ob-dots').innerHTML = STEPS.map((_, i) =>
      `<div class="ob-dot${i === currentStep ? ' ob-dot-active' : ''}" onclick="window.EpitopXOnboarding.goTo(${i})"></div>`
    ).join('');

    // Buttons
    const backBtn  = document.getElementById('ob-back-btn');
    const nextBtn  = document.getElementById('ob-next-btn');
    const skipBtn  = document.getElementById('ob-skip-btn');
    const isLast   = currentStep === STEPS.length - 1;
    const isFirst  = currentStep === 0;

    backBtn.style.display = isFirst ? 'none' : '';
    skipBtn.style.display = isLast ? 'none' : '';
    nextBtn.textContent   = isLast ? '🚀 Start with AI Agent' : 'Next →';
    nextBtn.style.background = isLast
      ? 'linear-gradient(135deg,#6366f1,#3b82f6)'
      : 'linear-gradient(135deg,#3b82f6,#2563eb)';
  }

  function show() {
    build();
    currentStep = 0;
    render();
    requestAnimationFrame(() => {
      overlay.classList.add('ob-visible');
    });
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }

  function hide() {
    if (overlay) {
      overlay.classList.remove('ob-visible');
      setTimeout(() => {
        if (overlay) { overlay.style.display = 'none'; }
      }, 300);
    }
    document.body.style.overflow = '';
  }

  function skip() {
    markOnboarded();
    hide();
  }

  function next() {
    if (currentStep < STEPS.length - 1) {
      currentStep++;
      render();
    } else {
      // Final step — go to agent
      markOnboarded();
      hide();
      const prompt = selectedPrompt;
      if (prompt) {
        try { sessionStorage.setItem('epitopx_agent_starter', prompt); } catch(_) {}
      }
      // Navigate to agent — login if needed
      if (typeof Auth !== 'undefined' && Auth.isAuthenticated()) {
        window.location.href = 'agent.html';
      } else {
        try { sessionStorage.setItem('_authRedirect', 'agent.html'); } catch(_) {}
        window.location.href = 'login.html';
      }
    }
  }

  function back() {
    if (currentStep > 0) { currentStep--; render(); }
  }

  function goTo(idx) {
    if (idx >= 0 && idx < STEPS.length) { currentStep = idx; render(); }
  }

  // Allow clicking a prompt in step 3
  window.setAgentPrompt = function(prompt) {
    selectedPrompt = prompt;
    // Highlight selected
    document.querySelectorAll('.ob-prompt-item').forEach(el => {
      el.style.borderColor = el.dataset.prompt === prompt
        ? 'rgba(99,102,241,0.5)' : 'rgba(226,232,240,1)';
      el.style.background  = el.dataset.prompt === prompt
        ? 'rgba(99,102,241,0.05)' : '';
    });
  };

  // Inject styles
  const style = document.createElement('style');
  style.textContent = `
    #ob-overlay {
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(15,23,42,0.65); backdrop-filter: blur(6px);
      display: flex; align-items: center; justify-content: center;
      padding: 1rem;
      opacity: 0; pointer-events: none;
      transition: opacity 0.3s ease;
    }
    #ob-overlay.ob-visible { opacity: 1; pointer-events: auto; }

    #ob-modal {
      background: #fff; border-radius: 1.5rem;
      width: 100%; max-width: 520px; max-height: 90vh; overflow-y: auto;
      box-shadow: 0 32px 80px rgba(0,0,0,0.2);
      position: relative;
      transform: translateY(20px) scale(0.97);
      transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1);
      padding: 2rem 2rem 1.5rem;
    }
    #ob-overlay.ob-visible #ob-modal {
      transform: translateY(0) scale(1);
    }

    #ob-close {
      position: absolute; top: 1rem; right: 1rem;
      width: 28px; height: 28px; border-radius: 50%;
      background: #f1f5f9; border: 1px solid #e2e8f0;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; color: #94a3b8;
      transition: all 0.15s;
    }
    #ob-close:hover { background: #fee2e2; color: #ef4444; border-color: #fca5a5; }

    #ob-footer {
      margin-top: 1.5rem; padding-top: 1.25rem;
      border-top: 1px solid #f1f5f9;
    }
    #ob-dots {
      display: flex; gap: .4rem; justify-content: center; margin-bottom: 1rem;
    }
    .ob-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #e2e8f0; cursor: pointer; transition: all 0.2s;
    }
    .ob-dot-active {
      background: linear-gradient(135deg,#3b82f6,#6366f1);
      width: 22px; border-radius: 4px;
    }

    #ob-actions {
      display: flex; align-items: center; justify-content: space-between;
    }
    #ob-skip-btn {
      font-size: .8rem; color: #94a3b8; background: none; border: none;
      cursor: pointer; font-family: inherit; transition: color 0.15s; padding: .25rem;
    }
    #ob-skip-btn:hover { color: #64748b; }

    #ob-back-btn {
      padding: .55rem 1.1rem; border-radius: .625rem;
      background: #f1f5f9; border: 1px solid #e2e8f0;
      font-size: .85rem; font-weight: 600; color: #475569;
      cursor: pointer; font-family: inherit; transition: all 0.15s;
    }
    #ob-back-btn:hover { background: #e2e8f0; }

    #ob-next-btn {
      padding: .6rem 1.4rem; border-radius: .625rem;
      background: linear-gradient(135deg,#3b82f6,#2563eb);
      border: none; color: #fff; font-size: .875rem; font-weight: 700;
      cursor: pointer; font-family: inherit;
      transition: transform 0.15s, box-shadow 0.15s;
      box-shadow: 0 4px 12px rgba(37,99,235,0.3);
    }
    #ob-next-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(37,99,235,0.4); }

    /* Feature grid */
    .ob-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: .625rem;
    }
    .ob-feat-card {
      display: flex; align-items: center; gap: .625rem;
      padding: .75rem .875rem; border-radius: .875rem;
      border: 1px solid #f1f5f9; background: #fafafa;
      transition: border-color 0.15s;
    }
    .ob-feat-card:hover { border-color: #bfdbfe; }
    .ob-feat-icon {
      width: 32px; height: 32px; border-radius: .5rem; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center; font-size: .95rem;
    }
    .ob-feat-title { font-size: .82rem; font-weight: 600; color: #1e293b; }
    .ob-feat-desc  { font-size: .72rem; color: #94a3b8; margin-top: .1rem; }

    /* Workflows */
    .ob-workflows { display: flex; flex-direction: column; gap: .75rem; }
    .ob-workflow {
      padding: .875rem 1rem; border-radius: .875rem;
      border: 1px solid #e2e8f0; background: #fafafa;
    }
    .ob-workflow-ai {
      border-color: rgba(99,102,241,.2); background: rgba(99,102,241,.03);
    }
    .ob-workflow-header { display: flex; align-items: center; gap: .5rem; margin-bottom: .5rem; }
    .ob-workflow-num { font-size: .68rem; font-weight: 800; color: #3b82f6; letter-spacing: .1em; }
    .ob-workflow-title { font-size: .85rem; font-weight: 700; color: #1e293b; }
    .ob-workflow-steps { display: flex; align-items: center; flex-wrap: wrap; gap: .3rem; }
    .ob-ws {
      font-size: .75rem; color: #475569;
      background: #eff6ff; border: 1px solid #bfdbfe; border-radius: .35rem;
      padding: .2rem .5rem;
    }
    .ob-ws-arrow { font-size: .7rem; color: #94a3b8; }

    /* Prompts */
    .ob-prompts {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 1rem;
      padding: .875rem 1rem;
    }
    .ob-prompt-label {
      font-size: .65rem; font-weight: 700; color: #6366f1;
      letter-spacing: .1em; text-transform: uppercase; margin-bottom: .625rem;
    }
    .ob-prompt-item {
      display: flex; align-items: flex-start; gap: .5rem;
      padding: .5rem .625rem; border-radius: .5rem;
      border: 1px solid #e2e8f0; background: #fff;
      font-size: .8rem; color: #374151; line-height: 1.5;
      cursor: pointer; transition: all 0.15s; margin-bottom: .35rem;
    }
    .ob-prompt-item:last-child { margin-bottom: 0; }
    .ob-prompt-item:hover { border-color: rgba(99,102,241,.4); background: rgba(99,102,241,.04); color: #4f46e5; }
    .ob-prompt-chip {
      color: #6366f1; font-weight: 700; flex-shrink: 0; font-size: .85rem;
    }

    @media (max-width: 480px) {
      #ob-modal { padding: 1.5rem 1.25rem 1.25rem; }
      .ob-grid { grid-template-columns: 1fr; }
    }
  `;
  document.head.appendChild(style);

  // Public API
  window.EpitopXOnboarding = { show, skip, next, back, goTo,
    reset() { try { localStorage.removeItem(STORAGE_KEY); } catch(_) {} show(); }
  };

  // Auto-show on first visit (not on agent page itself, or welcome page which has its own trigger)
  document.addEventListener('DOMContentLoaded', function () {
    const page = location.pathname.split('/').pop() || 'index.html';
    // Don't auto-show on these pages:
    const skipAutoShow = ['welcome.html', 'login.html', 'signup.html', 'privacy.html', 'cookies.html', 'pricing.html'];
    if (!skipAutoShow.includes(page) && !isOnboarded()) {
      setTimeout(show, 800);
    }

    // If a starter prompt was set (from onboarding step 3), inject it into agent textarea
    if (page === 'agent.html') {
      try {
        const starter = sessionStorage.getItem('epitopx_agent_starter');
        if (starter) {
          sessionStorage.removeItem('epitopx_agent_starter');
          const ta = document.getElementById('prompt-input');
          if (ta) {
            ta.value = starter;
            ta.dispatchEvent(new Event('input'));
          }
        }
      } catch(_) {}
    }
  });
})();
