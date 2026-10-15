# bot.py - APEX PREDATOR PRO - VERSION FINALE AVEC WHATSAPP
import time
import requests
from collections import deque
from datetime import datetime

# ============== CONFIG WHATSAPP ==============
TON_NUMERO_WHATSAPP = "2250700000000" # << METS TON NUMÉRO ICI sans + ex: 22507...
CALLMEBOT_APIKEY = "METS_TON_APIKEY_ICI" # << Tu le reçois sur CallMeBot

def envoyer_whatsapp(message):
    try:
        if "METS_TON" in CALLMEBOT_APIKEY or "METS_TON" in TON_NUMERO_WHATSAPP:
            print(f"📲 [SIMULATION WHATSAPP] {message}")
            return False
        url = f"https://api.callmebot.com/whatsapp.php?phone={TON_NUMERO_WHATSAPP}&text={message}&apikey={CALLMEBOT_APIKEY}"
        r = requests.get(url, timeout=10)
        print(f"📲 WhatsApp envoyé: {r.text}")
        return True
    except Exception as e:
        print(f"Erreur WhatsApp: {e}")
        return False

# ============== ETAT GLOBAL ==============
STATE = {
    "is_bot_active": False,
    "capital_total": 100.0,
    "capital_initial": 100.0,
    "perte_journaliere": 0.0,
    "is_kill_switch_global": False,
    "latence_ms": 0,
    "quota_weight_used": 0,
    "btc_price_history": deque(maxlen=100),
    "btc_dominance_history": deque(maxlen=100),
    "last_reset_day": datetime.now().date(),
    "trades_history": []
}

CONFIG = {
    "LATENCE_MAX_MS": 80,
    "FRAIS_BNB": 0.00075,
    "COUT_TOTAL_MAX": 0.0020,
    "QUOTA_MAX": 1200,
    "QUOTA_BLOCAGE": 0.8,
    "ANTI_SPOOFING_MS": 200,
    "ATR_MULTIPLIER": 1.5,
    "BTC_DROP_INTERDIT": -1.0,
    "BTC_DOMINANCE_HAUSSE": 0.5,
    "RISQUE_PAR_TRADE": 0.01,
    "STOP_LOSS_TRADE": 0.01,
    "STOP_JOURNALIER": 0.03,
    "STOP_GLOBAL": 0.08,
    "RATIO_RR_MIN": 2.0
}

# ============== MODULES ==============
class GestionnaireQuota:
    def check_and_add(self, weight):
        if STATE["quota_weight_used"] >= CONFIG["QUOTA_MAX"] * CONFIG["QUOTA_BLOCAGE"]:
            return False
        STATE["quota_weight_used"] += weight
        return True

class FiltreMaitreBTC:
    def check(self):
        if len(STATE["btc_price_history"]) < 2: return True
        prix_old = STATE["btc_price_history"][0]
        prix_now = STATE["btc_price_history"][-1]
        variation = ((prix_now - prix_old) / prix_old) * 100
        if variation <= CONFIG["BTC_DROP_INTERDIT"]:
            print(f"⛔ FILTRE BTC: {variation:.2f}% - INTERDICTION")
            return False
        return True

class ValidateurOrderBook:
    def __init__(self): self.walls = {}
    def valider(self, symbol, bids):
        now = time.time() * 1000
        key = f"{symbol}_{bids[0][1] if bids else 0}"
        if key not in self.walls:
            self.walls[key] = now
            return False
        if (now - self.walls[key]) < CONFIG["ANTI_SPOOFING_MS"]:
            return False
        return True

