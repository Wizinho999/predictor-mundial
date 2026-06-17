"""
modelo.py — Nucleo del predictor del Mundial 2026
Contiene toda la logica del modelo: Elo, Poisson, Dixon-Coles,
Monte Carlo, xG, cuotas, metricas de apuestas y fixture.
"""

import numpy as np
import pandas as pd
import requests
import time
import json
import io
from math import radians, sin, cos, sqrt, atan2
from scipy.stats import poisson
from functools import lru_cache
from typing import Optional

# ── Constantes ────────────────────────────────────────────────────────────
BASE_GOALS    = 2.55
HOME_BONUS    = 1.08
MAX_GOALS     = 8
N_SIMS        = 20_000   # reducido para respuesta rapida en API
RHO           = -0.10    # Dixon-Coles, se calibra al iniciar
ALTITUD_UMBRAL= 1000
TEMP_REF      = 18.0

FASE_MULT = {
    'grupos': 1.00, 'octavos': 0.95, 'cuartos': 0.90,
    'semifinal': 0.88, 'final': 0.85,
}
PESO_CUOTAS_POR_FASE = {
    'grupos': 0.20, 'octavos': 0.28, 'cuartos': 0.33,
    'semifinal': 0.38, 'final': 0.42,
}

# ── Datos de selecciones ───────────────────────────────────────────────────
FIFA_ELO = {
    'France': 1877, 'Spain': 1876, 'Argentina': 1875, 'England': 1826,
    'Portugal': 1764, 'Brazil': 1761, 'Netherlands': 1758, 'Morocco': 1756,
    'Belgium': 1735, 'Germany': 1730, 'Croatia': 1717, 'Italy': 1700,
    'Colombia': 1693, 'Senegal': 1689, 'Mexico': 1681, 'United States': 1673,
    'Uruguay': 1673, 'Japan': 1660, 'Switzerland': 1649, 'Denmark': 1621,
    'Ecuador': 1580, 'Canada': 1560, 'Australia': 1572, 'Iran': 1558,
    'South Korea': 1550, 'Poland': 1548, 'Turkey': 1540, 'Sweden': 1518,
    'Scotland': 1512, 'Norway': 1535, 'Austria': 1520, 'Czech Republic': 1495,
    'Nigeria': 1515, 'Algeria': 1510, 'Chile': 1505, 'Ghana': 1498,
    "Cote d'Ivoire": 1490, 'Egypt': 1530, 'Tunisia': 1475, 'South Africa': 1472,
    'Paraguay': 1465, 'Panama': 1468, 'Bosnia and Herzegovina': 1480,
    'Uzbekistan': 1420, 'Cabo Verde': 1420, 'Saudi Arabia': 1415,
    'Iraq': 1410, 'Jordan': 1400, 'Qatar': 1390, 'DR Congo': 1395,
    'Haiti': 1320, 'Curacao': 1310, 'New Zealand': 1280,
}

COUNTRY_COORDS = {
    'France': (46.2, 2.2), 'Spain': (40.4, -3.7), 'Argentina': (-34.6, -58.4),
    'England': (51.5, -0.1), 'Portugal': (38.7, -9.1), 'Brazil': (-15.8, -47.9),
    'Netherlands': (52.4, 4.9), 'Morocco': (34.0, -6.8), 'Belgium': (50.8, 4.4),
    'Germany': (52.5, 13.4), 'Croatia': (45.8, 16.0), 'Italy': (41.9, 12.5),
    'Colombia': (4.7, -74.1), 'Senegal': (14.7, -17.4), 'Mexico': (19.4, -99.1),
    'United States': (38.9, -77.0), 'Uruguay': (-34.9, -56.2), 'Japan': (35.7, 139.7),
    'Switzerland': (46.9, 7.4), 'Denmark': (55.7, 12.6), 'Canada': (45.4, -75.7),
    'Ecuador': (-0.2, -78.5), 'Australia': (-35.3, 149.1), 'Iran': (35.7, 51.4),
    'South Korea': (37.6, 126.9), 'Poland': (52.2, 21.0), 'Turkey': (39.9, 32.9),
    'Norway': (59.9, 10.7), 'Austria': (48.2, 16.4), 'Nigeria': (9.1, 7.4),
    'Algeria': (36.7, 3.1), 'Chile': (-33.5, -70.7), 'Ghana': (5.6, -0.2),
    "Cote d'Ivoire": (5.4, -4.0), 'South Africa': (-25.7, 28.2),
    'Paraguay': (-25.3, -57.6), 'Scotland': (55.9, -3.2), 'Sweden': (59.3, 18.1),
    'Egypt': (30.1, 31.2), 'Tunisia': (36.8, 10.2), 'Panama': (8.9, -79.5),
    'Haiti': (18.5, -72.3), 'Curacao': (12.1, -68.9),
    'Bosnia and Herzegovina': (43.8, 18.4), 'Czech Republic': (50.1, 14.4),
    'Uzbekistan': (41.3, 69.2), 'Saudi Arabia': (24.7, 46.7), 'Iraq': (33.3, 44.4),
    'Jordan': (31.9, 35.9), 'Qatar': (25.3, 51.5), 'Cabo Verde': (14.9, -23.5),
    'DR Congo': (-4.3, 15.3), 'New Zealand': (-41.3, 174.8),
}

