import requests
import time
import os
import threading
from flask import Flask

# --- CONFIGURATION (Settings) ---
# Environment Variables se Keys uthayenge (Render me jo save kiye hain)
API_KEY = os.environ.get("ODDS_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Constraints (Aapki shart: Dono side 2.5 se upar odds)
MIN_ODDS = 2.5
SPORTS = [
    "tennis_atp", 
    "tennis_wta", 
    "tennis_challenger", 
    "table_tennis_setka_cup" 
    # Aur sports add kar sakte hain comma lagake
]

app = Flask(__name__)

# --- TELEGRAM FUNCTION ---
def send_telegram_message(message):
    """Telegram par message bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        # timeout=10 isliye lagaya taki agar Telegram slow ho to bot atke nahi
        requests.post(url, json=payload, timeout=10) 
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# --- BOT BRAIN (Scanning Logic) ---
def check_odds():
    """Ye function odds check karega"""
    print("🚀 Bot Started Scanning...") # Logs me dikhega
    send_telegram_message("✅ System Live: Bot is scanning for 2.5+ Odds (Both Sides)")

    while True:
        try:
            print("🔍 Scanning markets...")
            
            # Har Sport ke liye check karna
            for sport in SPORTS:
                # Odds API ko call karna
                response = requests.get(
                    f'https://api.the-odds-api.com/v4/sports/{sport}/odds',
                    params={
                        'api_key': API_KEY,
                        'regions': 'uk,eu', # Bookmakers region
                        'markets': 'h2h',   # Head to Head (Jeet/Haar)
                        'oddsFormat': 'decimal'
                    },
                    timeout=15 
                )

                if response.status_code == 200:
                    matches = response.json()
                    for match in matches:
                        # Sirf live ya upcoming matches
                        
                        # Bookmakers check karna
                        for bookmaker in match.get('bookmakers', []):
                            markets = bookmaker.get('markets', [])
                            if not markets: continue
                            
                            outcomes = markets[0].get('outcomes', [])
                            if len(outcomes) == 2:
                                p1 = outcomes[0]
                                p2 = outcomes[1]
                                
                                # --- MAIN LOGIC (2.5+ Both Sides) ---
                                if p1['price'] >= MIN_ODDS and p2['price'] >= MIN_ODDS:
                                    msg = (
                                        f"🚨 **High Value Alert** 🚨\n\n"
                                        f"🎾 **{match['sport_title']}**\n"
                                        f"⚔️ {p1['name']} vs {p2['name']}\n"
                                        f"💰 Odds: {p1['price']} vs {p2['price']}\n"
                                        f"🏦 Bookie: {bookmaker['title']}\n"
                                        f"⏰ Time: {match['commence_time']}\n\n"
                                        f"⚠️ Note: Dono taraf high return hai."
                                    )
                                    print(f"Found Match: {p1['name']} vs {p2['name']}")
                                    send_telegram_message(msg)
                else:
                    print(f"⚠️ API Error: {response.status_code}")

            # Rate Limit bachane ke liye wait (180 seconds = 3 min)
            # Free API me zyada tez nahi chala sakte
            time.sleep(180) 

        except Exception as e:
            print(f"❌ Error in Loop: {e}")
            time.sleep(60) # Error aaye to 1 min ruk kar try kare

# --- SERVER & THREADING SETUP ---
# Ye sabse important part hai jo pehle missing tha

# 1. Background Thread start karna
t = threading.Thread(target=check_odds)
t.start()

# 2. Web Server (Render ko zinda rakhne ke liye)
@app.route('/')
def home():
    return "Tennis 2.5 Pro Bot is Running 🟢"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
