# api.py - APEX PREDATOR - VERSION FINALE RAILWAY + TESTNET + ANTI-500
from fastapi import FastAPI, Header, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import csv
import secrets
from dotenv import load_dotenv
import bot
import listing_watcher
import traceback

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ============== AJOUT JOUR 3 - LOGIN + PROTECTION DEBUG ==============
# Mot de passe dans Railway Variables : APEX_PASSWORD (par défaut apex1234 à changer)
APEX_PASSWORD = os.getenv("APEX_PASSWORD", "apex1234")
# Token simple en mémoire, pour Flutter étape suivante
_tokens_valides = set()

def verifier_admin(mdp: str = None, x_api_key: str = None, authorization: str = None):
 """Vérifie mot de passe OU token. Retourne True si OK."""
 # 1. Token déjà obtenu via /login
 if authorization and authorization.startswith("Bearer "):
 if authorization.replace("Bearer ", "").strip() in _tokens_valides:
 return True
 if x_api_key and x_api_key in _tokens_valides:
 return True
 # 2. Mot de passe direct
 if mdp and secrets.compare_digest(mdp, APEX_PASSWORD):
 return True
 if x_api_key and secrets.compare_digest(x_api_key, APEX_PASSWORD):
 return True
 return False

def _check_debug_auth(mdp: str = None, x_api_key: str = None, authorization: str = None):
 if not verifier_admin(mdp, x_api_key, authorization):
 return {"error": "Mot de passe requis pour debug", "need_login": True}
 return None

# Branche le watcher vers bot.py une seule fois au démarrage (Jour 1 + Jour 2)
try:
 if hasattr(listing_watcher, "set_callback_bot") and hasattr(bot, "on_nouveau_listing"):
 listing_watcher.set_callback_bot(bot.on_nouveau_listing)
except Exception as e:
 print(f" Branchement watcher->bot échoué (non bloquant): {e}")

@app.get("/")
def root(): 
 return {
 "message": "APEX API OK", 
 "testnet": os.getenv("BINANCE_TESTNET","true"),
 "binance_url": bot.BINANCE_BASE_URL
 }

# ============== AJOUT JOUR 3 - LOGIN pour Flutter ==============
@app.post("/login")
def login(mdp: str = Query(None), password: str = Query(None)):
 """Flutter appellera /login?mdp=TON_MDP - retourne un token à garder."""
 mot = mdp or password or ""
 if mot and secrets.compare_digest(mot, APEX_PASSWORD):
 token = secrets.token_urlsafe(24)
 _tokens_valides.add(token)
 return {"ok": True, "token": token, "message": "Login OK"}
 return {"ok": False, "error": "Mot de passe incorrect"}

@app.get("/auth/check")
def auth_check(authorization: str = Header(None), x_api_key: str = Header(None)):
 ok = verifier_admin(None, x_api_key, authorization)
 return {"auth": ok}

@app.get("/status")
def get_status():
 return {"is_active": bot.STATE["is_bot_active"], "is_locked": bot.STATE["is_kill_switch_global"], "capital": bot.STATE["capital_total"], "perte_jour": bot.STATE["perte_journaliere"], "latence": bot.STATE["latence_ms"], "quota": bot.STATE["quota_weight_used"],
 # === AJOUT JOUR 3 - Pour Flutter, tout en une seule route ===
 "pertes_consecutives": bot.STATE.get("pertes_consecutives", 0),
 "watcher_actif": bot.STATE.get("watcher_actif", False),
 "dernier_listing_titre": bot.STATE.get("dernier_listing_titre", ""),
 "dernier_listing_symbol": bot.STATE.get("dernier_listing_symbol", ""),
 "solde_binance_reel": bot.STATE.get("solde_binance_reel", bot.STATE["capital_total"]),
 }

# ============== BALANCE REEL TESTNET ==============
# === AJOUT JOUR 3 - On re-lit Binance en direct, plus seulement STATE au démarrage ===
@app.get("/balance")
def get_balance(): 
 try:
 # Re-lecture directe (fonction Jour 1)
 if hasattr(bot, "refresh_solde_reel"):
 reel = bot.refresh_solde_reel()
 if reel is not None:
 return {"total": reel, "capital": bot.STATE["capital_total"], "solde_binance_reel": reel}
 except Exception as e:
 print(f" Balance refresh échoué: {e}")
 return {"total": bot.STATE["capital_total"]}
@app.get("/solde")
def get_solde(): 
 try:
 if hasattr(bot, "refresh_solde_reel"):
 reel = bot.refresh_solde_reel()
 if reel is not None:
 return {"solde": reel, "total": reel, "capital": bot.STATE["capital_total"]}
 except Exception:
 pass
 return {"solde": bot.STATE["capital_total"], "total": bot.STATE["capital_total"]}
@app.get("/account")
def get_account(): 
 return {"total": bot.STATE["capital_total"]}
@app.get("/balances")
def get_balances(): 
 return {"total": bot.STATE["capital_total"]}
@app.get("/portfolio")
def get_portfolio(): 
 return {"total": bot.STATE["capital_total"]}

