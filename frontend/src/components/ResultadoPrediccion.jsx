const COLORES = {
  azul:   "bg-blue-600",
  gris:   "bg-gray-400",
  rojo:   "bg-red-500",
}

function BarraProb({ label, prob, color, sublabel }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-700 font-medium truncate max-w-[60%]">{label}</span>
        <span className="font-semibold text-gray-900">{(prob * 100).toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${(prob * 100).toFixed(1)}%` }}
        />
      </div>
      {sublabel && <p className="text-xs text-gray-400">{sublabel}</p>}
    </div>
  )
}

function MetricaCard({ label, v1, v2, total, ou, e1, e2 }) {
  return (
    <div className="bg-gray-50 rounded-xl p-4 space-y-2">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
      <div className="flex items-end justify-between">
        <div className="text-center">
          <p className="text-xl font-bold text-blue-600">{v1}</p>
          <p className="text-xs text-gray-400 truncate max-w-[70px]">{e1}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400">Total</p>
          <p className="text-2xl font-bold text-gray-800">{total}</p>
          <p className="text-xs text-gray-400">O/U {ou}</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-red-500">{v2}</p>
          <p className="text-xs text-gray-400 truncate max-w-[70px]">{e2}</p>
        </div>
      </div>
    </div>
  )
}

export default function ResultadoPrediccion({ data }) {
  if (!data) return null

  const { equipo1: e1, equipo2: e2, elo1, elo2, goles, metricas, sede, ventaja_e1, ventaja_e2 } = data

  const ventajaTxt = ventaja_e1 > ventaja_e2
    ? `${e1} tiene ventaja de sede`
    : ventaja_e2 > ventaja_e1
      ? `${e2} tiene ventaja de sede`
      : "Partido neutral"

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="text-center">
            <p className="text-lg font-bold text-gray-900">{e1}</p>
            <p className="text-xs text-gray-400">Elo {elo1}</p>
          </div>
          <div className="text-gray-300 text-2xl font-light">vs</div>
          <div className="text-center">
            <p className="text-lg font-bold text-gray-900">{e2}</p>
            <p className="text-xs text-gray-400">Elo {elo2}</p>
          </div>
        </div>

        {sede && (
          <div className="text-center text-xs text-gray-400 mb-4 space-y-0.5">
            <p>{sede.estadio} · {sede.nombre}</p>
            <p>{sede.altitud}m alt · {sede.temperatura}°C jun · {ventajaTxt}</p>
            <p>Dist. {e1}: {sede.distancia_e1?.toLocaleString()} km · {e2}: {sede.distancia_e2?.toLocaleString()} km</p>
          </div>
        )}

        {/* Probabilidades de resultado */}
        <div className="space-y-3">
          <BarraProb label={`Victoria ${e1}`} prob={goles.pw1} color={COLORES.azul} />
          <BarraProb label="Empate"            prob={goles.pd}  color={COLORES.gris} />
          <BarraProb label={`Victoria ${e2}`} prob={goles.pw2} color={COLORES.rojo} />
        </div>
      </div>

      {/* Top marcadores */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Top 10 marcadores mas probables</h3>
        <div className="space-y-2">
          {goles.top_resultados.map((r, i) => {
            const outcome = r.goles1 > r.goles2 ? `Victoria ${e1}` : r.goles1 < r.goles2 ? `Victoria ${e2}` : "Empate"
            const color   = r.goles1 > r.goles2 ? "text-blue-600" : r.goles1 < r.goles2 ? "text-red-500" : "text-gray-500"
            const bgColor = r.goles1 > r.goles2 ? "bg-blue-50" : r.goles1 < r.goles2 ? "bg-red-50" : "bg-gray-50"
            return (
              <div key={i} className={`flex items-center justify-between rounded-lg px-3 py-2 ${bgColor}`}>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-4">{i + 1}</span>
                  <span className="font-bold text-gray-800 text-sm">{r.goles1} – {r.goles2}</span>
                  <span className={`text-xs ${color}`}>{outcome}</span>
                </div>
                <span className="font-semibold text-gray-700 text-sm">{r.prob}%</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Metricas de apuestas */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Metricas de apuestas</h3>
        <div className="grid grid-cols-2 gap-3">
          {[
            ["corners",        "Corners"],
            ["tiros",          "Tiros totales"],
            ["tiros_al_arco",  "Tiros al arco"],
            ["faltas",         "Faltas"],
            ["amarillas",      "Tarjetas amarillas"],
            ["fuera_de_juego", "Fueras de juego"],
          ].map(([key, label]) => {
            const m = metricas[key]
            return (
              <MetricaCard
                key={key} label={label}
                v1={m[e1]} v2={m[e2]} total={m.total} ou={m.ou}
                e1={e1} e2={e2}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}
