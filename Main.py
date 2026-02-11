import requests
import time
import statistics
import os

# --- 1. SETTINGS (Keys Uthana) ---
API_KEY = os.getenv("ODDS_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- 2. SMART "ALAG-ALAG" CONFIG (Best Logic) ---
SPORTS_CONFIG = {
    # Table Tennis: Fast hai, thoda gap chalta hai (Setka blocked hai)
    'table_tennis': {
        'min_odds': 1.80,
        'max_odds': 2.50,
        'max_gap': 0.60,
        'min_books': 5
    },
    
    # Tennis ATP: Strict raho
    'tennis_atp': {
        'min_odds': 1.95,
        'max_odds': 2.30,
        'max_gap': 0.35,
        'min_books': 6
    },
    # Tennis WTA: Strict raho
    'tennis_wta': {
        'min_odds': 1.95,
        'max_odds': 2.30,
        'max_gap': 0.35,
        'min_books': 6
    },
    
    # Esports: Medium setting
    'esports_csgo': {
        'min_odds': 1.85,
        'max_odds': 2.40,
        'max_gap': 0.50,
        'min_books': 4
    }
}

# --- 3. SUPER BLACKLIST (Kachra Hatao) ---
BLACKLIST = [
    # Table Tennis Fixing Hubs
    'setka', 'liga pro', 'tt cup', 'win cup', 'czech liga', 'russia', 'ukraine',
    'armenia', 'belarus', 'master tour',
    
    # Tennis Low Tier
    'itf', 'futures', 'utr', 'exhibition', 'daily', 'pro series', 
    'invitational', 'club',
    
    # Fake/Virtual
    'simulated', 'srl', 'cyber', 'virtual', 'esoccer', 'ebasketball', 
    '2k', 'fifa',
    
    # Junior Leagues
    'u19', 'u21', 'youth', 'academy', 'regional', 'qualifier', 'amateur'
]

sent_alerts = set()

def is_safe(title, competition):
    """Check karta hai ki match safe hai ya fixing wala"""
    full_text = (title + " " + competition).lower()
    if any(bad in full_text for bad in BLACKLIST):
        return False
    return True

def send_alert(msg):
    """Telegram par message bhejta hai"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("✅ Message Sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

def scan():
    print("🔎 Scanning Markets...")
    
    for sport_key, config in SPORTS_CONFIG.items():
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                "apiKey": API_KEY,
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal"
            }
            r = requests.get(url, params=params, timeout=10)
            
            if r.status_code != 200:
                print(f"⚠️ API Error for {sport_key}: {r.status_code}")
                continue
                
            matches = r.json()
            
            if not isinstance(matches, list): continue

            for match in matches:
                match_id = match['id']
                if match_id in sent_alerts: continue
                
                # --- FILTER 1: BLACKLIST ---
                sport_title = match.get('sport_title', '')
                if not is_safe(sport_key, sport_title): 
                    continue 
                
                # --- FILTER 2: BOOKMAKERS COUNT ---
                books = match.get('bookmakers', [])
                if len(books) < config['min_books']: 
                    continue 
                
                h_odds_list, a_odds_list = [], []
                
                for b in books:
                    try:
                        outcomes = b['markets'][0]['outcomes']
                        if outcomes[0]['name'] == match['home_team']:
                            h_odds_list.append(outcomes[0]['price'])
                            a_odds_list.append(outcomes[1]['price'])
                        else:
                            h_odds_list.append(outcomes[1]['price'])
                            a_odds_list.append(outcomes[0]['price'])
                    except: continue
                
                if not h_odds_list: continue
                
                avg_h = statistics.mean(h_odds_list)
                avg_a = statistics.mean(a_odds_list)
                
                # --- FILTER 3: ODDS RANGE & GAP ---
                # Check Entry Gate (Min Odds)
                if not (avg_h >= config['min_odds'] and avg_a >= config['min_odds']): continue
                
                # Check Exit Gate (Max Odds)
                if not (avg_h <= config['max_odds'] and avg_a <= config['max_odds']): continue
                
                # Check Gap (Takkar)
                current_gap = abs(avg_h - avg_a)
                if current_gap > config['max_gap']: continue
                
                # --- SEND ALERT ---
                icon = "🏆"
                if "tennis" in sport_key: icon = "🎾"
                elif "table" in sport_key: icon = "🏓"
                elif "esports" in sport_key: icon = "🎮"
                
                msg = (
                    f"{icon} **SAFE MATCH ALERT** {icon}\n\n"
                    f"⚔️ **{match['home_team']} vs {match['away_team']}**\n"
                    f"🏆 League: {sport_title}\n"
                    f"📊 Odds: {avg_h:.2f} vs {avg_a:.2f}\n"
                    f"🛡️ Verified by {len(books)} Bookies"
                )
                
                send_alert(msg)
                sent_alerts.add(match_id)
                
        except Exception as e:
            print(f"Error scanning {sport_key}: {e}")
            pass

# --- MAIN LOOP (Jinda Rehne Wala Hissa) ---
if __name__ == "__main__":
    # 1. Start hote hi Message Bhejo
    print("🚀 Bot Starting...")
    start_msg = (
        "🤖 **BOT UPDATED SUCCESSFULLY!**\n"
        "✅ **Mode:** Ultra-Safe (Anti-Fixing)\n"
        "✅ **Logic:** Alag-Alag Factors Active\n"
        "🚀 **Scanning Started Now...**"
    )
    send_alert(start_msg)

    last_heartbeat = time.time()

    while True:
        try:
            # Match Scan karo
            scan()
            
            # 2. Har 1 Ghante (3600 seconds) mein Jinda Hone ka message
            current_time = time.time()
            if current_time - last_heartbeat > 3600:
                send_alert("🔔 **Boss, Main Jinda Hoon!** (System Healthy)")
                last_heartbeat = current_time
                
            # 5 Minute ka rest
            time.sleep(300)
            
        except Exception as e:
            print(f"Critical Error in Main Loop: {e}")
            time.sleep(60)