class RiskManager:
    def taille_position(self, capital, distance_sl):
        if distance_sl == 0: return 0
        return (capital * CONFIG["RISQUE_PAR_TRADE"]) / distance_sl

    def check_cout_et_rr(self, entree, cible, spread, slippage):
        cout = spread + (CONFIG["FRAIS_BNB"]*2) + slippage
        if cout > CONFIG["COUT_TOTAL_MAX"]: return False
        gain = (cible - entree) / entree
        ratio = gain / CONFIG["STOP_LOSS_TRADE"]
        return ratio >= CONFIG["RATIO_RR_MIN"]

    def check_kill_switch(self):
        perte_glob = (STATE["capital_total"] - STATE["capital_initial"]) / STATE["capital_initial"]
        if perte_glob <= -CONFIG["STOP_GLOBAL"]:
            STATE["is_kill_switch_global"] = True
            STATE["is_bot_active"] = False
            msg = f"🚨 KILL-SWITCH GLOBAL -8% ATTEINT: {perte_glob*100:.2f}% - Capital {STATE['capital_total']}€ - Bot VERROUILLÉ"
            print(msg)
            envoyer_whatsapp(msg)
            return "LEVEL3"
        if STATE["perte_journaliere"] <= -CONFIG["STOP_JOURNALIER"] * STATE["capital_initial"]:
            STATE["is_bot_active"] = False
            msg = f"🔒 KILL-SWITCH JOURNALIER -3% ATTEINT: {STATE['perte_journaliere']}€ - Bot OFF"
            print(msg)
            envoyer_whatsapp(msg)
            return "LEVEL2"
        return None

quota = GestionnaireQuota()
btc_filter = FiltreMaitreBTC()
orderbook_validator = ValidateurOrderBook()
risk = RiskManager()

# ============== FONCTIONS UTILES ==============
def check_daily_reset():
    today = datetime.now().date()
    if STATE["last_reset_day"]!= today:
        STATE["last_reset_day"] = today
        STATE["perte_journaliere"] = 0.0
        STATE["quota_weight_used"] = 0
        print("🔄 RESET JOURNALIER")

def enregistrer_trade(symbol, pnl, status="accepté"):
    check_daily_reset()
    STATE["capital_total"] += pnl
    if pnl < 0:
        STATE["perte_journaliere"] += pnl

    trade = {
        "heure": datetime.now().strftime("%H:%M:%S"),
        "symbol": symbol,
        "pnl": round(pnl, 2),
        "capital": round(STATE["capital_total"], 2),
        "status": status
    }
    STATE["trades_history"].insert(0, trade)
    if len(STATE["trades_history"]) > 50:
        STATE["trades_history"].pop()

    # Notif WhatsApp pour les nouveaux listings
    if "listing" in status.lower() or "alerte" in status.lower():
        envoyer_whatsapp(f"🚀 APEX: {symbol} - {status} à {trade['heure']}")

    risk.check_kill_switch()
    return trade

def executer_trade_logic(symbol, prix_entree, prix_cible, spread, slippage):
    check_daily_reset()
    if STATE["is_kill_switch_global"]: return {"status": "refusé", "raison": "Kill Switch Global -8%"}
    if not STATE["is_bot_active"]: return {"status": "refusé", "raison": "Bot OFF"}
    if STATE["latence_ms"] > CONFIG["LATENCE_MAX_MS"]: return {"status": "refusé", "raison": f"Latence {STATE['latence_ms']}ms > {CONFIG['LATENCE_MAX_MS']}ms"}
    if not quota.check_and_add(5): return {"status": "refusé", "raison": "Quota 80% atteint"}
    if not btc_filter.check(): return {"status": "refusé", "raison": "Filtre BTC"}

    distance_sl = prix_entree * CONFIG["STOP_LOSS_TRADE"]
    if not risk.check_cout_et_rr(prix_entree, prix_cible, spread, slippage):
        return {"status": "refusé", "raison": "Coût ou R/R invalide"}

    taille = risk.taille_position(STATE["capital_total"], distance_sl)
    return {"status": "accepté", "taille": round(taille,2), "ordre": "LIMIT Post-Only 300ms", "capital": STATE["capital_total"]}