SEDES = {
    'Vancouver':               {'lat': 49.28, 'lon': -123.11, 'alt': 3,    'pais': 'CAN', 'estadio': 'BC Place'},
    'Seattle':                 {'lat': 47.60, 'lon': -122.33, 'alt': 6,    'pais': 'USA', 'estadio': 'Lumen Field'},
    'San Francisco/Bay Area':  {'lat': 37.40, 'lon': -121.97, 'alt': 6,    'pais': 'USA', 'estadio': "Levi's Stadium"},
    'Los Angeles':             {'lat': 33.95, 'lon': -118.34, 'alt': 86,   'pais': 'USA', 'estadio': 'SoFi Stadium'},
    'Guadalajara':             {'lat': 20.68, 'lon': -103.46, 'alt': 1566, 'pais': 'MEX', 'estadio': 'Estadio Akron'},
    'Ciudad de Mexico':        {'lat': 19.30, 'lon':  -99.15, 'alt': 2240, 'pais': 'MEX', 'estadio': 'Estadio Azteca'},
    'Monterrey':               {'lat': 25.67, 'lon': -100.31, 'alt': 538,  'pais': 'MEX', 'estadio': 'Estadio BBVA'},
    'Kansas City':             {'lat': 39.05, 'lon':  -94.48, 'alt': 274,  'pais': 'USA', 'estadio': 'Arrowhead Stadium'},
    'Dallas':                  {'lat': 32.75, 'lon':  -97.09, 'alt': 186,  'pais': 'USA', 'estadio': 'AT&T Stadium'},
    'Houston':                 {'lat': 29.68, 'lon':  -95.41, 'alt': 12,   'pais': 'USA', 'estadio': 'NRG Stadium'},
    'Atlanta':                 {'lat': 33.76, 'lon':  -84.40, 'alt': 315,  'pais': 'USA', 'estadio': 'Mercedes-Benz Stadium'},
    'Toronto':                 {'lat': 43.63, 'lon':  -79.42, 'alt': 76,   'pais': 'CAN', 'estadio': 'BMO Field'},
    'Boston':                  {'lat': 42.09, 'lon':  -71.26, 'alt': 5,    'pais': 'USA', 'estadio': 'Gillette Stadium'},
    'Nueva York/Nueva Jersey': {'lat': 40.81, 'lon':  -74.07, 'alt': 2,    'pais': 'USA', 'estadio': 'MetLife Stadium'},
    'Philadelphia':            {'lat': 39.90, 'lon':  -75.17, 'alt': 9,    'pais': 'USA', 'estadio': 'Lincoln Financial Field'},
    'Miami':                   {'lat': 25.96, 'lon':  -80.24, 'alt': 3,    'pais': 'USA', 'estadio': 'Hard Rock Stadium'},
}

GRUPOS = {
    'A': ['Mexico', 'South Korea', 'South Africa', 'Czech Republic'],
    'B': ['Canada', 'Switzerland', 'Qatar', 'Bosnia and Herzegovina'],
    'C': ['Brazil', 'Morocco', 'Scotland', 'Haiti'],
    'D': ['United States', 'Paraguay', 'Australia', 'Turkey'],
    'E': ['Germany', "Cote d'Ivoire", 'Ecuador', 'Curacao'],
    'F': ['Japan', 'Netherlands', 'Sweden', 'Tunisia'],
    'G': ['France', 'Egypt', 'New Zealand', 'Senegal'],
    'H': ['Spain', 'Cabo Verde', 'Saudi Arabia', 'Uruguay'],
    'I': ['Portugal', 'DR Congo', 'Uzbekistan', 'Colombia'],
    'J': ['Argentina', 'Jordan', 'Austria', 'Algeria'],
    'K': ['Belgium', 'Norway', 'Iran', 'Iraq'],
    'L': ['England', 'Croatia', 'Ghana', 'Panama'],
}

PAISES_ANFITRION = {'USA': 'United States', 'MEX': 'Mexico', 'CAN': 'Canada'}

REGIONES_FRIAS = {
    'France', 'England', 'Germany', 'Netherlands', 'Belgium', 'Denmark',
    'Norway', 'Switzerland', 'Poland', 'Austria', 'Croatia', 'Czech Republic',
    'Bosnia and Herzegovina', 'Canada', 'Kosovo', 'Scotland', 'Sweden',
}
REGIONES_CALIDAS = {
    'Senegal', 'Nigeria', 'Ghana', "Cote d'Ivoire", 'Algeria', 'Morocco',
    'South Africa', 'DR Congo', 'Cabo Verde', 'Brazil', 'Colombia',
    'Ecuador', 'Paraguay', 'Saudi Arabia', 'Iraq', 'Jordan', 'Qatar',
    'Panama', 'Haiti', 'Curacao', 'Egypt', 'Tunisia',
}

