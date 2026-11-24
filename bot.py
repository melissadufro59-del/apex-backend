# bot.py - APEX PREDATOR PRO - VERSION FINALE RAILWAY + TESTNET + SOLDE REEL
import os
import time
import csv
import requests
from collections import deque
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============== CONFIG BINANCE TESTNET (Railway) ==============
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_SECRET_KEY") or os.getenv("BINANCE_SECRET")
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true")
BINANCE_BASE_URL = "https://testnet.binance.vision" if BINANCE_TESTNET.lower() == "true" else "https://api.binance.com"

# ============== LECTURE VRAI SOLDE BINANCE TESTNET - CORRIGÉ ==============
def get_solde_reel_binance():
 try:
 if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
 print(" Clés Binance non trouvées, on garde 100€ par défaut")
 return None
 
 try:
 from binance.client import Client
 is_testnet = BINANCE_TESTNET.lower() == "true"
 client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=is_testnet)
 account = client.get_account()
 
 total_estime_usdt = 0.0
 print("--- LECTURE BALANCES BINANCE TESTNET ---")
 for b in account['balances']:
 free = float(b['free']) + float(b['locked'])
 if free > 0.000001:
 asset = b['asset']
 print(f" Balance trouvée: {asset} = {free}")
 if asset in ['USDT', 'FDUSD', 'BUSD', 'USDC']:
 total_estime_usdt += free
 elif asset == 'BTC':
 total_estime_usdt += free * 65000
 elif asset == 'BNB':
 total_estime_usdt += free * 600
 elif asset == 'ETH':
 total_estime_usdt += free * 3000
 else:
 # Pour tout autre coin, on le compte au moins
 total_estime_usdt += free
 
 print(f" Solde Testnet réel lu: {total_estime_usdt} USDT")
 return total_estime_usdt if total_estime_usdt > 0 else None
 
 except ImportError:
 print(" python-binance non installé, install: pip install python-binance")
 return None
 except Exception as e:
 print(f" Erreur lecture Binance: {e} - on garde 100€")
 import traceback
 traceback.print_exc()
 return None
 except Exception as e:
 print(f"Erreur solde: {e}")
 return None

# ============== AJOUT JOUR 1 : VRAIS PRIX BINANCE POUR SOLDE EXACT ==============
# On garde ta fonction d'origine au-dessus en fallback.
# Celle-ci corrige les 2 bugs : prix en dur 65000/600/3000 + autres coins comptés comme 1 USDT
_cache_prix = {}
_cache_prix_time = 0

def get_prix_reel(asset):
 """Retourne le vrai prix en USDT pour un asset, via API publique Binance. Pour les étapes futures."""
 global _cache_prix, _cache_prix_time
 if asset in ['USDT', 'FDUSD', 'BUSD', 'USDC', 'USD']:
 return 1.0
 # Cache 60s pour ne pas spammer l'API et ne pas toucher au quota
 now = time.time()
 if asset in _cache_prix and (now - _cache_prix_time) < 60:
 return _cache_prix[asset]
 try:
 # On utilise l'API publique, pas besoin de clé, ça marche même en Testnet
 base = "https://api.binance.com"
 # Essai direct USDT
 r = requests.get(f"{base}/api/v3/ticker/price?symbol={asset}USDT", timeout=5)
 if r.status_code == 200:
 prix = float(r.json().get("price", 0))
 if prix > 0:
 _cache_prix[asset] = prix
 _cache_prix_time = now
 return prix
 # Si pas de paire USDT, on passe par BTC puis BTC/USDT
 r2 = requests.get(f"{base}/api/v3/ticker/price?symbol={asset}BTC", timeout=5)
 r3 = requests.get(f"{base}/api/v3/ticker/price?symbol=BTCUSDT", timeout=5)
 if r2.status_code == 200 and r3.status_code == 200:
 prix = float(r2.json().get("price", 0)) * float(r3.json().get("price", 0))
 if prix > 0:
 _cache_prix[asset] = prix
 _cache_prix_time = now
 return prix
 except Exception as e:
 print(f" Prix reel {asset} indisponible: {e}")
 return 0.0 # 0 = on ne compte pas ce coin plutôt que de le compter comme 1 USDT

