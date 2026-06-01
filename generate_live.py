#!/usr/bin/env python3
"""
MasterProps.ai — LIVE Ticket Generator v5
Fetches real odds from DBbet Marketing API, cross-references with sharp
bookmaker odds (The Odds API) and team stats (API-Football) to build
fewer, higher-quality tickets with verified edge.
"""

import random
import math
import re
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone
from pathlib import Path

# Market intelligence (sharp odds + team stats)
try:
    from market_intelligence import MarketIntel, odds_api_market_from_dbbet
    HAS_INTEL = True
except ImportError:
    HAS_INTEL = False
    print("⚠️  market_intelligence.py not found — running without sharp odds/stats")

BASE_DIR = Path(__file__).parent
TEMPLATE_FILE = BASE_DIR / 'template.html'
OUTPUT_FILE = BASE_DIR / 'index.html'
COUPONS_FILE = BASE_DIR / 'coupons.json'

# ── DBbet API Config ──
TOKEN_URL = "https://cpservm.com/gateway/token"
API_BASE = "https://cpservm.com/gateway/marketing/datafeed/prematch/api/v2"
CLIENT_ID = "partners-3151f4df3df18d1d17e3eae7a6c43792"
CLIENT_SECRET = "LDnyHnPGpVdar!gId431qn&YQRAZg!D5A1R010T5rk0F3ciWT1CHreULFN2Ly3Ck"
REF = "164"
PARTNER_LINK = "refpa1800.com"
LOGO_BASE = "https://nimblecd.com/sfiles/logo_teams/"

# ── Sport config ──
SPORT_MAP = {1: 'futbol', 2: 'hockey', 3: 'nba', 4: 'tenis', 5: 'mlb', 189: 'ufc'}
SPORT_NAMES = {
    'futbol': 'Fútbol', 'hockey': 'NHL', 'nba': 'NBA',
    'tenis': 'Tenis', 'mlb': 'MLB', 'ufc': 'UFC'
}

# ── Team abbreviations ──
TEAM_ABBREVS = {
    'Real Madrid': 'RMA', 'Barcelona': 'BAR', 'Atletico Madrid': 'ATM',
    'Manchester City': 'MCI', 'Manchester United': 'MUN', 'Liverpool': 'LIV',
    'Arsenal': 'ARS', 'Chelsea': 'CHE', 'Tottenham': 'TOT', 'Everton': 'EVE',
    'Bayern': 'BAY', 'Dortmund': 'BVB', 'Juventus': 'JUV',
    'Internazionale': 'INT', 'AC Milan': 'MIL', 'Paris': 'PSG',
    'Fiorentina': 'FIO', 'Atalanta': 'ATA', 'Roma': 'ROM',
    'Napoli': 'NAP', 'Lazio': 'LAZ', 'Bologna': 'BOL',
    'Colorado Avalanche': 'COL', 'Vegas Golden Knights': 'VGK',
    'Germany': 'GER', 'Brazil': 'BRA', 'Spain': 'ESP', 'France': 'FRA',
    'Argentina': 'ARG', 'England': 'ENG', 'Italy': 'ITA', 'Portugal': 'POR',
    'Crystal Palace': 'CRY', 'Brighton': 'BHA', 'Wolverhampton': 'WOL',
    'Burnley': 'BUR', 'Sunderland': 'SUN', 'Brentford': 'BRE',
    'Aston Villa': 'AVL', 'West Ham': 'WHU', 'Newcastle': 'NEW',
    # Sudamérica
    'Palmeiras': 'PAL', 'Flamengo': 'FLA', 'Corinthians': 'COR',
    'Cruzeiro': 'CRU', 'Botafogo': 'BOT', 'Fluminense': 'FLU',
    'São Paulo': 'SAO', 'Internacional': 'INT', 'Grêmio': 'GRE',
    'Santos': 'SAN', 'Vasco da Gama': 'VAS', 'Bragantino': 'BRA',
    'Atlético Mineiro': 'MIN', 'Athletico PR': 'CAP',
    'River Plate': 'RIV', 'Boca Juniors': 'BOC', 'Racing': 'RAC',
    'Independiente': 'IND', 'San Lorenzo': 'SLO', 'Vélez': 'VEL',
    'Talleres': 'TAL', 'Belgrano': 'BEL', 'Tigre': 'TIG',
    'Lanús': 'LAN', 'Banfield': 'BAN', 'Platense': 'PLA',
    'Huracán': 'HUR', 'Colón': 'COL', 'Unión': 'UNI',
    'Estudiantes': 'EST', 'Rosario Central': 'ROC',
    'Ind. Rivadavia': 'IRV', 'Ind. del Valle': 'IDV',
    'Olimpia': 'OLI', 'Libertad': 'LIB', 'Junior': 'JUN',
    'Santa Fe': 'STF', 'U. Católica': 'UCA', 'Macará': 'MAC',
    # MLB — nombres de equipo
    'Phillies': 'PHI', 'LA Dodgers': 'LAD', 'LA Angels': 'LAA',
    'NY Yankees': 'NYY', 'NY Mets': 'NYM', 'Red Sox': 'BOS',
    'Braves': 'ATL', 'Astros': 'HOU',
    'Giants': 'SFG', 'Padres': 'SDP', 'Rays': 'TBR',
    'Twins': 'MIN', 'White Sox': 'CHW',
    'Rangers': 'TEX', 'Guardians': 'CLE', 'Tigers': 'DET',
    'Mariners': 'SEA', 'Blue Jays': 'TOR', 'Brewers': 'MIL',
    'Pirates': 'PIT', 'Reds': 'CIN', 'Orioles': 'BAL',
    'Cardinals': 'STL', 'Nationals': 'WAS', 'Athletics': 'OAK',
    'Rockies': 'COL', 'Diamondbacks': 'ARI', 'Marlins': 'MIA',
    'KC Royals': 'KCR', 'Cubs': 'CHC',
    'Alianza': 'ALI',
}

# ── Tournament filtering ──
# Exclude friendlies — too unpredictable, low motivation
EXCLUDED_TOURNAMENT_KEYWORDS = [
    'friendl',          # Friendlies. National Teams / Friendlies U19
    'amistos',          # Spanish variants if any
    'club friendl',
    'mls+',             # MLS+ — formato corto poco confiable, mucha duplicación
    # ── Esports / gaming / simulación ──
    'esoccer',
    'e-soccer',
    'efootball',
    'e-football',
    'efighting',
    'cyber ',           # Cyber League, Cyber Cup
    'cyber.',
    'cyber-',
    'simulator',
    'simulated',
    'virtual ',
    'fifa league',
    'fifa cup',
    'fifa club',
    'volta ',
    'e-series',
    'eseries',
    'esports ',
    'e-sports',
    # ── Amateur / niche russian tournaments con equipos joke-name ──
    'magnitka',
    # ── Ligas menores / formatos chicos / regiones de bajo nivel ──
    'k3/k4',                                # South Korea Championship K3/K4
    'wk-league', 'wk league',               # South Korea WK-League (femenino menor)
    'australia cup',                        # Australia Cup
    'nsw cup',                              # Australia NSW Cup Women
    'china. second league', 'china second',
    'kazakhstan. premier',                  # Kazakhstan Premier League
    '6x6', 'mini euro',                     # Minifootball 6 vs 6
    'czech republic. qualification',
    'czech republic. 3 liga',
    'finnish cup',
    'philippines. ufl',
    'kenya. super league', 'kenya super',
    'vietnam',                              # Vietnam 2nd Division + Cup Women
    'utr pro',                              # UTR Pro Tennis Series (no pro real)
    'nhl',                                  # NHL (sólo 1 evento Stanley Cup final, descartado por pedido)
    'japan. npb', 'japan npb',              # NPB + Reserve + Winners
    'kbo',                                  # KBO South Korea + Winner
    # ── Reservas / Mujeres / Sub-20 — sin cobertura en The Odds API ──
    'u20', 'u19', 'u21', 'u23',            # Youth categories
    'sub 20', 'sub 19', 'sub 21', 'sub-20', 'sub-19', 'sub-21',
    'reserve', 'reserva',                   # Reserve leagues
    'women', 'femenin', 'female', 'mujeres',  # Women's leagues
    'youth', 'juvenil', 'junior',           # Youth/junior
    'primavera',                            # Italian youth league
    'opg',                                  # Torneio OPG U20
    # ── Ligas menores sin cobertura en The Odds API ──
    'série d', 'serie d',                   # Brazilian Serie D
    'série c', 'serie c',                   # Brazilian Serie C
    'sul-sudeste', 'suleste',               # Brazilian regional cups
    'copa paulista', 'gaucho u',            # Brazilian state youth
    'carioca c', 'carioca b',              # Campeonato Carioca C/B (regional BR)
    'campeonato carioca c', 'campeonato carioca b',
    'promocional amateur',                  # Torneo Promocional Amateur (ARG minor)
    'primera c ', 'primera c,',            # Primera C Metropolitana (ARG 4th)
    'primera b metropolitana',              # Primera B Metro (ARG 3rd)
    'primera b nacional',                   # Primera B Nacional
    'intermedia',                           # División Intermedia (Paraguay 2nd)
    # ── Divisiones 3ra/4ta/5ta de cualquier país ──
    'segunda b', 'tercera division',        # Spanish lower divisions
    'third league', 'third division',       # Generic 3rd division
    'fourth league', 'fourth division',     # Generic 4th
    'fifth league', 'fifth division',       # Generic 5th
    '3. liga', '4. liga', '5. liga',       # Czech/German 3rd-5th
    '3 liga', '4 liga',                    # Polish etc.
    '3. deild', '4. deild',               # Icelandic lower divisions
    '2 deild', '2. deild',                # Icelandic 2nd
    'division 1,', 'division 2', 'division 3',  # Scandinavian lower
    'esiliiga',                             # Estonian 2nd division
    'league two', 'usl league two',        # USL League Two (US amateur)
    # ── Campeonatos regionales (Brasil y otros) ──
    'campeonato mineiro', 'campeonato carioca',    # Brazilian state championships
    'campeonato gaucho', 'campeonato paranaense',
    'campeonato paulista', 'campeonato baiano',
    'campeonato catarinense', 'campeonato goiano',
    'campeonato capixaba', 'campeonato sergipano',
    'campeonato maranhense', 'campeonato piauiense',
    'campeonato paraibano', 'campeonato potiguar',
    'campeonato pernambucano', 'campeonato alagoano',
    'campeonato acreano', 'campeonato amapaense',
    'campeonato amazonense', 'campeonato matogrossense',
    'campeonato rondoniense', 'campeonato roraimense',
    'campeonato tocantinense', 'campeonato brasiliense',
    'liga gaucho', 'copa paulista',
    'simon bolivar',                        # Copa Simon Bolivar (Bolivia regional)
    # ── Ligas amateur / semi-pro ──
    'ahl',                                  # American Hockey League (minor)
    'latvian cup',                          # Latvia minor
    'silver league',                        # Minor volleyball/handball
    'liga 2',                               # Romanian/other 2nd division
    'ncaa',                                 # US college
    'qualification',                        # Qualification rounds
    'league cup',                           # Minor domestic cups
    'regionalliga',                         # German regional leagues
    'oberliga',                             # German amateur
    'landesliga',                           # German state leagues
    'kreisliga',                            # German district leagues
    'botola',                               # Morocco minor
    'stars league',                         # Qatar Stars League minor
    # ── Más islandesas/nórdicas menores ──
    'deild', 'delid',                       # Icelandic all lower divisions
    # ── Tenis circuitos menores (Challenger/ITF/Futures) ──
    'challenger', 'itf ',                   # ITF/Challenger circuits
    'birmingham', 'caltanissetta', 'heilbronn',  # Minor tour cities
    'tyler', 'harmon', 'perugia',          # Minor tour cities
    'santo domingo', 'prostejov', 'surbiton',
    # ── Primera B (genérica, no primera división) ──
    'primera b',                            # 2nd division Argentina/Chile/etc.
]
# Boost factor for preferred tournaments (Conmebol focus)
PREFERRED_TOURNAMENT_KEYWORDS = {
    'libertadores': 8,      # Copa Libertadores → 8x weight
    'sudamericana': 8,      # Copa Sudamericana → 8x weight
    'brasileiro': 4,        # Brazilian Serie A → 4x weight
    'copa argentina': 5,    # Copa Argentina → 5x weight
}

