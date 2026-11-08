// Pestaña 2 · Mi Envío: consulta CQRS (estado en la máquina de estados + eventos de dominio)
import { api } from '../api.js';
import { alertBox, btnCls, card, esc, fmtDate, FLUJO, heading, inputCls, money, pill, ESTADOS } from '../ui.js';

let root;
const ESTADO_API = {
  'Pendiente de confirmación': 'REGISTRADO',
  'Confirmada': 'CONFIRMADA',
  'Vehículo y conductor asignados': 'UNIDAD_ASIGNADA',
  'Mercancía recolectada': 'RECOLECTADO',
  'En revisión': 'EN_REVISION_POR_VENTAS',
  'Entregada': 'ENTREGADO_CON_POD',
  'Cancelada': 'CANCELADA'
};
export function mount(el) {
  root = el;
  root.innerHTML = heading('Consulta de órdenes · CQRS', 'Rastrea tu envío', 'Consulta el estado de la orden en la máquina de estados y su historial de eventos de dominio.') +
    `<form id="f" class="flex gap-3 max-w-xl"><input id="folio" placeholder="Folio, p. ej. ORD-1A2B3C4D5E" class="${inputCls}" required><button class="${btnCls}">Rastrear</button></form>
     <div id="recientes" class="mt-3 flex flex-wrap gap-2 text-xs"></div><div id="res" class="mt-6"></div>`;
  root.querySelector('#f').onsubmit = (e) => { e.preventDefault(); rastrear(root.querySelector('#folio').value.trim()); };
}

export async function onShow(params) {
  try {
    const lista = (await api.ordenes()).slice(-6).reverse();
    root.querySelector('#recientes').innerHTML = lista.length ? '<span class="text-slate-500 py-1">Recientes:</span>' + lista.map((o) => `<button data-f="${esc(o.folio)}" class="rounded-full border border-slate-300 bg-white px-3 py-1 hover:bg-slate-50">${esc(o.folio)}</button>`).join('') : '';
    root.querySelectorAll('[data-f]').forEach((b) => (b.onclick = () => { root.querySelector('#folio').value = b.dataset.f; rastrear(b.dataset.f); }));
  } catch { /* la lista es opcional */ }
  if (params?.folio) { root.querySelector('#folio').value = params.folio; rastrear(params.folio); }
}

async function rastrear(folio) {
  const res = root.querySelector('#res');
  try {
    const [o, ev] = await Promise.all([api.orden(folio), api.eventos(folio)]);
    const estado = ESTADO_API[o.estado] || o.estado;
    const enRevision = estado === 'EN_REVISION_POR_VENTAS', cancelada = estado === 'CANCELADA';
    const idx = FLUJO.indexOf(estado);
    const paso = (s, i) => `<div class="flex-1 min-w-[110px] text-center"><div class="mx-auto w-9 h-9 rounded-full grid place-items-center text-sm font-bold ${i <= idx ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}">${i + 1}</div><p class="mt-2 text-xs font-semibold ${i <= idx ? 'text-slate-900' : 'text-slate-400'}">${ESTADOS[s][0]}</p></div>`;
    res.innerHTML = card(`
      <div class="p-6 border-b border-slate-100 flex flex-wrap justify-between gap-3">
        <div><p class="text-xs text-slate-500">Folio</p><h2 class="text-2xl font-extrabold">${esc(o.numero_orden)}</h2>
        <p class="text-sm text-slate-600 mt-1">${esc(o.origen)} → ${esc(o.destino)} · ${esc(o.cliente)} · ${money(o.total)}</p></div>${pill(estado)}</div>
      <div class="p-6">${enRevision ? alertBox('warn', 'La orden fue retenida por una discrepancia de peso mayor al 15 % y espera recotización de Ventas.') : cancelada ? alertBox('err', 'La orden fue cancelada.') : `<div class="flex gap-2 flex-wrap">${FLUJO.map(paso).join('')}</div>`}</div>
      <div class="px-6 pb-6"><h3 class="font-bold mb-3">Eventos de dominio</h3>
        <ol class="space-y-3 border-l-2 border-slate-200 ml-2">${ev.map((e) => `<li class="pl-4 relative"><span class="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-blue-600"></span><p class="font-semibold text-sm">${esc(e.evento)}</p><p class="text-xs text-slate-500">${fmtDate(e.ocurrido_en)}${e.detalle ? ' · ' + esc(e.detalle) : ''}</p></li>`).join('')}</ol></div>`);
  } catch (err) { res.innerHTML = alertBox(err.status === 404 ? 'warn' : 'err', esc(err.message)); }
}
