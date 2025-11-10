import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime
import threading
from flask import Flask
import asyncio
from telegram import Bot

# === CONFIGURAZIONE ===
URL = "https://www.bonusveicolielettrici.mase.gov.it/index.html"
STATE_FILE = "status_bonus.json"

# Inserisci i tuoi dati Telegram (oppure usa variabili d'ambiente)
BOT_TOKEN = os.getenv("BOT_TOKEN") or "INSERIRE_QUA_TOKEN_TG"
CHAT_ID = os.getenv("CHAT_ID") or "INSERIRE_QUA_CHAT_ID_TG"

CHECK_INTERVAL = 60  # secondi tra un controllo e l'altro
MESSAGGIO_ESAURITI = "tutte le risorse risultano al momento prenotate".lower()

app = Flask(__name__)


def estrai_stato():
    """Scarica la pagina e verifica se il messaggio di fondi esauriti è presente."""
    try:
        r = requests.get(URL, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True).lower()
        return "esauriti" if MESSAGGIO_ESAURITI in text else "disponibili"
    except Exception as e:
        print(f"[{datetime.now()}] Errore durante il controllo: {e}")
        return None


def leggi_stato_precedente():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f).get("status")
    except Exception:
        return None


def salva_stato(stato):
    with open(STATE_FILE, "w") as f:
        json.dump({"status": stato, "timestamp": datetime.now().isoformat()}, f)


async def invia_notifica_async(messaggio):
    """Invia il messaggio Telegram in modalità asincrona"""
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=messaggio)
        print(f"[{datetime.now()}] ✅ Notifica inviata: {messaggio}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Errore invio notifica: {e}")


def invia_notifica(messaggio):
    asyncio.run(invia_notifica_async(messaggio))


def monitor_loop():
    print("=== Monitor Bonus Veicoli Elettrici avviato ===")
    print(f"Controllo ogni {CHECK_INTERVAL} secondi...\n")

    while True:
        stato_corrente = estrai_stato()
        stato_precedente = leggi_stato_precedente()

        if stato_corrente and stato_corrente != stato_precedente:
            salva_stato(stato_corrente)
            messaggio = (
                f"⚡ Stato fondi cambiato: {stato_precedente or 'sconosciuto'} → {stato_corrente.upper()}\n"
                f"🔗 {URL}"
            )
            invia_notifica(messaggio)
        else:
            print(f"[{datetime.now()}] Nessun cambiamento ({stato_corrente})")

        time.sleep(CHECK_INTERVAL)


@app.route("/")
def home():
    return f"<h3>Monitor attivo ✅</h3><p>Ultimo controllo: {datetime.now()}</p>"


if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
