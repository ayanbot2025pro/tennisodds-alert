import requests
import time
import os
import statistics
from datetime import datetime

# --- CONFIGURATION (Replit Secrets mein dalein) ---
API_KEY = os.environ.get('ODDS_API_KEY', 'd403989800ad1d506185151b1e5f6e23')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7578859102:AAHvi1Bqii1LHRWWsI_HVNeqD65i8Uv2YaU')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '1518433503')

# --- 1. SPORTS SELECTION (Fair & Fast) ---
SPORTS = ['table_tennis_gtt', 'tennis_atp', 'tennis_wta', 'esports_csgo', 'esports_dota2', 'esports_lol']

# --- 2. THE 7 GOLDEN FILTERS ---
MIN_BOOKMAKERS = 4       # Factor 1: Liquidity (4+ bookies means match is real)
SWING_MIN_ODDS = 1.80    # Factor 2: Swing Zone Start
SWING_MAX_ODDS = 2.40    # Factor 2: Swing Zone End
MAX_DIFF = 0.35          # Factor 3: Equal Fight (Fark kam hona chahiye)
SCAN_INTERVAL = 900      # 15 min wait
HEARTBEAT_INTERVAL = 3600 # 1 hour (Alive msg)

# --- 3. ANTI-FIXING BLACKLIST (Factor 4: Kachra Hatao) ---
# In keywords wale tournaments ko bot dekhega bhi nahi
BLACKLIST = ['itf', 'futures', 'm15', 'm25', 'qualifier', 'exhibition', 'friendly', 'unknown']

sent_alerts = [] 
last_heartbeat = time.time()

def is_fair_tournament(name):
    t_name = name.lower()
    return not any(bad in t_name for bad in BLACKLIST)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except: pass

def check_odds():
    print(f"🔍 Scan: {datetime.now().strftime('%H:%M:%S')}")
    for sport in SPORTS:
        try:
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
            params = {'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200: continue
            
            for match in r.json():
                m_id = match['id']
                if m_id in sent_alerts: continue

                # ANTI-FIXING: Match level check
                if not is_fair_tournament(match.get('sport_title', '')): continue

                # LIQUIDITY: 4+ Bookies check
                if len(match.get('bookmakers', [])) < MIN_BOOKMAKERS: continue

                h_odds, a_odds = [], []
                for b in match['bookmakers']:
                    try:
                        o = b['markets'][0]['outcomes']
                        if len(o) == 2:
                            h_odds.append(o[0]['price']); a_odds.append(o[1]['price'])
                    except: continue
                
                if not h_odds: continue
                avg_h, avg_a = statistics.mean(h_odds), statistics.mean(a_odds)

                # SWING LOGIC: 50-50 Match
                if (SWING_MIN_ODDS <= avg_h <= SWING_MAX_ODDS) and (SWING_MIN_ODDS <= avg_a <= SWING_MAX_ODDS):
                    if abs(avg_h - avg_a) <= MAX_DIFF:
                        msg = (f"💎 <b>DIAMOND MATCH FOUND!</b> 💎\n\n"
                               f"🏆 Sport: {sport.upper()}\n"
                               f"⚔️ {match['home_team']} vs {match['away_team']}\n\n"
                               f"⚖️ <b>Market Avg:</b> {avg_h:.2f} vs {avg_a:.2f}\n"
                               f"🛡️ <b>Safety:</b> {len(match['bookmakers'])} Bookies (Verified)\n\n"
                               f"✅ Swing pakka aayega. Ye match safe hai!")
                        send_telegram(msg)
                        sent_alerts.append(m_id)
        except: continue

if __name__ == "__main__":
    send_telegram("🤖 <b>BOT LIVE:</b> Anti-Fixing Mode ON. 🚀")
    while True:
        check_odds()
        if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
            send_telegram("🔔 <b>Boss, main Jinda hun!</b>\nScanning proper chal rahi hai. 😎")
            last_heartbeat = time.time()
        time.sleep(SCAN_INTERVAL)