# ============== AJOUT JOUR 3 - STATUT + INTERVALLE SURVEILLEUR ==============
@app.get("/watcher/status")
def watcher_status():
 try:
 if hasattr(listing_watcher, "get_watcher_status"):
 return listing_watcher.get_watcher_status()
 except Exception as e:
 print(f" watcher/status: {e}")
 return {"is_running": getattr(listing_watcher, "is_running", False), "watcher_actif": bot.STATE.get("watcher_actif", False), "dernier_titre": bot.STATE.get("dernier_listing_titre", ""), "dernier_symbol": bot.STATE.get("dernier_listing_symbol", "")}

@app.post("/watcher/interval")
def watcher_interval(secondes: int = 60):
 try:
 if hasattr(listing_watcher, "set_intervalle"):
 listing_watcher.set_intervalle(secondes)
 except Exception as e:
 print(f" watcher/interval: {e}")
 return {"intervalle": getattr(listing_watcher, "intervalle_secondes", secondes)}

@app.post("/bot/toggle")
def toggle_bot():
 if bot.STATE["is_kill_switch_global"]: return {"error": "Verrouillé -8%"}
 bot.STATE["is_bot_active"] = not bot.STATE["is_bot_active"]
 if bot.STATE["is_bot_active"]:
 listing_watcher.start_watcher()
 bot.envoyer_whatsapp(" APEX PREDATOR ON - Surveillance Binance active")
 else:
 listing_watcher.stop_watcher()
 bot.envoyer_whatsapp(" APEX PREDATOR OFF")
 return {"is_active": bot.STATE["is_bot_active"], "status": "ON" if bot.STATE["is_bot_active"] else "OFF"}

@app.post("/bot/urgence")
def urgence_stop():
 bot.STATE["is_bot_active"] = False
 bot.STATE["is_kill_switch_global"] = True
 listing_watcher.stop_watcher()
 bot.envoyer_whatsapp(" URGENCE: Bot vendu et verrouillé manuellement")
 return {"status": "Vendu, OFF"}

@app.post("/trade/executer")
def executer_trade(symbol: str, prix_entree: float, prix_cible: float, spread: float, slippage: float):
 return bot.executer_trade_logic(symbol, prix_entree, prix_cible, spread, slippage)

@app.get("/history")
def get_history():
 return {"history": bot.STATE["trades_history"]}

# NOUVEAU: Pour Netlify lire trades.csv direct
@app.get("/trades")
def get_trades_csv():
 try:
 if not os.path.exists("trades.csv"):
 return {"trades": []}
 trades = []
 with open("trades.csv", "r", encoding="utf-8") as f:
 reader = csv.DictReader(f)
 for row in reader:
 trades.insert(0, row)
 return {"trades": trades[:50]}
 except Exception as e:
 return {"trades": [], "erreur": str(e)}

# ============== AJOUT JOUR 3 - PROTECTION DES 2 ROUTES DANGEREUSES ==============
# On garde tes routes, on ajoute juste la vérification mot de passe en 1ère ligne
@app.get("/debug/perte")
def debug_perte(montant: float, mdp: str = Query(None), x_api_key: str = Header(None), authorization: str = Header(None)):
 err = _check_debug_auth(mdp, x_api_key, authorization)
 if err: return err
 trade = bot.enregistrer_trade("TEST", montant, "test-securite")
 return {"nouveau_capital": bot.STATE["capital_total"], "perte_jour": bot.STATE["perte_journaliere"], "is_locked": bot.STATE["is_kill_switch_global"], "trade": trade}

@app.get("/debug/reset")
def debug_reset(mdp: str = Query(None), x_api_key: str = Header(None), authorization: str = Header(None)):
 err = _check_debug_auth(mdp, x_api_key, authorization)
 if err: return err
 bot.STATE["capital_total"] = 100.0
 bot.STATE["perte_journaliere"] = 0.0
 bot.STATE["is_kill_switch_global"] = False
 bot.STATE["is_bot_active"] = False
 bot.STATE["trades_history"] = []
 # === AJOUT JOUR 3 - On reset aussi les nouveaux champs Jour 1 ===
 bot.STATE["pertes_consecutives"] = 0
 bot.STATE["dernier_listing_titre"] = ""
 bot.STATE["dernier_listing_symbol"] = ""
 bot.STATE["watcher_actif"] = False
 return {"message": "RESET OK - 100€"}

@app.get("/debug/annonce-test")
def test_annonce():
 try:
 result = listing_watcher.check_new_listing()
 return result if result else {"nouveau": False, "message": "Pas de nouveau listing pour l'instant"}
 except Exception as e:
 print("ERREUR annonce-test:", traceback.format_exc())
 return {"nouveau": False, "message": "Surveilleur OK mais Binance a bloqué", "erreur_detail": str(e)}

@app.get("/debug/whatsapp")
def test_whatsapp():
 try:
 ok = bot.envoyer_whatsapp(" Test APEX PREDATOR PRO - Sylla ton bot est connecté à WhatsApp")
 return {"whatsapp_envoyé": ok, "note": "Si apikey pas encore mise, regarde ton terminal"}
 except Exception as e:
 return {"whatsapp_envoyé": False, "erreur": str(e)}