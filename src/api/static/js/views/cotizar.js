// Pestaña 1 · Cotizar / Reservar (CU-01 + validación de crédito corporativo US-13)
import { api } from '../api.js';
import { alertBox, btnCls, card, esc, field, heading, inputCls, money, options, toast } from '../ui.js';

let root, go, catalogo, clientes, cotizacion;

export async function mount(el, ctx) {
  root = el; go = ctx.go;
  root.innerHTML = heading('CU-01 · Cotización', 'Cotiza y confirma tu envío', 'Calcula la tarifa con el motor del backend y confirma la orden. Los clientes corporativos con más de 30 días de morosidad quedan bloqueados.') +
    '<div id="cot-form"></div><div id="cot-result" class="mt-6"></div>';
}

export async function onShow() {
  try { [catalogo, clientes] = await Promise.all([api.catalogo(), api.clientes()]); } catch (e) { return toast(e.message); }
  const hoy = new Date().toISOString().slice(0, 10);
  const c = catalogo;
  root.querySelector('#cot-form').innerHTML = card(`
    <form id="f" class="p-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      ${field('Cliente', `<select id="cliente" class="${inputCls}">${options(clientes, (x) => x.id, (x) => x.razon_social, 'CLI-001')}</select>`)}
      ${field('Origen', `<select id="origen" class="${inputCls}">${options(c.ciudades, (x) => x, (x) => x, 'Monterrey')}</select>`)}
      ${field('Destino', `<select id="destino" class="${inputCls}">${options(c.ciudades, (x) => x, (x) => x, 'San Luis Potosí')}</select>`)}
      ${field('Fecha de recolección', `<input id="f1" type="date" min="${hoy}" value="${hoy}" class="${inputCls}">`)}
      ${field('Fecha de entrega', `<input id="f2" type="date" min="${hoy}" value="${hoy}" class="${inputCls}">`)}
      ${field('Tipo de unidad', `<select id="unidad" class="${inputCls}">${options(c.unidades, (x) => x.clave, (x) => `${x.nombre} (hasta ${x.peso_max_kg.toLocaleString('es-MX')} kg)`, 'rabon')}</select>`)}
      ${field('Tipo de carga', `<select id="carga" class="${inputCls}">${options(c.tipos_carga, (x) => x, (x) => x)}</select>`)}
      ${field('Peso (kg)', `<input id="peso" type="number" min="1" step="any" value="1000" class="${inputCls}">`)}
      ${field('Volumen (m³)', `<input id="vol" type="number" min="0.1" step="any" value="8" class="${inputCls}">`)}
      <div class="sm:col-span-2 lg:col-span-3 flex items-center gap-3"><button class="${btnCls}">Calcular cotización</button>
      <span class="text-xs text-slate-500">Las fechas se validan en la interfaz; el backend aún no las almacena.</span></div>
    </form>`);
  root.querySelector('#f').onsubmit = calcular;
}

async function calcular(e) {
  e.preventDefault();
  const v = (id) => root.querySelector(`#${id}`).value;
  const out = root.querySelector('#cot-result');
  if (v('f2') < v('f1')) return toast('La fecha de entrega no puede ser anterior a la recolección.');
  try {
    cotizacion = await api.cotizar({ 
      cliente_id: v('cliente'), 
      origen: v('origen'), 
      destino: v('destino'), 
      unidad: v('unidad'), 
      peso_kg: Number(v('peso')), 
      volumen_m3: Number(v('vol')), 
      tipo_carga: v('carga') 
    });
  } catch (err) { out.innerHTML = alertBox('err', esc(err.message)); return; }
  const q = cotizacion, ok = q.credito.apto;
  out.innerHTML = card(`
    <div class="p-6 border-b border-slate-100 flex flex-wrap justify-between gap-3">
      <div><p class="text-xs font-bold tracking-widest text-blue-600 uppercase">Resultado</p>
      <h2 class="text-xl font-extrabold">${esc(q.origen)} → ${esc(q.destino)} · ${q.distancia_km} km · ${esc(q.unidad)}</h2></div>
      <p class="text-3xl font-extrabold">${money(q.total)}</p></div>
    <div class="p-6 grid gap-4 sm:grid-cols-3 text-sm">
      <div><p class="text-slate-500">Subtotal</p><p class="font-bold">${money(q.subtotal)}</p></div>
      <div><p class="text-slate-500">IVA 16 %</p><p class="font-bold">${money(q.iva)}</p></div>
      <div><p class="text-slate-500">Total ${esc(q.moneda)}</p><p class="font-bold">${money(q.total)}</p></div></div>
    <div class="px-6 pb-6 space-y-4">${alertBox(ok ? 'ok' : 'err', `<b>Crédito (US-13):</b> ${esc(q.credito.mensaje)}`)}
      <button id="confirmar" class="${btnCls}">${ok ? 'Confirmar cotización y generar orden' : 'Intentar confirmar (el backend la rechazará)'}</button>
      <div id="conf-out"></div></div>`);
  out.querySelector('#confirmar').onclick = confirmar;
}

async function confirmar(e) {
  const v = (id) => root.querySelector(`#${id}`).value;
  const q = cotizacion, box = root.querySelector('#conf-out');
  e.target.disabled = true;
  let folio;
  try {
    // Se envían todos los datos requeridos por el backend para la creación de la orden
    const orden = await api.crearOrden({ 
      cliente_id: v('cliente'), 
      origen: q.origen, 
      destino: q.destino, 
      distancia_km: q.distancia_km, 
      subtotal: q.subtotal, 
      total: q.total,
      unidad: q.unidad,
      peso_kg: Number(v('peso')),
      volumen_m3: Number(v('vol')),
      tipo_carga: v('carga')
    });
    folio = orden.numero_orden;
    await api.confirmar(folio);
    box.innerHTML = alertBox('ok', `✓ Orden <b>${esc(folio)}</b> confirmada. <button data-rastrear class="underline font-bold ml-2">Rastrear envío →</button>`);
    box.querySelector('[data-rastrear]').onclick = () => go('envio', { folio });
  } catch (err) {
    box.innerHTML = alertBox('err', `${esc(err.message)}${folio ? `<br><span class="text-xs">La orden quedó registrada con el folio <b>${esc(folio)}</b> sin confirmar.</span>` : ''}`);
    e.target.disabled = false;
  }
}