BETTING_STATS = {
    'France':       {'corn_f':5.8,'corn_c':4.2,'shots_f':14.5,'sot_f':5.8,'fouls_f':11.2,'yc_f':1.4,'offsides_f':2.1},
    'Spain':        {'corn_f':6.2,'corn_c':3.8,'shots_f':15.8,'sot_f':6.2,'fouls_f': 9.8,'yc_f':1.3,'offsides_f':1.8},
    'Argentina':    {'corn_f':5.5,'corn_c':4.5,'shots_f':13.8,'sot_f':5.2,'fouls_f':12.4,'yc_f':1.8,'offsides_f':2.4},
    'England':      {'corn_f':5.9,'corn_c':4.1,'shots_f':14.2,'sot_f':5.5,'fouls_f':10.5,'yc_f':1.5,'offsides_f':2.0},
    'Portugal':     {'corn_f':5.7,'corn_c':4.3,'shots_f':14.8,'sot_f':5.9,'fouls_f':11.0,'yc_f':1.6,'offsides_f':2.2},
    'Brazil':       {'corn_f':5.6,'corn_c':4.4,'shots_f':14.0,'sot_f':5.4,'fouls_f':12.8,'yc_f':1.7,'offsides_f':2.5},
    'Netherlands':  {'corn_f':5.4,'corn_c':4.6,'shots_f':13.5,'sot_f':5.0,'fouls_f':11.5,'yc_f':1.5,'offsides_f':1.9},
    'Morocco':      {'corn_f':4.8,'corn_c':5.2,'shots_f':11.0,'sot_f':3.8,'fouls_f':14.2,'yc_f':2.2,'offsides_f':1.5},
    'Belgium':      {'corn_f':5.3,'corn_c':4.7,'shots_f':13.2,'sot_f':4.8,'fouls_f':11.8,'yc_f':1.6,'offsides_f':2.0},
    'Germany':      {'corn_f':5.5,'corn_c':4.5,'shots_f':14.0,'sot_f':5.3,'fouls_f':10.8,'yc_f':1.4,'offsides_f':2.1},
    'Croatia':      {'corn_f':4.9,'corn_c':5.1,'shots_f':11.5,'sot_f':4.0,'fouls_f':13.5,'yc_f':2.0,'offsides_f':1.6},
    'Italy':        {'corn_f':5.2,'corn_c':4.8,'shots_f':12.8,'sot_f':4.5,'fouls_f':12.0,'yc_f':1.8,'offsides_f':1.7},
    'Colombia':     {'corn_f':5.1,'corn_c':4.9,'shots_f':12.5,'sot_f':4.5,'fouls_f':13.0,'yc_f':1.9,'offsides_f':2.2},
    'Senegal':      {'corn_f':4.6,'corn_c':5.4,'shots_f':10.8,'sot_f':3.5,'fouls_f':14.5,'yc_f':2.3,'offsides_f':1.4},
    'Mexico':       {'corn_f':5.0,'corn_c':5.0,'shots_f':12.0,'sot_f':4.2,'fouls_f':13.2,'yc_f':2.0,'offsides_f':1.8},
    'United States':{'corn_f':5.2,'corn_c':4.8,'shots_f':12.2,'sot_f':4.4,'fouls_f':12.5,'yc_f':1.7,'offsides_f':1.6},
    'Uruguay':      {'corn_f':4.8,'corn_c':5.2,'shots_f':11.5,'sot_f':4.0,'fouls_f':14.0,'yc_f':2.1,'offsides_f':1.9},
    'Japan':        {'corn_f':5.0,'corn_c':5.0,'shots_f':12.5,'sot_f':4.3,'fouls_f':11.0,'yc_f':1.4,'offsides_f':1.7},
    'Switzerland':  {'corn_f':4.9,'corn_c':5.1,'shots_f':11.8,'sot_f':4.1,'fouls_f':12.0,'yc_f':1.6,'offsides_f':1.8},
    'Denmark':      {'corn_f':5.1,'corn_c':4.9,'shots_f':12.0,'sot_f':4.3,'fouls_f':11.5,'yc_f':1.5,'offsides_f':1.7},
    'Canada':       {'corn_f':4.8,'corn_c':5.2,'shots_f':11.2,'sot_f':3.8,'fouls_f':12.8,'yc_f':1.7,'offsides_f':1.5},
    'Ecuador':      {'corn_f':4.5,'corn_c':5.5,'shots_f':10.5,'sot_f':3.5,'fouls_f':13.5,'yc_f':2.0,'offsides_f':1.6},
    'Australia':    {'corn_f':4.6,'corn_c':5.4,'shots_f':10.8,'sot_f':3.6,'fouls_f':12.5,'yc_f':1.7,'offsides_f':1.5},
    'Iran':         {'corn_f':4.4,'corn_c':5.6,'shots_f':10.2,'sot_f':3.3,'fouls_f':14.8,'yc_f':2.4,'offsides_f':1.3},
    'South Korea':  {'corn_f':5.0,'corn_c':5.0,'shots_f':11.5,'sot_f':4.0,'fouls_f':12.0,'yc_f':1.6,'offsides_f':1.8},
    'Poland':       {'corn_f':4.7,'corn_c':5.3,'shots_f':11.0,'sot_f':3.8,'fouls_f':13.0,'yc_f':1.9,'offsides_f':1.5},
    'Turkey':       {'corn_f':4.8,'corn_c':5.2,'shots_f':11.2,'sot_f':3.9,'fouls_f':13.5,'yc_f':2.1,'offsides_f':1.6},
    'Norway':       {'corn_f':4.9,'corn_c':5.1,'shots_f':12.0,'sot_f':4.2,'fouls_f':11.8,'yc_f':1.5,'offsides_f':2.0},
    'Austria':      {'corn_f':4.8,'corn_c':5.2,'shots_f':11.5,'sot_f':4.0,'fouls_f':12.2,'yc_f':1.7,'offsides_f':1.7},
    'Scotland':     {'corn_f':4.7,'corn_c':5.3,'shots_f':11.2,'sot_f':3.8,'fouls_f':12.8,'yc_f':1.7,'offsides_f':1.6},
    'Sweden':       {'corn_f':4.8,'corn_c':5.2,'shots_f':11.5,'sot_f':4.0,'fouls_f':12.0,'yc_f':1.6,'offsides_f':1.8},
    'Algeria':      {'corn_f':4.6,'corn_c':5.4,'shots_f':10.8,'sot_f':3.6,'fouls_f':13.8,'yc_f':2.1,'offsides_f':1.4},
    'Chile':        {'corn_f':4.7,'corn_c':5.3,'shots_f':11.0,'sot_f':3.8,'fouls_f':13.5,'yc_f':2.0,'offsides_f':1.7},
    'Ghana':        {'corn_f':4.3,'corn_c':5.7,'shots_f':10.0,'sot_f':3.2,'fouls_f':14.2,'yc_f':2.2,'offsides_f':1.3},
    "Cote d'Ivoire":{'corn_f':4.5,'corn_c':5.5,'shots_f':10.5,'sot_f':3.4,'fouls_f':14.0,'yc_f':2.1,'offsides_f':1.4},
    'Egypt':        {'corn_f':4.5,'corn_c':5.5,'shots_f':10.5,'sot_f':3.5,'fouls_f':13.8,'yc_f':2.0,'offsides_f':1.5},
    'Tunisia':      {'corn_f':4.4,'corn_c':5.6,'shots_f':10.2,'sot_f':3.3,'fouls_f':14.5,'yc_f':2.2,'offsides_f':1.3},
    'South Africa': {'corn_f':4.2,'corn_c':5.8,'shots_f': 9.8,'sot_f':3.1,'fouls_f':14.5,'yc_f':2.3,'offsides_f':1.2},
    'Paraguay':     {'corn_f':4.4,'corn_c':5.6,'shots_f':10.2,'sot_f':3.3,'fouls_f':14.2,'yc_f':2.2,'offsides_f':1.5},
    'Panama':       {'corn_f':4.2,'corn_c':5.8,'shots_f': 9.8,'sot_f':3.2,'fouls_f':14.8,'yc_f':2.3,'offsides_f':1.3},
    'Haiti':        {'corn_f':3.8,'corn_c':6.2,'shots_f': 8.5,'sot_f':2.6,'fouls_f':15.5,'yc_f':2.6,'offsides_f':1.0},
    'Curacao':      {'corn_f':4.0,'corn_c':6.0,'shots_f': 9.0,'sot_f':2.8,'fouls_f':15.0,'yc_f':2.5,'offsides_f':1.1},
    'Bosnia and Herzegovina': {'corn_f':4.6,'corn_c':5.4,'shots_f':10.8,'sot_f':3.6,'fouls_f':13.2,'yc_f':2.0,'offsides_f':1.5},
    'Czech Republic':{'corn_f':4.8,'corn_c':5.2,'shots_f':11.2,'sot_f':3.9,'fouls_f':12.5,'yc_f':1.8,'offsides_f':1.6},
    'Uzbekistan':   {'corn_f':4.0,'corn_c':6.0,'shots_f': 9.0,'sot_f':2.8,'fouls_f':15.0,'yc_f':2.5,'offsides_f':1.2},
    'Saudi Arabia': {'corn_f':4.2,'corn_c':5.8,'shots_f': 9.5,'sot_f':3.0,'fouls_f':14.8,'yc_f':2.4,'offsides_f':1.3},
    'Iraq':         {'corn_f':4.1,'corn_c':5.9,'shots_f': 9.2,'sot_f':2.9,'fouls_f':15.2,'yc_f':2.5,'offsides_f':1.2},
    'Jordan':       {'corn_f':4.0,'corn_c':6.0,'shots_f': 9.0,'sot_f':2.8,'fouls_f':15.0,'yc_f':2.5,'offsides_f':1.1},
    'Qatar':        {'corn_f':4.2,'corn_c':5.8,'shots_f': 9.5,'sot_f':3.0,'fouls_f':14.5,'yc_f':2.3,'offsides_f':1.3},
    'Cabo Verde':   {'corn_f':4.0,'corn_c':6.0,'shots_f': 8.8,'sot_f':2.7,'fouls_f':15.5,'yc_f':2.6,'offsides_f':1.1},
    'DR Congo':     {'corn_f':4.1,'corn_c':5.9,'shots_f': 9.2,'sot_f':2.9,'fouls_f':15.0,'yc_f':2.4,'offsides_f':1.2},
    'New Zealand':  {'corn_f':3.8,'corn_c':6.2,'shots_f': 8.2,'sot_f':2.5,'fouls_f':16.0,'yc_f':2.8,'offsides_f':1.0},
}

