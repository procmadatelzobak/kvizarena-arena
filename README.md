# KvízAréna - Herní Server (Aréna)

Toto je backendový server pro projekt KvízAréna, určený pro hraní kvízů. Jedná se o samostatnou Flask aplikaci, která obsluhuje herní logiku, spravuje databázi kvízů a (v budoucnu) profily hráčů.

## Klíčové vlastnosti

* **Zabezpečená herní logika:** Server validuje všechny odpovědi. Klient nikdy nezná správnou odpověď předem.
* **Časové limity:** Server hlídá časové limity pro odpovědi na otázky.
* **Správa kvízů:** Administrátorské rozhraní pro import kvízů ve formátu CSV (exportovaných z modulu Vševěd).
* **Herní API:** REST API pro komunikaci s webovým/mobilním klientem (PWA).

## Automatická instalace na Ubuntu 25.10+

Pro rychlé zprovoznění serveru na Ubuntu 25.10 a novějším můžete použít skript
`scripts/install_server.sh`, který provede veškeré kroky za vás:

```bash
chmod +x scripts/install_server.sh
./scripts/install_server.sh
```

Skript aktualizuje systémové balíčky, vytvoří (nebo znovu použije) virtuální
prostředí, nainstaluje závislosti z `requirements.txt` a připraví `.env` soubor
na základě šablony `.env.example` včetně vygenerování nového `SECRET_KEY`.

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

4.  **Inicializace databáze:**
    ```bash
    flask --app app init-db
    ```

5.  **Spuštění aplikace:**
    ```bash
    ./run.sh
    ```

    Spouštěcí skript automaticky aktivuje vytvořené virtuální prostředí, ověří existenci
    databázového souboru z hodnoty `DATABASE_URL` v souboru `.env` (nebo použije výchozí
    `kvizarena.db`) a v případě potřeby databázi inicializuje příkazem `flask init-db`.
    Server následně spustí ve vývojovém režimu na portu definovaném proměnnou `PORT` (výchozí
    `5000`).

## Administrátorské rozhraní

Po spuštění serveru je možné otevřít administraci na adrese `http://localhost:5000/admin/kvizy`.
Rozhraní umožňuje:

* zobrazit existující kvízy včetně počtu přiřazených otázek a mazat je,
* vytvořit nový kvíz pomocí jednoduchého formuláře,
* importovat kvíz z CSV souboru. CSV musí obsahovat sloupce `otazka`, `spravna_odpoved`,
  `spatna_odpoved1`, `spatna_odpoved2`, `spatna_odpoved3` a volitelně `tema`, `obtiznost`,
  `zdroj_url`.

Sekce pro vytváření a import kvízů jsou zobrazeny v samostatných kartách vedle sebe a stránka
navíc zvýrazňuje flash zprávy (úspěch/varování/chyba), aby administrátor okamžitě viděl výsledek
provedené akce.

Při importu se existující otázky (podle textu) znovu nevytvářejí, místo toho se znovu využijí.
Řádky s nekompletními údaji se bezpečně přeskočí a zaznamenají do logu, takže vadný CSV
soubor nezastaví import celého kvízu.
