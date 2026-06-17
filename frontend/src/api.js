const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Error en la API')
  }
  return res.json()
}

export const api = {
  equipos:      ()            => apiFetch('/equipos'),
  sedes:        ()            => apiFetch('/sedes'),
  grupos:       ()            => apiFetch('/grupos'),
  fechas:       ()            => apiFetch('/fixture/fechas'),
  partidosDia:  (fecha)       => apiFetch(`/fixture/${fecha}`),
  predecirDia:  (fecha)       => apiFetch(`/predecir-dia/${fecha}`),
  predecir:     (body)        => apiFetch('/predecir', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  }),
}