_avg_bs = {
    k: round(sum(v[k] for v in BETTING_STATS.values()) / len(BETTING_STATS), 2)
    for k in ['corn_f', 'corn_c', 'shots_f', 'sot_f', 'fouls_f', 'yc_f', 'offsides_f']
}

FIXTURE_URL = 'https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json'

NOMBRE_MAP = {
    'Mexico': 'Mexico', 'South Africa': 'South Africa', 'South Korea': 'South Korea',
    'Czech Republic': 'Czech Republic', 'Czechia': 'Czech Republic',
    'Canada': 'Canada', 'Switzerland': 'Switzerland', 'Qatar': 'Qatar',
    'Bosnia and Herzegovina': 'Bosnia and Herzegovina', 'Uruguay': 'Uruguay',
    'Senegal': 'Senegal', 'Norway': 'Norway', 'DR Congo': 'DR Congo',
    'USA': 'United States', 'United States': 'United States',
    'Paraguay': 'Paraguay', 'Australia': 'Australia', 'Turkey': 'Turkey',
    'Germany': 'Germany', 'Ecuador': 'Ecuador', 'Curacao': 'Curacao',
    "Côte d'Ivoire": "Cote d'Ivoire", "Cote d'Ivoire": "Cote d'Ivoire",
    'Brazil': 'Brazil', 'England': 'England', 'Algeria': 'Algeria',
    'Iraq': 'Iraq', 'Netherlands': 'Netherlands', 'Sweden': 'Sweden',
    'Tunisia': 'Tunisia', 'France': 'France', 'Egypt': 'Egypt',
    'New Zealand': 'New Zealand', 'Spain': 'Spain', 'Cabo Verde': 'Cabo Verde',
    'Cape Verde': 'Cabo Verde', 'Saudi Arabia': 'Saudi Arabia',
    'Portugal': 'Portugal', 'Uzbekistan': 'Uzbekistan', 'Colombia': 'Colombia',
    'Argentina': 'Argentina', 'Jordan': 'Jordan', 'Austria': 'Austria',
    'Belgium': 'Belgium', 'Iran': 'Iran', 'IR Iran': 'Iran',
    'Croatia': 'Croatia', 'Ghana': 'Ghana', 'Panama': 'Panama',
    'Japan': 'Japan', 'Scotland': 'Scotland', 'Haiti': 'Haiti',
    'Morocco': 'Morocco', 'Korea Republic': 'South Korea',
}

