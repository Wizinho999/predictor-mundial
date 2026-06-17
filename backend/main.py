"""
main.py — FastAPI backend del Predictor Mundial 2026
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import modelo

@asynccontextmanager
async def lifespan(app: FastAPI):
    modelo.inicializar()
    yield

app = FastAPI(title="Predictor Mundial 2026", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ────────────────────────────────────────────────────────────────
class PredecirRequest(BaseModel):
    equipo1:       str
    equipo2:       str
    fase:          str  = "grupos"
    sede:          Optional[str] = None
    descanso_diff: int  = 0

# ── Endpoints ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "mensaje": "Predictor Mundial 2026 activo"}

@app.get("/equipos")
def listar_equipos():
    return {
        "equipos": sorted(modelo.FIFA_ELO.keys()),
        "total":   len(modelo.FIFA_ELO),
    }

@app.get("/sedes")
def listar_sedes():
    return {
        "sedes": [
            {
                "nombre":  nombre,
                "estadio": d["estadio"],
                "ciudad":  nombre,
                "altitud": d["alt"],
                "pais":    d["pais"],
                "alta_altitud": d["alt"] >= modelo.ALTITUD_UMBRAL,
            }
            for nombre, d in modelo.SEDES.items()
        ]
    }

@app.get("/grupos")
def listar_grupos():
    return {
        "grupos": [
            {
                "nombre":  letra,
                "equipos": [
                    {"nombre": e, "elo": modelo.FIFA_ELO.get(e, 0)}
                    for e in equipos
                ],
            }
            for letra, equipos in modelo.GRUPOS.items()
        ]
    }

@app.get("/fixture/fechas")
def listar_fechas():
    return {"fechas": modelo.fechas_disponibles()}

@app.get("/fixture/{fecha}")
def partidos_del_dia(fecha: str):
    partidos = modelo.partidos_por_fecha(fecha)
    if not partidos:
        raise HTTPException(404, f"No hay partidos para {fecha}")
    return {"fecha": fecha, "partidos": partidos}

@app.post("/predecir")
def predecir(req: PredecirRequest):
    if req.equipo1 not in modelo.FIFA_ELO:
        raise HTTPException(400, f"Equipo no encontrado: {req.equipo1}")
    if req.equipo2 not in modelo.FIFA_ELO:
        raise HTTPException(400, f"Equipo no encontrado: {req.equipo2}")
    if req.equipo1 == req.equipo2:
        raise HTTPException(400, "Los equipos deben ser distintos")

    goles   = modelo.predecir_goles(req.equipo1, req.equipo2, req.fase, req.sede, req.descanso_diff)
    metricas= modelo.predecir_metricas(req.equipo1, req.equipo2, req.sede)
    hb1,hb2 = modelo.ventaja_relativa(req.equipo1, req.equipo2, req.sede)

    sede_info = None
    if req.sede and req.sede in modelo.SEDES:
        sd = modelo.SEDES[req.sede]
        _, d1 = modelo.factor_distancia(req.equipo1, req.sede)
        _, d2 = modelo.factor_distancia(req.equipo2, req.sede)
        sede_info = {
            "nombre":       req.sede,
            "estadio":      sd["estadio"],
            "altitud":      sd["alt"],
            "temperatura":  modelo._estado["temp_sede"].get(req.sede, 20.0),
            "alta_altitud": sd["alt"] >= modelo.ALTITUD_UMBRAL,
            "distancia_e1": d1,
            "distancia_e2": d2,
        }

    return {
        "equipo1":     req.equipo1,
        "equipo2":     req.equipo2,
        "elo1":        modelo.FIFA_ELO[req.equipo1],
        "elo2":        modelo.FIFA_ELO[req.equipo2],
        "fase":        req.fase,
        "sede":        sede_info,
        "ventaja_e1":  hb1,
        "ventaja_e2":  hb2,
        "goles":       goles,
        "metricas":    metricas,
    }

@app.get("/predecir-dia/{fecha}")
def predecir_dia(fecha: str):
    partidos = modelo.partidos_por_fecha(fecha)
    if not partidos:
        raise HTTPException(404, f"No hay partidos para {fecha}")

    resultados = []
    for p in partidos:
        t1, t2 = p["t1"], p["t2"]
        if t1 not in modelo.FIFA_ELO or t2 not in modelo.FIFA_ELO:
            resultados.append({**p, "error": f"Equipo no encontrado: {t1 if t1 not in modelo.FIFA_ELO else t2}"})
            continue
        goles    = modelo.predecir_goles(t1, t2, p["fase"], p["sede"])
        metricas = modelo.predecir_metricas(t1, t2, p["sede"])
        hb1, hb2 = modelo.ventaja_relativa(t1, t2, p["sede"])
        resultados.append({
            **p,
            "elo1":       modelo.FIFA_ELO[t1],
            "elo2":       modelo.FIFA_ELO[t2],
            "ventaja_e1": hb1,
            "ventaja_e2": hb2,
            "goles":      goles,
            "metricas":   metricas,
        })

    return {"fecha": fecha, "partidos": resultados}