# ── Interesting market keywords ──
INTERESTING_KEYWORDS = [
    'Handicap', 'Total', 'Both Teams', 'HT-FT', 'Win And Total',
    'Individual Total', 'Race To', 'W1', 'W2', 'To Win',
    'Next Goal', 'Clean Sheet', 'Win To Nil', 'To Score',
    'Corners', 'Cards', 'Yellow', 'Odd', 'Even',
    'Not To Lose', 'Difference', 'Any Team', 'Neither',
    'Draw', 'No Draw', 'Half', 'Penalty',
    'Win By', 'Exact Score', 'Double Chance',
]

# Markets that are GENERIC (no team-specific) — show match instead of one team
# Type IDs from DBbet:
#   9/10 Total Over/Under, 180/181 BTTS Yes/No, 182/183 Total Even Yes/No,
#   5 = 12 (either team wins), 580 = Race To... Neither
#   1808/1809 Any Team Win To Nil, 4850/4851 Any Team Win Diff 1,
#   4918/4919 Any Team Win Diff 3+
#   188/189/190 1st Half vs 2nd Half (general match flow)
#   731 Correct Score, 8617/8618 Correct Score 17way
#   518/519 Penalty Awarded
GENERIC_MARKET_TYPES = {
    9, 10, 180, 181, 182, 183, 5, 580,
    1808, 1809, 4850, 4851, 4918, 4919,
    188, 189, 190,
    731, 8617, 8618,
    518, 519,
}
# Markets that imply a specific team winning — used to avoid contradictions
TEAM_WINNER_MARKETS = {'W1', 'W2', '1X', 'X2', '12'}

# ── Spanish translations for prop display ──
TRANSLATIONS = {
    'Over': 'Más de', 'Under': 'Menos de', 'Handicap': 'Hándicap',
    'Both Teams To Score - Yes': 'Ambos anotan - Sí',
    'Both Teams To Score - No': 'Ambos anotan - No',
    'Individual Total': 'Total Individual',
    'Race To': 'Primero en',
    'Goals': 'goles', 'Clean Sheet': 'Valla invicta',
    'Win To Nil': 'Gana sin goles en contra',
    'Team 1': 'Local', 'Team 2': 'Visitante',
    'Win And Total': 'Gana y Total',
    'Not To Lose': 'No pierde',
    'To Score Next Goal': 'Anota próximo gol',
    'Neither Team': 'Ninguno',
    ' And Total': ' y Total',
    ' To Win ': ' Gana ',
    'Any Team To': 'Algún equipo',
    ' Or More ': ' o más ',
    ' With Difference Of': ' por diferencia de',
    'Total Odd': 'Total Impar',
    'Total Even': 'Total Par',
    ' - Yes': ' - Sí',
    ' Wins ': ' Gana ',
    ' By ': ' por ',
    'Goal': 'Gol',
    'Corners': 'Córners',
    'Cards': 'Tarjetas',
    'Yellow': 'Amarilla',
    'Red': 'Roja',
    'Half Time': '1er Tiempo',
    'Full Time': 'Final',
    'Next ': 'Próximo ',
    'Score': 'Marca',
    'First': 'Primer',
    'Last': 'Último',
    'penalty': 'penal',
    'Penalty': 'Penal',
    'Draw': 'Empate',
    'No Draw': 'Sin Empate',
}

# ── Team/Country name translations (EN → ES) ──
TEAM_NAME_ES = {
    # Selecciones
    'Spain': 'España', 'France': 'Francia', 'Germany': 'Alemania',
    'England': 'Inglaterra', 'Netherlands': 'Holanda', 'Brazil': 'Brasil',
    'Mexico': 'México', 'Switzerland': 'Suiza', 'Sweden': 'Suecia',
    'Scotland': 'Escocia', 'Japan': 'Japón', 'South Korea': 'Corea del Sur',
    'Turkey': 'Turquía', 'South Africa': 'Sudáfrica',
    'Bosnia and Herzegovina': 'Bosnia', 'Czech Republic': 'Rep. Checa',
    'Cape Verde': 'Cabo Verde', 'Curacao': 'Curazao',
    'DR Congo': 'RD Congo', 'Saudi Arabia': 'Arabia Saudita',
    'Haiti': 'Haití', 'Iraq': 'Irak', 'Tunisia': 'Túnez',
    'Belgium': 'Bélgica', 'Egypt': 'Egipto', 'Panama': 'Panamá',
    'Morocco': 'Marruecos', 'Croatia': 'Croacia',
    'United States': 'EE.UU.', 'USA': 'EE.UU.', 'Costa Rica': 'Costa Rica',
    'North Korea': 'Corea del Norte', 'Ivory Coast': 'Costa de Marfil',
    'Denmark': 'Dinamarca', 'Poland': 'Polonia', 'Norway': 'Noruega',
    'Finland': 'Finlandia', 'Greece': 'Grecia', 'Romania': 'Rumania',
    'Hungary': 'Hungría', 'Serbia': 'Serbia', 'Slovakia': 'Eslovaquia',
    'Slovenia': 'Eslovenia', 'Albania': 'Albania', 'Iceland': 'Islandia',
    'Wales': 'Gales', 'Ireland': 'Irlanda', 'Russia': 'Rusia',
    'Ukraine': 'Ucrania', 'Peru': 'Perú', 'Chile': 'Chile',
    'Colombia': 'Colombia', 'Ecuador': 'Ecuador', 'Bolivia': 'Bolivia',
    'Venezuela': 'Venezuela', 'Honduras': 'Honduras',
    'Jamaica': 'Jamaica', 'Canada': 'Canadá', 'Uzbekistan': 'Uzbekistán',
    'Azerbaijan': 'Azerbaiyán', 'Kazakhstan': 'Kazajistán',
    'Cameroon': 'Camerún', 'Nigeria': 'Nigeria', 'Algeria': 'Argelia',
    'China': 'China', 'Iran': 'Irán', 'New Zealand': 'Nueva Zelanda',
    # Clubes — acortar nombres largos
    'Brighton & Hove Albion': 'Brighton', 'VfB Stuttgart': 'Stuttgart',
    'Nottingham Forest': 'Nott. Forest', 'Bologna 1909': 'Bologna',
    'Sassuolo Calcio': 'Sassuolo', 'Internazionale Milano': 'Inter de Milán',
    'Udinese Calcio': 'Udinese', 'Bayern Munich': 'Bayern Múnich',
    'Manchester United': 'Man. United', 'Manchester City': 'Man. City',
    'Tottenham Hotspur': 'Tottenham', 'West Ham United': 'West Ham',
    'Newcastle United': 'Newcastle', 'Hellas Verona': 'Verona',
    'Levante UD': 'Levante', 'Leeds United': 'Leeds',
    'Spartak Moscow': 'Spartak Moscú', 'Crystal Palace': 'Crystal Palace',
    'Wolverhampton Wanderers': 'Wolverhampton',
    'Paris Saint-Germain': 'PSG',
    'Cremonese': 'Cremonese',
}


def get_token():
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, headers={
        'Content-Type': 'application/x-www-form-urlencoded'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())['access_token']


def fetch_events(token):
    url = (f"{API_BASE}/sportevents?"
           f"ref={REF}&SchemeOfGettingOddsOperations=GetAllOdds"
           f"&partnerLink={PARTNER_LINK}&count=1000")
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def abbrev(name):
    for full, ab in TEAM_ABBREVS.items():
        if full.lower() in name.lower():
            return ab
    words = name.split()
    # Skip leading tokens that are not letters (e.g. "1." in "1. Slovacko")
    for w in words:
        if w and w[0].isalpha() and len(w) >= 2:
            return w[:3].upper()
    return (words[0][:3]).upper() if words else 'UNK'


