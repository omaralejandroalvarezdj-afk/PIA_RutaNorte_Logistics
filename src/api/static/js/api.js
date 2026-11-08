// Cliente REST de RutaNorte. Misma origen que la API (sin CORS). Cada función = un endpoint.
async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* respuesta sin cuerpo */ }
  if (!res.ok) {
    const detail = Array.isArray(data?.detail) ? data.detail.map((d) => d.msg).join('; ') : data?.detail;
    const err = new Error(data?.mensaje || detail || res.statusText);
    err.status = res.status;
    throw err;
  }
  return data;
}

const enc = encodeURIComponent;
export const api = {
  catalogo: () => request('/catalogo'),
  clientes: () => request('/clientes'),
  cotizar: (b) => request('/cotizaciones', { method: 'POST', body: b }),
  crearOrden: (b) => request('/orders', { method: 'POST', body: b }),
  ordenes: () => request('/orders'),
  orden: (id) => request(`/orders/${enc(id)}`),
  eventos: (id) => request(`/orders/${enc(id)}/eventos`),
  confirmar: (id) => request(`/orders/${enc(id)}/confirmar`, { method: 'POST' }),
  asignar: (id, b) => request(`/orders/${enc(id)}/asignar-recursos`, { method: 'POST', body: b }),
  validar: (id, b) => request(`/orders/${enc(id)}/validar-recoleccion`, { method: 'POST', body: b }),
  entregar: (id, b) => request(`/orders/${enc(id)}/entregar`, { method: 'POST', body: b }),
  cancelar: (id, motivo) => request(`/orders/${enc(id)}/cancelar`, { method: 'POST', body: { motivo } }),
  flota: () => request('/flota'),
  kpis: () => request('/kpis'),
};
