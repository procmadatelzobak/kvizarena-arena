# KvízAréna - Herní Server (Aréna)

Toto je backendový server pro projekt KvízAréna, určený pro hraní kvízů. Jedná se o samostatnou Flask aplikaci, která obsluhuje herní logiku, spravuje databázi kvízů a (v budoucnu) profily hráčů.

## Klíčové vlastnosti

* **Zabezpečená herní logika:** Server validuje všechny odpovědi. Klient nikdy nezná správnou odpověď předem.
* **Časové limity:** Server hlídá časové limity pro odpovědi na otázky.
* **Správa kvízů:** Administrátorské rozhraní pro import kvízů ve formátu CSV (exportovaných z modulu Vševěd).
* **Herní API:** REST API pro komunikaci s webovým/mobilním klientem (PWA).

## Nastavení a spuštění (MVP)

1.  **Klonování repozitáře:**
    ```bash
    git clone [URL_VAŠEHO_REPOZITÁŘE]
    cd kvizarena-arena
    ```

2.  **Vytvoření virtuálního prostředí:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # (Nebo venv\Scripts\activate.bat na Windows)
    ```

3.  **Instalace závislostí:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Spuštění aplikace:**
    ```bash
    flask run
    ```