def get_solde_reel_binance_corrige():
 """Version corrigée utilisée pour le capital de départ + pour /balance en direct (étape api.py)."""
 try:
 if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
 return None
 from binance.client import Client
 is_testnet = BINANCE_TESTNET.lower() == "true"
 client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=is_testnet)
 account = client.get_account()
 total = 0.0
 print("--- LECTURE BALANCES CORRIGÉE JOUR 1 ---")
 for b in account['balances']:
 free = float(b['free']) + float(b['locked'])
 if free > 0.000001:
 asset = b['asset']
 prix = get_prix_reel(asset)
 valeur = free * prix
 print(f" {asset} = {free} x {prix} = {valeur:.2f} USDT")
 total += valeur
 print(f" Solde Testnet CORRIGÉ: {total:.2f} USDT")
 return total if total > 0 else None
 except Exception as e:
 print(f" Solde corrigé échoué, on garde l'ancienne fonction: {e}")
 return get_solde_reel_binance()

def refresh_solde_reel():
 """Pour api.py étape suivante : re-lit Binance en direct sans redémarrer Railway."""
 nouveau = get_solde_reel_binance_corrige()
 if nouveau is not None and nouveau > 0:
 # On ne touche pas au capital_initial, on met juste à jour le capital_total affiché
 # si le bot n'a pas encore tradé (sinon on garderait l'évolution des trades)
 # Pour l'affichage Flutter, on stocke aussi le solde brut Binance
 STATE["solde_binance_reel"] = nouveau
 return nouveau
 return STATE.get("solde_binance_reel", STATE["capital_total"])

# ============== CONFIG WHATSAPP ==============
TON_NUMERO_WHATSAPP = os.getenv("TON_NUMERO_WHATSAPP", "2250700000000")
CALLMEBOT_APIKEY = os.getenv("CALLMEBOT_APIKEY", "METS_TON_APIKEY_ICI")

def envoyer_whatsapp(message):
 try:
 if "METS_TON" in CALLMEBOT_APIKEY or not CALLMEBOT_APIKEY or len(CALLMEBOT_APIKEY) < 5:
 print(f" [SIMULATION WHATSAPP] {message}")
 return False
 url = f"https://api.callmebot.com/whatsapp.php?phone={TON_NUMERO_WHATSAPP}&text={message}&apikey={CALLMEBOT_APIKEY}"
 r = requests.get(url, timeout=10)
 print(f" WhatsApp envoyé: {r.text}")
 return True
 except Exception as e:
 print(f"Erreur WhatsApp: {e}")
 return False

# ============== ETAT GLOBAL ==============
SOLDE_REEL = get_solde_reel_binance_corrige()
# Si corrigé échoue, on retombe sur ton ancienne logique 100€
if SOLDE_REEL is None:
 SOLDE_REEL = get_solde_reel_binance()
CAPITAL_DEPART = SOLDE_REEL if SOLDE_REEL is not None and SOLDE_REEL > 0 else 100.0

