#!/usr/bin/env python3
"""
MasterProps — Market Intelligence Module
Fetches sharp odds (The Odds API) and team stats (API-Football) to calculate
TRUE edge and confidence for each pick.

Shared module: can be used by both MasterProps and Gambeta.

Usage:
    from market_intelligence import MarketIntel
    intel = MarketIntel(odds_api_key="...", football_api_key="...")
    intel.fetch_all()

    # For each prop from DBbet:
    edge = intel.true_edge(home_team, away_team, market_type, param, dbbet_odds)
    conf = intel.team_confidence(home_team, away_team, sport)
"""

import json
import urllib.request
import urllib.parse
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CACHE_DIR = Path(__file__).parent / '.cache'
CACHE_DIR.mkdir(exist_ok=True)

# ── The Odds API Config ──
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
# Sport keys mapping (The Odds API → our internal)
ODDS_SPORT_MAP = {
    'soccer_argentina_primera_division': 'futbol',
    'soccer_brazil_serie_a': 'futbol',
    'soccer_brazil_serie_b': 'futbol',
    'soccer_chile_primera_division': 'futbol',
    'soccer_colombia_primera_a': 'futbol',
    'soccer_mexico_ligamx': 'futbol',
    'soccer_usa_mls': 'futbol',
    'soccer_epl': 'futbol',
    'soccer_spain_la_liga': 'futbol',
    'soccer_italy_serie_a': 'futbol',
    'soccer_germany_bundesliga': 'futbol',
    'soccer_france_ligue_one': 'futbol',
    'soccer_uefa_champs_league': 'futbol',
    'soccer_uefa_europa_league': 'futbol',
    'soccer_copa_libertadores': 'futbol',
    'soccer_copa_sudamericana': 'futbol',
    'soccer_conmebol_copa_america': 'futbol',
    'soccer_peru_primera_division': 'futbol',
    'soccer_ecuador_primera_a': 'futbol',
    'soccer_uruguay_primera_division': 'futbol',
    'soccer_paraguay_primera_division': 'futbol',
    'soccer_japan_j_league': 'futbol',
    'soccer_korea_kleague1': 'futbol',
    'soccer_turkey_super_league': 'futbol',
    'soccer_portugal_primeira_liga': 'futbol',
    'soccer_netherlands_eredivisie': 'futbol',
    'soccer_belgium_first_div': 'futbol',
    'soccer_scotland_premiership': 'futbol',
    'soccer_league_of_ireland': 'futbol',
    'soccer_fifa_world_cup': 'futbol',
    'basketball_nba': 'nba',
    'baseball_mlb': 'mlb',
    'icehockey_nhl': 'hockey',
    'americanfootball_nfl': 'nfl',
    'mma_mixed_martial_arts': 'mma',
    'tennis_atp_french_open': 'tenis',
    'tennis_wta_french_open': 'tenis',
    'tennis_atp_wimbledon': 'tenis',
    'tennis_atp_us_open': 'tenis',
}

# Sharp bookmakers (the reference for "true" odds)
SHARP_BOOKS = ['pinnacle', 'betfair_ex_eu', 'matchbook']
# Also use market consensus from these for broader coverage
SOFT_BOOKS = ['bet365', 'unibet', 'williamhill', 'marathonbet', '1xbet',
              'betway', 'bwin', 'betsson', 'coolbet']

# ── API-Football Config ──
FOOTBALL_API_BASE = "https://v3.football.api-sports.io"


