import { useState, useEffect } from "react"
import { api } from "../api"

function PartidoCard({ partido }) {
  const { t1, t2, grupo, ciudad, hora, jugado, resultado, goles, metricas, error } = partido

  if (error) {
    return (
      <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
        <p className="text-sm text-gray-500">{t1} vs {t2}</p>
        <p className="text-xs text-red-400 mt-1">{error}</p>
      </div>
    )
  }

  const pw1 = goles?.pw1 ?? 0
  const pd  = goles?.pd  ?? 0
  const pw2 = goles?.pw2 ?? 0

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-4">
      {/* Header partido */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-400">{grupo} · {ciudad} · {hora}</div>
        {jugado && resultado?.ft && (
          <span className="bg-green-50 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
            Jugado: {resultado.ft[0]}–{resultado.ft[1]}
          </span>
        )}
      </div>

      {/* Equipos + barras */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="w-28 text-sm font-semibold text-gray-800 truncate">{t1}</span>
          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-600 rounded-full" style={{ width: `${(pw1*100).toFixed(0)}%` }} />
          </div>
          <span className="w-10 text-right text-sm font-bold text-blue-600">{(pw1*100).toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="w-28 text-sm text-gray-500">Empate</span>
          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-gray-400 rounded-full" style={{ width: `${(pd*100).toFixed(0)}%` }} />
          </div>
          <span className="w-10 text-right text-sm font-bold text-gray-500">{(pd*100).toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="w-28 text-sm font-semibold text-gray-800 truncate">{t2}</span>
          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-red-500 rounded-full" style={{ width: `${(pw2*100).toFixed(0)}%` }} />
          </div>
          <span className="w-10 text-right text-sm font-bold text-red-500">{(pw2*100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Top 3 marcadores */}
      {goles?.top_resultados && (
        <div className="flex gap-2 flex-wrap">
          {goles.top_resultados.slice(0, 3).map((r, i) => (
            <span key={i} className="bg-gray-50 border border-gray-100 text-xs px-2 py-1 rounded-lg text-gray-600">
              {r.goles1}–{r.goles2} <span className="text-gray-400">({r.prob}%)</span>
            </span>
          ))}
        </div>
      )}

      {/* Metricas compactas */}
      {metricas && (
        <div className="grid grid-cols-3 gap-2 border-t border-gray-50 pt-3">
          {[
            ["Corners",    metricas.corners?.ou],
            ["Tiros",      metricas.tiros?.ou],
            ["Amarillas",  metricas.amarillas?.ou],
          ].map(([label, ou]) => (
            <div key={label} className="text-center">
              <p className="text-xs text-gray-400">{label}</p>
              <p className="text-sm font-bold text-gray-700">O/U {ou}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function PartidosDelDia() {
  const [fechas,   setFechas]   = useState([])
  const [fecha,    setFecha]    = useState("")
  const [partidos, setPartidos] = useState([])
  const [loading,  setLoading]  = useState(false)

  useEffect(() => {
    api.fechas().then(d => {
      setFechas(d.fechas)
      if (d.fechas.length > 0) setFecha(d.fechas[0])
    })
  }, [])

  const cargar = async () => {
    if (!fecha) return
    setLoading(true)
    try {
      const d = await api.predecirDia(fecha)
      setPartidos(d.partidos)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Partidos del dia</h2>
        <div className="flex gap-3">
          <select
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={fecha}
            onChange={e => setFecha(e.target.value)}
          >
            {fechas.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          <button
            onClick={cargar}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Cargando..." : "Ver partidos"}
          </button>
        </div>
      </div>

      {partidos.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {partidos.map((p, i) => <PartidoCard key={i} partido={p} />)}
        </div>
      )}
    </div>
  )
}
