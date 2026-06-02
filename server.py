import json
import time
import urllib.request
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

API_KEY = '824faa7348564e16a5d4301ca43897a9'
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
            return {'prob1': 40, 'probX': 28, 'prob2': 32, 'btts': 55, 'over25': 50, 'homeGoalsAvg': 1.5, 'awayGoalsAvg': 1.2}

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

        if parsed.path == '/api/matches':
            league = params.get('league', [None])[0]
            date = params.get('date', [None])[0]
            if league and date:
                url = f"{API_BASE}/competitions/{league}/matches?dateFrom={date}&dateTo={date}"
                ck = f"matches_{league}_{date}"
            elif league:
                url = f"{API_BASE}/competitions/{league}/matches"
                ck = f"matches_{league}"
            elif date:
                url = f"{API_BASE}/matches?dateFrom={date}&dateTo={date}"
                ck = f"matches_{date}"
            else:
                url = f"{API_BASE}/matches"
                ck = "matches_all"
            try:
                data = self.fetch_api(url, cache_key=ck, ttl=120)
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

        else:
            self.send_json({'error': 'not found'}, 404)

print("Serveur EMASCORE demarré sur http://localhost:8080")
HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()