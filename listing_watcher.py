# listing_watcher.py - VERSION FINALE 100% ANTI-CRASH
import requests
import threading
import time
import re

watcher_thread = None
is_running = False

# === AJOUT JOUR 2 - Mémoire anti-doublon + config pour les autres étapes ===
# On ne supprime rien, on ajoute juste la mémoire que bot.py utilisera aussi
dernier_titre_vu = ""
dernier_symbol_vu = ""
intervalle_secondes = 60 # Sera modifiable depuis Flutter / api.py plus tard
_callback_bot = None # Pour éviter import circulaire, api.py branchera bot.on_nouveau_listing

def set_callback_bot(callback):
 """Appelée par api.py / bot.py pour brancher la connexion. Évite l'import circulaire."""
 global _callback_bot
 _callback_bot = callback

def set_intervalle(secondes):
 """Pour Flutter étape suivante : changer l'intervalle depuis les Paramètres."""
 global intervalle_secondes
 try:
 s = int(secondes)
 if 10 <= s <= 300:
 intervalle_secondes = s
 except Exception:
 pass

def extraire_symbol(titre):
 """AJOUT JOUR 2 : Extrait le symbole ex: 'Binance Will List XYZ (XYZ)' -> 'XYZ'"""
 if not titre:
 return ""
 # Cherche le pattern (XXX) à la fin, ex: Binance Will List PEPE (PEPE)
 m = re.findall(r"\(([A-Z0-9]{2,15})\)", titre.upper())
 if m:
 return m[-1]
 # Sinon cherche "Will List XXX"
 m2 = re.search(r"WILL LIST\s+([A-Z0-9]{2,15})", titre.upper())
 if m2:
 return m2.group(1)
 return ""

def est_vrai_listing(titre):
 """AJOUT JOUR 2 : Filtre - seulement les vrais listings, pas maintenance / delisting / promo"""
 if not titre:
 return False
 t = titre.lower()
 # On refuse tout ce qui n'est pas un listing
 if any(x in t for x in ["delist", "maintenance", "suspend", "remove", "promotion", "airdrop", "earn", "futures", "margin"]):
 return False
 # On accepte seulement Will List / New Listing / Lists
 if "will list" in t or "lists " in t or "new listing" in t or "will support" in t:
 return True
 return False

def check_new_listing():
 global dernier_titre_vu, dernier_symbol_vu
 try:
 url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?current=1&size=5&type=1"
 headers = {"User-Agent": "Mozilla/5.0"}
 r = requests.get(url, headers=headers, timeout=10)

 if r.status_code!= 200:
 return {"nouveau": False, "message": f"Binance répond {r.status_code}, mais surveilleur OK"}

 data = r.json()
 if not data:
 return {"nouveau": False, "message": "Réponse vide, mais surveilleur OK"}

 # On cherche les articles sans crasher
 articles = []
 if isinstance(data, dict):
 d = data.get("data")
 if isinstance(d, dict):
 articles = d.get("catalogs") or d.get("articles") or d.get("list") or []
 elif isinstance(d, list):
 articles = d

 if not articles:
 return {"nouveau": False, "message": "Pas de nouveau listing pour l'instant - Surveilleur ACTIF"}

 first = articles[0]
 titre = "Nouvelle annonce Binance"
 if isinstance(first, dict):
 titre = first.get("title") or first.get("name") or titre

 # === AJOUT JOUR 2 - 1. Filtre Will List ===
 if not est_vrai_listing(titre):
 return {"nouveau": False, "message": f"Annonce ignorée (pas un listing): {titre}", "titre": titre, "source": "Binance API Live"}

 # === AJOUT JOUR 2 - 2. Mémoire anti-doublon ===
 if titre == dernier_titre_vu:
 return {"nouveau": False, "message": "Même annonce déjà vue - Surveilleur ACTIF", "titre": titre, "source": "Binance API Live"}

 # C'est vraiment nouveau
 symbol = extraire_symbol(titre)
 dernier_titre_vu = titre
 dernier_symbol_vu = symbol

 # === AJOUT JOUR 2 - 3. Connexion à bot.py (sans casser si bot pas dispo) ===
 # On essaie le callback branché par api.py, sinon import direct de bot
 try:
 if _callback_bot is not None:
 _callback_bot(titre, symbol)
 else:
 # Import ici, pas en haut, pour éviter boucle import bot <-> watcher
 import bot as bot_module
 # On sync aussi STATE de bot.py pour que api.py / Flutter le lisent
 bot_module.STATE["dernier_listing_titre"] = titre
 bot_module.STATE["dernier_listing_symbol"] = symbol
 if hasattr(bot_module, "on_nouveau_listing"):
 bot_module.on_nouveau_listing(titre, symbol)
 except Exception as e:
 # Anti-crash : même si bot.py échoue, le watcher ne plante pas
 print(f" Watcher -> bot connexion échouée (non bloquant): {e}")

 return {"nouveau": True, "titre": titre, "symbol": symbol, "source": "Binance API Live"}

 except Exception as e:
 return {"nouveau": False, "message": "Surveilleur OK - en attente Binance", "erreur": str(e)}

def loop_watcher():
 global is_running
 print(" Surveillance Binance lancée")
 while is_running:
 result = check_new_listing()
 if result.get("nouveau"):
 print(f" NOUVEAU LISTING DÉTECTÉ: {result.get('titre')} - Symbol: {result.get('symbol','')}")
 # === AJOUT JOUR 2 - Intervalle variable, pas 60 en dur ===
 # On dort par petits bouts pour s'arrêter vite si stop_watcher() est appelé
 for _ in range(int(intervalle_secondes)):
 if not is_running:
 break
 time.sleep(1)
 print(" Surveillance arrêtée")

def start_watcher():
 global watcher_thread, is_running
 if is_running: return
 is_running = True
 # === AJOUT JOUR 2 - Sync avec bot.py pour que Flutter affiche ACTIF ===
 try:
 import bot as bot_module
 bot_module.STATE["watcher_actif"] = True
 except Exception:
 pass
 watcher_thread = threading.Thread(target=loop_watcher, daemon=True)
 watcher_thread.start()

def stop_watcher():
 global is_running
 is_running = False
 # === AJOUT JOUR 2 - Sync avec bot.py ===
 try:
 import bot as bot_module
 bot_module.STATE["watcher_actif"] = False
 except Exception:
 pass

# === AJOUT JOUR 2 - Pour api.py / Flutter : statut du surveilleur ===
def get_watcher_status():
 return {
 "is_running": is_running,
 "watcher_actif": is_running,
 "dernier_titre": dernier_titre_vu,
 "dernier_symbol": dernier_symbol_vu,
 "intervalle": intervalle_secondes,
 }