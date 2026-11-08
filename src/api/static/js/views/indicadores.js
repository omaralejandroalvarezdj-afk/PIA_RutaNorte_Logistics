// Pestaña 4 · Indicadores: KPIs calculados por el backend + tablas de órdenes y flota
import { api } from '../api.js';
import { alertBox, card, esc, ESTADOS, heading, money, pill, toast } from '../ui.js';

let root;
export function mount(el) {
  root = el;
  root.innerHTML = heading('Dashboard', 'Indicadores de la operación', 'Métricas calculadas en tiempo real por el backend a partir de las órdenes y el historial de eventos.') +
    '<div class="flex justify-end mb-4"><button id="r" class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold hover:bg-slate-50">Actualizar</button></div><div id="d"></div>';
  root.querySelector('#r').onclick = onShow;
}

export async function onShow() {
  const d = root.querySelector('#d');
  try {
    const [k, ordenes, flota] = await Promise.all([api.kpis(), api.ordenes(), api.flota()]);
    const kpi = (t, v, s = '') => card(`<div class="p-5"><p class="text-sm text-slate-500">${t}</p><p class="text-3xl font-extrabold mt-1">${v}</p><p class="text-xs text-slate-400 mt-1">${s}</p></div>`);
    const max = Math.max(1, ...Object.values(k.por_estado));
    const barras = Object.keys(ESTADOS).map((s) => { const n = k.por_estado[s] || 0; return `<div><div class="flex justify-between text-sm mb-1"><span>${ESTADOS[s][0]}</span><b>${n}</b></div><div class="h-2.5 rounded-full bg-slate-100"><div class="h-2.5 rounded-full bg-blue-600" style="width:${(n / max) * 100}%"></div></div></div>`; }).join('');
    const th = (...c) => `<tr>${c.map((x) => `<th class="text-left font-semibold text-slate-500 text-xs uppercase px-4 py-2">${x}</th>`).join('')}</tr>`;
    d.innerHTML = `<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      ${kpi('Órdenes', k.total_ordenes)}${kpi('Discrepancias de peso', k.discrepancias_peso, `${k.tasa_discrepancia_pct} % de las órdenes`)}${kpi('Entregas con POD', k.entregas_completadas)}
      ${kpi('Ciclo promedio', k.ciclo_promedio_horas == null ? '—' : k.ciclo_promedio_horas + ' h', 'registro → entrega')}${kpi('Monto confirmado', money(k.monto_confirmado_mxn), 'órdenes confirmadas')}</div>
      <div class="grid gap-6 lg:grid-cols-2 mt-6">
        ${card(`<div class="p-5"><h2 class="font-bold mb-4">Órdenes por estado</h2><div class="space-y-4">${barras}</div></div>`)}
        ${card(`<div class="p-5"><h2 class="font-bold mb-3">Estado de la flota</h2></div><table class="w-full text-sm">${th('Placas', 'Unidad', 'Estado')}${flota.vehiculos.map((v) => `<tr class="border-t border-slate-100"><td class="px-4 py-2 font-semibold">${esc(v.placas)}</td><td class="px-4 py-2">${esc(v.tipo_unidad)}</td><td class="px-4 py-2">${esc(v.estado)}</td></tr>`).join('')}</table>`)}
      </div>
      ${card(`<div class="p-5"><h2 class="font-bold">Órdenes recientes</h2></div><div class="overflow-x-auto"><table class="w-full text-sm">${th('Folio', 'Cliente', 'Ruta', 'Total', 'Estado')}${ordenes.slice(-8).reverse().map((o) => `<tr class="border-t border-slate-100"><td class="px-4 py-2 font-semibold">${esc(o.folio)}</td><td class="px-4 py-2">${esc(o.cliente)}</td><td class="px-4 py-2">${esc(o.origen)} → ${esc(o.destino)}</td><td class="px-4 py-2">${money(o.total)}</td><td class="px-4 py-2">${pill(o.estatus_actual)}</td></tr>`).join('') || '<tr><td class="px-4 py-6 text-slate-500" colspan="5">Sin órdenes todavía.</td></tr>'}</table></div>`, 'mt-6')}
      <p class="text-xs text-slate-400 mt-4">Actualizado: ${new Date().toLocaleTimeString('es-MX')}</p>`;
  } catch (e) { toast(e.message); d.innerHTML = alertBox('err', esc(e.message)); }
}
