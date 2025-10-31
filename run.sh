#!/bin/bash
# Spouštěcí skript pro KvízArénu (pro vývoj a testování na serveru)

# Zjistí absolutní cestu ke skriptu
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

# Přesun do adresáře se skriptem
cd "$SCRIPT_DIR"

# Nastavení proměnných prostředí pro Flask
export FLASK_APP=app
export FLASK_DEBUG=1

# Zjistíme název DB ze souboru .env, abychom mohli zkontrolovat její existenci
DB_URL=$(grep "DATABASE_URL=" .env | cut -d'=' -f2)
# Získáme cestu za 'sqlite:///'
DB_FILE=$(echo $DB_URL | sed 's#sqlite:///##')

# Výchozí hodnota, pokud by .env selhalo
if [ -z "$DB_FILE" ]; then
    DB_FILE="kvizarena.db"
fi

if [ ! -f "$DB_FILE" ]; then
    echo "POZOR: Databáze '$DB_FILE' nebyla nalezena."
    echo "Spouštím inicializaci databáze (flask init-db)..."
    # 'flask init-db' zavolá příkaz, který definujeme v app/database.py
    # Nyní bude fungovat díky 'export FLASK_APP=app'
    flask init-db
    if [ $? -eq 0 ]; then
        echo "Databáze úspěšně vytvořena."
    else
        echo "CHYBA: Selhala inicializace databáze."
        exit 1
    fi
fi

echo "Spouštím server KvízAréna (Flask development server)..."

# Načtení portu z .env, výchozí je 5000
PORT=$(grep "PORT=" .env | cut -d'=' -f2)
: ${PORT:=5000}

echo "Aplikace poběží na: [http://0.0.0.0](http://0.0.0.0):$PORT"
echo "(Pro produkční nasazení použijte gunicorn nebo waitress)"

# Spustí aplikaci standardním způsobem
flask run --host=0.0.0.0 --port=$PORT