STATE = {
 "is_bot_active": False,
 "capital_total": CAPITAL_DEPART,
 "capital_initial": CAPITAL_DEPART,
 "perte_journaliere": 0.0,
 "is_kill_switch_global": False,
 "latence_ms": 0,
 "quota_weight_used": 0,
 "btc_price_history": deque(maxlen=100),
 "btc_dominance_history": deque(maxlen=100),
 "last_reset_day": datetime.now().date(),
 "trades_history": [],
 # === AJOUT JOUR 1 - Pour étapes restantes (ne casse rien) ===
 "solde_binance_reel": CAPITAL_DEPART,
 "pertes_consecutives": 0,
 "dernier_listing_titre": "",
 "watcher_actif": False,
 "dernier_listing_symbol": "",
 "dernier_listing_heure": "",
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
 "RATIO_RR_MIN": 2.0,
 # === AJOUT JOUR 1 - Tes règles restantes ===
 "MONTANT_MAX_PAR_TRADE": 20.0,
 "MAX_PERTES_CONSECUTIVES": 3,
 "STOP_PAR_TRADE_PCT": 0.01,
}

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
 print(f" FILTRE BTC: {variation:.2f}% - INTERDICTION")
 return False
 return True
 # === AJOUT JOUR 1 - Dominance BTC (étape restante) ===
 def check_dominance(self):
 if len(STATE["btc_dominance_history"]) < 2: return True
 old = STATE["btc_dominance_history"][0]
 now = STATE["btc_dominance_history"][-1]
 hausse = now - old
 if hausse >= CONFIG["BTC_DOMINANCE_HAUSSE"]:
 print(f" FILTRE DOMINANCE: +{hausse:.2f}% - INTERDICTION")
 return False
 return True
 def check_complet(self):
 return self.check() and self.check_dominance()

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
 taille = (capital * CONFIG["RISQUE_PAR_TRADE"]) / distance_sl
 # === AJOUT JOUR 1 - Plafond 20$ par trade (ta règle) ===
 if taille > CONFIG["MONTANT_MAX_PAR_TRADE"]:
 taille = CONFIG["MONTANT_MAX_PAR_TRADE"]
 return taille
 def check_cout_et_rr(self, entree, cible, spread, slippage):
 cout = spread + (CONFIG["FRAIS_BNB"]*2) + slippage
 if cout > CONFIG["COUT_TOTAL_MAX"]: return False
 gain = (cible - entree) / entree
 ratio = gain / CONFIG["STOP_LOSS_TRADE"]
 return ratio >= CONFIG["RATIO_RR_MIN"]
 def check_kill_switch(self):
 # === AJOUT JOUR 1 - LEVEL 1 : Stop par trade -1% ===
 # Vérifié dans enregistrer_trade via pertes_consecutives, on garde Level 2 et 3 ici
 perte_glob = (STATE["capital_total"] - STATE["capital_initial"]) / STATE["capital_initial"]
 if perte_glob <= -CONFIG["STOP_GLOBAL"]:
 STATE["is_kill_switch_global"] = True
 STATE["is_bot_active"] = False
 msg = f" KILL-SWITCH GLOBAL -8% ATTEINT: {perte_glob*100:.2f}%"
 print(msg)
 envoyer_whatsapp(msg)
 return "LEVEL3"
 if STATE["perte_journaliere"] <= -CONFIG["STOP_JOURNALIER"] * STATE["capital_initial"]:
 STATE["is_bot_active"] = False
 return "LEVEL2"
 return None
 # === AJOUT JOUR 1 - 3 pertes d'affilée ===
 def check_pertes_consecutives(self):
 if STATE.get("pertes_consecutives", 0) >= CONFIG["MAX_PERTES_CONSECUTIVES"]:
 STATE["is_bot_active"] = False
 msg = f" STOP 3 PERTES D'AFFILÉE - Bot mis OFF pour aujourd'hui"
 print(msg)
 envoyer_whatsapp(msg)
 return True
 return False

quota = GestionnaireQuota()
btc_filter = FiltreMaitreBTC()
orderbook_validator = ValidateurOrderBook()
risk = RiskManager()

def sauvegarder_csv(trade):
 try:
 file_exists = os.path.isfile("trades.csv")
 with open("trades.csv", "a", newline="", encoding="utf-8") as f:
 writer = csv.DictWriter(f, fieldnames=["heure","symbol","pnl","capital","status"])
 if not file_exists:
 writer.writeheader()
 writer.writerow(trade)
 except Exception as e:
 print(f"Erreur CSV: {e}")

