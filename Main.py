import requests
import time
import statistics
import os
from flask import Flask
from threading import Thread

# --- FAKE SERVER ---
app = Flask('')
@app.route('/')
def home():
    return "I am alive!"
def run():
    try: app.run(host='0.0.0.0', port=10000)
    except: pass
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- SETTINGS ---
API_KEY = os.getenv("ODDS_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SPORTS_CONFIG = {
    'table_tennis': {'min': 1.80, 'max': 2.50, 'gap': 0.60, 'min_books': 5},
    'tennis_atp': {'min': 1.95, 'max': 2.30, 'gap': 0.35, 'min_books': 6},
    'tennis_wta': {'min': 1.95, 'max': 2.30, 'gap': 0.35, 'min_books': 6},
    'esports_csgo': {'min': 1.85, 'max': 2.40, 'gap': 0.50, 'min_books': 4}
}

BLACKLIST = ['setka', 'liga pro', 'tt cup', 'itf', 'futures', 'virtual', 'cyber', 'simulated']
sent_alerts = set()

def is_safe(title, competition):
    full_text = (str(title) + " " + str(competition)).lower()
    if any(bad in full_text for bad in BLACKLIST): return False
    return True

# --- DEBUG ALERT FUNCTION (Saboot Dikhayega) ---
def send_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        print(f"📨 Try Sending: {msg[:20]}...") # Log mein likho
        response = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        
        # Agar Telegram ne mana kiya, toh error chhap do
        if response.status_code != 200:
            print(f"❌ TELEGRAM ERROR: {response.text}")
        else:
            print("✅ Message Sent Successfully!")
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")

def scan():
    print(f"🔎 Scanning... (Time: {time.strftime('%H:%M')})")
    for sport_key, config in SPORTS_CONFIG.items():
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {"apiKey": API_KEY, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal"}
            r = requests.get(url, params=params, timeout=10)
            
            # Agar API Key khatam ya Error hai
            if r.status_code != 200:
                print(f"⚠️ API ERROR ({sport_key}): {r.status_code}")
                continue
                
            matches = r.json()
            if not isinstance(matches, list): continue

            for match in matches:
                match_id = match['id']
                if match_id in sent_alerts: continue
                
                sport_title = match.get('sport_title', '')
                if not is_safe(sport_key, sport_title): continue 
                
                books = match.get('bookmakers', [])
                if len(books) < config['min_books']: continue 
                
                h_odds, a_odds = [], []
                for b in books:
                    try:
                        outcomes = b['markets'][0]['outcomes']
                        if outcomes[0]['name'] == match['home_team']:
                            h_odds.append(outcomes[0]['price'])
                            a_odds.append(outcomes[1]['price'])
                        else:
                            h_odds.append(outcomes[1]['price'])
                            a_odds.append(outcomes[0]['price'])
                    except: continue
                
                if not h_odds: continue
                avg_h = statistics.mean(h_odds)
                avg_a = statistics.mean(a_odds)
                
                if not (avg_h >= config['min_odds'] and avg_a >= config['min_odds']): continue
                if not (avg_h <= config['max_odds'] and avg_a <= config['max_odds']): continue
                if abs(avg_h - avg_a) > config['max_gap']: continue
                
                msg = f"🏆 SAFE MATCH: {match['home_team']} vs {match['away_team']}"
                send_alert(msg)
                sent_alerts.add(match_id)
        except Exception as e:
            print(f"Scan Error: {e}")

if __name__ == "__main__":
    keep_alive()
    # Test Message Bhejo
    send_alert("🛠️ **DEBUG MODE ON: Checking Telegram Connection...**")
    
    last_heartbeat = time.time()
    while True:
        try:
            scan()
            if time.time() - last_heartbeat > 3600:
                send_alert("🔔 Heartbeat Check")
                last_heartbeat = time.time()
            time.sleep(300)
        except: time.sleep(60)
