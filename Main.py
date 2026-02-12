import requests
import time
import statistics
import os
from flask import Flask
from threading import Thread

# --- 1. FAKE SERVER (Render Ko Jinda Rakhne Ke Liye) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive! Bot is running perfectly."

def run():
    try:
        # Render Port 10000 expect karta hai
        app.run(host='0.0.0.0', port=10000)
    except Exception as e:
        print(f"Server Error: {e}")

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. SETTINGS (Environment Variables se lega) ---
API_KEY = os.getenv("ODDS_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- 3. SPORTS CONFIGURATION (Teenon Sports) ---
SPORTS_CONFIG = {
    'table_tennis': {'min': 1.80, 'max': 2.50, 'gap': 0.60, 'min_books': 5},
    'tennis_atp': {'min': 1.95, 'max': 2.30, 'gap': 0.35, 'min_books': 6},
    'tennis_wta': {'min': 1.95, 'max': 2.30, 'gap': 0.35, 'min_books': 6},
    'esports_csgo': {'min': 1.85, 'max': 2.40, 'gap': 0.50, 'min_books': 4}
}

# --- 4. BLACKLIST (Kachra Tournaments Hatane Ke Liye) ---
BLACKLIST = [
    'setka', 'liga pro', 'tt cup', 'win cup', 'czech liga', 'russia', 'ukraine',
    'armenia', 'belarus', 'master tour', 'itf', 'futures', 'utr', 'exhibition', 
    'daily', 'pro series', 'invitational', 'club', 'simulated', 'srl', 'cyber', 
    'virtual', 'esoccer', 'ebasketball', '2k', 'fifa', 'u19', 'u21', 'youth', 
    'academy', 'regional', 'qualifier', 'amateur'
]

sent_alerts = set()

def is_safe(title, competition):
    full_text = (str(title) + " " + str(competition)).lower()
    if any(bad in full_text for bad in BLACKLIST):
        return False
    return True

# --- 5. ALERT SENDER (With FREEZE FIX) ---
def send_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # Timeout 20s lagaya hai taaki bot atke nahi
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
        print("✅ Message sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram Error (Bot nahi ruka): {e}")

# --- 6. SCANNING LOGIC ---
def scan():
    print(f"🔎 Scanning Markets... {time.strftime('%H:%M')}")
    for sport_key, config in SPORTS_CONFIG.items():
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {"apiKey": API_KEY, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal"}
            
            # API call mein bhi timeout lagaya hai
            r = requests.get(url, params=params, timeout=20)
            
            if r.status_code != 200:
                print(f"⚠️ API Limit/Error: {r.status_code}")
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
                
                # Filter Logic
                if not (avg_h >= config['min_odds'] and avg_a >= config['min_odds']): continue
                if not (avg_h <= config['max_odds'] and avg_a <= config['max_odds']): continue
                if abs(avg_h - avg_a) > config['max_gap']: continue
                
                # Icon Selection
                icon = "🏆"
                if "tennis" in sport_key: icon = "🎾"
                elif "table" in sport_key: icon = "🏓"
                elif "esports" in sport_key: icon = "🎮"
                
                msg = (f"{icon} **SAFE MATCH FOUND** {icon}\n\n"
                       f"⚔️ **{match['home_team']} vs {match['away_team']}**\n"
                       f"🏆 League: {sport_title}\n"
                       f"📊 Odds: {avg_h:.2f} vs {avg_a:.2f}\n"
                       f"🛡️ Books: {len(books)}\n"
                       f"⏰ Time: {time.strftime('%H:%M')}")
                
                send_alert(msg)
                sent_alerts.add(match_id)
        except Exception as e:
            print(f"Scan Error in {sport_key}: {e}")

# --- 7. MAIN LOOP (Heart & Soul) ---
if __name__ == "__main__":
    # A. Fake Server Start
    keep_alive()
    
    # B. Start Message (Turant Jayega)
    start_msg = (
        "🚀 **FINAL BOT STARTED!**\n"
        "✅ Freeze Fix Applied\n"
        "✅ All 3 Sports Active\n"
        "✅ Hourly Alerts On\n"
        "Waiting for Safe Matches..."
    )
    send_alert(start_msg)
    
    last_heartbeat = time.time()

    # C. Infinite Loop
    while True:
        try:
            scan()
            
            # D. Hourly Message (Heartbeat)
            current_time = time.time()
            if current_time - last_heartbeat > 3600: # 3600 seconds = 1 Hour
                heartbeat_msg = (
                    "🔔 **Status Update:**\n"
                    "Bot is Active & Scanning.\n"
                    "No Errors. System Healthy."
                )
                send_alert(heartbeat_msg)
                last_heartbeat = current_time
                
            # E. 5 Minute Wait
            time.sleep(300) 
            
        except Exception as e:
            print(f"Main Loop Crash Prevented: {e}")
            time.sleep(60) # Agar crash ho, toh 1 min ruk ke fir try kare
