import requests
import time
import os
import threading
import statistics
import csv
from flask import Flask
from datetime import datetime, timedelta

# ═══════════════════════════════════════════
# 1. SETTINGS
# ═══════════════════════════════════════════
API_KEY = os.environ.get("ODDS_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

app = Flask(__name__)

# ═══════════════════════════════════════════
# 2. TRUSTED BOOKIES
# ═══════════════════════════════════════════
TRUSTED_BOOKIES = [
    'pinnacle', 'bet365', 'williamhill', 'betfair_ex_eu', 'betfair_sb_uk',
    'unibet', 'betonlineag', '888sport', 'betway', 'boylesports',
    'ladbrokes', 'bovada'
]

# ═══════════════════════════════════════════
# 3. SPORT CONFIG (Aapki Exact Screenshot Wali Settings)
# ═══════════════════════════════════════════
SPORTS_CONFIG = {
    # Tennis Strict Range (1.90 - 2.30)
    'tennis_atp': {
        'min_odds': 1.90, 'max_odds': 2.30, 
        'max_gap': 0.40,  
        'min_books': 5,
        'desc': "🎾 ATP Tennis",
        'whitelist': ['atp', 'grand slam', 'masters'],
        'blacklist': ['challenger', 'itf']
    },
    'tennis_wta': {
        'min_odds': 1.90, 'max_odds': 2.30, 
        'max_gap': 0.40,
        'min_books': 5,
        'desc': "🎾 WTA Tennis",
        'whitelist': ['wta', 'grand slam'],
        'blacklist': ['itf', '125']
    },
    # Table Tennis Badi Range (1.80 - 2.50) kyunki game tez hai
    'table_tennis': {
        'min_odds': 1.80, 'max_odds': 2.50, 
        'max_gap': 0.70,  
        'min_books': 4,
        'desc': "🏓 Table Tennis",
        'whitelist': ['ittf', 'wtt', 'world championship', 'olympics'],
        'blacklist': ['setka', 'liga pro', 'cup']
    },
    # Esports Medium Range (1.85 - 2.40)
    'esports_csgo': {
        'min_odds': 1.85, 'max_odds': 2.40,
        'max_gap': 0.55,
        'min_books': 4,
        'desc': "🎮 CS:GO",
        'whitelist': ['major', 'iem', 'blast', 'esl'],
        'blacklist': ['academy', 'qualifier']
    }
}

ALERTED_MATCHES = set()

# ═══════════════════════════════════════════
# 4. FUNCTIONS
# ═══════════════════════════════════════════
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def is_safe(sport_key, tournament):
    t_name = (tournament or "").lower()
    rules = SPORTS_CONFIG[sport_key]
    for bad in rules['blacklist']:
        if bad in t_name: return False
    for good in rules['whitelist']:
        if good in t_name: return True
    return False

# ═══════════════════════════════════════════
# 5. ALIVE CHECKER (Har 2 Ghante)
# ═══════════════════════════════════════════
def alive_checker():
    while True:
        # 20k plan hai, to alive message thoda kam bhejenge taaki quota bache
        time.sleep(7200) # 2 Hours
        print("🟢 Bot is still running...")

# ═══════════════════════════════════════════
# 6. MAIN SCANNER (9 Minute Speed)
# ═══════════════════════════════════════════
def scan_market():
    print("🚀 Bot Started: 20k Plan Mode (9 Min Interval)")
    send_telegram("✅ <b>Bot Active: 20k Plan Mode</b>\nSpeed: Every 9 Mins (Month Safe)")
    
    threading.Thread(target=alive_checker, daemon=True).start()

    while True:
        try:
            for sport_key, rules in SPORTS_CONFIG.items():
                response = requests.get(
                    f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds',
                    params={'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'},
                    timeout=15
                )
                
                if response.status_code != 200: continue
                matches = response.json()

                for match in matches:
                    mid = match['id']
                    if mid in ALERTED_MATCHES: continue
                    
                    tournament = match.get('sport_title', '')
                    if not is_safe(sport_key, tournament): continue
                    
                    try:
                        if datetime.strptime(match['commence_time'], "%Y-%m-%dT%H:%M:%SZ") > datetime.utcnow() + timedelta(hours=24):
                            continue
                    except: pass

                    valid_books = [b for b in match['bookmakers'] if b['key'] in TRUSTED_BOOKIES]
                    if len(valid_books) < rules['min_books']: continue

                    h_odds, a_odds = [], []
                    for b in valid_books:
                        try:
                            outcomes = b['markets'][0]['outcomes']
                            p1 = next((o['price'] for o in outcomes if o['name'] == match['home_team']), None)
                            p2 = next((o['price'] for o in outcomes if o['name'] != match['home_team']), None)
                            if p1 and p2: h_odds.append(p1); a_odds.append(p2)
                        except: continue
                    
                    if not h_odds: continue
                    avg_h = statistics.median(h_odds)
                    avg_a = statistics.median(a_odds)
                    gap = abs(avg_h - avg_a)

                    if (rules['min_odds'] <= avg_h <= rules['max_odds'] and 
                        rules['min_odds'] <= avg_a <= rules['max_odds'] and 
                        gap <= rules['max_gap']):
                        
                        msg = (
                            f"🚨 <b>PRE-MATCH ALERT</b>\n\n"
                            f"🏆 {rules['desc']}\n"
                            f"🏟️ {tournament}\n"
                            f"⚔️ <b>{match['home_team']}</b> vs <b>{match['away_team']}</b>\n\n"
                            f"📊 <b>Odds:</b> {avg_h:.2f} vs {avg_a:.2f}\n"
                            f"📉 <b>Gap:</b> {gap:.2f}\n"
                            f"⏰ <b>Start:</b> {match['commence_time'].replace('T', ' ').replace('Z', '')}"
                        )
                        send_telegram(msg)
                        ALERTED_MATCHES.add(mid)

            # 🛑 IMPORTANT: 9 Minutes Sleep (540 Seconds)
            # Ye setting 20,000 requests ko poora 30 din chalayegi.
            print("💤 Waiting 9 mins (Quota Saving)...")
            time.sleep(540)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

# ═══════════════════════════════════════════
# 7. SERVER
# ═══════════════════════════════════════════
threading.Thread(target=scan_market, daemon=True).start()

@app.route('/')
def home(): return "Tennis 2.5 Pro (20k Plan) Active 🟢"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