def translate(display):
    d = display
    # Phase 1: Multi-word phrases first (order matters!)
    multi_word = [
        ('Any Team To Win With Difference Of', 'Algún equipo gana por diferencia de'),
        ('Any Team To Win', 'Algún equipo gana'),
        ('Any Team To', 'Algún equipo'),
        ('Both Teams To Score - Yes', 'Ambos anotan - Sí'),
        ('Both Teams To Score - No', 'Ambos anotan - No'),
        ('Win And Total', 'Gana y Total'),
        ('Win To Nil', 'Gana sin goles en contra'),
        ('Not To Lose', 'No pierde'),
        ('To Score Next Goal', 'Anota próximo gol'),
        ('Neither Team', 'Ninguno'),
        ('Individual Total', 'Total Individual'),
        ('Race To', 'Primero en'),
        ('Clean Sheet', 'Valla invicta'),
        ('Half Time', '1er Tiempo'),
        ('Full Time', 'Final'),
        ('No Draw', 'Sin Empate'),
    ]
    for en, es in multi_word:
        d = d.replace(en, es)
    # Phase 2: Single-word translations
    for en, es in TRANSLATIONS.items():
        d = d.replace(en, es)
    # Phase 3: Clean up leftover English fragments
    d = d.replace(' To Gana', ' Gana')
    d = d.replace(' To No pierde', ' No pierde')
    d = d.replace(' To Valla invicta', ' Valla invicta')
    d = d.replace('Any Team ', 'Algún equipo ')
    d = d.replace(' Wins ', ' Gana ')
    d = d.replace(' By ', ' por ')
    d = d.replace('Goals', 'Goles')
    d = d.replace('Goal', 'Gol')
    d = d.replace('Corners', 'Córners')
    d = d.replace(' Or More', ' o más')
    d = d.replace(' Of ', ' de ')
    d = d.replace('To Nil', 'sin goles en contra')
    d = d.replace(' To ', ' ')
    d = d.replace('goles en contra -', 'goles en contra -')
    # Double-space cleanup
    while '  ' in d:
        d = d.replace('  ', ' ')
    return d.strip()


def short_name(name):
    """Get a clean, compact full team name by stripping common club prefixes/suffixes."""
    if not name:
        return name
    s = translate_name(name)

    # ── Exact overrides for known long names ──
    EXACT = {
        'Sociedade Esportiva Palmeiras': 'Palmeiras',
        'Clube Atletico Mineiro': 'Atlético Mineiro',
        'Cruzeiro Esporte Clube': 'Cruzeiro',
        'Club Social y Deportivo Macara': 'Macará',
        'Botafogo de Futebol e Regatas': 'Botafogo',
        'Club Independiente Santa Fe': 'Santa Fe',
        'Alianza Atletico Sullana': 'Alianza',
        'Racing Club de Avellaneda': 'Racing',
        'River Plate Buenos Aires': 'River Plate',
        'Juventud de Las Piedras': 'Juventud',
        'Junior de Barranquilla': 'Junior',
        'Universidad Catolica Santiago': 'U. Católica',
        'Universidad Central de Venezuela': 'UCV',
        'Independiente del Valle': 'Ind. del Valle',
        'Independiente Rivadavia': 'Ind. Rivadavia',
        'Philadelphia Phillies': 'Phillies',
        'San Francisco Giants': 'Giants',
        'Red Bull Bragantino': 'Bragantino',
        'Barcelona Sporting Club': 'Barcelona SC',
        'America de Cali': 'América de Cali',
        'Club Olimpia': 'Olimpia',
        'Club Libertad': 'Libertad',
        'Club Atletico Tigre': 'Tigre',
        'Club Atletico Talleres': 'Talleres',
        'Club Atletico Belgrano': 'Belgrano',
        'Club Atletico Velez Sarsfield': 'Vélez',
        'Club Atletico Huracan': 'Huracán',
        'Club Atletico Lanus': 'Lanús',
        'Club Atletico Banfield': 'Banfield',
        'Club Atletico Union': 'Unión',
        'Club Atletico Platense': 'Platense',
        'Club Atletico Colon': 'Colón',
        'Club Atletico San Lorenzo': 'San Lorenzo',
        'Club Atletico Rosario Central': 'Rosario Central',
        'Club Atletico Estudiantes': 'Estudiantes',
        'Club Atletico Independiente': 'Independiente',
        'Club Atletico Boca Juniors': 'Boca Juniors',
        'Club Atletico River Plate': 'River Plate',
        'Atletico Nacional': 'Atl. Nacional',
        'Atletico Paranaense': 'Athletico PR',
        'Atletico Goianiense': 'Atlético GO',
        'Sport Club Internacional': 'Internacional',
        'Sport Club Corinthians Paulista': 'Corinthians',
        'Clube de Regatas do Flamengo': 'Flamengo',
        'Sao Paulo Futebol Clube': 'São Paulo',
        'Santos Futebol Clube': 'Santos',
        'Fluminense Football Club': 'Fluminense',
        'Gremio Porto Alegrense': 'Grêmio',
        'CR Vasco da Gama': 'Vasco da Gama',
        'Audax Italiano': 'Audax Italiano',
        'Deportivo Carabobo': 'Carabobo',
        'Academia Puerto Cabello': 'Puerto Cabello',
        'Tampa Bay Rays': 'Rays',
        'Boston Red Sox': 'Red Sox',
        'Atlanta Braves': 'Braves',
        'Baltimore Orioles': 'Orioles',
        'Los Angeles Dodgers': 'LA Dodgers',
        'Los Angeles Angels': 'LA Angels',
        'Colorado Rockies': 'Rockies',
        'San Diego Padres': 'Padres',
        'Arizona Diamondbacks': 'Diamondbacks',
        'Chicago White Sox': 'White Sox',
        'Minnesota Twins': 'Twins',
        'Kansas City Royals': 'KC Royals',
        'Texas Rangers': 'Rangers',
        'Houston Astros': 'Astros',
        'Detroit Tigers': 'Tigers',
        'New York Yankees': 'NY Yankees',
        'New York Mets': 'NY Mets',
        'Toronto Blue Jays': 'Blue Jays',
        'Milwaukee Brewers': 'Brewers',
        'Pittsburgh Pirates': 'Pirates',
        'Cincinnati Reds': 'Reds',
        'St. Louis Cardinals': 'Cardinals',
        'Washington Nationals': 'Nationals',
        'Miami Marlins': 'Marlins',
        'Seattle Mariners': 'Mariners',
        'Oakland Athletics': 'Athletics',
        'Cleveland Guardians': 'Guardians',
        'Chicago Cubs': 'Cubs',
    }
    if s in EXACT:
        return EXACT[s]

    # ── Strip common prefixes that just add noise ──
    prefixes = [
        'Club Atletico ', 'Clube Atletico ',
        'Sociedade Esportiva ', 'Sport Club ',
        'Clube de Regatas ', 'CR ',
        'Football Club ', 'FC ',
        'Athletic Club ',
        'Club Social y Deportivo ',
        'Club Independiente ',
        'Club Deportivo ', 'CD ',
        'Club ',
        'EC ', 'SC ',
        'Esporte Clube ',
        'AS ', 'AC ',
        'Real ',
        'CF ',
    ]
    for p in prefixes:
        if s.startswith(p):
            candidate = s[len(p):]
            # Don't strip if it leaves less than 3 chars
            if len(candidate.strip()) >= 3:
                s = candidate
                break  # only strip one prefix

    # ── Strip common suffixes ──
    suffixes = [
        ' Football Club', ' Futebol Clube',
        ' de Avellaneda', ' de Las Piedras',
        ' Buenos Aires', ' Paulista',
        ' Porto Alegrense', ' Esporte Clube',
        ' de Futebol e Regatas',
        ' Sporting Club',
        ' Santiago',
        ' de Barranquilla',
        ' de Cali',
        ' FC', ' CF', ' SC',
    ]
    for sf in suffixes:
        if s.endswith(sf):
            candidate = s[:-len(sf)]
            if len(candidate.strip()) >= 3:
                s = candidate
                break  # only strip one suffix

    return s.strip()


def translate_name(name):
    """Translate team/country names to Spanish."""
    # Try exact match first
    if name in TEAM_NAME_ES:
        return TEAM_NAME_ES[name]
    # Try partial match for club names
    for en, es in TEAM_NAME_ES.items():
        if en.lower() == name.lower():
            return es
    return name


def translate_match(t1, t2, tournament):
    """Build a Spanish-friendly match string — just tournament since player has rival context."""
    t1_es = translate_name(t1)
    t2_es = translate_name(t2)
    if tournament:
        short = tournament.split('.')[-1].strip() if '.' in tournament else tournament
        short = short.replace('World Cup', 'Mundial')
        short = short.replace('Champions League', 'Champions')
        short = short.replace('Premier League', 'Premier League')
        short = short.replace('Germany DFB Pokal', 'Copa de Alemania')
        short = short.replace('Coupe de France', 'Copa de Francia')
        short = short.replace('Russian Cup', 'Copa de Rusia')
        short = short.replace('Copa Libertadores', 'Libertadores')
        short = short.replace('Copa Sudamericana', 'Sudamericana')
        return f"{short}"
    return f"{t1_es} vs {t2_es}"


# ══════════════════════════════════════════════════════════════════════
# POISSON PREDICTIVE MODEL (football)
# ══════════════════════════════════════════════════════════════════════
# For each football match: extracts the bookmaker's W1/X/W2 + Total Over 2.5
# anchor cuotas, devigs them, then grid-searches (λ_home, λ_away) to find
# the Poisson parameters that best fit. From those λs we re-price every
# other market (handicaps, individual totals, BTTS, etc.) and compute
# edge = model_prob × bookmaker_odd - 1.
# Positive edge = bookie cuota mispriced HIGH = value pick (in model's view).
import math as _math


def _poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * _math.exp(-lam) / _math.factorial(k)


def _poisson_cdf(k, lam, max_k=15):
    """P(X ≤ k)"""
    return sum(_poisson_pmf(i, lam) for i in range(min(int(k), max_k) + 1))


def model_p_home_win(lh, la, max_goals=10):
    p = 0.0
    for h in range(max_goals + 1):
        ph = _poisson_pmf(h, lh)
        for a in range(h):
            p += ph * _poisson_pmf(a, la)
    return p


def model_p_draw(lh, la, max_goals=10):
    return sum(_poisson_pmf(k, lh) * _poisson_pmf(k, la) for k in range(max_goals + 1))


def model_p_away_win(lh, la, max_goals=10):
    return max(0.0, 1.0 - model_p_home_win(lh, la, max_goals) - model_p_draw(lh, la, max_goals))


def model_p_total_over(threshold, lh, la):
    """P(H + A > threshold) for fractional threshold like 2.5."""
    lam_total = lh + la
    floor_t = int(_math.floor(threshold))
    return max(0.0, 1.0 - _poisson_cdf(floor_t, lam_total))


def model_p_individual_total_over(threshold, lam):
    """P(team's goals > threshold)"""
    floor_t = int(_math.floor(threshold))
    return max(0.0, 1.0 - _poisson_cdf(floor_t, lam))


def model_p_btts(lh, la):
    """P(both teams score)"""
    return (1 - _math.exp(-lh)) * (1 - _math.exp(-la))