CIUDAD_SEDE_MAP = {
    'Mexico City': 'Ciudad de Mexico', 'Guadalajara': 'Guadalajara',
    'Guadalajara (Zapopan)': 'Guadalajara', 'Monterrey': 'Monterrey',
    'Vancouver': 'Vancouver', 'Toronto': 'Toronto', 'Seattle': 'Seattle',
    'San Francisco': 'San Francisco/Bay Area',
    'San Francisco Bay Area': 'San Francisco/Bay Area',
    'Los Angeles': 'Los Angeles', 'Kansas City': 'Kansas City',
    'Dallas': 'Dallas', 'Houston': 'Houston', 'Atlanta': 'Atlanta',
    'Miami': 'Miami', 'Boston': 'Boston', 'New York': 'Nueva York/Nueva Jersey',
    'New York City': 'Nueva York/Nueva Jersey',
    'New York/New Jersey': 'Nueva York/Nueva Jersey',
    'East Rutherford': 'Nueva York/Nueva Jersey', 'Philadelphia': 'Philadelphia',
}

RONDA_FASE_MAP = {
    'Matchday': 'grupos', 'Round of 32': 'octavos', 'Round of 16': 'octavos',
    'Quarter-final': 'cuartos', 'Semi-final': 'semifinal',
    'Final': 'final', 'Third place': 'semifinal',
}

# ── Estado global (se inicializa una vez al arrancar) ─────────────────────
_estado = {
    'team_stats': {},
    'xg_data': {},
    'temp_sede': {},
    'fixture': [],
    'rho': -0.10,
    'inicializado': False,
}

# ── Funciones geograficas ──────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(d_lon/2)**2
    return round(2 * R * atan2(sqrt(a), sqrt(1-a)), 0)

def factor_distancia(team, sede_nombre):
    coords = COUNTRY_COORDS.get(team)
    sede   = SEDES.get(sede_nombre)
    if not coords or not sede:
        return 0.0, 0
    dist   = haversine(coords[0], coords[1], sede['lat'], sede['lon'])
    factor = 0.0 if dist < 9000 else 0.03 if dist < 13000 else 0.06
    return factor, int(dist)

def penalizacion_altitud(alt_sede, team, pais_sede):
    if alt_sede < ALTITUD_UMBRAL:
        return 0.0
    coords = COUNTRY_COORDS.get(team, (0, 0))
    if pais_sede == 'MEX' and team == 'Mexico':
        return 0.0
    if pais_sede == 'USA' and team == 'United States':
        return 0.0
    if pais_sede == 'CAN' and team == 'Canada':
        return 0.0
    return round(min(0.35, (alt_sede - ALTITUD_UMBRAL) / 500 * 0.07), 4)

def factor_temperatura(temp_sede, equipo):
    delta = temp_sede - TEMP_REF
    if equipo in REGIONES_FRIAS   and delta >  5:
        return round(min(0.12, delta * 0.012), 4)
    if equipo in REGIONES_CALIDAS and delta < -5:
        return round(min(0.08, abs(delta) * 0.008), 4)
    return 0.0

