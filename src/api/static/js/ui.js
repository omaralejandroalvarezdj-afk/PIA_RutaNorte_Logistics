// Utilidades de presentación compartidas por las vistas.
export const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const money = (v) => Number(v).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
export const fmtDate = (iso) => new Date(iso).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' });

export const ESTADOS = {
  REGISTRADO: ['Registrado', 'bg-slate-100 text-slate-700'],
  CONFIRMADA: ['Confirmada', 'bg-blue-50 text-blue-700'],
  UNIDAD_ASIGNADA: ['Unidad asignada', 'bg-indigo-50 text-indigo-700'],
  RECOLECTADO: ['Recolectado', 'bg-sky-50 text-sky-700'],
  EN_REVISION_POR_VENTAS: ['En revisión por Ventas', 'bg-amber-50 text-amber-800'],
  ENTREGADO_CON_POD: ['Entregado con POD', 'bg-green-50 text-green-700'],
  CANCELADA: ['Cancelada', 'bg-red-50 text-red-700'],
};
export const FLUJO = ['REGISTRADO', 'CONFIRMADA', 'UNIDAD_ASIGNADA', 'RECOLECTADO', 'ENTREGADO_CON_POD'];

export const pill = (estado) => {
  const [label, cls] = ESTADOS[estado] || [estado, 'bg-slate-100 text-slate-700'];
  return `<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${cls}">● ${esc(label)}</span>`;
};

let toastTimer;
export function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 4500);
}

export const alertBox = (tipo, html) => {
  const c = { ok: 'bg-green-50 text-green-800 border-green-200', warn: 'bg-amber-50 text-amber-900 border-amber-200', err: 'bg-red-50 text-red-800 border-red-200' }[tipo];
  return `<div class="rounded-xl border p-4 text-sm ${c}">${html}</div>`;
};

export const card = (inner, extra = '') => `<div class="bg-white rounded-2xl border border-slate-200 shadow-sm ${extra}">${inner}</div>`;
export const heading = (kicker, title, sub = '') => `
  <div class="mb-6"><p class="text-xs font-bold tracking-widest text-blue-600 uppercase mb-2">${kicker}</p>
  <h1 class="text-3xl font-extrabold tracking-tight">${title}</h1>${sub ? `<p class="mt-2 text-slate-500 max-w-2xl">${sub}</p>` : ''}</div>`;
export const field = (label, control) => `<label class="block text-sm font-semibold text-slate-700">${label}<div class="mt-1.5 font-normal">${control}</div></label>`;
export const inputCls = 'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500';
export const btnCls = 'rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm px-4 py-2.5 disabled:opacity-50';
export const btn2Cls = 'rounded-lg border border-slate-300 hover:bg-slate-50 font-semibold text-sm px-4 py-2.5';
export const options = (items, value, label, selected) => items.map((i) => `<option value="${esc(value(i))}" ${selected === value(i) ? 'selected' : ''}>${esc(label(i))}</option>`).join('');