def model_p_handicap(handicap, lh, la, is_home, max_goals=10):
    """P(team covers handicap). Handicap is from team's perspective.
    e.g. Handicap 1 (-1.5) means team1 needs to win by 2+."""
    p = 0.0
    for h in range(max_goals + 1):
        ph = _poisson_pmf(h, lh)
        for a in range(max_goals + 1):
            pa = _poisson_pmf(a, la)
            if is_home:
                diff = (h - a) + handicap
            else:
                diff = (a - h) + handicap
            # Asian handicap with fractional: covers if diff > 0
            # For integer handicap, push is excluded (treated as half-loss in practice)
            if diff > 0.01:
                p += ph * pa
    return p


def devig_pair(o1, o2):
    """Remove margin from a 2-way market."""
    if not o1 or not o2:
        return None, None
    p1, p2 = 1/o1, 1/o2
    s = p1 + p2
    if s <= 0:
        return None, None
    return p1/s, p2/s


def devig_triple(o1, ox, o2):
    """Remove margin from 1X2."""
    if not o1 or not ox or not o2:
        return None, None, None
    p1, px, p2 = 1/o1, 1/ox, 1/o2
    s = p1 + px + p2
    if s <= 0:
        return None, None, None
    return p1/s, px/s, p2/s


def fit_match_lambdas(event):
    """Grid-search the Poisson lambdas that best fit the bookmaker's anchors.
    Returns (λ_home, λ_away) or None if anchors missing.
    Only for football matches."""
    if event.get('sportId', 0) != 1:
        return None

    odds_by_key = {}
    for odd in event.get('oddsLocalization', []):
        if odd.get('isBlocked'):
            continue
        key = (odd.get('type'), round(odd.get('parameter', 0), 2))
        odds_by_key[key] = odd.get('oddsMarket', 0)

    w1 = odds_by_key.get((1, 0.0))
    x = odds_by_key.get((2, 0.0))
    w2 = odds_by_key.get((3, 0.0))
    o25 = odds_by_key.get((9, 2.5))
    u25 = odds_by_key.get((10, 2.5))

    if not all([w1, x, w2]):
        return None
    if not (o25 and u25):
        # Fall back to alternative anchors
        o15 = odds_by_key.get((9, 1.5))
        u15 = odds_by_key.get((10, 1.5))
        if not (o15 and u15):
            return None
        po_fair, _ = devig_pair(o15, u15)
        anchor_total_threshold = 1.5
        anchor_total_prob = po_fair
    else:
        po_fair, _ = devig_pair(o25, u25)
        anchor_total_threshold = 2.5
        anchor_total_prob = po_fair

    p1_fair, px_fair, p2_fair = devig_triple(w1, x, w2)
    if not (p1_fair and px_fair and p2_fair and anchor_total_prob):
        return None

    # Grid search (lh, la) — coarse then fine
    best = None
    best_err = float('inf')
    # Coarse pass
    for lh_t in range(3, 36):
        lh = lh_t / 10.0
        for la_t in range(3, 36):
            la = la_t / 10.0
            err = (model_p_home_win(lh, la) - p1_fair) ** 2
            err += (model_p_draw(lh, la) - px_fair) ** 2
            err += (model_p_away_win(lh, la) - p2_fair) ** 2
            err += (model_p_total_over(anchor_total_threshold, lh, la) - anchor_total_prob) ** 2
            if err < best_err:
                best_err = err
                best = (lh, la)
    # Fine pass around best
    if best:
        lh0, la0 = best
        for dlh in range(-9, 10):
            lh = max(0.1, lh0 + dlh / 100.0)
            for dla in range(-9, 10):
                la = max(0.1, la0 + dla / 100.0)
                err = (model_p_home_win(lh, la) - p1_fair) ** 2
                err += (model_p_draw(lh, la) - px_fair) ** 2
                err += (model_p_away_win(lh, la) - p2_fair) ** 2
                err += (model_p_total_over(anchor_total_threshold, lh, la) - anchor_total_prob) ** 2
                if err < best_err:
                    best_err = err
                    best = (lh, la)
    return best


def model_probability(odd_type, param, lh, la):
    """Return the model's probability for a given market type, or None if unsupported."""
    if lh is None or la is None:
        return None
    t = odd_type
    if t == 1: return model_p_home_win(lh, la)
    if t == 2: return model_p_draw(lh, la)
    if t == 3: return model_p_away_win(lh, la)
    if t == 4: return model_p_home_win(lh, la) + model_p_draw(lh, la)        # 1X
    if t == 5: return model_p_home_win(lh, la) + model_p_away_win(lh, la)    # 12
    if t == 6: return model_p_draw(lh, la) + model_p_away_win(lh, la)        # 2X
    if t == 7: return model_p_handicap(param, lh, la, is_home=True)          # Handicap 1
    if t == 8: return model_p_handicap(param, lh, la, is_home=False)         # Handicap 2
    if t == 9: return model_p_total_over(param, lh, la)                      # Total Over
    if t == 10: return max(0.0, 1.0 - model_p_total_over(param, lh, la))     # Total Under
    if t == 11: return model_p_individual_total_over(param, lh)              # Ind Total 1 Over
    if t == 12: return max(0.0, 1.0 - model_p_individual_total_over(param, lh))  # Ind Total 1 Under
    if t == 13: return model_p_individual_total_over(param, la)              # Ind Total 2 Over
    if t == 14: return max(0.0, 1.0 - model_p_individual_total_over(param, la))  # Ind Total 2 Under
    if t == 180: return model_p_btts(lh, la)                                  # BTTS Yes
    if t == 181: return max(0.0, 1.0 - model_p_btts(lh, la))                 # BTTS No
    return None


# ══════════════════════════════════════════════════════════════════════


