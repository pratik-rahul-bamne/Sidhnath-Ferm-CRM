/* =================================================
   Siddhanth Firm – Main JS
   ================================================= */

// ── Sidebar Toggle ──
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar) {
    const isOpen = sidebar.classList.toggle('open');
    if (backdrop) backdrop.classList.toggle('open', isOpen);
    document.body.classList.toggle('sidebar-mobile-open', isOpen);
  }
}
// Close sidebar on outside click (mobile)
document.addEventListener('click', function(e) {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.getElementById('sidebarToggle');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar && sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== toggle && (!backdrop || !backdrop.contains(e.target))) {
    sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    document.body.classList.remove('sidebar-mobile-open');
  }
});

// ── Global Search ──
const searchInput = document.getElementById('globalSearch');
const searchResults = document.getElementById('searchResults');
let searchTimeout = null;

if (searchInput) {
  searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const q = this.value.trim();
    if (!q) {
      searchResults.innerHTML = '';
      searchResults.classList.remove('open');
      return;
    }
    searchTimeout = setTimeout(() => doSearch(q), 280);
  });

  searchInput.addEventListener('focus', function() {
    if (this.value.trim().length > 0) searchResults.classList.add('open');
  });

  document.addEventListener('click', function(e) {
    if (searchResults && !searchResults.contains(e.target) && e.target !== searchInput) {
      searchResults.classList.remove('open');
    }
  });
}

function doSearch(q) {
  fetch('/api/search?q=' + encodeURIComponent(q))
    .then(r => r.json())
    .then(data => {
      if (!data.length) {
        searchResults.innerHTML = '<div class="search-result-item"><span class="result-date">No results found.</span></div>';
      } else {
        searchResults.innerHTML = data.map(item => `
          <div class="search-result-item" style="cursor: pointer;" onclick="if('${item.url || ''}') window.location.href='${item.url || '#'}'">
            <div class="result-type" style="font-weight: 700; color: var(--gold-dark, #b8860b); font-size: 0.72rem; text-transform: uppercase;">${item.type} ${item.receipt_no ? '· ' + item.receipt_no : ''}</div>
            <div class="result-name" style="font-weight: 600; font-size: 0.9rem;">${item.customer_name}</div>
            <div class="result-date" style="font-size: 0.75rem; color: var(--text-muted, #6c757d);">${item.date || ''} ${item.contact_no ? '· ' + item.contact_no : ''}</div>
          </div>
        `).join('');
      }
      searchResults.classList.add('open');
    })
    .catch(() => {
      searchResults.classList.remove('open');
    });
}

// ── Auto-dismiss flash messages ──
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.5s';
      setTimeout(() => el.remove(), 500);
    }, 4500);
  });
});

// ── Table filter (client-side) ──
function filterTable(inputId, tableId) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);
  if (!input || !table) return;
  input.addEventListener('keyup', function() {
    const filter = this.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none';
    });
  });
}
