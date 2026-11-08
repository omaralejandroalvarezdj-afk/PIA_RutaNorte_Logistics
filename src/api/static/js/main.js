import * as cotizar from './views/cotizar.js';
import * as envio from './views/envio.js';
import * as operaciones from './views/operaciones.js';
import * as indicadores from './views/indicadores.js';

const views = { cotizar, envio, operaciones, indicadores };
const root = (name) => document.getElementById(`panel-${name}`);

for (const [name, view] of Object.entries(views)) view.mount(root(name), { go });

export function go(name, params) {
  if (!views[name]) name = 'cotizar';
  document.querySelectorAll('[data-tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === name)));
  document.querySelectorAll('[data-panel]').forEach((p) => (p.hidden = p.id !== `panel-${name}`));
  history.replaceState(null, '', `#${name}`);
  views[name].onShow?.(params);
  window.scrollTo({ top: 0 });
}

document.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => go(b.dataset.tab)));
go(location.hash.slice(1) || 'cotizar');