def build_prop_pool(data, start_ts_min=None, start_ts_max=None, day_label=None):
    """Convert API events into a PROP_POOL compatible format.
    Filters events between start_ts_min and start_ts_max (UTC timestamps).
    Tags each prop with day_label (e.g. 'sat', 'sun').
    """
    props = []
    now = datetime.now(timezone.utc)
    if start_ts_min is None:
        start_ts_min = now.timestamp()
    if start_ts_max is None:
        start_ts_max = now.timestamp() + 24 * 3600
    skipped_future = 0

    for event in data.get('items', []):
        start_ts = event.get('startDate', 0)
        if start_ts and start_ts > start_ts_max:
            skipped_future += 1
            continue
        if start_ts and start_ts < start_ts_min:
            continue  # skip events outside window

        sport_id = event.get('sportId', 0)
        # Only allow recognized sports (skip horse racing, table tennis, snooker, etc.)
        if sport_id not in SPORT_MAP:
            continue
        sport = SPORT_MAP[sport_id]

        # ── PREDICTIVE MODEL ──
        # Fit Poisson lambdas from the bookie's anchor odds (football only)
        lambdas = fit_match_lambdas(event)  # None for non-football
        t1 = event.get('opponent1NameLocalization', 'Team A')
        t2 = event.get('opponent2NameLocalization', 'Team B')
        match = f"{t1} vs {t2}"
        tournament = event.get('tournamentNameLocalization', '')
        link = event.get('link', '')
        # Skip excluded tournaments AND team names (friendlies, reserves, U20, etc.)
        tlow = tournament.lower()
        t1low = t1.lower()
        t2low = t2.lower()
        combined = f"{tlow} {t1low} {t2low}"
        if any(kw in combined for kw in EXCLUDED_TOURNAMENT_KEYWORDS):
            continue
        # Compute boost weight for preferred tournaments
        boost_weight = 1
        for kw, w in PREFERRED_TOURNAMENT_KEYWORDS.items():
            if kw in tlow:
                boost_weight = max(boost_weight, w)
                break
        date_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime('%b %d · %H:%M') if start_ts else 'TBD'
        ab1, ab2 = abbrev(t1), abbrev(t2)

        # Get logo URLs
        img1_list = event.get('imageOpponent1', [])
        img2_list = event.get('imageOpponent2', [])
        logo1 = f"{LOGO_BASE}{img1_list[0]}" if img1_list else ''
        logo2 = f"{LOGO_BASE}{img2_list[0]}" if img2_list else ''

        for odd in event.get('oddsLocalization', []):
            if odd.get('isBlocked', False):
                continue
            odds_val = odd.get('oddsMarket', 0)
            # Min odds threshold: 1.30 normal, 1.20 para torneos preferidos (más alternativas)
            min_odd = 1.20 if boost_weight > 1 else 1.30
            if odds_val < min_odd:
                continue  # skip near-certain outcomes
            display = odd.get('display', '')

            # Filter interesting markets
            if not any(kw.lower() in display.lower() for kw in INTERESTING_KEYWORDS):
                continue

            # Determine which team and logo
            otype = odd.get('type', 0)
            if otype in GENERIC_MARKET_TYPES:
                # Generic market (Total, BTTS, Even/Odd, Any Team, etc.) — show MATCH not a team
                player, rival, team, logo = None, None, '', ''
                is_generic = True
            else:
                # Strip parameter parens first — they contain numbers that confuse the 1/2 check
                display_core = re.sub(r'\([^)]*\)', '', display)
                if '1' in display_core and '2' not in display_core:
                    player, rival, team, logo = t1, t2, ab1, logo1
                elif '2' in display_core and '1' not in display_core:
                    player, rival, team, logo = t2, t1, ab2, logo2
                else:
                    player, rival, team, logo = t1, t2, ab1, logo1
                is_generic = False

            # Translate names — format: "(vs Rival) Equipo"
            if is_generic:
                # For generic markets, the "player" line shows both teams
                t1_es = translate_name(t1)
                t2_es = translate_name(t2)
                player_display = f"{short_name(t1)} vs {short_name(t2)}"
                player_es = player_display
                rival_es = ''
            else:
                player_es = short_name(player)
                rival_es = short_name(rival)
                player_display = f"({abbrev(rival_es)} vs) {player_es}"
            match_display = translate_match(t1, t2, tournament)

            # Detect if this is a team-winner market (for anti-contradiction)
            is_winner_pick = (not is_generic) and any(wm in display for wm in TEAM_WINNER_MARKETS)
            side = 'home' if (not is_generic and player == t1) else 'away'

            # Personalize prop text with full team names (Peñarol, not PEN)
            n1 = short_name(t1)
            n2 = short_name(t2)
            translated_prop = translate(display)
            personalized = translated_prop
            personalized = personalized.replace('Hándicap 1 ', f'Hándicap {n1} ')
            personalized = personalized.replace('Hándicap 2 ', f'Hándicap {n2} ')
            personalized = personalized.replace('Total Individual 1 ', f'Total {n1} ')
            personalized = personalized.replace('Total Individual 2 ', f'Total {n2} ')
            personalized = personalized.replace('Local ', f'{n1} ')
            personalized = personalized.replace('Visitante ', f'{n2} ')
            personalized = personalized.replace(' - Local', f' - {n1}')
            personalized = personalized.replace(' - Visitante', f' - {n2}')
            # Standalone W1/W2/1X/X2/12
            import re as _re_subst
            personalized = _re_subst.sub(r'^W1$', f'Gana {n1}', personalized)
            personalized = _re_subst.sub(r'^W2$', f'Gana {n2}', personalized)
            personalized = _re_subst.sub(r'^1X$', f'Gana {n1} o Empate', personalized)
            personalized = _re_subst.sub(r'^X2$', f'Empate o Gana {n2}', personalized)
            personalized = _re_subst.sub(r'^12$', f'{n1} o {n2}', personalized)

            # === Reescritura en lenguaje natural ===
            # Unidad por deporte (goles / carreras / puntos / etc.)
            _unit_map = {'futbol': 'goles', 'hockey': 'goles', 'mlb': 'carreras',
                         'nba': 'puntos', 'tenis': 'puntos', 'ufc': ''}
            _u = _unit_map.get(sport, 'goles')
            # 1) Totales individuales con equipo: "Total Penarol Más de (1.5)" → "Más de 1.5 goles de Penarol"
            personalized = _re_subst.sub(
                r'Total (' + _re_subst.escape(n1) + r'|' + _re_subst.escape(n2) + r') Más de \((-?\d+(?:\.\d+)?)\)',
                lambda m: f'Más de {m.group(2)} {_u} de {m.group(1)}',
                personalized)
            personalized = _re_subst.sub(
                r'Total (' + _re_subst.escape(n1) + r'|' + _re_subst.escape(n2) + r') Menos de \((-?\d+(?:\.\d+)?)\)',
                lambda m: f'Menos de {m.group(2)} {_u} de {m.group(1)}',
                personalized)
            # 2) Total general: "Total Más de (2.5)" → "Más de 2.5 goles"
            personalized = _re_subst.sub(r'Total Más de \((-?\d+(?:\.\d+)?)\)', lambda m: f'Más de {m.group(1)} {_u}', personalized)
            personalized = _re_subst.sub(r'Total Menos de \((-?\d+(?:\.\d+)?)\)', lambda m: f'Menos de {m.group(1)} {_u}', personalized)
            # 3) Compound (en frases como "Gana y Total > (X)"): "Total > (X)" / "Total < (X)"
            personalized = _re_subst.sub(r'Total > \((-?\d+(?:\.\d+)?)\)', lambda m: f'Más de {m.group(1)} {_u}', personalized)
            personalized = _re_subst.sub(r'Total < \((-?\d+(?:\.\d+)?)\)', lambda m: f'Menos de {m.group(1)} {_u}', personalized)
            # 4) Hándicap → HÁ con paréntesis quitados. (Preserva sufijo " Sets")
            # Positivos llevan "+", negativos ya tienen "-"
            def _fmt_handicap(m):
                name, val, sets = m.group(1), m.group(2), m.group(3) or ''
                prefix = '+' if not val.startswith('-') and val not in ('0', '0.0') else ''
                return f'HÁ {name} {prefix}{val}{sets}'
            personalized = _re_subst.sub(r'Hándicap (.+?) \((-?\d+(?:\.\d+)?)\)( Sets)?', _fmt_handicap, personalized)
            # 5) Limpieza: doble espacio
            personalized = _re_subst.sub(r'\s+', ' ', personalized).strip()
            # ── EDGE CALCULATION ──
            # Priority: Sharp market edge (The Odds API) > Poisson model edge
            edge_val = None
            model_p = None
            sharp_edge = None

            # 1) Sharp edge from market intelligence (if available)
            if HAS_INTEL and hasattr(build_prop_pool, '_intel') and build_prop_pool._intel:
                intel = build_prop_pool._intel
                mapping = odds_api_market_from_dbbet(
                    odd.get('type', 0), odd.get('parameter', 0), t1, t2
                )
                if mapping:
                    mkt, outcome, param_str = mapping
                    sharp_edge = intel.true_edge(t1, t2, mkt, outcome, param_str, odds_val)
                    if sharp_edge is not None:
                        edge_val = round(max(-0.30, min(0.30, sharp_edge)), 4)

            # 2) Fallback: Poisson model edge (if no sharp data)
            if edge_val is None and lambdas:
                model_p = model_probability(
                    odd.get('type', 0),
                    odd.get('parameter', 0),
                    lambdas[0], lambdas[1]
                )
                if model_p is not None and 0.04 <= model_p <= 0.96:
                    raw_edge = (model_p * odds_val) - 1
                    edge_val = round(max(-0.30, min(0.25, raw_edge)), 4)

            prop_obj = {
                'player': player_display,
                'prop': personalized,
                'match': match_display,
                'odd': round(odds_val, 2),
                'sport': sport,
                'team': team,
                'date': date_str,
                'link': link,
                'logo': logo,
                'is_winner': is_winner_pick,
                'side': side,
                'match_key': f"{t1} vs {t2}",
                'day': day_label or 'today',
                'tournament': tournament,
                'edge': edge_val,           # None if no data, else fraction (-0.05 = -5%)
                'sharp_edge': sharp_edge,   # Edge from sharp books (None if unavailable)
                'model_p': model_p,         # Poisson probability (None or 0..1)
                'edge_source': 'sharp' if sharp_edge is not None else ('poisson' if model_p is not None else None),
                # SaveCoupon fields for coupon code generation
                'game_id': event.get('sportEventId', 0),
                'type_id': odd.get('type', 0),
                'param': odd.get('parameter', 0),
                'player_id': odd.get('playerId', 0),
            }
            # Duplicate prop boost_weight times so build_tickets picks it more often
            for _ in range(boost_weight):
                props.append(prop_obj)

    if skipped_future:
        print(f"   ⏭️  {skipped_future} eventos descartados (fuera de ventana 24h)")
    return props


# ──────────────────────────────────────────────
# Ticket building (same logic as v3, adapted)
# ──────────────────────────────────────────────

def _esc(s):
    return str(s).replace("'", "\\'").replace("\n", " ")


def calculate_confidence(legs):
    """Calculate confidence score (1-6) for a ticket.

    Uses three layers:
    1. Edge quality: how many legs have verified sharp edge > 0
    2. Team stats: form, injuries (from API-Football when available)
    3. Odds consistency: probability distribution variance
    """
    probs = [1/leg['odd'] for leg in legs]
    avg_prob = sum(probs) / len(probs)
    n = len(legs)

    # Base from average probability
    if avg_prob > 0.55: base = 5
    elif avg_prob > 0.45: base = 4
    elif avg_prob > 0.35: base = 3
    elif avg_prob > 0.25: base = 2
    else: base = 1

    # Penalty for too many legs
    if n >= 6: base = max(1, base - 2)
    elif n >= 5: base = max(1, base - 1)

    # Bonus for consistent probabilities (low variance)
    variance = sum((p - avg_prob)**2 for p in probs) / len(probs)
    if variance < 0.01: base = min(6, base + 1)

    # ── NEW: Edge quality bonus ──
    # If we have sharp edge data, reward tickets where most legs have positive edge
    sharp_edges = [l.get('sharp_edge') for l in legs if l.get('sharp_edge') is not None]
    if sharp_edges:
        positive_pct = sum(1 for e in sharp_edges if e > 0) / len(sharp_edges)
        if positive_pct >= 0.8:
            base = min(6, base + 1)  # 80%+ legs have positive sharp edge
        elif positive_pct >= 0.6:
            pass  # neutral
        else:
            base = max(1, base - 1)  # too many negative-edge legs

        # Extra bonus if average sharp edge is strongly positive
        avg_sharp = sum(sharp_edges) / len(sharp_edges)
        if avg_sharp >= 0.05:  # 5%+ average edge across the ticket
            base = min(6, base + 1)

    # ── NEW: Team stats adjustment ──
    if HAS_INTEL and hasattr(build_prop_pool, '_intel') and build_prop_pool._intel:
        intel = build_prop_pool._intel
        stat_adjustments = 0
        stat_count = 0

        for leg in legs:
            if leg.get('sport') != 'futbol':
                continue
            mk = leg.get('match_key', '')
            if ' vs ' not in mk:
                continue
            parts = mk.split(' vs ')
            if len(parts) != 2:
                continue
            conf = intel.team_confidence(parts[0].strip(), parts[1].strip())
            if conf['score'] != 3:  # 3 is neutral (no data)
                stat_adjustments += conf['score'] - 3
                stat_count += 1

        if stat_count >= 2:
            avg_adj = stat_adjustments / stat_count
            if avg_adj >= 0.5:
                base = min(6, base + 1)
            elif avg_adj <= -0.5:
                base = max(1, base - 1)

    return min(6, max(1, base))


def prop_key(p):
    return f"{p['player']}|{p['prop']}"


