import { useState } from "react"
import { api } from "./api"
import SelectorPartido from "./components/SelectorPartido"
import ResultadoPrediccion from "./components/ResultadoPrediccion"
import PartidosDelDia from "./components/PartidosDelDia"

const TABS = [
  { id: "predictor", label: "Predictor" },
  { id: "dia",       label: "Partidos del dia" },
]

export default function App() {
  const [tab,       setTab]       = useState("predictor")
  const [resultado, setResultado] = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)

  const predecir = async (form) => {
    setLoading(true)
    setError(null)
    setResultado(null)
    try {
      const data = await api.predecir(form)
      setResultado(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Predictor Mundial 2026</h1>
            <p className="text-xs text-gray-400">Elo · Poisson · Dixon-Coles · Monte Carlo · xG</p>
          </div>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  tab === t.id
                    ? "bg-white shadow-sm text-gray-900"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-4 py-6">
        {tab === "predictor" && (
          <div className="grid md:grid-cols-[380px_1fr] gap-6 items-start">
            <div className="space-y-4">
              <SelectorPartido onPredecir={predecir} loading={loading} />
              {error && (
                <div className="bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl px-4 py-3">
                  {error}
                </div>
              )}
            </div>
            <div>
              {resultado
                ? <ResultadoPrediccion data={resultado} />
                : (
                  <div className="flex items-center justify-center h-64 text-gray-300 text-sm">
                    Selecciona dos equipos y presiona "Predecir partido"
                  </div>
                )
              }
            </div>
          </div>
        )}

        {tab === "dia" && <PartidosDelDia />}
      </main>

      <footer className="text-center text-xs text-gray-300 py-8">
        Datos: martj42 · StatsBomb · openfootball · Open-Meteo
      </footer>
    </div>
  )
}