class MarketIntel:
    """Fetches and caches market data for edge/confidence calculations."""

    def __init__(self, odds_api_key=None, football_api_key=None):
        self.odds_api_key = odds_api_key or os.environ.get('ODDS_API_KEY', '')
        self.football_api_key = football_api_key or os.environ.get('FOOTBALL_API_KEY', '')

        # Data stores
        self.sharp_odds = {}       # key: "home|away|market|param" → {sharp_prob, consensus_prob, books}
        self.team_form = {}        # key: team_name → {wins, draws, losses, goals_for, goals_against, form_str}
        self.team_injuries = {}    # key: team_name → [{player, reason, type}]
        self.h2h = {}             # key: "home|away" → {home_wins, away_wins, draws, avg_goals}
        self.standings = {}        # key: team_name → {rank, points, played, gd}

        self._odds_api_calls = 0
        self._football_api_calls = 0

    # ════════════════════════════════════════════
    # THE ODDS API — Sharp odds for edge calculation
    # ════════════════════════════════════════════

    def _odds_api_get(self, endpoint, params=None):
        """Make a request to The Odds API with caching."""
        if not self.odds_api_key:
            return None

        if params is None:
            params = {}
        params['apiKey'] = self.odds_api_key

        url = f"{ODDS_API_BASE}{endpoint}?{urllib.parse.urlencode(params)}"
        cache_key = url.replace(self.odds_api_key, 'KEY')
        cache_file = CACHE_DIR / f"odds_{hash(cache_key) & 0xFFFFFFFF:08x}.json"

        # Cache for 30 minutes
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < 1800:
                with open(cache_file) as f:
                    return json.load(f)

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                # Save remaining credits from headers
                remaining = resp.headers.get('x-requests-remaining', '?')
                used = resp.headers.get('x-requests-used', '?')
                print(f"   📊 Odds API: {remaining} créditos restantes (usados: {used})")

                cache_file.write_text(json.dumps(data))
                self._odds_api_calls += 1
                return data
        except Exception as e:
            print(f"   ⚠️  Odds API error: {e}")
            return None

    def fetch_sharp_odds(self):
        """Fetch odds from sharp bookmakers for all upcoming events."""
        if not self.odds_api_key:
            print("   ⚠️  No Odds API key — skipping sharp odds")
            return

        print("📊 Fetching sharp odds from The Odds API...")

        # Get list of available sports
        sports_to_fetch = list(ODDS_SPORT_MAP.keys())

        for sport_key in sports_to_fetch:
            data = self._odds_api_get(f"/sports/{sport_key}/odds", {
                'regions': 'eu',
                'markets': 'h2h,totals,spreads',
                'oddsFormat': 'decimal',
                'bookmakers': ','.join(SHARP_BOOKS + SOFT_BOOKS),
            })

            if not data:
                continue

            for event in data:
                home = event.get('home_team', '')
                away = event.get('away_team', '')

                if not home or not away:
                    continue

                for bookmaker in event.get('bookmakers', []):
                    book_key = bookmaker.get('key', '')
                    is_sharp = book_key in SHARP_BOOKS

                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key', '')  # h2h, totals, spreads

                        for outcome in market.get('outcomes', []):
                            name = outcome.get('name', '')
                            price = outcome.get('price', 0)
                            point = outcome.get('point', None)

                            if price <= 1.0:
                                continue

                            # Normalize the lookup key
                            param_str = str(point) if point is not None else ''
                            lookup = f"{_norm(home)}|{_norm(away)}|{market_key}|{name}|{param_str}"

                            if lookup not in self.sharp_odds:
                                self.sharp_odds[lookup] = {
                                    'sharp_prices': [],
                                    'soft_prices': [],
                                    'home': home,
                                    'away': away,
                                    'market': market_key,
                                    'outcome': name,
                                    'param': point,
                                }

                            entry = self.sharp_odds[lookup]
                            if is_sharp:
                                entry['sharp_prices'].append(price)
                            else:
                                entry['soft_prices'].append(price)

        # Calculate consensus probabilities
        for key, entry in self.sharp_odds.items():
            sharp = entry['sharp_prices']
            soft = entry['soft_prices']

            if sharp:
                # Use sharp bookmaker average as the "true" probability
                avg_price = sum(sharp) / len(sharp)
                entry['sharp_prob'] = 1.0 / avg_price
                entry['sharp_price'] = avg_price
            elif soft:
                # Fallback: use soft book consensus (less reliable but better than nothing)
                avg_price = sum(soft) / len(soft)
                # Apply margin correction (~5% overround for soft books)
                entry['sharp_prob'] = min(0.98, (1.0 / avg_price) * 0.95)
                entry['sharp_price'] = avg_price
            else:
                entry['sharp_prob'] = None
                entry['sharp_price'] = None

        n_events = len(set(f"{v['home']}|{v['away']}" for v in self.sharp_odds.values()))
        n_markets = len(self.sharp_odds)
        print(f"   ✅ {n_events} eventos, {n_markets} mercados con odds sharp cargados")

    # ════════════════════════════════════════════
    # API-FOOTBALL — Team stats, form, injuries
    # ════════════════════════════════════════════

    def _football_api_get(self, endpoint, params=None):
        """Make a request to API-Football with caching."""
        if not self.football_api_key:
            return None

        url = f"{FOOTBALL_API_BASE}{endpoint}"
        if params:
            url += '?' + urllib.parse.urlencode(params)

        cache_key = url
        cache_file = CACHE_DIR / f"fb_{hash(cache_key) & 0xFFFFFFFF:08x}.json"

        # Cache for 6 hours (stats don't change that fast)
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < 21600:
                with open(cache_file) as f:
                    return json.load(f)

        try:
            req = urllib.request.Request(url, headers={
                'x-apisports-key': self.football_api_key,
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                remaining = resp.headers.get('x-ratelimit-requests-remaining', '?')
                print(f"   ⚽ Football API: {remaining} requests restantes hoy")

                cache_file.write_text(json.dumps(data))
                self._football_api_calls += 1
                return data
        except Exception as e:
            print(f"   ⚠️  Football API error: {e}")
            return None

    def fetch_team_stats(self, team_pairs):
        """Fetch form, injuries, and h2h for a list of (home, away) pairs.
        Only fetches for football matches to conserve API calls."""
        if not self.football_api_key:
            print("   ⚠️  No Football API key — skipping team stats")
            return

        print(f"⚽ Fetching team stats from API-Football for {len(team_pairs)} matches...")

        # First, get today's fixtures to map team names → fixture IDs
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%d')

        fixtures_today = self._football_api_get('/fixtures', {
            'date': today, 'status': 'NS'  # Not Started
        })
        fixtures_tomorrow = self._football_api_get('/fixtures', {
            'date': tomorrow, 'status': 'NS'
        })

        all_fixtures = []
        for fx_data in [fixtures_today, fixtures_tomorrow]:
            if fx_data and 'response' in fx_data:
                all_fixtures.extend(fx_data['response'])

        print(f"   📅 {len(all_fixtures)} fixtures encontrados para hoy/mañana")

        # Map fixture data
        fixture_map = {}  # "home_norm|away_norm" → fixture_info
        for fx in all_fixtures:
            teams = fx.get('teams', {})
            home_name = teams.get('home', {}).get('name', '')
            away_name = teams.get('away', {}).get('name', '')
            home_id = teams.get('home', {}).get('id', 0)
            away_id = teams.get('away', {}).get('id', 0)
            league_id = fx.get('league', {}).get('id', 0)
            season = fx.get('league', {}).get('season', 2024)
            fixture_id = fx.get('fixture', {}).get('id', 0)

            key = f"{_norm(home_name)}|{_norm(away_name)}"
            fixture_map[key] = {
                'fixture_id': fixture_id,
                'home_id': home_id, 'away_id': away_id,
                'home_name': home_name, 'away_name': away_name,
                'league_id': league_id, 'season': season,
            }

        # For each match we care about, fetch stats
        matched = 0
        for home, away in team_pairs:
            key = f"{_norm(home)}|{_norm(away)}"

            # Try to find in fixtures (fuzzy match)
            fx = fixture_map.get(key)
            if not fx:
                # Try reversed
                fx = fixture_map.get(f"{_norm(away)}|{_norm(home)}")
            if not fx:
                # Fuzzy match
                fx = _fuzzy_find_fixture(home, away, fixture_map)

            if not fx:
                continue

            matched += 1

            # Fetch last 5 matches for each team (form)
            for team_id, team_name in [(fx['home_id'], home), (fx['away_id'], away)]:
                if _norm(team_name) in self.team_form:
                    continue  # Already fetched

                last5 = self._football_api_get('/fixtures', {
                    'team': team_id, 'last': 5
                })

                if last5 and 'response' in last5:
                    form = _parse_form(last5['response'], team_id)
                    self.team_form[_norm(team_name)] = form

            # Fetch injuries for the fixture
            injuries = self._football_api_get('/injuries', {
                'fixture': fx['fixture_id']
            })
            if injuries and 'response' in injuries:
                for inj in injuries['response']:
                    team_name_inj = inj.get('team', {}).get('name', '')
                    player_name = inj.get('player', {}).get('name', '')
                    reason = inj.get('player', {}).get('reason', '')
                    inj_type = inj.get('player', {}).get('type', '')

                    tn = _norm(team_name_inj)
                    if tn not in self.team_injuries:
                        self.team_injuries[tn] = []
                    self.team_injuries[tn].append({
                        'player': player_name,
                        'reason': reason,
                        'type': inj_type,
                    })

            # Fetch H2H
            h2h_data = self._football_api_get('/fixtures/headtohead', {
                'h2h': f"{fx['home_id']}-{fx['away_id']}", 'last': 10
            })
            if h2h_data and 'response' in h2h_data:
                h2h_stats = _parse_h2h(h2h_data['response'], fx['home_id'], fx['away_id'])
                h2h_key = f"{_norm(home)}|{_norm(away)}"
                self.h2h[h2h_key] = h2h_stats

        print(f"   ✅ Stats cargados para {matched}/{len(team_pairs)} partidos")
        print(f"   📋 Forma: {len(self.team_form)} equipos | Lesiones: {len(self.team_injuries)} equipos | H2H: {len(self.h2h)} cruces")

    # ════════════════════════════════════════════
    # EDGE & CONFIDENCE CALCULATIONS
    # ════════════════════════════════════════════

    def true_edge(self, home, away, market_type, outcome_name, param, dbbet_odds):
        """Calculate true edge comparing DBbet odds vs sharp market.

        Returns:
            float or None: edge as fraction (0.05 = 5% edge). None if no sharp data.
        """
        param_str = str(param) if param is not None else ''

        # Try exact match first
        lookup = f"{_norm(home)}|{_norm(away)}|{market_type}|{outcome_name}|{param_str}"
        entry = self.sharp_odds.get(lookup)

        if not entry or entry.get('sharp_prob') is None:
            # Try fuzzy matching
            entry = self._fuzzy_find_odds(home, away, market_type, outcome_name, param_str)

        if not entry or entry.get('sharp_prob') is None:
            return None

        sharp_prob = entry['sharp_prob']
        # Edge = sharp_prob × dbbet_odds - 1
        # Positive = DBbet is paying MORE than the sharp market thinks it should
        edge = (sharp_prob * dbbet_odds) - 1.0
        return round(edge, 4)

    def team_confidence(self, home, away, sport='futbol'):
        """Calculate confidence score (1-6) based on team stats.

        Factors:
        - Team form (last 5 matches)
        - Injuries
        - H2H history

        Returns:
            dict: {score: 1-6, factors: [...reasons...]}
        """
        factors = []
        score_adjustments = 0
        base = 3  # neutral

        if sport != 'futbol':
            return {'score': base, 'factors': ['No stats available for this sport']}

        home_n = _norm(home)
        away_n = _norm(away)

        # 1. Team form (last 5 matches)
        home_form = self.team_form.get(home_n)
        away_form = self.team_form.get(away_n)

        if home_form:
            if home_form['win_pct'] >= 0.7:
                score_adjustments += 1
                factors.append(f"🏠 {home} en gran racha ({home_form['form_str']})")
            elif home_form['win_pct'] <= 0.2:
                score_adjustments -= 1
                factors.append(f"⚠️ {home} en mala racha ({home_form['form_str']})")

            # Goals scored tells us if teams are attacking
            if home_form['avg_gf'] >= 2.0:
                factors.append(f"⚽ {home} promedia {home_form['avg_gf']:.1f} goles/partido")

        if away_form:
            if away_form['win_pct'] >= 0.7:
                score_adjustments += 1
                factors.append(f"✈️ {away} en gran racha ({away_form['form_str']})")
            elif away_form['win_pct'] <= 0.2:
                score_adjustments -= 1
                factors.append(f"⚠️ {away} en mala racha ({away_form['form_str']})")

        # 2. Injuries
        home_injuries = self.team_injuries.get(home_n, [])
        away_injuries = self.team_injuries.get(away_n, [])

        if len(home_injuries) >= 3:
            score_adjustments -= 1
            factors.append(f"🏥 {home} con {len(home_injuries)} lesionados")
        if len(away_injuries) >= 3:
            score_adjustments -= 1
            factors.append(f"🏥 {away} con {len(away_injuries)} lesionados")

        # 3. H2H
        h2h_key = f"{home_n}|{away_n}"
        h2h = self.h2h.get(h2h_key) or self.h2h.get(f"{away_n}|{home_n}")

        if h2h:
            if h2h['total'] >= 3:
                factors.append(f"📊 H2H: {h2h['home_wins']}W-{h2h['draws']}D-{h2h['away_wins']}L en últimos {h2h['total']}")
                if h2h['avg_goals'] >= 3.0:
                    factors.append(f"🔥 H2H promedia {h2h['avg_goals']:.1f} goles")

        final_score = max(1, min(6, base + score_adjustments))

        return {'score': final_score, 'factors': factors}

    def get_match_intel(self, home, away, sport='futbol'):
        """Get a full intelligence report for a match.
        Returns dict with all available data."""
        home_n = _norm(home)
        away_n = _norm(away)

        return {
            'home_form': self.team_form.get(home_n),
            'away_form': self.team_form.get(away_n),
            'home_injuries': self.team_injuries.get(home_n, []),
            'away_injuries': self.team_injuries.get(away_n, []),
            'h2h': self.h2h.get(f"{home_n}|{away_n}") or self.h2h.get(f"{away_n}|{home_n}"),
            'confidence': self.team_confidence(home, away, sport),
        }

    def fetch_all(self, football_pairs=None):
        """Fetch all market intelligence data."""
        self.fetch_sharp_odds()
        if football_pairs:
            self.fetch_team_stats(football_pairs)

        print(f"\n📈 Market Intelligence Summary:")
        print(f"   Odds API calls: {self._odds_api_calls}")
        print(f"   Football API calls: {self._football_api_calls}")
        print(f"   Sharp odds: {len(self.sharp_odds)} markets")
        print(f"   Team form: {len(self.team_form)} teams")
        print(f"   Injuries: {sum(len(v) for v in self.team_injuries.values())} players")
        print(f"   H2H records: {len(self.h2h)} matchups")

    def _fuzzy_find_odds(self, home, away, market, outcome, param_str):
        """Try to fuzzy-match odds entry by team name similarity."""
        home_n = _norm(home)
        away_n = _norm(away)

        best = None
        best_score = 0

        for key, entry in self.sharp_odds.items():
            e_home = _norm(entry.get('home', ''))
            e_away = _norm(entry.get('away', ''))
            e_market = entry.get('market', '')

            # Market must match
            if e_market != market:
                continue

            # Check team name overlap
            score = _name_similarity(home_n, e_home) + _name_similarity(away_n, e_away)
            if score > best_score and score >= 1.0:
                # Also check outcome/param match
                if outcome.lower() in key.lower() or param_str in key:
                    best = entry
                    best_score = score

        return best


# ════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════

def _norm(name):
    """Normalize team name for matching."""
    if not name:
        return ''
    n = name.lower().strip()
    # Remove common suffixes/prefixes
    for rem in ['fc', 'cf', 'sc', 'ac', 'ssc', 'afc', 'bsc', 'fk', 'sk',
                'club', 'deportivo', 'atletico', 'sporting', 'real',
                'de futbol', 'esporte clube', 'futebol e regatas']:
        n = n.replace(rem, '')
    # Remove extra spaces and punctuation
    n = ' '.join(n.split())
    n = n.strip(' .-')
    return n


def _name_similarity(a, b):
    """Simple word-overlap similarity between team names."""
    if not a or not b:
        return 0
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0
    overlap = words_a & words_b
    return len(overlap) / min(len(words_a), len(words_b))


def _fuzzy_find_fixture(home, away, fixture_map):
    """Fuzzy match team names to fixture map."""
    home_n = _norm(home)
    away_n = _norm(away)

    best_key = None
    best_score = 0

    for key, fx in fixture_map.items():
        fx_home = _norm(fx['home_name'])
        fx_away = _norm(fx['away_name'])

        score = _name_similarity(home_n, fx_home) + _name_similarity(away_n, fx_away)
        # Also try reversed
        score_rev = _name_similarity(home_n, fx_away) + _name_similarity(away_n, fx_home)
        score = max(score, score_rev)

        if score > best_score and score >= 1.0:
            best_key = key
            best_score = score

    return fixture_map.get(best_key) if best_key else None


def _parse_form(fixtures, team_id):
    """Parse last N fixtures into form data."""
    wins, draws, losses = 0, 0, 0
    goals_for, goals_against = 0, 0
    form_chars = []

    for fx in fixtures:
        teams = fx.get('teams', {})
        goals = fx.get('goals', {})
        score = fx.get('score', {})

        is_home = teams.get('home', {}).get('id') == team_id

        if is_home:
            gf = goals.get('home', 0) or 0
            ga = goals.get('away', 0) or 0
            won = teams.get('home', {}).get('winner')
        else:
            gf = goals.get('away', 0) or 0
            ga = goals.get('home', 0) or 0
            won = teams.get('away', {}).get('winner')

        goals_for += gf
        goals_against += ga

        if won is True:
            wins += 1
            form_chars.append('W')
        elif won is False:
            losses += 1
            form_chars.append('L')
        else:
            draws += 1
            form_chars.append('D')

    n = len(fixtures) or 1
    return {
        'wins': wins, 'draws': draws, 'losses': losses,
        'goals_for': goals_for, 'goals_against': goals_against,
        'avg_gf': round(goals_for / n, 2),
        'avg_ga': round(goals_against / n, 2),
        'win_pct': round(wins / n, 2),
        'form_str': ''.join(form_chars),  # e.g. "WWDLW"
        'clean_sheets': sum(1 for fx in fixtures
                          if (fx.get('goals', {}).get('away' if fx.get('teams', {}).get('home', {}).get('id') == team_id else 'home', 0) or 0) == 0),
    }


def _parse_h2h(fixtures, home_id, away_id):
    """Parse H2H fixtures."""
    home_wins, away_wins, draws = 0, 0, 0
    total_goals = 0

    for fx in fixtures:
        teams = fx.get('teams', {})
        goals = fx.get('goals', {})

        gh = goals.get('home', 0) or 0
        ga = goals.get('away', 0) or 0
        total_goals += gh + ga

        home_winner = teams.get('home', {}).get('winner')

        fx_home_id = teams.get('home', {}).get('id')

        if home_winner is True:
            if fx_home_id == home_id:
                home_wins += 1
            else:
                away_wins += 1
        elif home_winner is False:
            if fx_home_id == home_id:
                away_wins += 1
            else:
                home_wins += 1
        else:
            draws += 1

    n = len(fixtures) or 1
    return {
        'home_wins': home_wins,
        'away_wins': away_wins,
        'draws': draws,
        'total': len(fixtures),
        'avg_goals': round(total_goals / n, 2),
    }


# ════════════════════════════════════════════
# MARKET TYPE MAPPING (The Odds API → DBbet)
# ════════════════════════════════════════════
# The Odds API markets: h2h (1x2), totals (over/under), spreads (handicap)
# DBbet markets use numeric type IDs

def odds_api_market_from_dbbet(odd_type, param, t1, t2):
    """Map a DBbet market to The Odds API lookup format.
    Returns (market_key, outcome_name, param_str) or None."""

    # 1X2 (moneyline)
    if odd_type in (1, 2, 3):  # home/draw/away
        outcome = t1 if odd_type == 1 else ('Draw' if odd_type == 2 else t2)
        return 'h2h', outcome, ''

    # Over/Under totals
    if odd_type in (9, 10):  # over/under
        ou = 'Over' if odd_type == 9 else 'Under'
        return 'totals', ou, str(param)

    # Handicap/Spread
    if odd_type in (7, 8):  # handicap home/away
        return 'spreads', t1 if odd_type == 7 else t2, str(param)

    return None


if __name__ == '__main__':
    # Quick test
    intel = MarketIntel()
    if intel.odds_api_key:
        intel.fetch_sharp_odds()
        print(f"\nLoaded {len(intel.sharp_odds)} sharp odds entries")
        # Show a few examples
        for i, (k, v) in enumerate(intel.sharp_odds.items()):
            if v.get('sharp_prob') and i < 5:
                print(f"  {v['home']} vs {v['away']} | {v['market']} {v['outcome']} | "
                      f"Sharp: {v['sharp_price']:.2f} (prob {v['sharp_prob']:.1%})")
    else:
        print("Set ODDS_API_KEY and FOOTBALL_API_KEY env vars to test")