def build_tickets(pool):
    """Build tickets. REGLA: máximo 1 apuesta por partido en cada billete."""
    tickets = []
    used_keys = set()

    # Identify unique matches available
    unique_matches = list(set(p['match'] for p in pool))
    n_matches = len(unique_matches)
    print(f"   🏟️  {n_matches} partidos disponibles: {', '.join(unique_matches[:5])}")

    # Split pool by odds range
    # REGLA: 1 wildcard (3-10) + resto ≤x3.00. Billetes LARGOS (6-8 selecciones).
    ultra = [p for p in pool if 1.30 <= p['odd'] <= 1.50]   # 🎯 cuotas ~x1.40 (favoritas)
    low = [p for p in pool if 1.50 < p['odd'] <= 1.80]
    mid = [p for p in pool if 1.80 < p['odd'] <= 2.30]
    high = [p for p in pool if 2.30 < p['odd'] <= 3.00]
    very_high = [p for p in pool if 3.00 < p['odd'] <= 10.0]  # wildcard, capeada a x10

    print(f"   ultra(1.3-1.5): {len(ultra)}, low(1.5-1.8): {len(low)}, "
          f"mid(1.8-2.3): {len(mid)}, high(2.3-3): {len(high)}, wildcard(3-10): {len(very_high)}")
    print(f"   ⚠️  REGLA: 1 wildcard (x3-10) + resto ≤x3.00. Billetes 6-15 selecciones (megalodones!).")

    # Anti-contradiction: track which side we've committed to per match
    # e.g. winner_side['Lens vs Nice'] = 'home' → never pick 'away wins' for that match
    winner_side = {}  # match_key → 'home' or 'away'

    def _edge_sort_key(p):
        """Sort: higher edge first; None edges treated as -1 (skeptical). Add jitter for variety."""
        e = p.get('edge')
        base = e if (e is not None) else -1.0
        return -(base + random.uniform(-0.02, 0.02))

    def pick_legs(pools_config, min_sports=1):
        """Pick legs enforcing MAX 1 leg per match + no contradictions.
        Prioriza picks de mayor edge (Modelo Poisson)."""
        selected = []
        sports_used = set()
        matches_used = set()
        for pool_list, count in pools_config:
            available = [p for p in pool_list
                         if prop_key(p) not in used_keys
                         and p['match'] not in matches_used]
            # Sort by edge desc with small jitter (so tickets are diverse but biased to value)
            available.sort(key=_edge_sort_key)
            picked = 0
            for p in available:
                if picked >= count:
                    break
                if p['match'] in matches_used:
                    continue
                # Anti-contradiction: if this is a winner pick, check consistency
                if p.get('is_winner') and p.get('match_key'):
                    mk = p['match_key']
                    committed = winner_side.get(mk)
                    if committed and committed != p['side']:
                        continue  # skip — contradicts a previous ticket
                selected.append(p)
                sports_used.add(p['sport'])
                matches_used.add(p['match'])
                picked += 1
        total_needed = sum(c for _, c in pools_config)
        if len(selected) >= total_needed:
            for s in selected:
                used_keys.add(prop_key(s))
                # Record winner commitment for anti-contradiction
                if s.get('is_winner') and s.get('match_key'):
                    winner_side[s['match_key']] = s['side']
            return selected
        return None

    # Determine ticket sizes based on available matches
    max_legs = min(n_matches, 15)  # Hasta 15 selecciones — Megalodones desbloqueados

    # ══════════════════════════════════════════════════════════════════
    # REGLA CLAVE: 1 wildcard (x3.00-10.00) + resto ≤x3.00. Billetes LARGOS (6-15 selecciones).
    # very_high (wildcard) = x3.00-10.00 (máx 1 por billete, capeada para evitar absurdos)
    # high = x2.30-3.00, mid = x1.80-2.30, low = x1.50-1.80, ultra = x1.30-1.50
    #
    # TIERS (por cuota total):
    #   Megalodón:  x1000+
    #   Whale:      x100-999
    #   Shark:      x10-99
    #   Hunter:     x3-9.9
    #   Confiable:  x5-9    (5-10 legs, confianza 5/6)
    #   Segura:     x3-6    (5-10 legs, confianza 6/6)
    # ══════════════════════════════════════════════════════════════════

    # Build ticket combos — billetes LARGOS (6-8 selecciones), foco en cuotas ~1.40
    ticket_combos = []

    if n_matches >= 15:
        ticket_combos = [
            # 15 selecciones — MEGALODÓN extremo
            ((very_high, 1), (high, 3), (mid, 4), (low, 4), (ultra, 3)),
            ((very_high, 1), (high, 2), (mid, 4), (low, 4), (ultra, 4)),
            # 14 selecciones
            ((very_high, 1), (high, 3), (mid, 4), (low, 3), (ultra, 3)),
            ((very_high, 1), (high, 2), (mid, 3), (low, 4), (ultra, 4)),
            # 13 selecciones
            ((very_high, 1), (high, 3), (mid, 3), (low, 3), (ultra, 3)),
            ((very_high, 1), (high, 2), (mid, 4), (low, 3), (ultra, 3)),
            # 12 selecciones
            ((very_high, 1), (high, 3), (mid, 3), (low, 3), (ultra, 2)),
            ((very_high, 1), (high, 2), (mid, 3), (low, 3), (ultra, 3)),
            ((very_high, 1), (high, 2), (mid, 4), (low, 3), (ultra, 2)),
            # 11 selecciones
            ((very_high, 1), (high, 3), (mid, 3), (low, 2), (ultra, 2)),
            ((very_high, 1), (high, 2), (mid, 3), (low, 3), (ultra, 2)),
            ((very_high, 1), (high, 2), (mid, 2), (low, 3), (ultra, 3)),
            # 10 selecciones
            ((very_high, 1), (high, 3), (mid, 3), (low, 2), (ultra, 1)),
            ((very_high, 1), (high, 2), (mid, 3), (low, 2), (ultra, 2)),
            ((very_high, 1), (high, 2), (mid, 2), (low, 3), (ultra, 2)),
            ((very_high, 1), (mid, 3), (low, 3), (ultra, 3)),
            # 9 selecciones
            ((very_high, 1), (high, 2), (mid, 3), (low, 2), (ultra, 1)),
            ((very_high, 1), (high, 2), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (mid, 3), (low, 2), (ultra, 3)),
            # 8 selecciones — foco en x1.40
            ((very_high, 1), (high, 1), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 2), (ultra, 3)),
            ((very_high, 1), (high, 2), (mid, 2), (low, 1), (ultra, 2)),
            ((very_high, 1), (low, 3), (ultra, 4)),
            ((very_high, 1), (mid, 3), (low, 2), (ultra, 2)),
            # 7 selecciones
            ((very_high, 1), (high, 1), (mid, 2), (low, 1), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (low, 3), (ultra, 3)),
            # 6 selecciones
            ((very_high, 1), (high, 1), (mid, 1), (low, 1), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 1), (ultra, 2)),
        ]
    elif n_matches >= 10:
        ticket_combos = [
            # 10 selecciones — megalodón posible
            ((very_high, 1), (high, 3), (mid, 3), (low, 2), (ultra, 1)),
            ((very_high, 1), (high, 2), (mid, 3), (low, 2), (ultra, 2)),
            ((very_high, 1), (mid, 3), (low, 3), (ultra, 3)),
            # 9 selecciones
            ((very_high, 1), (high, 2), (mid, 3), (low, 2), (ultra, 1)),
            ((very_high, 1), (mid, 3), (low, 2), (ultra, 3)),
            # 8 selecciones
            ((very_high, 1), (high, 1), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 2), (ultra, 3)),
            ((very_high, 1), (low, 3), (ultra, 4)),
            # 7 selecciones
            ((very_high, 1), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (low, 3), (ultra, 3)),
            # 6 selecciones
            ((very_high, 1), (mid, 2), (low, 1), (ultra, 2)),
            ((very_high, 1), (low, 2), (ultra, 3)),
        ]
    elif n_matches >= 8:
        ticket_combos = [
            # 8 selecciones — máximo tedio, foco en x1.40
            ((very_high, 1), (high, 1), (mid, 2), (low, 2), (ultra, 2)),  # ~1 wc + variado
            ((very_high, 1), (mid, 2), (low, 2), (ultra, 3)),               # foco ultras
            ((very_high, 1), (high, 2), (mid, 2), (low, 1), (ultra, 2)),
            ((very_high, 1), (low, 3), (ultra, 4)),                          # MUY tedioso
            ((very_high, 1), (mid, 3), (low, 2), (ultra, 2)),
            ((high, 1), (mid, 2), (low, 3), (ultra, 2)),                     # sin wildcard
            ((high, 2), (mid, 2), (low, 2), (ultra, 2)),
            # 7 selecciones
            ((very_high, 1), (high, 1), (mid, 2), (low, 1), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 2), (ultra, 2)),
            ((very_high, 1), (high, 1), (low, 2), (ultra, 3)),
            ((very_high, 1), (low, 3), (ultra, 3)),
            ((high, 1), (mid, 2), (low, 2), (ultra, 2)),
            # 6 selecciones
            ((very_high, 1), (high, 1), (mid, 1), (low, 1), (ultra, 2)),
            ((very_high, 1), (mid, 2), (low, 1), (ultra, 2)),
            ((very_high, 1), (low, 2), (ultra, 3)),
            ((high, 1), (mid, 1), (low, 2), (ultra, 2)),
            ((mid, 2), (low, 2), (ultra, 2)),
        ]
    elif n_matches >= 6:
        L = n_matches
        ticket_combos = [
            ((very_high, 1), (mid, 2), (low, min(2, L-3)), (ultra, min(2, L-5))),
            ((very_high, 1), (low, min(2, L-1)), (ultra, min(3, L-3))),
            ((very_high, 1), (mid, 1), (low, min(2, L-2)), (ultra, min(2, L-4))),
            ((high, 1), (mid, 1), (low, min(2, L-2)), (ultra, min(2, L-4))),
            ((mid, 2), (low, min(2, L-2)), (ultra, min(2, L-4))),
        ]
    elif n_matches >= 4:
        L = n_matches
        ticket_combos = [
            ((very_high, 1), (low, min(2, L-1)), (ultra, min(1, L-3))),
            ((very_high, 1), (mid, 1), (ultra, min(2, L-2))),
            ((high, 1), (low, 1), (ultra, min(2, L-2))),
            ((mid, 1), (low, 1), (ultra, min(2, L-2))),
        ]
    elif n_matches >= 3:
        ticket_combos = [
            ((very_high, 1), (mid, 1), (ultra, 1)),
            ((very_high, 1), (low, min(2, n_matches-1))),
            ((mid, 1), (low, 1), (ultra, 1)),
            ((low, min(2, n_matches)), (ultra, min(1, n_matches-2))),
        ]
    else:
        ticket_combos = [
            ((very_high, 1), (ultra, min(1, n_matches-1))),
            ((low, min(2, n_matches)),),
            ((mid, min(2, n_matches)),),
        ]

    ATTEMPTS_PER_COMBO = 6
    for combo in ticket_combos:
        pools_cfg = list(combo)
        for _ in range(ATTEMPTS_PER_COMBO):
            for pl, _ in pools_cfg:
                random.shuffle(pl)
            legs = pick_legs(pools_cfg)
            if legs:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if total >= 3.0:  # mínimo para cualquier tier
                    # Compute model score: avg edge mapped to 0-10
                    edges = [l.get('edge') for l in legs if l.get('edge') is not None]
                    if edges:
                        avg_edge = sum(edges) / len(edges)
                        coverage = len(edges) / len(legs)
                        # Map avg_edge [-0.15..+0.10] to score [0..10], adjust by coverage
                        raw_score = max(0.0, min(10.0, (avg_edge + 0.15) / 0.25 * 10))
                        model_score = round(raw_score * coverage + 5 * (1 - coverage), 1)
                    else:
                        model_score = None  # no covered markets (e.g. tenis/mlb-heavy ticket)
                    tickets.append({
                        'tier': 'pending',
                        'legs': legs,
                        'total_odds': total,
                        'confidence': calculate_confidence(legs),
                        'model_score': model_score,
                        'avg_edge': round(avg_edge, 4) if edges else None,
                        'model_coverage': round(coverage, 2) if edges else 0.0,
                    })

    # ── GENERAR BILLETES SEGUROS/CONFIABLES (cuotas bajas, 5-10 selecciones) ──
    # Estos billetes usan SÓLO cuotas ultra + low para maximizar probabilidad de acierto.
    safe_combos = []
    if n_matches >= 10:
        safe_combos = [
            # 10 selecciones — cuota total ~x5-x15 con puras ultras/lows
            ((low, 3), (ultra, 7)),
            ((low, 2), (ultra, 8)),
            ((ultra, 10),),
            # 9 selecciones
            ((low, 3), (ultra, 6)),
            ((low, 2), (ultra, 7)),
            ((ultra, 9),),
            # 8 selecciones
            ((low, 2), (ultra, 6)),
            ((low, 3), (ultra, 5)),
            ((ultra, 8),),
            # 7 selecciones
            ((low, 2), (ultra, 5)),
            ((low, 1), (ultra, 6)),
            ((ultra, 7),),
            # 6 selecciones
            ((low, 2), (ultra, 4)),
            ((low, 1), (ultra, 5)),
            ((ultra, 6),),
            # 5 selecciones
            ((low, 2), (ultra, 3)),
            ((low, 1), (ultra, 4)),
            ((ultra, 5),),
        ]
    elif n_matches >= 7:
        safe_combos = [
            ((low, 2), (ultra, 5)),
            ((low, 3), (ultra, 4)),
            ((ultra, 7),),
            ((low, 2), (ultra, 4)),
            ((low, 1), (ultra, 5)),
            ((ultra, 6),),
            ((low, 2), (ultra, 3)),
            ((low, 1), (ultra, 4)),
            ((ultra, 5),),
        ]
    elif n_matches >= 5:
        safe_combos = [
            ((low, 2), (ultra, 3)),
            ((low, 1), (ultra, 4)),
            ((ultra, 5),),
            ((low, 1), (ultra, 3)),
            ((low, 2), (ultra, 2)),
        ]

    safe_tickets = []
    SAFE_ATTEMPTS = 8
    for combo in safe_combos:
        pools_cfg = list(combo)
        for _ in range(SAFE_ATTEMPTS):
            for pl, _ in pools_cfg:
                random.shuffle(pl)
            legs = pick_legs(pools_cfg)
            if legs and len(legs) >= 5:
                total = round(math.prod(l['odd'] for l in legs), 1)
                if 3.0 <= total <= 9.0:
                    edges = [l.get('edge') for l in legs if l.get('edge') is not None]
                    if edges:
                        avg_edge = sum(edges) / len(edges)
                        coverage = len(edges) / len(legs)
                        raw_score = max(0.0, min(10.0, (avg_edge + 0.15) / 0.25 * 10))
                        model_score = round(raw_score * coverage + 5 * (1 - coverage), 1)
                    else:
                        model_score = None
                    safe_tickets.append({
                        'tier': 'pending_safe',
                        'legs': legs,
                        'total_odds': total,
                        'confidence': 6 if total <= 6.0 else 5,  # segura=6, confiable=5
                        'model_score': model_score,
                        'avg_edge': round(avg_edge, 4) if edges else None,
                        'model_coverage': round(coverage, 2) if edges else 0.0,
                    })

    print(f"   🔒 Billetes seguros/confiables generados: {len(safe_tickets)}")

    # ── FILTRO DE CONFIANZA ──
    # Quitar billetes de baja confianza (confianza 1, 2). Sólo se publican medio+.
    MIN_CONFIDENCE = 3
    before_filter = len(tickets)
    tickets = [t for t in tickets if t['confidence'] >= MIN_CONFIDENCE]
    print(f"   🎯 Filtro confianza ≥{MIN_CONFIDENCE}: {before_filter} → {len(tickets)} billetes")

    # Classify tiers by total odds
    for t in tickets:
        odds = t['total_odds']
        if odds >= 1000:
            t['tier'] = 'megalodon'
        elif odds >= 100:
            t['tier'] = 'whale'
        elif odds >= 10:
            t['tier'] = 'shark'
        else:
            t['tier'] = 'hunter'

    # Classify safe tickets: segura (x3-6) vs confiable (x5-9)
    for t in safe_tickets:
        if t['total_odds'] <= 6.0:
            t['tier'] = 'segura'
            t['confidence'] = 6
        else:
            t['tier'] = 'confiable'
            t['confidence'] = 5

    # ── CAP POR TIER ──
    # Limitar cantidad por tier — la página crasheaba con 350+ billetes.
    tier_order = {'megalodon': 0, 'whale': 1, 'shark': 2, 'hunter': 3, 'confiable': 4, 'segura': 5}
    tier_caps = {'megalodon': 8, 'whale': 12, 'shark': 10, 'hunter': 6, 'confiable': 6, 'segura': 6}

    # Merge safe tickets into main list
    tickets.extend(safe_tickets)

    by_tier = {k: [] for k in tier_caps}
    for t in tickets:
        if t['tier'] in by_tier:
            by_tier[t['tier']].append(t)
    capped = []
    for tier, max_n in tier_caps.items():
        # Ordenar por (confianza DESC, cuota DESC) y tomar los mejores
        sorted_tier = sorted(by_tier[tier], key=lambda t: (-t['confidence'], -t['total_odds']))
        kept = sorted_tier[:max_n]
        capped.extend(kept)
        if sorted_tier and len(sorted_tier) > max_n:
            print(f"   ✂️  Tier {tier}: {len(sorted_tier)} → {len(kept)} (cap)")
    tickets = capped

    tickets.sort(key=lambda t: (tier_order[t['tier']], -t['total_odds']))

    # Assign IDs
    counters = {'megalodon': 0, 'whale': 0, 'shark': 0, 'hunter': 0, 'confiable': 0, 'segura': 0}
    for ticket in tickets:
        tier = ticket['tier']
        counters[tier] += 1
        ticket['id'] = f"{tier[0].upper()}{counters[tier]}"
        sports_in = list(set(l['sport'] for l in ticket['legs']))
        if len(sports_in) == 1:
            ticket['title'] = f"{SPORT_NAMES.get(sports_in[0], 'Multi')} Props Mix"
        elif len(sports_in) == 2:
            ticket['title'] = f"{SPORT_NAMES.get(sports_in[0], '?')} + {SPORT_NAMES.get(sports_in[1], '?')}"
        else:
            ticket['title'] = f"Multi-Sport x{len(sports_in)}"

    # Verify: zero duplicate props, max 1 leg per match, max 1 leg >x3, all legs ≤x10
    all_keys = []
    for t in tickets:
        wildcard_count = sum(1 for l in t['legs'] if l['odd'] > 3.00)
        assert wildcard_count <= 1, \
            f"REGLA VIOLADA en {t['id']}: {wildcard_count} selecciones >x3.00 (máx 1)"
        for l in t['legs']:
            assert l['odd'] <= 10.0, \
                f"REGLA VIOLADA en {t['id']}: cuota {l['odd']} > x10 (no permitido)"
        match_check = set()
        for l in t['legs']:
            all_keys.append(prop_key(l))
            assert l['match'] not in match_check, \
                f"DUPLICATE MATCH in {t['id']}: {l['match']}"
            match_check.add(l['match'])
    assert len(all_keys) == len(set(all_keys)), "DUPLICATE PROP FOUND!"

    return tickets


