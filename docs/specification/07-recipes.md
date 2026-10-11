# 07 — Recipes

## 7.1 Recipe catalogue

- `RCP-001` Recipes are loaded at startup from a **recipe file** (default `recipes.json`, path configurable `recipes.file`, relative to the configuration file's directory, `Q-19`). If `recipes.file` is not set and the default file does not exist, the legacy catalogue shipped with the application is used; if `recipes.file` is set and the file does not exist, the application refuses to start (`Q-22`). Format: [data/recipes.schema.json](data/recipes.schema.json). `[NEW]` (legacy: recipes hard-coded in source code)
- `RCP-002` The initial recipe file MUST contain exactly the 8 legacy recipes of [data/recipes.json](data/recipes.json), in this order.
- `RCP-003` Invalid recipe file (syntax, schema, duplicate IDs, unknown goal type, missing parameter) → the application logs a precise error (file, recipe id, goal index) and **refuses to start**.
- `RCP-004` The catalogue is read-only at runtime (no recipe editing in the UI; see `Q-09`).
- `RCP-005` The list of recipes (`id`, `name`) is published to clients (`IF-030`).

## 7.2 Goal definition format

```json
{ "type": "HeatUp", "temperature": 62 }
{ "type": "Rest", "temperature": 62, "minutes": 30,
  "name": "Verzuckerungsrast", "description": "Verzuckerungsrast @62 for 30min" }
{ "type": "IodineTest", "temperature": 62, "minutes": 10 }
{ "type": "CookWater", "name": "Cooking Water", "description": "Cooking water for 20min", "minutes": 20 }
{ "type": "PourInBrewingWater" } { "type": "MashIn" } { "type": "Lautering" } { "type": "HeatUpForHopsCooking" }
```

| type | required | optional |
|---|---|---|
| `PourInBrewingWater` | – | – |
| `HeatUp` | `temperature` | – |
| `MashIn` | – | – |
| `Rest` | `temperature`, `minutes` | `name`, `description` (both or neither; default texts per `GOAL-004`) |
| `IodineTest` | `temperature`, `minutes` | – |
| `Lautering` | – | – |
| `HeatUpForHopsCooking` | – | – |
| `CookWater` | `name`, `description`, `minutes` | – |

Temperatures in °C (number, 0…110), minutes integer ≥ 0.

## 7.3 Legacy recipe catalogue (human-readable)

Recipe texts (including German names and legacy typos) are reproduced **verbatim**.

### 1. `ZORA` — `München 12.6 - SUD1:ZORA`
1. PourInBrewingWater
2. HeatUp 40
3. MashIn
4. HeatUp 50
5. Rest 50 °C / 25 min — `Maltoserast` / `Maltoserast @50 for 25min`
6. HeatUp 62
7. Rest 62 °C / 30 min — `Verzuckerungsrast` / `Verzuckerungsrast @62 for 30min`
8. HeatUp 70
9. Rest 70 °C / 40 min — `2. Verzuckerungsrast` / `2. Verzuckerungsrast @70 for 40min`
10. IodineTest 68 °C / 10 min  *(note: 68 after a 70 °C rest — see `Q-05`)*
11. HeatUp 76

### 2. `HANCOCK` — `München 12.6 - SUD3:HANCOCK`
1. PourInBrewingWater
2. HeatUp 40
3. MashIn
4. HeatUp 50
5. Rest 50 °C / 30 min — `Eiweißrast` / `Eiweißrast @50 for 30min`
6. HeatUp 66
7. Rest 66 °C / 110 min — `Maltoserast` / `Maltoserast @66 for 110min`
8. IodineTest 66 °C / 10 min
9. HeatUp 78

### 3. `HIPA` — `München 12.6 - SUD4:HIPA`
1. PourInBrewingWater
2. HeatUp 68
3. MashIn
4. Rest 68 °C / 60 min — `Verzuckerungsrast` / `Verzuckuerungsrast @68 for 60min`
5. IodineTest 68 °C / 10 min

### 4. `WIT` — `München 12.6 - SUD5:WIT`
1. PourInBrewingWater
2. HeatUp 40
3. MashIn
4. HeatUp 65
5. Rest 65 °C / 50 min — `Maltoserast` / `Maltoserast @65 for 50min`
6. IodineTest 65 °C / 10 min
7. HeatUp 78

### 5. `BENIWEISS` — `München 12.6 - SUD2:BENIWEISS`
1. PourInBrewingWater
2. HeatUp 40
3. MashIn
4. HeatUp 52
5. Rest 52 °C / 30 min — `Eiweißrast` / `Eiweißrast @52 for 30min`
6. HeatUp 65
7. Rest 65 °C / 30 min — `Maltoserastr` / `Maltoserastr @65 for 30min`
8. HeatUp 73
9. Rest 73 °C / 40 min — `Verzuckerungsrast` / `Verzuckerungsrast @73 for 40min`
10. IodineTest 73 °C / 10 min
11. HeatUp 78

### 6. `WaterBoil` — `Water Boiling`
1. HeatUpForHopsCooking (97 °C, boost)
2. CookWater 20 min — `Cooking Water` / `Cooking water for 20min`

### 7. `Dummy` — `My Dummy Process`
1. HeatUp 62
2. Rest 62 °C / 10 min (default texts)
3. IodineTest 62 °C / 10 min
4. HeatUp 78
5. Lautering
6. HeatUpForHopsCooking

### 8. `TEST` — `Test Process`
1. IodineTest 25 °C / 1 min

> All brewing recipes end after heating up for lautering; lautering and boiling
> were never added (legacy `// ...` / `TODO go on`). After the last goal the
> engine switches everything off (`ENG-025`).

## 7.4 Test fixture recipe (from legacy unit test)

Used by acceptance tests only; not part of the production catalogue.

`PID` — `TEST PROCESS`: PourInBrewingWater, HeatUp 25, MashIn, HeatUp 40,
Rest 40/2 (default texts), IodineTest 40/1, HeatUp 50, Lautering, HeatUpForHopsCooking.
