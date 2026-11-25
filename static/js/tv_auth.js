// TaskVise sign-in / sign-up behaviour. Without JS the form still posts and every sign-up step is visible.
(() => {
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // show / hide password
  $$('[data-reveal]').forEach((btn) => btn.addEventListener('click', () => {
    const input = btn.parentElement.querySelector('input');
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.textContent = show ? 'Hide' : 'Show';
    btn.setAttribute('aria-pressed', String(show));
  }));

  // skills as chips, stored in the hidden field the server already reads (comma separated)
  const chips = document.querySelector('.chips');
  if (chips) {
    const hidden = document.getElementById('skills');
    const input = chips.querySelector('input');
    const skills = [];
    const sync = () => { hidden.value = skills.join(', '); hidden.setCustomValidity(skills.length ? '' : 'Add at least one skill'); };
    const draw = () => {
      $$('.chip', chips).forEach((c) => c.replaceChildren());
      $$('.chip', chips).forEach((c) => c.hidden = true);
      skills.forEach((name, i) => {
        const chip = document.createElement('span'); chip.className = 'chip'; chip.append(name);
        const x = document.createElement('button'); x.type = 'button'; x.setAttribute('aria-label', `Remove ${name}`); x.textContent = '×';
        x.addEventListener('click', () => { skills.splice(i, 1); draw(); sync(); });
        chip.append(x); chips.insertBefore(chip, input);
      });
      sync();
    };
    const add = () => {
      input.value.split(',').map((s) => s.trim()).filter(Boolean).forEach((s) => {
        if (!skills.some((k) => k.toLowerCase() === s.toLowerCase()) && skills.length < 15) skills.push(s);
      });
      input.value = ''; draw();
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(); }
      if (e.key === 'Backspace' && !input.value && skills.length) { skills.pop(); draw(); }
    });
    input.addEventListener('blur', add);
    chips.addEventListener('click', () => input.focus());
    sync();
  }

  // stepper
  const steps = $$('.step');
  if (steps.length > 1) {
    const items = $$('.stepper li');
    let i = 0;
    const show = (n) => {
      i = Math.max(0, Math.min(steps.length - 1, n));
      steps.forEach((s, k) => { s.hidden = k !== i; });
      items.forEach((li, k) => { k === i ? li.setAttribute('aria-current', 'step') : li.removeAttribute('aria-current'); li.toggleAttribute('data-done', k < i); });
      (steps[i].querySelector('input, select') || {}).focus?.({ preventScroll: true });
    };
    $$('[data-next]').forEach((b) => b.addEventListener('click', () => {
      const bad = $$('input, select', steps[i]).find((x) => !x.checkValidity());
      if (bad) { bad.reportValidity(); return; }
      show(i + 1);
    }));
    $$('[data-back]').forEach((b) => b.addEventListener('click', () => show(i - 1)));
    show(0);
  }
})();
