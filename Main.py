import requests
import time
import os
import threading
from flask import Flask

# ═══════════════════════════════════════════
# 1. SETTINGS & KEYS
# ═══════════════════════════════════════════
API_KEY = os.environ.get("ODDS_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

app = Flask(__name__)

# ═══════════════════════════════════════════
# 2. TRUSTED BOOKIES (Inke alawa kisi ko nahi manenge)
# ═══════════════════════════════════════════
TRUSTED_BOOKIES = [
    'pinnacle', 'bet365', 'williamhill', 'betfair_ex_eu', 'betfair_sb_uk',
    'unibet', 'betonlineag', '888sport', 'betway', 'boylesports',
    'ladbrokes', 'bovada'
]

# ═══════════════════════════════════════════
# 3. SPORT CONFIGURATION (Aapke Screenshot Wale Exact Odds)
# ═══════════════════════════════════════════
SPORTS_CONFIG = {
    # 🎾 TENNIS (ATP/WTA) -> Aapka Range: 1.90 - 2.30
    'tennis_atp': {
        'min_odds': 1.90, 
        'max_odds': 2.30, 
        'max_gap': 0.45,  # (2.30 - 1.90 = 0.40 hota hai, thoda buffer diya)
        'min_books': 5, 
        'desc': "🎾 ATP Tennis"
    },
    'tennis_wta': {
        'min_odds': 1.90, 
        'max_odds': 2.30, 
        'max_gap': 0.45,
        'min_books': 5, 
        'desc': "🎾 WTA Tennis"
    },
    
    # 🏓 TABLE TENNIS -> Aapka Range: 1.80 - 2.50
    'table_tennis': {
        'min_odds': 1.80, 
        'max_odds': 2.50, 
        'max_gap': 0.75,  # (2.50 - 1.80 = 0.70 gap allow hai)
        'min_books': 5, 
        'desc': "🏓 Table Tennis"
    },
    
    # 🎮 ESPORTS -> Aapka Range: 1.85 - 2.40
    'esports_csgo': {
        'min_odds': 1.85, 
        'max_odds': 2.40, 
        'max_gap': 0.60, 
        'min_books': 4, 
        'desc': "🎮 CS:GO Esports"
    }
}

# ═══════════════════════════════════════════
# 4. BLACKLIST (Fixing / Kachra Leagues Block)
# ═══════════════════════════════════════════
BLACKLIST = [
    'setka', 'liga pro', 'tt cup', 'win cup', 'virtual', 'simulated', 'cyber', 
    'itf', 'futures', 'm15', 'm25', 'u18', 'u19', 'u21', 'youth', 'exhibition', 
    'academy', 'qualifier', 'tier 3', 'tier 4'
]

# Cache (Duplicate alerts rokne ke liye)
alerted_matches = set()

# ═══════════════════════════════════════════
# 5. FUNCTIONS
# ═══════════════════════════════════════════

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def is_safe_tournament(name):
    """Agar naam me blacklist word hai to False dega"""
    name_lower = (name or "").lower()
    for bad in BLACKLIST:
        if bad in name_lower:
            return False
    return True

# ═══════════════════════════════════════════
# 6. MAIN SCANNING LOGIC (Bot ka Dimaag)
# ═══════════════════════════════════════════
def scan_market():
    print("🚀 Bot Started with User's Exact Odds Range...")
    send_telegram(
        "✅ **Bot Live: Strict Mode**\n"
        "🎾 Tennis: 1.90 - 2.30\n"
        "🏓 TT: 1.80 - 2.50\n"
        "🎮 Esports: 1.85 - 2.40"
    )

    while True:
        try:
            for sport_key, rules in SPORTS_CONFIG.items():
                print(f"🔍 Scanning {rules['desc']}...")
                
                # API Call
                response = requests.get(
                    f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds',
                    params={
                        'apiKey': API_KEY,  
                        'regions': 'eu',    # Europe Bookies (Best for Tennis/TT)
                        'markets': 'h2h',
                        'oddsFormat': 'decimal'
                    },
                    timeout=15
                )

                if response.status_code != 200:
                    print(f"⚠️ API Error: {response.status_code}")
                    continue

                matches = response.json()
                
                for match in matches:
                    match_id = match['id']
                    if match_id in alerted_matches: continue 

                    # 1. TOURNAMENT SAFETY CHECK
                    tournament = match.get('sport_title', '')
                    if not is_safe_tournament(tournament):
                        continue 

                    # 2. BOOKIE COUNT CHECK
                    valid_books = [b for b in match['bookmakers'] if b['key'] in TRUSTED_BOOKIES]
                    if len(valid_books) < rules['min_books']:
                        continue

                    # 3. ODDS AVERAGE NIKALNA
                    h_odds, a_odds = [], []
                    home_team = match['home_team']
                    
                    for b in valid_books:
                        try:
                            outcomes = b['markets'][0]['outcomes']
                            p1 = next((o['price'] for o in outcomes if o['name'] == home_team), None)
                            p2 = next((o['price'] for o in outcomes if o['name'] != home_team), None)
                            if p1 and p2:
                                h_odds.append(p1)
                                a_odds.append(p2)
                        except: continue

                    if not h_odds: continue

                    avg_h = sum(h_odds) / len(h_odds)
                    avg_a = sum(a_odds) / len(a_odds)
                    gap = abs(avg_h - avg_a)

                    # 4. MAIN FACTOR CHECK (AND LOGIC)
                    # Hum check kar rahe hain ki kya DONO khiladi aapke range me hain?
                    
                    h_good = rules['min_odds'] <= avg_h <= rules['max_odds']
                    a_good = rules['min_odds'] <= avg_a <= rules['max_odds']
                    
                    # Agar Dono range me hain, aur gap limit me hai -> ALERT
                    if h_good and a_good and gap <= rules['max_gap']:
                        
                        msg = (
                            f"🚨 <b>PERFECT MATCH FOUND</b>\n\n"
                            f"🏆 {rules['desc']}\n"
                            f"🏟️ {tournament}\n"
                            f"⚔️ <b>{match['home_team']}</b> vs <b>{match['away_team']}</b>\n\n"
                            f"💰 Odds: <b>{avg_h:.2f}</b> vs <b>{avg_a:.2f}</b>\n"
                            f"📉 Gap: {gap:.2f}\n"
                            f"🛡️ Verified on: {len(valid_books)} Bookies\n"
                            f"⏰ Start: {match['commence_time']}"
                        )
                        send_telegram(msg)
                        alerted_matches.add(match_id)
                        print(f"✅ Alert: {match['home_team']} vs {match['away_team']}")

            # 3 Minute Wait
            time.sleep(180) 

        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

# ═══════════════════════════════════════════
# 7. SERVER KEEP-ALIVE
# ═══════════════════════════════════════════
threading.Thread(target=scan_market).start()

@app.route('/')
def home():
    return "Tennis 2.5 Pro (Exact User Config) is Running 🟢"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