def ventaja_relativa(t1, t2, sede_nombre):
    if not sede_nombre or sede_nombre not in SEDES:
        return 1.0, 1.0
    pais_sede = SEDES[sede_nombre]['pais']
    anfitrion = PAISES_ANFITRION.get(pais_sede)
    if t1 == anfitrion:
        return HOME_BONUS, 1.0
    if t2 == anfitrion:
        return 1.0, HOME_BONUS
    _, dist1 = factor_distancia(t1, sede_nombre)
    _, dist2 = factor_distancia(t2, sede_nombre)
    total    = dist1 + dist2
    if total == 0:
        return 1.0, 1.0
    prop   = (dist2 - dist1) / total
    bonus1 = 1.0 + max(0,  prop) * (HOME_BONUS - 1.0)
    bonus2 = 1.0 + max(0, -prop) * (HOME_BONUS - 1.0)
    return round(bonus1, 4), round(bonus2, 4)

# ── Temperatura de sede ────────────────────────────────────────────────────
def obtener_temperatura_junio(lat, lon):
    url = (
        f'https://archive-api.open-meteo.com/v1/archive'
        f'?latitude={lat}&longitude={lon}'
        f'&start_date=2023-06-01&end_date=2023-06-30'
        f'&daily=temperature_2m_mean&timezone=auto'
    )
    try:
        r    = requests.get(url, timeout=10)
        data = r.json()
        vals = [t for t in data.get('daily', {}).get('temperature_2m_mean', []) if t]
        return round(sum(vals) / len(vals), 1) if vals else 20.0
    except Exception:
        return 20.0

# ── Dixon-Coles ────────────────────────────────────────────────────────────
def dixon_coles_tau(g1, g2, l1, l2, rho):
    if g1 == 0 and g2 == 0: return max(1e-6, 1 - l1 * l2 * rho)
    if g1 == 1 and g2 == 0: return max(1e-6, 1 + l2 * rho)
    if g1 == 0 and g2 == 1: return max(1e-6, 1 + l1 * rho)
    if g1 == 1 and g2 == 1: return max(1e-6, 1 - rho)
    return 1.0

def poisson_dixon_coles(l1, l2, max_g=MAX_GOALS, rho=None):
    rho   = rho if rho is not None else _estado['rho']
    res   = {}
    total = 0.0
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            p = poisson.pmf(i, l1) * poisson.pmf(j, l2) * dixon_coles_tau(i, j, l1, l2, rho)
            res[(i, j)] = p
            total += p
    return {k: v / total for k, v in res.items()}

def monte_carlo_dc(l1, l2, n=N_SIMS):
    rho = _estado['rho']
    np.random.seed(42)
    g1r = np.random.poisson(l1, n)
    g2r = np.random.poisson(l2, n)
    res = {}
    for a, b in zip(g1r, g2r):
        tau = dixon_coles_tau(a, b, l1, l2, rho)
        if np.random.random() < tau:
            res[(a, b)] = res.get((a, b), 0) + 1
    total = sum(res.values())
    return {k: v / total for k, v in res.items()} if total else {(0, 0): 1.0}

# ── Lambdas ────────────────────────────────────────────────────────────────
def get_lambdas(t1, t2, fase='grupos', sede=None, descanso_diff=0):
    elo1, elo2 = FIFA_ELO.get(t1, 1400), FIFA_ELO.get(t2, 1400)
    ef         = 10 ** ((elo1 - elo2) / 400)
    p1, p2     = ef / (1 + ef), 1 / (1 + ef)

    a1 = _estado['team_stats'].get(t1, {}).get('att_norm', 1.0)
    d1 = _estado['team_stats'].get(t1, {}).get('def_norm', 1.0)
    a2 = _estado['team_stats'].get(t2, {}).get('att_norm', 1.0)
    d2 = _estado['team_stats'].get(t2, {}).get('def_norm', 1.0)

    fm       = FASE_MULT.get(fase, 1.0)
    hb1, hb2 = ventaja_relativa(t1, t2, sede)

    l1 = (0.6 * BASE_GOALS * p1 * 2 * hb1 + 0.4 * BASE_GOALS * a1 / max(d2, 0.1) * hb1) * fm
    l2 = (0.6 * BASE_GOALS * p2 * 2 * hb2 + 0.4 * BASE_GOALS * a2 / max(d1, 0.1) * hb2) * fm

    xg = _estado['xg_data']
    if xg and t1 in xg and t2 in xg:
        l1_xg = (xg[t1]['xg'] / max(xg[t2]['xga'], 0.5)) * BASE_GOALS * hb1 * fm
        l2_xg = (xg[t2]['xg'] / max(xg[t1]['xga'], 0.5)) * BASE_GOALS * hb2 * fm
        l1 = 0.70 * l1 + 0.30 * l1_xg
        l2 = 0.70 * l2 + 0.30 * l2_xg

    if sede and sede in SEDES:
        sd   = SEDES[sede]
        temp = _estado['temp_sede'].get(sede, 20.0)
        l1  *= (1 - penalizacion_altitud(sd['alt'], t1, sd['pais']))
        l2  *= (1 - penalizacion_altitud(sd['alt'], t2, sd['pais']))
        l1  *= (1 - factor_temperatura(temp, t1))
        l2  *= (1 - factor_temperatura(temp, t2))
        f1, _ = factor_distancia(t1, sede)
        f2, _ = factor_distancia(t2, sede)
        l1  *= (1 - f1)
        l2  *= (1 - f2)

    if descanso_diff:
        v   = float(np.clip(descanso_diff * 0.015, -0.06, 0.06))
        l1 *= (1 + v)
        l2 *= (1 - v)

    return round(float(np.clip(l1, 0.25, 5.0)), 3), round(float(np.clip(l2, 0.25, 5.0)), 3)

