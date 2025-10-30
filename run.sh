#!/bin/bash
# Spouštěcí skript pro KvízArénu

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
VENV_PATH="$SCRIPT_DIR/venv/bin/activate"

if [ ! -f "$VENV_PATH" ]; then
    echo "Chyba: Virtuální prostředí nebylo nalezeno."
    echo "Nejprve spusť instalační skript ./setup.sh"
    exit 1
fi

# Aktivace prostředí
echo "Aktivuji virtuální prostředí..."
source $VENV_PATH

# Přesun do adresáře se skriptem (pokud je třeba)
cd "$SCRIPT_DIR"

# Kontrola, zda byla databáze inicializována
DB_FILE=$(grep "DATABASE_URL" .env | cut -d'/' -f3)
if [ -z "$DB_FILE" ]; then
    DB_FILE="kvizarena.db" # Výchozí, pokud .env selže
fi

if [ ! -f "$DB_FILE" ]; then
    echo "POZOR: Databáze '$DB_FILE' nebyla nalezena."
    echo "Spouštím inicializaci databáze (flask init-db)..."
    flask init-db
    echo "Databáze vytvořena."
fi

echo "Spouštím server KvízAréna (Flask development server)..."
echo "Aplikace poběží na: http://127.0.0.1:5000"
echo "(Pro produkční nasazení použijte gunicorn nebo waitress)"

# Načtení portu z .env, výchozí je 5000
PORT=$(grep "PORT=" .env | cut -d'=' -f2)
: ${PORT:=5000}

flask run --host=0.0.0.0 --port=$PORT
