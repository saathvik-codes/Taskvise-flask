// Keeps big tables light. Dashboards render every row; with hundreds of tasks that is thousands of page elements.
// This shows the first rows and a "Show all" button, and shows everything as soon as someone searches or filters.
(() => {
  const LIMIT = 40;
  const done = new WeakSet();
  let expandAll = false;

  const apply = (tbody) => {
    if (done.has(tbody)) return;
    const rows = [...tbody.rows];
    if (rows.length <= LIMIT) return;
    done.add(tbody);
    rows.slice(LIMIT).forEach((r) => r.classList.add('tv-more'));
    const table = tbody.closest('table');
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'tv-showall'; btn.textContent = `Show all ${rows.length} rows`;
    btn.addEventListener('click', () => { tbody.querySelectorAll('.tv-more').forEach((r) => r.classList.remove('tv-more')); btn.hidden = true; });
    table.insertAdjacentElement('afterend', btn);
  };

  const scan = () => {
    if (expandAll) return;
    document.querySelectorAll('table tbody').forEach(apply);
  };

  let timer;
  new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(scan, 120); })
    .observe(document.documentElement, { childList: true, subtree: true });

  // searching or filtering must be able to reach every row
  const reveal = () => {
    expandAll = true;
    document.querySelectorAll('.tv-more').forEach((r) => r.classList.remove('tv-more'));
    document.querySelectorAll('.tv-showall').forEach((b) => { b.hidden = true; });
  };
  document.addEventListener('input', (e) => { if (e.target.matches('input[type="search"], input[type="text"], input:not([type])')) reveal(); });
  document.addEventListener('change', (e) => { if (e.target.matches('select')) reveal(); });


  // a broken avatar (uploads do not persist on serverless hosting) falls back to the initial
  document.addEventListener('error', (e) => {
    const img = e.target;
    if (!(img instanceof HTMLImageElement) || !img.matches('.user-avatar img, .user-avatar-small img, .user-avatar-image, [class*="avatar"] img')) return;
    const holder = img.parentElement;
    const name = (document.querySelector('.user-details h3, .user-info h3')?.textContent || 'U').trim();
    img.remove();
    if (holder && !holder.textContent.trim()) holder.textContent = name.charAt(0).toUpperCase();
  }, true);
  // mark the current quick filter
  document.addEventListener('DOMContentLoaded', () => {
    const f = new URLSearchParams(location.search).get('filter');
    document.querySelectorAll('.qf-link').forEach((a) => {
      const af = new URL(a.href, location.href).searchParams.get('filter');
      if ((af || null) === (f || null)) a.classList.add('active');
    });
  });

  document.addEventListener('DOMContentLoaded', scan);
})();
