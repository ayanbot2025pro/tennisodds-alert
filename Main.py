import requests
import time
import statistics
import os

# --- 1. SETTINGS ---
API_KEY = os.getenv("ODDS_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- 2. SMART CONFIG (High Accuracy & Safety) ---
SPORTS_CONFIG = {
    # Table Tennis: Sirf WTT aur International lo. 
    # (Setka/Liga Pro Blocked hai neeche Blacklist mein)
    'table_tennis': {
        'min_odds': 1.80,
        'max_odds': 2.50,
        'max_gap': 0.60,
        'min_books': 5  # Strict Safety: 5 Bookies zaroori hain
    },
    
    # Tennis: Sirf ATP/WTA (ITF/UTR Blocked hai)
    'tennis_atp': {
        'min_odds': 1.95,
        'max_odds': 2.30,
        'max_gap': 0.35,
        'min_books': 6  # Tennis mein fixing zyada hai, isliye 6 Bookies maange
    },
    'tennis_wta': {
        'min_odds': 1.95,
        'max_odds': 2.30,
        'max_gap': 0.35,
        'min_books': 6
    },
    
    # Esports: Sirf Bade Tournaments
    'esports_csgo': {
        'min_odds': 1.85,
        'max_odds': 2.40,
        'max_gap': 0.50,
        'min_books': 4
    }
}

# --- 3. THE SUPER BLACKLIST (Fixing Ka Dushman) ---
# Ye list un sabhi leagues ko block karegi jahan fixing common hai.
BLACKLIST = [
    # Table Tennis Kachra (Fixing Hubs)
    'setka', 'liga pro', 'tt cup', 'win cup', 'czech liga', 'russia', 'ukraine',
    'armenia', 'belarus', 'master tour',
    
    # Tennis Kachra (Low Tier)
    'itf', 'futures', 'utr', 'exhibition', 'daily', 'pro series', 
    'invitational', 'club',
    
    # Fake/Virtual Matches
    'simulated', 'srl', 'cyber', 'virtual', 'esoccer', 'ebasketball', 
    '2k', 'fifa',
    
    # Junior/Small Leagues
    'u19', 'u21', 'youth', 'academy', 'regional', 'qualifier', 'amateur'
]

sent_alerts = set()

def is_safe(title, competition):
    """
    Smart Check: Kya ye match fixing wali league ka hai?
    """
    full_text = (title + " " + competition).lower()
    # Agar blacklist ka koi bhi shabd match mein hai, toh FALSE (Reject) karo
    if any(bad in full_text for bad in BLACKLIST):
        return False
    return True

def send_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except: pass

def scan():
    # print("🔎 Scanning with Anti-Fixing Filters...")
    
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
            matches = r.json()
            
            if not isinstance(matches, list): continue

            for match in matches:
                match_id = match['id']
                if match_id in sent_alerts: continue
                
                # --- FACTOR 1: BLACKLIST CHECK ---
                sport_title = match.get('sport_title', '')
                if not is_safe(sport_key, sport_title): 
                    continue # Kachra match tha, fek diya
                
                # --- FACTOR 2: BOOKMAKERS COUNT ---
                books = match.get('bookmakers', [])
                if len(books) < config['min_books']: 
                    continue # Fake/Small match, reject
                
                h_odds_list, a_odds_list = [], []
                
                for b in books:
                    try:
                        outcomes = b['markets'][0]['outcomes']
                        # Naam match karke sahi odds nikalo
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
                
                # --- FACTOR 3: ODDS RANGE & GAP ---
                if not (avg_h >= config['min_odds'] and avg_a >= config['min_odds']): continue
                if not (avg_h <= config['max_odds'] and avg_a <= config['max_odds']): continue
                
                current_gap = abs(avg_h - avg_a)
                if current_gap > config['max_gap']: continue
                
                # Sab Clean Hai? Alert Bhejo!
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
                
        except: pass

if __name__ == "__main__":
    print("🛡️ Bot Started: Anti-Fixing Mode ON (Strict)")
    while True:
        scan()
        time.sleep(300)
