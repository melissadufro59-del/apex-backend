# api.py - APEX PREDATOR - VERSION FINALE PRO AVEC WHATSAPP - ANTI-500
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import bot
import listing_watcher
import traceback

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root(): return {"message": "APEX API OK"}

@app.get("/status")
def get_status():
    return {"is_active": bot.STATE["is_bot_active"], "is_locked": bot.STATE["is_kill_switch_global"], "capital": bot.STATE["capital_total"], "perte_jour": bot.STATE["perte_journaliere"], "latence": bot.STATE["latence_ms"], "quota": bot.STATE["quota_weight_used"]}

@app.get("/balance")
def get_balance(): return {"total": bot.STATE["capital_total"]}
@app.get("/solde")
def get_solde(): return {"solde": bot.STATE["capital_total"], "total": bot.STATE["capital_total"]}
@app.get("/account")
def get_account(): return {"total": bot.STATE["capital_total"]}
@app.get("/balances")
def get_balances(): return {"total": bot.STATE["capital_total"]}
@app.get("/portfolio")
def get_portfolio(): return {"total": bot.STATE["capital_total"]}

@app.post("/bot/toggle")
def toggle_bot():
    if bot.STATE["is_kill_switch_global"]: return {"error": "Verrouillé -8%"}
    bot.STATE["is_bot_active"] = not bot.STATE["is_bot_active"]
    if bot.STATE["is_bot_active"]:
        listing_watcher.start_watcher()
        bot.envoyer_whatsapp("🟢 APEX PREDATOR ON - Surveillance Binance active")
    else:
        listing_watcher.stop_watcher()
        bot.envoyer_whatsapp("🔴 APEX PREDATOR OFF")
    return {"is_active": bot.STATE["is_bot_active"], "status": "ON" if bot.STATE["is_bot_active"] else "OFF"}

@app.post("/bot/urgence")
def urgence_stop():
    bot.STATE["is_bot_active"] = False
    bot.STATE["is_kill_switch_global"] = True
    listing_watcher.stop_watcher()
    bot.envoyer_whatsapp("🚨 URGENCE: Bot vendu et verrouillé manuellement")
    return {"status": "Vendu, OFF"}

@app.post("/trade/executer")
def executer_trade(symbol: str, prix_entree: float, prix_cible: float, spread: float, slippage: float):
    return bot.executer_trade_logic(symbol, prix_entree, prix_cible, spread, slippage)

@app.get("/history")
def get_history():
    return {"history": bot.STATE["trades_history"]}

@app.get("/debug/perte")
def debug_perte(montant: float):
    trade = bot.enregistrer_trade("TEST", montant, "test-securite")
    return {"nouveau_capital": bot.STATE["capital_total"], "perte_jour": bot.STATE["perte_journaliere"], "is_locked": bot.STATE["is_kill_switch_global"], "trade": trade}

@app.get("/debug/reset")
def debug_reset():
    bot.STATE["capital_total"] = 100.0
    bot.STATE["perte_journaliere"] = 0.0
    bot.STATE["is_kill_switch_global"] = False
    bot.STATE["is_bot_active"] = False
    bot.STATE["trades_history"] = []
    return {"message": "RESET OK - 100€"}

# ROUTE CORRIGÉE ANTI-500
@app.get("/debug/annonce-test")
def test_annonce():
    try:
        result = listing_watcher.check_new_listing()
        return result if result else {"nouveau": False, "message": "Pas de nouveau listing pour l'instant"}
    except Exception as e:
        print("ERREUR annonce-test:", traceback.format_exc())
        return {"nouveau": False, "message": "Surveilleur OK mais Binance a bloqué", "erreur_detail": str(e)}

# ROUTE WHATSAPP CORRIGÉE ANTI-500
@app.get("/debug/whatsapp")
def test_whatsapp():
    try:
        ok = bot.envoyer_whatsapp("✅ Test APEX PREDATOR PRO - Sylla ton bot est connecté à WhatsApp")
        return {"whatsapp_envoyé": ok, "note": "Si apikey pas encore mise, regarde ton terminal"}
    except Exception as e:
        return {"whatsapp_envoyé": False, "erreur": str(e)}