# listing_watcher.py - VERSION FINALE 100% ANTI-CRASH
import requests
import threading
import time

watcher_thread = None
is_running = False

def check_new_listing():
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

        return {"nouveau": True, "titre": titre, "source": "Binance API Live"}

    except Exception as e:
        return {"nouveau": False, "message": "Surveilleur OK - en attente Binance", "erreur": str(e)}

def loop_watcher():
    global is_running
    print("👁️ Surveillance Binance lancée")
    while is_running:
        result = check_new_listing()
        if result.get("nouveau"):
            print(f"🚀 NOUVEAU LISTING DÉTECTÉ: {result.get('titre')}")
        time.sleep(60)
    print("👁️ Surveillance arrêtée")

def start_watcher():
    global watcher_thread, is_running
    if is_running: return
    is_running = True
    watcher_thread = threading.Thread(target=loop_watcher, daemon=True)
    watcher_thread.start()

def stop_watcher():
    global is_running
    is_running = False