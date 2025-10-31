# KvízAréna - Specifikace MVP (Minimum Viable Product)

Tento dokument definuje základní funkčnost (MVP) pro projekt **KvízAréna**, serverovou aplikaci určenou pro hraní kvízů.

## 1. Souhrn projektu

KvízAréna je serverová aplikace (backend) postavená na frameworku **Flask**. Jejím úkolem je spravovat databázi kvízů a poskytovat zabezpečené **JSON API** pro herní klienty (typicky webovou PWA).

Projekt je záměrně oddělen od **Vševěda** (nástroje pro tvorbu kvízů). Data (kvízy) se mezi těmito dvěma systémy přenášejí manuálně pomocí **CSV souborů**.

## 2. Klíčové technologie

* **Jazyk:** Python
* **Framework:** Flask (s využitím "Application Factory" a "Blueprints")
* **Databáze:** Flask-SQLAlchemy (navrženo pro SQLite s budoucí migrací na MariaDB/PostgreSQL)
* **Testování:** Pytest
* **Spouštění:** Skripty `setup.sh` a `run.sh`

## 3. Databázové schéma (MVP)

Databáze (`app/database.py`) obsahuje 4 hlavní modely:

1.  **`Otazka`**: Uchovává text otázky, 4 odpovědi (1 správná, 3 špatné) a metadata. Text otázky je unikátní.
2.  **`Kviz`**: Definuje kvíz jako celek. Obsahuje název, popis a klíčový atribut `time_limit_per_question` (časový limit na otázku v sekundách). Název kvízu je unikátní.
3.  **`KvizOtazky`**: Spojovací tabulka, která řadí otázky ke kvízům a definuje jejich pořadí (`poradi`).
4.  **`GameSession`**: Klíčová tabulka pro hraní. Uchovává stav aktivní hry pro anonymního hráče. Obsahuje `session_id` (UUID), `kviz_id_fk`, aktuální skóre (`score`), index otázky (`current_question_index`) a časové razítko poslední otázky (`last_question_timestamp`) pro validaci časového limitu.

## 4. Funkce implementované v MVP

MVP se skládá ze dvou hlavních modulů (Blueprintů):

### A. Admin Panel (Backend & Frontend)
* **Adresa:** `/admin/kvizy`
* **Účel:** Správa obsahu kvízů.
* **Funkce:**
    * **Zobrazení kvízů:** Seznam všech kvízů v databázi, včetně počtu otázek.
    * **Vytvoření kvízu:** Formulář pro manuální vytvoření nového (prázdného) kvízu s názvem, popisem a časovým limitem.
    * **Smazání kvízu:** Možnost smazat kvíz (díky `cascade` v databázi se smažou i související vazby na otázky).
    * **Import CSV:** Klíčová funkce pro nahrání CSV souboru (exportovaného z Vševěda).
        * Import automaticky vytvoří `Kviz`.
        * Při importu prochází řádky CSV. Pokud otázka (dle textu) v DB neexistuje, vytvoří ji.
        * Vytvoří vazby `KvizOtazky` a zachová pořadí z CSV.

### B. Herní API (Pouze Backend)
* **Adresa:** `/api/game/...`
* **Účel:** Poskytnutí zabezpečených endpointů pro herního klienta.
* **Bezpečnost:** Klient nikdy nezná správnou odpověď. Veškerá logika (skóre, časomíra) se počítá **výhradně na serveru**.
* **Endpointy:**
    * **`POST /api/game/start/<int:quiz_id>`**
        * **Akce:** Vytvoří novou `GameSession` v databázi.
        * **Vrací (JSON):** `session_id`, název kvízu, časový limit, celkový počet otázek a první otázku (s náhodně zamíchanými odpověďmi).
    * **`POST /api/game/answer`**
        * **Očekává (JSON):** `{ "session_id": "...", "answer_text": "..." }`
        * **Akce (Logika na serveru):**
            1.  Najde `GameSession` podle `session_id`.
            2.  Zkontroluje časový limit (porovnáním `time.time()` a `last_question_timestamp`).
            3.  Zkontroluje, zda `answer_text` odpovídá `spravna_odpoved` u aktuální otázky.
            4.  Pokud ano (a včas), zvýší `score` v session.
            5.  Posune `current_question_index` o 1.
            6.  Aktualizuje `last_question_timestamp`.
        * **Vrací (JSON, pokud hra pokračuje):** Výsledek (`is_correct`, `feedback`), text správné odpovědi, aktuální skóre a objekt `next_question` (s novými zamíchanými odpověďmi).
        * **Vrací (JSON, pokud hra skončila):** Výsledek, `quiz_finished: true` a `final_score`.

## 5. Chybějící komponenty (Další kroky)

Backend (Admin a API) je pro MVP hotový. Chybí následující komponenty, které jsou dalším krokem vývoje:

### A. Chybějící API Endpoint (Lobby)

Musí být vytvořen nový blueprint (nebo přidán do `game_api.py`), který umožní klientovi **zobrazit seznam dostupných kvízů**.

* **`GET /api/quizzes`**
    * **Akce:** Načte všechny kvízy z tabulky `Kviz`.
    * **Vrací (JSON):** Seznam objektů, každý obsahuje např. `kviz_id`, `nazev`, `popis` a `pocet_otazek`.

### B. Herní Klient (PWA)

Musí být vytvořen frontend (HTML, CSS, JavaScript), který bude komunikovat s hotovým API.

* **Technologie:** Responzivní web (PWA).
* **Obrazovka 1: Lobby (Seznam kvízů)**
    * Po načtení zavolá `GET /api/quizzes`.
    * Zobrazí seznam kvízů jako tlačítka.
* **Obrazovka 2: Hra**
    * Po kliknutí na kvíz zavolá `POST /api/game/start/<id>`.
    * Uloží si `session_id` z odpovědi.
    * Zobrazí herní rozhraní: text otázky, 4 tlačítka s odpověďmi, skóre, číslo otázky.
    * Spustí vizuální odpočet časového limitu (dle `time_limit` z odpovědi).
    * Po kliknutí na odpověď (nebo vypršení času) zavolá `POST /api/game/answer` a pošle `{ "session_id": "...", "answer_text": "..." }`.
    * Zobrazí výsledek (správně/špatně, zvýrazní správnou odpověď).
    * Pokud `quiz_finished: false`, zobrazí `next_question` a opakuje cyklus.
    * Pokud `quiz_finished: true`, zobrazí finální skóre.

## 6. Budoucí rozsah (Mimo MVP)

Následující nápady byly zmíněny v původním brainstormingu a jsou plánovány až po dokončení MVP:

* **Autentizace:** Přihlašování přes OAuth (Google, Apple).
* **Uživatelské účty:** Tabulka `users` (e-mail, nickname, role).
* **Gamifikace:** Systém "coinů", odměny za hraní.
* **Sociální funkce:** Vyzvání kamaráda, přímé souboje (Kvízová bitka).
* **Žebříčky:** Týdenní turnaje, globální skóre.