# ── Prediccion de goles ────────────────────────────────────────────────────
def predecir_goles(t1, t2, fase='grupos', sede=None, descanso_diff=0):
    l1, l2  = get_lambdas(t1, t2, fase, sede, descanso_diff)
    dist_dc = poisson_dixon_coles(l1, l2)
    dist_mc = monte_carlo_dc(l1, l2)

    xg = _estado['xg_data']
    if xg and t1 in xg and t2 in xg:
        fm       = FASE_MULT.get(fase, 1.0)
        hb1, hb2 = ventaja_relativa(t1, t2, sede)
        l1_xg = float(np.clip((xg[t1]['xg'] / max(xg[t2]['xga'], 0.5)) * BASE_GOALS * hb1 * fm, 0.25, 5.0))
        l2_xg = float(np.clip((xg[t2]['xg'] / max(xg[t1]['xga'], 0.5)) * BASE_GOALS * hb2 * fm, 0.25, 5.0))
        dist_xg = poisson_dixon_coles(l1_xg, l2_xg)
    else:
        dist_xg = dist_dc

    scores = set(dist_dc) | set(dist_mc) | set(dist_xg)
    dist   = {s: 0.50 * dist_dc.get(s, 0) + 0.30 * dist_mc.get(s, 0) + 0.20 * dist_xg.get(s, 0) for s in scores}
    total  = sum(dist.values())
    dist   = {k: v / total for k, v in dist.items()}

    pw1 = sum(p for (g1, g2), p in dist.items() if g1 > g2)
    pd  = sum(p for (g1, g2), p in dist.items() if g1 == g2)
    pw2 = sum(p for (g1, g2), p in dist.items() if g1 < g2)

    top = sorted(dist.items(), key=lambda x: -x[1])[:10]

    return {
        'l1': l1, 'l2': l2,
        'pw1': round(pw1, 4), 'pd': round(pd, 4), 'pw2': round(pw2, 4),
        'top_resultados': [
            {'goles1': g1, 'goles2': g2, 'prob': round(p * 100, 2)}
            for (g1, g2), p in top
        ],
    }

# ── Metricas de apuestas ───────────────────────────────────────────────────
def predecir_metricas(t1, t2, sede=None):
    s1 = BETTING_STATS.get(t1, _avg_bs)
    s2 = BETTING_STATS.get(t2, _avg_bs)

    elo1, elo2 = FIFA_ELO.get(t1, 1400), FIFA_ELO.get(t2, 1400)
    adj        = float(np.clip((elo1 - elo2) / 400 * 0.08, -0.20, 0.20))

    alt1 = alt2 = 0.0
    if sede and sede in SEDES:
        sd   = SEDES[sede]
        alt1 = penalizacion_altitud(sd['alt'], t1, sd['pais'])
        alt2 = penalizacion_altitud(sd['alt'], t2, sd['pais'])

    def calc(kf, kc, sign=1):
        v1 = ((s1.get(kf, 5.0) + s2.get(kc, 5.0)) / 2) * (1 + sign * adj) * (1 - alt1)
        v2 = ((s2.get(kf, 5.0) + s1.get(kc, 5.0)) / 2) * (1 - sign * adj) * (1 - alt2)
        return round(v1, 2), round(v2, 2), round(v1 + v2, 2)

    c1,  c2,  ct  = calc('corn_f',    'corn_c',  sign=1)
    sh1, sh2, sht = calc('shots_f',   'shots_f', sign=1)
    so1, so2, sot = calc('sot_f',     'sot_f',   sign=1)
    f1_,f2_,ft    = calc('fouls_f',   'fouls_f', sign=-1)
    f1_ = round(f1_ * (1 + alt1 * 0.5), 2)
    f2_ = round(f2_ * (1 + alt2 * 0.5), 2)

    yc1 = round(s1.get('yc_f', 1.8) * (1 - adj * 0.5) * (1 + alt1 * 0.3), 2)
    yc2 = round(s2.get('yc_f', 1.8) * (1 + adj * 0.5) * (1 + alt2 * 0.3), 2)
    oj1 = round(s1.get('offsides_f', 1.7) * (1 + adj * 0.3), 2)
    oj2 = round(s2.get('offsides_f', 1.7) * (1 - adj * 0.3), 2)

    return {
        'corners':        {t1: c1,   t2: c2,   'total': ct,              'ou': round(ct, 1)},
        'tiros':          {t1: sh1,  t2: sh2,  'total': sht,             'ou': round(sht, 1)},
        'tiros_al_arco':  {t1: so1,  t2: so2,  'total': sot,             'ou': round(sot, 1)},
        'faltas':         {t1: f1_,  t2: f2_,  'total': round(f1_+f2_,2),'ou': round(f1_+f2_, 1)},
        'amarillas':      {t1: yc1,  t2: yc2,  'total': round(yc1+yc2,2),'ou': round(yc1+yc2, 1)},
        'fuera_de_juego': {t1: oj1,  t2: oj2,  'total': round(oj1+oj2,2),'ou': round(oj1+oj2, 1)},
    }

