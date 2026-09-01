# Agenda Hoquei Patins Catalunya (no oficial)

Aplicació web no oficial per cercar i filtrar el calendari de partits de
Hoquei Patins de la FECAPA. Les dades es descarreguen automàticament
**un cop al dia** des del backend públic de la FECAPA (sidgad) mitjançant
una GitHub Action, i es guarden a `data.json`. `index.html` simplement
llegeix aquest fitxer.

> ⚠️ Aquesta eina **no té cap vincle amb la FECAPA**. Fa servir dades
> públiques del seu portal de competicions. Pot contenir errors o quedar
> desactualitzada; per a informació oficial, consulta sempre
> https://www.hoqueipatins.fecapa.cat/ag/

## Com posar-ho en marxa (uns 10 minuts, gratuït)

1. **Crea un repositori nou a GitHub** (per exemple `agenda-hoquei-patins`),
   públic.
2. **Puja tots els fitxers d'aquesta carpeta** al repositori, mantenint
   l'estructura:
   ```
   index.html
   data.json
   scripts/update_data.py
   .github/workflows/update-data.yml
   ```
3. **Activa GitHub Pages**: al repositori, ves a *Settings → Pages* i
   configura "Deploy from a branch" → branch `main`, carpeta `/ (root)`.
   Al cap d'un minut tindràs l'app publicada a una URL del tipus
   `https://el-teu-usuari.github.io/agenda-hoquei-patins/`.
4. **Dona permisos d'escriptura a les Actions**: a *Settings → Actions →
   General → Workflow permissions*, selecciona **"Read and write
   permissions"** i desa. (Sense això, la Action no podrà fer *commit* del
   `data.json` actualitzat.)
5. **Prova-ho manualment un cop**: ves a la pestanya *Actions* del
   repositori, obre "Actualitza dades de l'agenda" i clica *"Run workflow"*.
   Si tot va bé, veuràs un commit nou amb el `data.json` actualitzat al cap
   d'un minut.

A partir d'aquí, la Action s'executarà tota sola cada dia a les 05:00 UTC i
mantindrà `data.json` — i per tant la web— al dia, sense que hagis de fer
res més.

## Si la Action falla

El backend de la FECAPA (`server2.sidgad.es`) no és una API pública
documentada — és l'endpoint intern que fa servir la seva pròpia pàgina.
Si en algun moment canvien alguna cosa (format de resposta, paràmetres
obligatoris, etc.), la Action fallarà i **no tocarà el `data.json` existent**
(l'app seguirà funcionant amb les últimes dades bones conegudes).

Per arreglar-ho:
1. Obre https://www.hoqueipatins.fecapa.cat/ag/ amb les eines de
   desenvolupador del navegador (pestanya *Network*, filtra per "sidgad").
2. Mira si la petició a `00_fecapa_agenda_1.php` porta algun paràmetre nou
   al *Payload*.
3. Actualitza el diccionari `POST_PARAMS` a `scripts/update_data.py` amb
   aquests paràmetres.
4. Si el format de la taula HTML ha canviat, ajusta l'expressió regular
   `ROW_RE` del mateix fitxer.

## Estructura de `data.json`

Per mantenir el fitxer petit, els partits es guarden com a arrays curts en
lloc d'objectes:

```json
{
  "generated": "01/09/2026 06:00 UTC",
  "comps": ["Nom competició 0", "Nom competició 1", ...],
  "venues": ["Nom pista 0", "Nom pista 1", ...],
  "clubs": [[idClub, "Nom oficial del club"], ...],
  "matches": [
    [compIdx, "dd/mm/aaaa", "hh:mm", "Equip local", "Equip visitant", "resultat o buit", venueIdx, idClub1, idClub2],
    ...
  ]
}
```

`index.html` reconstrueix aquesta informació en memòria en carregar la
pàgina.

## Executar l'actualització a mà (opcional)

Si tens Python 3 instal·lat:

```bash
pip install --upgrade pip
python3 scripts/update_data.py
```

Això sobreescriu `data.json` amb les dades més recents.