def check_daily_reset():
 today = datetime.now().date()
 if STATE["last_reset_day"]!= today:
 STATE["last_reset_day"] = today
 STATE["perte_journaliere"] = 0.0
 STATE["quota_weight_used"] = 0
 # === AJOUT JOUR 1 ===
 STATE["pertes_consecutives"] = 0
 print(" RESET JOURNALIER")

def enregistrer_trade(symbol, pnl, status="accepté"):
 check_daily_reset()
 STATE["capital_total"] += pnl
 if pnl < 0:
 STATE["perte_journaliere"] += pnl
 # === AJOUT JOUR 1 - Compteur pertes consécutives ===
 STATE["pertes_consecutives"] = STATE.get("pertes_consecutives", 0) + 1
 # LEVEL 1 : si un seul trade perd plus de -1% du capital, on log
 if pnl <= -CONFIG["STOP_PAR_TRADE_PCT"] * STATE["capital_initial"]:
 print(f" LEVEL 1: Perte trade {pnl:.2f} >= -1%")
 else:
 STATE["pertes_consecutives"] = 0
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
 sauvegarder_csv(trade)
 if "listing" in status.lower():
 envoyer_whatsapp(f" APEX: {symbol} - {status}")
 risk.check_kill_switch()
 # === AJOUT JOUR 1 ===
 risk.check_pertes_consecutives()
 return trade

def executer_trade_logic(symbol, prix_entree, prix_cible, spread, slippage):
 check_daily_reset()
 if STATE["is_kill_switch_global"]: return {"status": "refusé", "raison": "Kill Switch Global -8%"}
 if not STATE["is_bot_active"]: return {"status": "refusé", "raison": "Bot OFF"}
 if STATE["latence_ms"] > CONFIG["LATENCE_MAX_MS"]: return {"status": "refusé", "raison": f"Latence {STATE['latence_ms']}ms"}
 if not quota.check_and_add(5): return {"status": "refusé", "raison": "Quota 80%"}
 if not btc_filter.check(): return {"status": "refusé", "raison": "Filtre BTC"}
 # === AJOUT JOUR 1 - On ajoute Dominance sans enlever Filtre BTC ===
 if not btc_filter.check_dominance(): return {"status": "refusé", "raison": "Filtre Dominance BTC"}
 distance_sl = prix_entree * CONFIG["STOP_LOSS_TRADE"]
 if not risk.check_cout_et_rr(prix_entree, prix_cible, spread, slippage):
 return {"status": "refusé", "raison": "Coût ou R/R invalide"}
 taille = risk.taille_position(STATE["capital_total"], distance_sl)
 return {"status": "accepté", "taille": round(taille,2), "ordre": "LIMIT Post-Only 300ms", "capital": STATE["capital_total"]}

# ============== AJOUT JOUR 1 - HOOK POUR listing_watcher.py (étape suivante) ==============
# Le Surveilleur appellera cette fonction, pas un print(). On prépare déjà la connexion.
def on_nouveau_listing(titre, symbol=""):
 """Appelée par listing_watcher quand un vrai 'Will List' est détecté."""
 # Anti-doublon : si c'est le même titre que la dernière fois, on ignore
 if titre == STATE.get("dernier_listing_titre", ""):
 print(f" Listing déjà vu, ignoré: {titre}")
 return {"status": "ignoré", "raison": "Déjà vu"}
 STATE["dernier_listing_titre"] = titre
 STATE["dernier_listing_symbol"] = symbol
 STATE["dernier_listing_heure"] = datetime.now().strftime("%H:%M:%S")
 msg = f" NOUVEAU LISTING BINANCE: {titre} {symbol}"
 print(msg)
 # WhatsApp en veille comme tu veux, mais l'alerte est envoyée si apikey mise
 envoyer_whatsapp(msg)
 # Si le bot est ON, on ne trade pas en auto ici, on laisse executer_trade_logic décider via api.py
 # Pour les étapes suivantes, api.py lira STATE['dernier_listing_titre']
 return {"status": "nouveau", "titre": titre, "symbol": symbol}