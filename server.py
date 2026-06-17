import json
import time
import urllib.request
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

API_KEY = '824faa7348564e16a5d4301ca43897a9'
API_FOOTBALL_KEY = 'e49778fd035bade96e4537dd0a4a2032'
API_FOOTBALL_BASE = 'https://v3.football.api-sports.io'

FIFA_RANKING = {
    773: 1,   # France
    760: 2,   # Spain
    762: 3,   # Argentina
    770: 4,   # England
    765: 5,   # Portugal
    764: 6,   # Brazil
    8601: 7,  # Netherlands
    815: 8,   # Morocco
    805: 9,   # Belgium
    759: 10,  # Germany
    799: 11,  # Croatia
    818: 13,  # Colombia
    804: 14,  # Senegal
    769: 15,  # Mexico
    771: 16,  # USA
    758: 17,  # Uruguay
    766: 18,  # Japan
    788: 19,  # Switzerland
    792: 24,  # Sweden
    772: 22,  # South Korea
    779: 23,  # Australia
    803: 28,  # Turkey
    840: 21,  # Iran
    791: 30,  # Ecuador
    816: 33,  # Austria
    802: 40,  # Tunisia
    778: 35,  # Algeria
    825: 34,  # Egypt
    761: 50,  # Paraguay
    8049: 85, # Jordan
    801: 56,  # Saudi Arabia
    8872: 25, # Norway
    8062: 65, # Iraq
    1935: 50, # Ivory Coast
    828: 47,  # Canada
    8030: 55, # Qatar
    1060: 60, # Bosnia
    836: 75,  # Haiti
    8873: 39, # Scotland
    9460: 120,# Curacao
    774: 63,  # South Africa
    798: 37,  # Czechia
    783: 102, # New Zealand
    1930: 72, # Cape Verde
    763: 52,  # Ghana
    1836: 78, # Panama
    8070: 68, # Uzbekistan
    1934: 90, # Congo DR
    762: 3,   # Argentina
}

def fifa_prob(home_id, away_id):
    home_rank = FIFA_RANKING.get(home_id, 80)
    away_rank = FIFA_RANKING.get(away_id, 80)
    home_pts = 1000 / home_rank
    away_pts = 1000 / away_rank
    home_adv = home_pts * 1.1
    total = home_adv + away_pts + (home_pts + away_pts) * 0.15
    prob1 = round((home_adv / total) * 100)
    prob2 = round((away_pts / total) * 100)
    probX = 100 - prob1 - prob2
    prob1 = max(15, min(78, prob1))
    prob2 = max(8, min(70, prob2))
    probX = max(12, min(38, 100 - prob1 - prob2))
    avg_goals = 2.5
    avg_goals = 2.5
    hG = round(avg_goals * (home_adv / (home_adv + away_pts)), 1)
    aG = round(avg_goals * (away_pts / (home_adv + away_pts)), 1)
    import math
    p_home_scores = 1 - math.exp(-hG)
    p_away_scores = 1 - math.exp(-aG)
    btts = min(80, max(25, round(p_home_scores * p_away_scores * 100)))
    avg_goals = hG + aG
    over25 = min(75, max(20, round((1 - math.exp(-avg_goals) * (1 + avg_goals + avg_goals**2/2)) * 100)))
    rank_diff = abs(home_rank - away_rank)
    if rank_diff < 10:
        probX = max(20, probX)
    elif rank_diff < 30:
        probX = max(17, probX)
    else:
        probX = max(12, probX)
    prob1 = min(78, 100 - prob2 - probX)
    best = max([('1', prob1), ('X', probX), ('2', prob2)], key=lambda x: x[1])
    return {
        'prob1': prob1, 'probX': probX, 'prob2': prob2,
        'btts': btts, 'over25': over25,
        'homeGoalsAvg': hG, 'awayGoalsAvg': aG,
        'bestMarket': best[0], 'bestProb': best[1], 'highConfidence': best[1] >= 55
    }


def fetch_api_football(endpoint, params={}):
    import urllib.parse
    url = API_FOOTBALL_BASE + endpoint
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header('x-apisports-key', API_FOOTBALL_KEY)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"API-Football error: {e}")
        return None

