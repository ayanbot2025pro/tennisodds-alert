import requests
import time
import statistics
import os
from datetime import datetime

# ═══════════════════════════════════════════
# ✅ FINAL OPTIMIZED SETTINGS (GOLDEN CONFIG)
# ═══════════════════════════════════════════

API_KEY = os.environ.get('ODDS_API_KEY')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# ✅ BEST SPORTS LIST (High Volume & High Swing)
SPORTS = [
    'table_tennis',       # Sabse Zyada Matches
    'tennis_atp',         # Big Leagues
    'tennis_wta',         # Big Leagues
    'esports_csgo',       # Fast Swing
    'esports_dota2',      # Fast Swing
    'esports_lol'         # Fast Swing
]

# ✅ GOLDEN CRITERIA (85-92% Chance Logic)
MIN_ODDS = 2.00           # 2.00 se niche swing mushkil hai
MAX_ODDS = 2.80           # 2.80 tak hi match close rehta hai
MAX_GAP = 0.70            # Gap badhaya taaki matches miss na hon
MIN_BOOKMAKERS = 4        # Fake match se bachne ke liye
MAX_VIG = 0.08            # Quality Check

# ✅ TOURNAMENT BLACKLIST (Kachra Hatao)
BLACKLIST = [
    'itf', 'futures', 'm15', 'm25', 'challenger',
    'friendly', 'exhibition',
    'setka', 'tt-cup', 'tt cup',
    'tier 3', 'tier 4', 'qualifier', 'academy', 'regional',
    'simulated', 'cyber', 'srl'
]

sent_alerts = set()

# ═══════════════════════════════════════════
# Functions
# ═══════════════════════════════════════════

def is_safe_match(event_name, tournament):
    text = f"{event_name} {tournament}".lower()
    for keyword in BLACKLIST:
        if keyword in text:
            return False
    return True

def calculate_vig(odds_list):
    if not odds_list or len(odds_list) < 2: return 1.0
    implied_probs = [1/odd for odd in odds_list]
    return sum(implied_probs) - 1.0

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=10)
    except: pass

def check_odds():
    print(f"Scanning at {datetime.now().strftime('%H:%M')}...")
    
    for sport in SPORTS:
        try:
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
            params = {'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
            r = requests.get(url, params=params, timeout=10)
            
            if r.status_code != 200: continue
            
            matches = r.json()
            for match in matches:
                m_id = match['id']
                if m_id in sent_alerts: continue
                
                # Filter 1: Tournament Safety
                if not is_safe_match(f"{match['home_team']} {match['away_team']}", match.get('sport_title', '')): continue
                
                # Filter 2: Bookmaker Count
                bookmakers = match.get('bookmakers', [])
                if len(bookmakers) < MIN_BOOKMAKERS: continue

                h_odds, a_odds = [], []
                for b in bookmakers:
                    try:
                        o = b['markets'][0]['outcomes']
                        for outcome in o:
                            if outcome['name'] == match['home_team']: h_odds.append(outcome['price'])
                            elif outcome['name'] == match['away_team']: a_odds.append(outcome['price'])
                    except: continue
                
                if len(h_odds) < MIN_BOOKMAKERS or len(a_odds) < MIN_BOOKMAKERS: continue
                
                avg_h = statistics.mean(h_odds)
                avg_a = statistics.mean(a_odds)

                # ✅ Filter 3: The Golden Zone (2.00 to 2.80)
                if (MIN_ODDS <= avg_h <= MAX_ODDS) and (MIN_ODDS <= avg_a <= MAX_ODDS):
                    
                    # ✅ Filter 4: Gap Check
                    gap = abs(avg_h - avg_a)
                    if gap <= MAX_GAP:
                        
                        # ✅ Filter 5: VIG Check
                        vig = calculate_vig([avg_h, avg_a])
                        if vig <= MAX_VIG:
                            
                            msg = (f"🚀 <b>JACKPOT ALERT!</b>\n\n"
                                   f"🏆 {sport.upper()}\n⚔️ {match['home_team']} vs {match['away_team']}\n"
                                   f"⚖️ Odds: {avg_h:.2f} vs {avg_a:.2f}\n"
                                   f"📊 Gap: {gap:.2f} | VIG: {vig:.3f}\n"
                                   f"✅ Verified: {len(bookmakers)} Bookies")
                            
                            send_telegram(msg)
                            sent_alerts.add(m_id)

        except Exception as e:
            print(f"Error: {e}")
            continue

if __name__ == "__main__":
    # Startup Message
    send_telegram(f"🤖 <b>BOT RESTARTED + HEARTBEAT ON</b>\nRange: {MIN_ODDS}-{MAX_ODDS} | Gap: {MAX_GAP}")
    
    last_heartbeat = time.time()
    
    while True:
        check_odds()
        
        # ✅ HEARTBEAT CHECK (Har 1 Ghante Mein)
        if time.time() - last_heartbeat > 3600:
            send_telegram(f"🔔 <b>Boss, Main Jinda Hoon!</b>\nSab kuch sahi chal raha hai.\nTime: {datetime.now().strftime('%H:%M')}")
            last_heartbeat = time.time()
            
        time.sleep(600) # 10 min wait
