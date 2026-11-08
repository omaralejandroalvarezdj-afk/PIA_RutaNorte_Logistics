// Pestaña 3 · Operaciones / Sucursal: CU-02 asignar, CU-03/CU-04 recolección y discrepancia >15 %, CU-05 entrega
import { api } from '../api.js';
import { alertBox, btn2Cls, btnCls, card, esc, field, heading, inputCls, options, pill, toast } from '../ui.js';

let root, ordenes = [], flota = { vehiculos: [], operadores: [] }, sel = null;

export function mount(el) {
  root = el;
  root.innerHTML = heading('CU-02 · CU-03 · CU-04 · CU-05', 'Operaciones de sucursal', 'Asigna recursos, valida la recolección y registra la entrega. Si el peso real supera en más de 15 % lo cotizado, la orden pasa a "En revisión por Ventas".') +
    `<div class="grid gap-4 sm:grid-cols-3 mb-6" id="stats"></div>
     <div class="grid gap-6 lg:grid-cols-5"><div class="lg:col-span-2" id="lista"></div><div class="lg:col-span-3" id="accion"></div></div>`;
}

export async function onShow() { await cargar(); }

async function cargar() {
  try { [ordenes, flota] = await Promise.all([api.ordenes(), api.flota()]); } catch (e) { return toast(e.message); }
  const n = (f) => ordenes.filter(f).length;
  const stat = (t, v) => card(`<div class="p-5"><p class="text-sm text-slate-500">${t}</p><p class="text-3xl font-extrabold">${v}</p></div>`);
  root.querySelector('#stats').innerHTML = stat('Órdenes', ordenes.length) + stat('Recolectadas o entregadas', n((o) => ['RECOLECTADO', 'ENTREGADO_CON_POD'].includes(o.estatus_actual))) + stat('En revisión por Ventas', n((o) => o.estatus_actual === 'EN_REVISION_POR_VENTAS'));
  root.querySelector('#lista').innerHTML = card(`<div class="p-4 font-bold border-b border-slate-100">Órdenes</div><div class="divide-y divide-slate-100 max-h-[480px] overflow-y-auto">` +
    (ordenes.length ? [...ordenes].reverse().map((o) => `<button data-o="${esc(o.folio)}" class="w-full text-left p-4 flex justify-between gap-3 hover:bg-slate-50 ${o.folio === sel ? 'bg-blue-50' : ''}"><div><p class="font-bold text-sm">${esc(o.folio)}</p><p class="text-xs text-slate-500">${esc(o.origen)} → ${esc(o.destino)}</p></div>${pill(o.estatus_actual)}</button>`).join('') : '<p class="p-6 text-sm text-slate-500">Aún no hay órdenes. Crea una en "Cotizar / Reservar".</p>') + '</div>');
  root.querySelectorAll('[data-o]').forEach((b) => (b.onclick = () => { sel = b.dataset.o; cargar(); }));
  panel();
}