API_BASE = 'https://api.football-data.org/v4'
PORT = 8080
CACHE = {}
CACHE_TIME = {}

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"{format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def fetch_api(self, url, cache_key=None, ttl=300):
        if cache_key and cache_key in CACHE and time.time() - CACHE_TIME.get(cache_key, 0) < ttl:
            return CACHE[cache_key]
        req = urllib.request.Request(url)
        req.add_header('X-Auth-Token', API_KEY)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if cache_key:
            CACHE[cache_key] = data
            CACHE_TIME[cache_key] = time.time()
        return data

    def calc_probs(self, home_id, away_id, league):
        if league == "WC" and (home_id in FIFA_RANKING or away_id in FIFA_RANKING):
            return fifa_prob(home_id, away_id)
        try:
            cache_key = f"{league}_finished"
            data = self.fetch_api(
                f"{API_BASE}/competitions/{league}/matches?status=FINISHED",
                cache_key=cache_key, ttl=300
            )
            matches = data.get('matches', [])
            home_wins = home_draws = home_losses = 0
            away_wins = away_draws = away_losses = 0
            home_goals_for = home_goals_against = 0
            away_goals_for = away_goals_against = 0
            for m in matches[-30:]:
                ht = m['homeTeam']['id']
                at = m['awayTeam']['id']
                hw = m['score']['fullTime']['home']
                aw = m['score']['fullTime']['away']
                if hw is None or aw is None:
                    continue
                if ht == home_id:
                    home_goals_for += hw
                    home_goals_against += aw
                    if hw > aw: home_wins += 1
                    elif hw == aw: home_draws += 1
                    else: home_losses += 1
                if at == away_id:
                    away_goals_for += aw
                    away_goals_against += hw
                    if aw > hw: away_wins += 1
                    elif aw == hw: away_draws += 1
                    else: away_losses += 1
            home_total = max(home_wins + home_draws + home_losses, 1)
            away_total = max(away_wins + away_draws + away_losses, 1)
            # Force avec ponderation buts
            home_strength = (home_wins * 3 + home_draws * 1 + (home_goals_for - home_goals_against) * 0.5 + 2) / home_total
            away_strength = (away_wins * 3 + away_draws * 1 + (away_goals_for - away_goals_against) * 0.5 + 1) / away_total
            # Avantage domicile
            home_strength *= 1.2
            total = home_strength + away_strength + 1.2
            prob1 = min(80, max(25, round((home_strength / total) * 100)))
            probX = min(40, max(15, round((1.2 / total) * 100)))
            prob2 = max(5, 100 - prob1 - probX)
            prob1 = 100 - prob2 - probX
            all_goals = home_goals_for + away_goals_for
            all_games = home_total + away_total
            avg_goals = all_goals / max(all_games, 1)
            hG = home_goals_for / home_total
            aG = away_goals_for / away_total
            btts = min(80, max(30, round((hG * 0.7 + aG * 0.7) * 45 + 10)))
            over25 = min(78, max(25, round(avg_goals * 18 + 15)))
            win_market = max([('1', prob1), ('X', probX), ('2', prob2)], key=lambda x: x[1])
            best_market = win_market
            high_confidence = best_market[1] >= 55
            return {
                'prob1': prob1, 'probX': probX, 'prob2': prob2,
                'btts': btts, 'over25': over25,
                'homeGoalsAvg': round(home_goals_for / home_total, 1) if home_goals_for > 0 else 1.2,
                'awayGoalsAvg': round(away_goals_for / away_total, 1) if away_goals_for > 0 else 1.0,
                'bestMarket': best_market[0], 'bestProb': best_market[1], 'highConfidence': high_confidence
            }
        except Exception as e:
            print(f"calc_probs error: {e}")
            return fifa_prob(home_id, away_id)

    def find_team_id(self, name, league):
        try:
            cache_key = f"matches_{league}"
            data = self.fetch_api(
                f"{API_BASE}/competitions/{league}/matches",
                cache_key=cache_key, ttl=300
            )
            matches = data.get('matches', [])
            for m in matches:
                ht = m['homeTeam']
                at = m['awayTeam']
                if name.lower() in ht.get('name','').lower() or name.lower() in ht.get('shortName','').lower():
                    return ht['id']
                if name.lower() in at.get('name','').lower() or name.lower() in at.get('shortName','').lower():
                    return at['id']
        except:
            pass
        return 0

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == '/ping':
            self.send_json({"status": "ok"})
        elif parsed.path == '/api/matches':
            league = params.get('league', [None])[0]
            date = params.get('date', [None])[0]
            if league and date:
                from datetime import datetime, timedelta
                date_next = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                url = f"{API_BASE}/competitions/{league}/matches?dateFrom={date}&dateTo={date_next}"
                ck = f"matches_{league}_{date}"
            elif league:
                from datetime import datetime, timedelta
                today = datetime.utcnow().strftime("%Y-%m-%d")
                all_matches = params.get('all', [None])[0]
                if all_matches:
                    url = f"{API_BASE}/competitions/{league}/matches"
                    ck = f"matches_{league}_all"
                    ttl_val = 600
                else:
                    from datetime import datetime, timedelta
                    today = datetime.utcnow().strftime("%Y-%m-%d")
                    date_next = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
                    url = f"{API_BASE}/competitions/{league}/matches?dateFrom={today}&dateTo={date_next}"
                    ck = f"matches_{league}_{today}_v2"
            elif date:
                from datetime import datetime, timedelta
                date_next = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                url = f"{API_BASE}/matches?dateFrom={date}&dateTo={date_next}"
                ck = f"matches_{date}"
            else:
                from datetime import datetime, timedelta
                today = datetime.utcnow().strftime("%Y-%m-%d")
                date_next = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
                url = f"{API_BASE}/matches?dateFrom={today}&dateTo={date_next}"
                ck = f"matches_all_{today}"
            try:
                data = self.fetch_api(url, cache_key=ck, ttl=locals().get("ttl_val", 120))
                self.send_json(data)
            except Exception as e:
                if '403' in str(e):
                    self.send_json({'error': 'plan_required', 'matches': []}, 200)
                else:
                    self.send_json({'error': str(e), 'matches': []}, 200)

        elif parsed.path == '/api/probs':
            home_id = int(params.get('home', [0])[0])
            away_id = int(params.get('away', [0])[0])
            league = params.get('league', ['PL'])[0]
            if home_id == 0:
                home_name = params.get('homeName', [''])[0]
                home_id = self.find_team_id(home_name, league)
            if away_id == 0:
                away_name = params.get('awayName', [''])[0]
                away_id = self.find_team_id(away_name, league)
            probs = self.calc_probs(home_id, away_id, league)
            self.send_json(probs)

        elif parsed.path == '/api/af_fixtures':
            date = params.get('date', [None])[0]
            league = params.get('league', [None])[0]
            if not date:
                from datetime import datetime
                date = datetime.utcnow().strftime('%Y-%m-%d')
            ck = f"af_fixtures_{date}_{league}"
            cached = CACHE.get(ck)
            if cached and time.time() - CACHE_TIME.get(ck, 0) < 300:
                self.send_json(cached)
            else:
                p = {'date': date}
                if league:
                    p['league'] = league
                    p['season'] = '2026'
                data = fetch_api_football('/fixtures', p)
                if data:
                    CACHE[ck] = data
                    CACHE_TIME[ck] = time.time()
                    self.send_json(data)
                else:
                    self.send_json({'error': 'not found'}, 404)
        elif parsed.path == '/api/admin/login':
            import json as json2
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json2.loads(self.rfile.read(length).decode())
                email = body.get('email', '')
                password = body.get('password', '')
                ADMIN_EMAILS = ['emarichard11@gmail.com']
                ADMIN_PASS = 'RITCHJS97'
                if email in ADMIN_EMAILS and password == ADMIN_PASS:
                    self.send_json({'success': True, 'token': 'EMA_ADMIN_' + email})
                else:
                    self.send_json({'success': False, 'error': 'Accès refusé'}, 403)
            except Exception as e:
                self.send_json({'error': str(e)}, 400)
        elif parsed.path == '/api/fixture_stats':
            fixture_id = params.get('id', [None])[0]
            if fixture_id:
                ck = f"fixture_stats_{fixture_id}"
                cached = CACHE.get(ck)
                if cached and time.time() - CACHE_TIME.get(ck, 0) < 300:
                    self.send_json(cached)
                else:
                    data = fetch_api_football('/fixtures/statistics', {'fixture': fixture_id})
                    if data:
                        CACHE[ck] = data
                        CACHE_TIME[ck] = time.time()
                        self.send_json(data)
                    else:
                        self.send_json({'error': 'not found'}, 404)
            else:
                self.send_json({'error': 'missing id'}, 400)
        elif parsed.path == '/api/fixture_odds':
            fixture_id = params.get('id', [None])[0]
            if fixture_id:
                ck = f"fixture_odds_{fixture_id}"
                cached = CACHE.get(ck)
                if cached and time.time() - CACHE_TIME.get(ck, 0) < 300:
                    self.send_json(cached)
                else:
                    data = fetch_api_football('/odds', {'fixture': fixture_id})
                    if data:
                        CACHE[ck] = data
                        CACHE_TIME[ck] = time.time()
                        self.send_json(data)
                    else:
                        self.send_json({'error': 'not found'}, 404)
            else:
                self.send_json({'error': 'missing id'}, 400)
            self.send_json({'error': 'not found'}, 404)

print("Serveur EMASCORE demarré sur http://localhost:8080")
HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()