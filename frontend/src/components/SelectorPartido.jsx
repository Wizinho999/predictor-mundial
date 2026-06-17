import { useState, useEffect } from "react"
import { api } from "../api"

const FASES = [
  { value: "grupos",    label: "Fase de grupos" },
  { value: "octavos",   label: "Octavos de final" },
  { value: "cuartos",   label: "Cuartos de final" },
  { value: "semifinal", label: "Semifinal" },
  { value: "final",     label: "Final" },
]

export default function SelectorPartido({ onPredecir, loading }) {
  const [equipos, setEquipos] = useState([])
  const [sedes,   setSedes]   = useState([])
  const [form, setForm] = useState({
    equipo1: "Argentina", equipo2: "France",
    fase: "grupos", sede: "", descanso_diff: 0,
  })

  useEffect(() => {
    api.equipos().then(d => setEquipos(d.equipos))
    api.sedes().then(d => setSedes(d.sedes))
  }, [])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const elo1 = /* placeholder — viene del backend */ null
  const elo2 = null

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-5">
      <h2 className="text-lg font-semibold text-gray-800">Prediccion de partido</h2>

      <div className="grid grid-cols-2 gap-4">
        {[["equipo1","Equipo 1"],["equipo2","Equipo 2"]].map(([key, label]) => (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
            <select
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form[key]}
              onChange={e => set(key, e.target.value)}
            >
              {equipos.map(e => <option key={e} value={e}>{e}</option>)}
            </select>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Fase</label>
          <select
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.fase}
            onChange={e => set("fase", e.target.value)}
          >
            {FASES.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Sede</label>
          <select
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.sede}
            onChange={e => set("sede", e.target.value)}
          >
            <option value="">Sin especificar (neutral)</option>
            {sedes.map(s => (
              <option key={s.nombre} value={s.nombre}>
                {s.nombre} {s.alta_altitud ? "⛰" : ""} — {s.estadio}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Diferencia de descanso: {form.descanso_diff === 0
            ? "Mismo descanso"
            : form.descanso_diff > 0
              ? `${form.equipo1} tiene ${form.descanso_diff} dia(s) mas`
              : `${form.equipo2} tiene ${Math.abs(form.descanso_diff)} dia(s) mas`}
        </label>
        <input
          type="range" min={-3} max={3} step={1}
          value={form.descanso_diff}
          onChange={e => set("descanso_diff", Number(e.target.value))}
          className="w-full accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>-3 (ventaja E2)</span>
          <span>0</span>
          <span>+3 (ventaja E1)</span>
        </div>
      </div>

      <button
        onClick={() => onPredecir(form)}
        disabled={loading || !form.equipo1 || !form.equipo2 || form.equipo1 === form.equipo2}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm"
      >
        {loading ? "Calculando..." : "Predecir partido"}
      </button>
    </div>
  )
}
