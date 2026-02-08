import requests
import time
import os
import statistics
from datetime import datetime
from flask import Flask
from threading import Thread

# --- 1. DUMMY WEBSITE (Render ko Free rakhne ke liye) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "I am alive! Boss Bot is running."

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_server():
    t = Thread(target=run_web_server)
    t.start()

# --- 2. SETTINGS (SECRETS) ---
API_KEY = os.environ.get('ODDS_API_KEY')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# --- CONFIGURATION ---
MIN_BOOKMAKERS = 4
SWING_MIN_ODDS = 1.80
SWING_MAX_ODDS = 2.40
SCAN_INTERVAL = 900       # 15 Minutes
HEARTBEAT_INTERVAL = 3600 # 1 Hour

SPORTS = ['table_tennis_gtt', 'tennis_atp', 'tennis_wta', 'esports_csgo', 'esports_dota2', 'esports_lol']
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
    print(f"Scanning... {datetime.now()}")
    for sport in SPORTS:
        try:
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
            params = {'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200: continue
            
            for match in r.json():
                m_id = match['id']
                if m_id in sent_alerts: continue
                if not is_fair_tournament(match.get('sport_title', '')): continue
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

                if (SWING_MIN_ODDS <= avg_h <= SWING_MAX_ODDS) and (SWING_MIN_ODDS <= avg_a <= SWING_MAX_ODDS):
                    if abs(avg_h - avg_a) <= 0.35:
                        msg = (f"💎 <b>FREE MODE ALERT!</b> 💎\n\n"
                               f"🏆 {sport.upper()}\n⚔️ {match['home_team']} vs {match['away_team']}\n"
                               f"⚖️ Avg Odds: {avg_h:.2f} vs {avg_a:.2f}\n"
                               f"✅ Verified: {len(match['bookmakers'])} Bookies")
                        send_telegram(msg)
                        sent_alerts.append(m_id)
        except: continue

if __name__ == "__main__":
    # Pehle nakli server chalao
    start_server()
    
    # Fir asli bot chalao
    send_telegram("🤖 <b>BOT STARTED (FREE VERSION)</b>\nPaise bach gaye Boss! 😎")
    while True:
        check_odds()
        if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
            send_telegram("🔔 <b>Boss, main Jinda hun!</b>")
            last_heartbeat = time.time()
        time.sleep(SCAN_INTERVAL)
