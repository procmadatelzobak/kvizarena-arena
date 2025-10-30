#!/bin/bash
# Instalační skript pro KvízArénu na Ubuntu 25.10+
set -e

echo "=== Spouštím instalaci KvízAréna Serveru ==="

# Krok 1: Aktualizace systému a instalace základních balíčků
echo "[1/4] Aktualizace balíčků a instalace python3-venv..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Krok 2: Kontrola a vytvoření virtuálního prostředí
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[2/4] Vytvářím virtuální prostředí (venv)..."
    python3 -m venv $VENV_DIR
else
    echo "[2/4] Virtuální prostředí (venv) již existuje."
fi

# Krok 3: Aktivace prostředí a instalace závislostí
echo "[3/4] Aktivuji prostředí a instaluji závislosti z requirements.txt..."
source $VENV_DIR/bin/activate
pip install -r requirements.txt
deactivate

# Krok 4: Vytvoření .env souboru (pokud neexistuje)
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "[4/4] Vytvářím .env soubor z .env.example..."
    cp .env.example .env
    # Vygenerujeme nový tajný klíč
    NEW_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(24))')
    sed -i "s/SECRET_KEY=change-me/SECRET_KEY=$NEW_KEY/" .env
    echo "DŮLEŽITÉ: .env soubor byl vytvořen. Zkontrolujte jeho obsah."
else
    echo "[4/4] Soubor .env již existuje."
fi

echo "=== Instalace dokončena ==="
echo "Pro spuštění databáze (pouze poprvé):"
echo "  source venv/bin/activate"
echo "  flask init-db"
echo ""
echo "Pro spuštění aplikace použijte skript ./run.sh"
