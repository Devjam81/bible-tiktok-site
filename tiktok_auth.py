"""
╔══════════════════════════════════════════════════════════╗
║         TIKTOK OAUTH 2.0 — Obtenir ton access token     ║
╚══════════════════════════════════════════════════════════╝

Lance ce script UNE FOIS pour connecter ton compte TikTok.
Le token sera sauvegardé dans .env automatiquement.

Usage:
    python tiktok_auth.py
"""

import os
import json
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_KEY    = os.getenv("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
REDIRECT_URI  = "https://devjam81.github.io/bible-tiktok-site/callback"
SCOPE         = "video.publish,user.info.basic"

# État OAuth (anti-CSRF)
STATE = "bible_tiktok_bot_2026"

# Token reçu
received_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global received_code
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            if "code" in params:
                received_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"""
                <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#1a1a2e;color:white">
                <h1 style="color:#FFD700">&#10003; Connexion reussie!</h1>
                <p>Tu peux fermer cette fenetre et retourner au terminal.</p>
                </body></html>
                """)
            else:
                self.send_response(400)
                self.end_headers()
                error = params.get("error", ["inconnu"])[0]
                print(f"\n❌ Erreur TikTok: {error}")

    def log_message(self, format, *args):
        pass  # Silencer les logs HTTP


def get_authorization_url() -> str:
    base = "https://www.tiktok.com/v2/auth/authorize/"
    params = (
        f"client_key={CLIENT_KEY}"
        f"&scope={SCOPE}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={STATE}"
    )
    return f"{base}?{params}"


def exchange_code_for_token(code: str) -> dict:
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    payload = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()


def save_tokens(token_data: dict):
    """Sauvegarde les tokens dans .env"""
    env_file = ".env"
    set_key(env_file, "TIKTOK_ACCESS_TOKEN", token_data["access_token"])
    set_key(env_file, "TIKTOK_REFRESH_TOKEN", token_data["refresh_token"])
    set_key(env_file, "TIKTOK_OPEN_ID", token_data["open_id"])
    print(f"\n✅ Tokens sauvegardés dans .env")
    print(f"   open_id: {token_data['open_id']}")
    print(f"   expires_in: {token_data['expires_in']}s (~24h)")
    print(f"   refresh_token valable: {token_data.get('refresh_expires_in', '?')}s (~1 an)")


def refresh_access_token():
    """Rafraîchit le token avant qu'il expire (à appeler chaque jour)."""
    load_dotenv()
    refresh_token = os.getenv("TIKTOK_REFRESH_TOKEN")
    if not refresh_token:
        print("❌ Pas de refresh token — relance tiktok_auth.py")
        return

    url = "https://open.tiktokapis.com/v2/oauth/token/"
    payload = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=payload, headers=headers)
    data = resp.json()

    if "access_token" in data:
        set_key(".env", "TIKTOK_ACCESS_TOKEN", data["access_token"])
        if "refresh_token" in data:
            set_key(".env", "TIKTOK_REFRESH_TOKEN", data["refresh_token"])
        print("✅ Token rafraîchi avec succès")
    else:
        print(f"❌ Erreur refresh: {data}")


if __name__ == "__main__":
    import sys

    if "--refresh" in sys.argv:
        refresh_access_token()
        exit()

    if not CLIENT_KEY or not CLIENT_SECRET:
        print("❌ TIKTOK_CLIENT_KEY et TIKTOK_CLIENT_SECRET manquants dans .env")
        print("   → Va sur https://developers.tiktok.com et crée une app")
        exit(1)

    print("\n" + "="*55)
    print("  TIKTOK AUTH — Connexion de ton compte")
    print("="*55)
    print("\n1. Une fenêtre va s'ouvrir dans ton navigateur")
    print("2. Connecte-toi avec ton compte TikTok")
    print("3. Autorise l'application")
    print("4. Reviens ici — le token sera sauvegardé auto\n")
    input("Appuie sur ENTRÉE pour continuer...")

    auth_url = get_authorization_url()
    webbrowser.open(auth_url)
    print(f"\n🌐 URL ouverte: {auth_url}\n")

    # Serveur local pour recevoir le callback
    server = HTTPServer(("localhost", 8888), CallbackHandler)
    print("⏳ En attente du callback TikTok (port 8888)...")

    while received_code is None:
        server.handle_request()

    print(f"\n✅ Code reçu! Échange contre un token...")
    token_data = exchange_code_for_token(received_code)
    save_tokens(token_data)
    print("\n🎉 Configuration terminée! Tu peux lancer bible_tiktok_bot.py")
