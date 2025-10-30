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
