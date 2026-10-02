/**
 * ZEZO Commercial Real Estate & Portfolio Intelligence - Core Application Script
 * Faithful implementation of studio-grade SaaS animation & interactivity blueprint
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Lucide Icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({
      attrs: {
        'stroke-width': 1.75
      }
    });
  }

  // 2. Word & Element Reveal Observer (Staggered Animation)
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const el = entry.target;

        // If element has data-words, split into animated word spans
        if (el.hasAttribute('data-words') && !el.dataset.wordsProcessed) {
          el.dataset.wordsProcessed = 'true';
          const text = el.textContent.trim();
          const words = text.split(/\s+/);
          el.innerHTML = '';
          words.forEach((word, index) => {
            const span = document.createElement('span');
            span.className = 'word-reveal';
            span.textContent = word + ' ';
            el.appendChild(span);

            setTimeout(() => {
              span.classList.add('revealed');
            }, 80 + index * 40);
          });
        }

        // Reveal container element
        el.classList.remove('opacity-0', 'translate-y-4');
        revealObserver.unobserve(el);
      }
    });
  }, { threshold: 0.12 });

  document.querySelectorAll('[data-reveal], [data-words]').forEach((el) => {
    revealObserver.observe(el);
  });

  // 3. Dynamic Real Estate Ticker Rotation
  const tickerItems = [
    { icon: 'sparkles', text: 'Institutional Real Estate Intelligence' },
    { icon: 'trending-up', text: 'Commercial Cap Rates average 7.8% across top hubs' },
    { icon: 'building-2', text: '14,200+ Verified Assets under management' },
    { icon: 'calculator', text: 'Instant AI Underwriting & Cash Flow Engines' },
    { icon: 'shield-check', text: 'Institutional Custody & Enterprise Governance' }
  ];

  const tickerText = document.getElementById('ticker-text');
  const tickerIcon = document.getElementById('ticker-icon');
  let tickerIdx = 0;

  if (tickerText && tickerIcon) {
    setInterval(() => {
      tickerText.classList.add('opacity-0', '-translate-y-1');
      tickerIcon.classList.add('opacity-0');

      setTimeout(() => {
        tickerIdx = (tickerIdx + 1) % tickerItems.length;
        tickerText.textContent = tickerItems[tickerIdx].text;
        
        tickerIcon.innerHTML = '';
        const ic = document.createElement('i');
        ic.setAttribute('data-lucide', tickerItems[tickerIdx].icon);
        ic.className = 'h-4 w-4 text-amber-500';
        tickerIcon.appendChild(ic);

        if (typeof lucide !== 'undefined') {
          lucide.createIcons({
            attrs: { 'stroke-width': 1.75 }
          });
        }

        tickerText.classList.remove('opacity-0', '-translate-y-1');
        tickerIcon.classList.remove('opacity-0');
      }, 300);
    }, 3200);
  }

  // 4. Interactive Card Mouse Glow Position Tracker
  document.querySelectorAll('.cap-card').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mx', `${x}px`);
      card.style.setProperty('--my', `${y}px`);
      card.style.setProperty('--glow-o', '1');
    });

    card.addEventListener('mouseleave', () => {
      card.style.setProperty('--glow-o', '0');
    });
  });
});

// 5. Interactive Console Tab Switcher
function selectTab(btnElement, categoryName) {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.classList.remove('active', 'bg-zinc-900', 'text-white', 'shadow-md');
    btn.classList.add('bg-zinc-100', 'text-zinc-600', 'hover:bg-zinc-200');
  });

  btnElement.classList.remove('bg-zinc-100', 'text-zinc-600', 'hover:bg-zinc-200');
  btnElement.classList.add('active', 'bg-zinc-900', 'text-white', 'shadow-md');
  
  const searchInput = document.querySelector('.search-input');
  if (searchInput && categoryName) {
    searchInput.placeholder = `Search ${categoryName} (e.g. Financial District, Midtown, Austin)...`;
  }
}

// 6. Real Estate Search Trigger Function
function triggerSearch(event) {
  if (event) event.preventDefault();
  
  const activeTab = document.querySelector('.tab-btn.active')?.innerText.trim() || 'Commercial Asset';
  const locationInput = document.querySelector('.search-input')?.value.trim() || 'Target Market';
  const assetClass = document.querySelector('.select-asset')?.value || 'Grade-A High-Rise';
  const investment = document.querySelector('.select-investment')?.value || '$50M – $250M';

  // Create clean notification toast
  const toast = document.createElement('div');
  toast.className = 'fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-full bg-zinc-900 text-white px-6 py-3.5 shadow-2xl border border-zinc-700 animate-bounce';
  toast.innerHTML = `
    <span class="h-2.5 w-2.5 rounded-full bg-amber-400 animate-pulse"></span>
    <span class="text-sm font-medium">Initiating AI Analysis for <strong>${activeTab}</strong> (${assetClass}) in <em>${locationInput}</em> [Budget: ${investment}]...</span>
  `;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.transition = 'all 0.5s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translate(-50%, 20px)';
    setTimeout(() => toast.remove(), 500);
  }, 4000);
}
