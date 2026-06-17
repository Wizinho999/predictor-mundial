# Predictor Mundial 2026

Modelo predictivo de partidos del Mundial 2026.
Elo FIFA + Poisson bivariado + Dixon-Coles + Monte Carlo + xG StatsBomb/Understat.

## Stack

- **Backend:** FastAPI (Python) — desplegado en Render
- **Frontend:** React + Tailwind — desplegado en Vercel

---

## Desarrollo local

### Opcion A: Docker (recomendado, un solo comando)

```bash
docker-compose up --build
```

Frontend: http://localhost:5173
Backend:  http://localhost:8000/docs

### Opcion B: Manual

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Deploy en produccion

### 1. Subir a GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/predictor-mundial
git push -u origin main
```

### 2. Backend en Render

1. Ir a https://render.com y crear cuenta
2. New → Web Service → conectar tu repositorio
3. Configurar:
   - **Root directory:** `backend`
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Copiar la URL que te da Render (ej: https://predictor-mundial.onrender.com)

### 3. Frontend en Vercel

1. Ir a https://vercel.com y crear cuenta
2. New Project → importar tu repositorio
3. Configurar:
   - **Root directory:** `frontend`
   - **Framework preset:** Vite
4. Agregar variable de entorno:
   - `VITE_API_URL` = URL de tu backend en Render
5. Deploy

---

## Estructura del proyecto

```
predictor-mundial/
├── backend/
│   ├── main.py          # FastAPI: endpoints
│   ├── modelo.py        # Logica del modelo
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/
│   │       ├── SelectorPartido.jsx
│   │       ├── ResultadoPrediccion.jsx
│   │       └── PartidosDelDia.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── README.md
```

## Endpoints del backend

| Metodo | Ruta                  | Descripcion                          |
|--------|-----------------------|--------------------------------------|
| GET    | /equipos              | Lista los 52 equipos con Elo         |
| GET    | /sedes                | Las 16 sedes oficiales               |
| GET    | /grupos               | Grupos A-L del Mundial               |
| GET    | /fixture/fechas       | Fechas con partidos disponibles      |
| GET    | /fixture/{fecha}      | Partidos de una fecha (sin predecir) |
| POST   | /predecir             | Prediccion completa de un partido    |
| GET    | /predecir-dia/{fecha} | Predice todos los partidos del dia   |