# ── Fixture ────────────────────────────────────────────────────────────────
def cargar_fixture():
    try:
        r   = requests.get(FIXTURE_URL, timeout=15)
        return r.json().get('matches', [])
    except Exception:
        return []

def partidos_por_fecha(fecha_str):
    fixture = _estado['fixture']
    result  = []
    for p in fixture:
        if p.get('date') != fecha_str:
            continue
        t1 = NOMBRE_MAP.get(p.get('team1', ''), p.get('team1', ''))
        t2 = NOMBRE_MAP.get(p.get('team2', ''), p.get('team2', ''))
        fase_raw = p.get('round', '')
        fase = 'grupos'
        for key, val in RONDA_FASE_MAP.items():
            if key.lower() in fase_raw.lower():
                fase = val
                break
        sede = CIUDAD_SEDE_MAP.get(p.get('ground', ''))
        score = p.get('score')
        result.append({
            't1': t1, 't2': t2,
            'fase': fase, 'sede': sede,
            'grupo': p.get('group', ''),
            'ciudad': p.get('ground', ''),
            'hora': p.get('time', ''),
            'jugado': score is not None,
            'resultado': score,
        })
    return result

def fechas_disponibles():
    return sorted(set(p['date'] for p in _estado['fixture']))

# ── Inicializacion ─────────────────────────────────────────────────────────
def inicializar():
    """
    Carga todos los datos externos una sola vez al arrancar la API.
    Descarga historial, calcula stats, xG y temperaturas.
    """
    if _estado['inicializado']:
        return

    print("Inicializando modelo...")

    # Historial de partidos
    try:
        URL  = 'https://raw.githubusercontent.com/martj42/international_results/master/results.csv'
        resp = requests.get(URL, timeout=30)
        df   = pd.read_csv(io.StringIO(resp.text))
        df['date'] = pd.to_datetime(df['date'])
        df   = df[df['date'] >= '2010-01-01'].copy()

        TW = {
            'FIFA World Cup': 3.0, 'UEFA Euro': 2.5, 'Copa America': 2.5,
            'African Cup of Nations': 2.5, 'AFC Asian Cup': 2.5,
            'CONCACAF Gold Cup': 2.0, 'UEFA Nations League': 2.0,
            'FIFA World Cup qualification': 2.0, 'Friendly': 0.5,
        }
        def gw(t):
            for k, w in TW.items():
                if k.lower() in str(t).lower(): return w
            return 1.0

        df['weight']       = df['tournament'].apply(gw)
        max_date           = df['date'].max()
        df['time_weight']  = np.exp(-(max_date - df['date']).dt.days / 1200)
        df['total_weight'] = df['weight'] * df['time_weight']

        stats = {}
        for team in FIFA_ELO:
            home = df[df['home_team'] == team].tail(30)
            away = df[df['away_team'] == team].tail(30)
            gf   = (home['home_score'] * home['total_weight']).sum() + \
                   (away['away_score'] * away['total_weight']).sum()
            gc   = (home['away_score'] * home['total_weight']).sum() + \
                   (away['home_score'] * away['total_weight']).sum()
            w    = home['total_weight'].sum() + away['total_weight'].sum()
            if w > 0.1 and len(home) + len(away) >= 3:
                stats[team] = {'att': gf/w, 'def': gc/w}
            else:
                stats[team] = {'att': 1.2, 'def': 1.2}

        avg_att = np.mean([v['att'] for v in stats.values()])
        avg_def = np.mean([v['def'] for v in stats.values()])
        for t in stats:
            stats[t]['att_norm'] = stats[t]['att'] / avg_att
            stats[t]['def_norm'] = stats[t]['def'] / avg_def

        _estado['team_stats'] = stats

        # Calibrar rho
        df_cal = df[df['weight'] >= 1.0].tail(3000)
        l_med  = df_cal['home_score'].mean()
        rho_vals = np.linspace(-0.20, 0.0, 21)
        ll_vals  = []
        for rho in rho_vals:
            ll = 0.0
            for _, row in df_cal.iterrows():
                g1 = int(row['home_score']); g2 = int(row['away_score'])
                pp = poisson.pmf(g1, l_med) * poisson.pmf(g2, l_med)
                if pp <= 0: continue
                tau = dixon_coles_tau(g1, g2, l_med, l_med, rho)
                ll -= np.log(max(1e-10, pp * tau))
            ll_vals.append(ll)
        _estado['rho'] = round(float(rho_vals[np.argmin(ll_vals)]), 4)
        print(f"  Rho calibrado: {_estado['rho']}")

    except Exception as e:
        print(f"  Error cargando historial: {e}")

    # Temperaturas de sedes
    print("  Cargando temperaturas...")
    for nombre, datos in SEDES.items():
        _estado['temp_sede'][nombre] = obtener_temperatura_junio(datos['lat'], datos['lon'])
        time.sleep(0.5)

    # Fixture
    print("  Cargando fixture...")
    _estado['fixture'] = cargar_fixture()

    _estado['inicializado'] = True
    print("Modelo listo.")