function panel() {
  const box = root.querySelector('#accion'), o = ordenes.find((x) => x.folio === sel);
  if (!o) { box.innerHTML = card('<p class="p-8 text-center text-slate-500">Selecciona una orden de la lista.</p>'); return; }
  const e = o.estatus_actual;
  let body = '';
  if (e === 'REGISTRADO') body = `<p class="text-sm mb-4">Orden registrada. Confírmala para continuar (valida crédito del cliente).</p><button id="a-conf" class="${btnCls}">Confirmar cotización (CU-01)</button>`;
  else if (e === 'CONFIRMADA') body = `<form id="a-asig" class="grid gap-4 sm:grid-cols-2">${field('Vehículo', `<select id="veh" class="${inputCls}">${options(flota.vehiculos, (v) => v.id, (v) => `${v.placas} · ${v.tipo_unidad} (${v.estado})`)}</select>`)}
    ${field('Operador', `<select id="ope" class="${inputCls}">${options(flota.operadores, (x) => x.id, (x) => x.nombre)}</select>`)}<div class="sm:col-span-2"><button class="${btnCls}">Asignar unidad y operador (CU-02)</button></div></form>`;
  else if (e === 'UNIDAD_ASIGNADA') body = `<form id="a-val" class="grid gap-4 sm:grid-cols-2">${field('Peso cotizado (kg)', `<input id="pc" type="number" min="1" step="any" value="1000" class="${inputCls}">`)}${field('Peso real (kg)', `<input id="pr" type="number" min="1" step="any" value="1160" class="${inputCls}">`)}
    <div class="sm:col-span-2"><button class="${btnCls}">Validar recolección (CU-03 / CU-04)</button><p class="text-xs text-slate-500 mt-2">Prueba 1000 vs 1160 kg para activar la revisión por discrepancia (&gt; 15 %).</p></div></form>`;
  else if (e === 'RECOLECTADO') body = `<form id="a-ent" class="grid gap-4 sm:grid-cols-2">${field('Firma digital', `<input id="firma" class="${inputCls}" value="FirmaDigitalReceptor" required>`)}${field('INE del receptor', `<input id="ine" class="${inputCls}" value="1234567890" required>`)}
    <div class="sm:col-span-2">${field('Fotografías (separadas por coma)', `<input id="fotos" class="${inputCls}" value="entrega1.jpg">`)}</div><div class="sm:col-span-2"><button class="${btnCls}">Registrar entrega con POD (CU-05)</button></div></form>`;
  else if (e === 'EN_REVISION_POR_VENTAS') body = alertBox('warn', 'Orden retenida por discrepancia de peso. Ventas debe recotizar con el cliente.');
  else body = '<p class="text-sm text-slate-500">Esta orden está en un estado final.</p>';
  const cancel = !['ENTREGADO_CON_POD', 'CANCELADA'].includes(e) ? `<button id="a-can" class="${btn2Cls} text-red-700">Cancelar orden</button>` : '';
  box.innerHTML = card(`<div class="p-5 border-b border-slate-100 flex justify-between items-center gap-3"><div><h2 class="font-extrabold text-lg">${esc(o.folio)}</h2><p class="text-xs text-slate-500">${esc(o.cliente)}</p></div>${pill(e)}</div>
    <div class="p-5">${body}<div id="fb" class="mt-4"></div></div>${cancel ? `<div class="px-5 pb-5">${cancel}</div>` : ''}`);
  const $ = (s) => box.querySelector(s), v = (s) => $(s).value;
  if ($('#a-conf')) $('#a-conf').onclick = () => run(() => api.confirmar(sel));
  if ($('#a-asig')) $('#a-asig').onsubmit = (ev) => { ev.preventDefault(); const veh = flota.vehiculos.find((x) => x.id === v('#veh')), ope = flota.operadores.find((x) => x.id === v('#ope')); run(() => api.asignar(sel, { vehiculo_id: veh.id, placas: veh.placas, tipo_unidad: veh.tipo_unidad, operador_id: ope.id, nombre_operador: ope.nombre })); };
  if ($('#a-val')) $('#a-val').onsubmit = (ev) => { ev.preventDefault(); run(() => api.validar(sel, { peso_cotizado: Number(v('#pc')), peso_real: Number(v('#pr')) })); };
  if ($('#a-ent')) $('#a-ent').onsubmit = (ev) => { ev.preventDefault(); run(() => api.entregar(sel, { firma_digital: v('#firma'), ine: v('#ine'), fotografias: v('#fotos').split(',').map((s) => s.trim()).filter(Boolean) })); };
  if ($('#a-can')) $('#a-can').onclick = () => { const m = prompt('Motivo de la cancelación:'); if (m) run(() => api.cancelar(sel, m)); };
}

async function run(accion) {
  const fb = () => root.querySelector('#fb');
  let msg;
  try { const r = await accion(); msg = alertBox('ok', '✓ ' + esc(r.mensaje)); }
  catch (err) { msg = alertBox(err.status === 409 ? 'warn' : 'err', `<b>${err.status || ''}</b> ${esc(err.message)}`); }
  await cargar();
  if (fb()) fb().innerHTML = msg;
}