def generate_ticket_js(tickets):
    """PRINCIPIO 2: Cada billete lleva publishedAt — lo publicado no se modifica."""
    if not tickets:
        return "const TICKETS = [];"
    published_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    lines = ["const TICKETS = ["]
    for ticket in tickets:
        legs_js = []
        for leg in ticket['legs']:
            # Convert link to Spanish version
            leg_link = leg.get('link', '').replace('/en/', '/es/')
            edge_val = leg.get('edge')
            edge_js = f"{edge_val}" if edge_val is not None else "null"
            legs_js.append(
                f"    {{player:'{_esc(leg['player'])}', "
                f"prop:'{_esc(leg['prop'])}', "
                f"match:'{_esc(leg['match'])}', "
                f"odd:{leg['odd']}, sport:'{leg['sport']}', "
                f"team:'{_esc(leg['team'])}', date:'{leg.get('date', '')}', "
                f"logo:'{_esc(leg.get('logo', ''))}', "
                f"edge:{edge_js}, "
                f"link:'{_esc(leg_link)}'}}"
            )
        sport_counts = {}
        for leg in ticket['legs']:
            sport_counts[leg['sport']] = sport_counts.get(leg['sport'], 0) + 1
        primary_sport = max(sport_counts, key=sport_counts.get)
        ms = ticket.get('model_score')
        ms_js = f"{ms}" if ms is not None else "null"
        ae = ticket.get('avg_edge')
        ae_js = f"{ae}" if ae is not None else "null"
        lines.append(
            f"  {{ id:'{ticket['id']}', tier:'{ticket['tier']}', "
            f"sport:'{primary_sport}', title:'{_esc(ticket['title'])}', "
            f"confidence:{ticket['confidence']}, totalOdds:{ticket['total_odds']}, "
            f"modelScore:{ms_js}, avgEdge:{ae_js}, "
            f"publishedAt:'{published_at}', "
            f"couponCode:'{_esc(ticket.get('coupon_code', ''))}', legs:[\n" +
            ",\n".join(legs_js) +
            "\n  ]},"
        )
    lines.append("];")
    return "\n".join(lines)


def generate_results_js(tickets):
    # In live mode, no resolved results yet
    return "const LEG_RESULTS = {};"


def update_html(tickets_js, results_js, filepath):
    content = filepath.read_text(encoding='utf-8')
    pattern = r'const TICKETS = \[[\s\S]*?\];'
    if re.search(pattern, content):
        content = re.sub(pattern, tickets_js, content, count=1)
    pattern2 = r'const LEG_RESULTS = \{[^}]*\};'
    if re.search(pattern2, content):
        content = re.sub(pattern2, results_js, content, count=1)
    filepath.write_text(content, encoding='utf-8')
    print(f"  ✅ {filepath.name} updated")


