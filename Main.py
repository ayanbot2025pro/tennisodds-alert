import requests
import time
import statistics
import os
from datetime import datetime
from flask import Flask
from threading import Thread

# ═══════════════════════════════════════════
# 1. RENDER KI FIXING (Nakli Website)
# ═══════════════════════════════════════════
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ═══════════════════════════════════════════
# 2. SETTINGS (Golden Config)
# ═══════════════════════════════════════════
API_KEY = os.environ.get('ODDS_API_KEY')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SPORTS = ['table_tennis', 'tennis_atp', 'tennis_wta', 'esports_csgo', 'esports_dota2']
MIN_ODDS, MAX_ODDS, MAX_GAP, MIN_BOOKMAKERS, MAX_VIG = 2.00, 2.80, 0.70, 4, 0.08

BLACKLIST = ['itf', 'futures', 'm15', 'm25', 'challenger', 'friendly', 'exhibition', 'setka', 'tt-cup', 'simulated']

sent_alerts = set()

# ═══════════════════════════════════════════
# 3. FUNCTIONS
# ═══════════════════════════════════════════
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except: pass

def check_odds():
    for sport in SPORTS:
        try:
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
            params = {'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200: continue
            
            for match in r.json():
                if match['id'] in sent_alerts: continue
                bookmakers = match.get('bookmakers', [])
                if len(bookmakers) < MIN_BOOKMAKERS: continue

                h_odds, a_odds = [], []
                for b in bookmakers:
                    try:
                        o = b['markets'][0]['outcomes']
                        for x in o:
                            if x['name'] == match['home_team']: h_odds.append(x['price'])
                            elif x['name'] == match['away_team']: a_odds.append(x['price'])
                    except: continue
                
                if len(h_odds) < MIN_BOOKMAKERS: continue
                avg_h, avg_a = statistics.mean(h_odds), statistics.mean(a_odds)
                gap = abs(avg_h - avg_a)

                if (MIN_ODDS <= avg_h <= MAX_ODDS) and (MIN_ODDS <= avg_a <= MAX_ODDS) and gap <= MAX_GAP:
                    msg = f"🚀 <b>JACKPOT ALERT!</b>\n\n🏆 {sport.upper()}\n⚔️ {match['home_team']} vs {match['away_team']}\n⚖️ Odds: {avg_h:.2f} | {avg_a:.2f}\n📊 Gap: {gap:.2f}"
                    send_telegram(msg)
                    sent_alerts.add(match['id'])
        except: continue

# ═══════════════════════════════════════════
# 4. MAIN LOOP
# ═══════════════════════════════════════════
if __name__ == "__main__":
    # Website start karo background mein
    Thread(target=run_web_server).start()
    
    send_telegram("🤖 <b>BOT RESTARTED + PORT FIX DONE</b>\nAb error nahi aayega!")
    
    last_heartbeat = time.time()
    while True:
        check_odds()
        # HEARTBEAT (Har 1 ghante mein)
        if time.time() - last_heartbeat > 3600:
            send_telegram("🔔 <b>Boss, Main Jinda Hoon!</b>")
            last_heartbeat = time.time()
        time.sleep(600)
