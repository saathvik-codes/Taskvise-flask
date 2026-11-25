/* Places TaskVise illustrations: empty states (by wording), page-header spots, role overview art. */
(() => {
  const base = '/static/illustrations/';
  const EMPTY = [
    [/leave/i, 'tv-empty-leave'], [/attendance/i, 'tv-empty-attendance'], [/notification/i, 'tv-empty-notifications'],
    [/help request|help/i, 'tv-empty-help'], [/skill|recommendation|gap/i, 'tv-empty-skills'], [/analytic|chart|trend|distribution|performance data|department/i, 'tv-empty-analytics'],
    [/note/i, 'tv-empty-notes'], [/project/i, 'tv-empty-projects'], [/employee|team member|joiner|people|payroll/i, 'tv-empty-employees'], [/task/i, 'tv-empty-tasks'],
  ];
  const art = (name, cls) => { const i = new Image(); i.src = `${base}${name}.webp`; i.alt = ''; i.className = cls; i.width = 160; i.height = 120; i.decoding = 'async'; i.onerror = () => i.remove(); return i; };

  const emptyStates = () => {
    document.querySelectorAll('.empty-state, .no-data, .empty').forEach((el) => {
      if (el.dataset.tvArt || el.querySelector('img')) return;
      el.dataset.tvArt = '1';
      const hit = EMPTY.find(([re]) => re.test(el.textContent || ''));
      if (!hit) return;
      el.querySelectorAll('i.fas, i.far, svg').forEach((n) => { if (n.closest('.empty-state, .no-data, .empty') === el && !n.closest('button, a')) n.remove(); });
      el.prepend(art(hit[1], 'tv-empty-art'));
    });
  };

  const headerArt = () => {
    const head = document.querySelector('.content-header');
    if (!head || head.querySelector('.tv-header-art')) return;
    const p = location.pathname;
    let name = null;
    if (/workload/.test(p)) name = 'tv-workload';
    else if (/payment/.test(p)) name = 'tv-payments';
    else if (/(overview|dashboard)\/?$/.test(p)) name = { admin: 'tv-role-admin', hr: 'tv-role-hr', manager: 'tv-role-manager', teamlead: 'tv-role-lead', employee: 'tv-role-employee' }[p.split('/')[1]];
    if (name) head.append(art(name, 'tv-header-art'));
  };

  const run = () => { emptyStates(); headerArt(); };
  let t; new MutationObserver(() => { clearTimeout(t); t = setTimeout(run, 150); }).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener('DOMContentLoaded', run);
})();