def main():
    print("🚀 MasterProps LIVE Generator v5 — Weekend Edition")
    print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    # 1. Get token
    print("🔑 Authenticating with DBbet API...")
    token = get_token()
    print("✅ Token obtained")

    # 2. Fetch events
    print("📡 Fetching events with odds...")
    data = fetch_events(token)
    event_count = data.get('count', 0)
    print(f"✅ {event_count} events loaded")

    # 2b. Initialize Market Intelligence (sharp odds + team stats)
    intel = None
    if HAS_INTEL:
        odds_key = os.environ.get('ODDS_API_KEY', '')
        fb_key = os.environ.get('FOOTBALL_API_KEY', '')
        if odds_key or fb_key:
            print("\n📈 Initializing Market Intelligence...")
            intel = MarketIntel(odds_api_key=odds_key, football_api_key=fb_key)

            # Fetch sharp odds
            intel.fetch_sharp_odds()

            # Extract football match pairs for team stats
            football_pairs = []
            for event in data.get('items', []):
                if event.get('sportId') == 1:  # Football
                    t1 = event.get('opponent1NameLocalization', '')
                    t2 = event.get('opponent2NameLocalization', '')
                    if t1 and t2:
                        football_pairs.append((t1, t2))
            if football_pairs:
                # Limit to avoid burning too many API calls
                intel.fetch_team_stats(football_pairs[:50])

            intel.fetch_all()  # Summary

            # Attach intel to build_prop_pool so it can access sharp odds
            build_prop_pool._intel = intel
        else:
            print("\n⚠️  ODDS_API_KEY / FOOTBALL_API_KEY not set — running without market intelligence")
            print("   Set env vars to enable sharp edge calculation and team stats")
    else:
        build_prop_pool._intel = None

    # 3. Build prop pools — Saturday, Sunday, Combined
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    # Dynamic: HOY (today) and MAÑANA (tomorrow) in Argentina TZ (UTC-3)
    ar_offset = timedelta(hours=-3)
    now_ar = now + ar_offset
    today_ar = now_ar.date()
    tomorrow_ar = today_ar + timedelta(days=1)
    # Convert Argentina day boundaries back to UTC timestamps
    sat_start = (datetime.combine(today_ar, datetime.min.time(), tzinfo=timezone.utc) - ar_offset).timestamp()
    sat_end = (datetime.combine(today_ar, datetime.max.time(), tzinfo=timezone.utc) - ar_offset).timestamp()
    sun_start = (datetime.combine(tomorrow_ar, datetime.min.time(), tzinfo=timezone.utc) - ar_offset).timestamp()
    sun_end = (datetime.combine(tomorrow_ar, datetime.max.time(), tzinfo=timezone.utc) - ar_offset).timestamp()

    print("\n🎯 Building prop pools...")

    print("  📅 HOY:")
    pool_sat = build_prop_pool(data, start_ts_min=sat_start, start_ts_max=sat_end, day_label='sat')
    print(f"     ✅ {len(pool_sat)} props")

    print("  📅 MAÑANA:")
    pool_sun = build_prop_pool(data, start_ts_min=sun_start, start_ts_max=sun_end, day_label='sun')
    print(f"     ✅ {len(pool_sun)} props")

    print("  📅 HOY+MAÑANA (combinado):")
    pool_weekend = build_prop_pool(data, start_ts_min=sat_start, start_ts_max=sun_end, day_label='weekend')
    print(f"     ✅ {len(pool_weekend)} props")

    # 3b. Quality filter — remove picks with confirmed negative sharp edge
    if intel and intel.sharp_odds:
        for pool_name, pool in [('HOY', pool_sat), ('MAÑANA', pool_sun), ('COMBINADO', pool_weekend)]:
            before = len(pool)
            # Remove picks where sharp bookmakers say edge is clearly negative (< -5%)
            filtered = [p for p in pool if p.get('sharp_edge') is None or p['sharp_edge'] > -0.05]
            removed = before - len(filtered)
            if removed > 0:
                pool.clear()
                pool.extend(filtered)
                print(f"  🚫 {pool_name}: {removed} picks descartados (edge sharp < -5%)")

        # Stats
        for pool_name, pool in [('HOY', pool_sat), ('MAÑANA', pool_sun)]:
            sharp_count = sum(1 for p in pool if p.get('sharp_edge') is not None)
            pos_count = sum(1 for p in pool if (p.get('sharp_edge') or 0) > 0)
            print(f"  📊 {pool_name}: {sharp_count} picks con datos sharp, {pos_count} con edge positivo")

    # 4. Generate tickets for each group
    all_tickets = []

    # Saturday tickets (sharks, hunters, whales)
    if pool_sat:
        print("\n🎰 === HOY — Building tickets ===")
        sat_tickets = build_tickets(pool_sat)
        # Re-prefix IDs to avoid collisions: SAT-M1, SAT-W1, etc.
        for t in sat_tickets:
            t['id'] = f"SAT-{t['id']}"
            t['title'] = f"Hoy · {t['title']}"
        all_tickets.extend(sat_tickets)
        print(f"  ✅ {len(sat_tickets)} tickets hoy")
    else:
        print("\n⚠️  No props for HOY")

    # Sunday tickets (sharks, hunters, whales)
    if pool_sun:
        print("\n🎰 === MAÑANA — Building tickets ===")
        sun_tickets = build_tickets(pool_sun)
        for t in sun_tickets:
            t['id'] = f"SUN-{t['id']}"
            t['title'] = f"Mañ · {t['title']}"
        all_tickets.extend(sun_tickets)
        print(f"  ✅ {len(sun_tickets)} tickets mañana")
    else:
        print("\n⚠️  No props for MAÑANA")

    # Combined weekend — Megalodones and Whales ONLY (x100+)
    if pool_weekend:
        print("\n🎰 === HOY+MAÑANA — Megalodones & Whales ===")
        weekend_tickets = build_tickets(pool_weekend)
        # Only keep megalodones and whales from the combined pool
        mega_whale = [t for t in weekend_tickets if t['tier'] in ('megalodon', 'whale')]
        for t in mega_whale:
            t['id'] = f"WKD-{t['id']}"
            t['title'] = f"Wkd · {t['title']}"
        all_tickets.extend(mega_whale)
        print(f"  ✅ {len(mega_whale)} megalodones/whales 48h")
    else:
        print("\n⚠️  No props for HOY+MAÑANA")

    tickets = all_tickets

    # Sort: megalodones first, then whales, sharks, hunters
    tier_order = {'megalodon': 0, 'whale': 1, 'shark': 2, 'hunter': 3, 'confiable': 4, 'segura': 5}
    tickets.sort(key=lambda t: (tier_order.get(t['tier'], 99), -t['total_odds']))

    print(f"\n📊 RESUMEN TOTAL: {len(tickets)} tickets")
    for t in tickets:
        sports_in = set(l['sport'] for l in t['legs'])
        print(f"  {t['id']:12s} [{t['tier'].upper():10s}] x{t['total_odds']:>8.1f} | "
              f"{len(t['legs'])} legs | {', '.join(sports_in)} | conf: {t['confidence']}/6")
        for l in t['legs']:
            print(f"      x{l['odd']:.2f} {l['player'][:20]:20s} {l['prop'][:40]}")

    # 5. Generate tickets_data.json for coupon code generation
    tickets_data = []
    for t in tickets:
        events = []
        for leg in t['legs']:
            events.append({
                'GameId': leg.get('game_id', 0),
                'Type': leg.get('type_id', 0),
                'Coef': leg['odd'],
                'Param': leg.get('param', 0),
                'PlayerId': leg.get('player_id', 0),
            })
        tickets_data.append({
            'ticket_id': t['id'],
            'events': events,
        })

    TICKETS_DATA_FILE = BASE_DIR / 'tickets_data.json'
    TICKETS_DATA_FILE.write_text(json.dumps(tickets_data, indent=2), encoding='utf-8')
    print(f"\n📋 tickets_data.json saved ({len(tickets_data)} tickets)")

    # 5b. Generate coupon codes via Playwright (if available)
    coupons = {}
    try:
        from generate_coupons import generate_coupon_codes
        print("\n🎫 Generating coupon codes via Playwright...")
        coupons = generate_coupon_codes(tickets_data)
        print(f"✅ Generated {len(coupons)} coupon codes")
    except ImportError:
        print("\n⚠️  Playwright not available — skipping coupon generation")
        print("   Run: pip install playwright && playwright install chromium")
        print("   Then: python generate_coupons.py")
        if COUPONS_FILE.exists():
            try:
                coupons = json.loads(COUPONS_FILE.read_text(encoding='utf-8'))
                print(f"   📋 Loaded {len(coupons)} existing coupon codes")
            except Exception:
                pass
    except Exception as e:
        print(f"\n⚠️  Coupon generation failed: {e}")
        if COUPONS_FILE.exists():
            try:
                coupons = json.loads(COUPONS_FILE.read_text(encoding='utf-8'))
                print(f"   📋 Loaded {len(coupons)} existing coupon codes")
            except Exception:
                pass

    for t in tickets:
        t['coupon_code'] = coupons.get(t['id'], '')

    # 6. Verify zero duplicates within each group
    # Note: props CAN repeat across groups (sat vs sun vs weekend) — that's expected
    # But within each group, no duplicates allowed
    all_sels = [f"{l['player']}|{l['prop']}" for t in tickets for l in t['legs']]
    unique_sels = len(set(all_sels))
    print(f"\n🔍 Total: {len(all_sels)} selecciones, {unique_sels} únicas")
    # Duplicates across groups (SAT vs WKD) are OK since they share the same pool
    print("✅ Cross-group overlap is expected (weekend reuses sat+sun props)")

    # 7. Copy template → index.html, then inject data
    tickets_js = generate_ticket_js(tickets)
    results_js = generate_results_js(tickets)

    print("\n📝 Updating HTML files...")
    import shutil
    shutil.copy2(TEMPLATE_FILE, OUTPUT_FILE)
    print(f"  📋 template.html → index.html")
    update_html(tickets_js, results_js, OUTPUT_FILE)
    update_html(tickets_js, results_js, TEMPLATE_FILE)

    # 8. Update coupons.json template
    coupon_template = {t['id']: coupons.get(t['id'], '') for t in tickets}
    COUPONS_FILE.write_text(json.dumps(coupon_template, indent=2), encoding='utf-8')
    assigned = sum(1 for v in coupon_template.values() if v)
    print(f"🎫 coupons.json saved ({assigned}/{len(coupon_template)} codes assigned)")

    print("\n🎉 DONE — Weekend tickets generated from DBbet API!")


if __name__ == '__main__':
    main()
