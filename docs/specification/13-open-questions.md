# 13 — Open Questions

Decisions for the product owner. Each question states the **current spec
default** (used until answered). Record answers here and update the affected
spec section; do not silently change behaviour.

| ID | Question | Current default in spec | Affects |
|---|---|---|---|
| `Q-01` | Pause semantics: should pause switch the pump off as well as the heater, and freeze timers? | Heater off, pump off, timers frozen, reminders silenced | `ENG-013`, `ENG-030` |
| `Q-02` | After `Stopped`/`Finished`, should **Start** restart the recipe from the beginning (implicit reload) instead of being rejected? | Rejected; brewer must load again | `ENG-012` |
| `Q-03` | Should **MashIn** (and PourInBrewingWater) hold the temperature of the preceding HeatUp while waiting for confirmation? Legacy does not (temperature drifts down; pump keeps running). | Legacy behaviour: no temperature control, actuators unchanged | `GOAL-001`, `GOAL-003` |
| `Q-04` | Boil (`CookWater`, target 100 °C) runs at 50 % heating because of the near-target band. Intended, or should boiling use full power / a configurable boil power? | Legacy behaviour (50 %) | `GOAL-008`, `CTL-012` |
| `Q-05` | Recipe `ZORA`: iodine test at **68 °C** directly after a rest at **70 °C** — data error (should be 70)? | Keep 68 (verbatim) | `07-recipes.md`, `data/recipes.json` |
| `Q-06` | Treat DS18B20 power-on value `85.0 °C` as invalid? | Valid (legacy) | `HW-031` |
| `Q-07` | Fix spelling in UI texts (`successfull` → `successful`, `Verzuckuerungsrast`, `Maltoserastr`)? | Keep verbatim | `GOAL-005`, recipes |
| `Q-08` | Should the chart history reset when a new process is loaded/started, and should target temperatures / goal boundaries be drawn (the legacy UI contained a mock-up of this)? | History since server start, temperature only | `IF-042`, `UI-020` |
| `Q-09` | Recipe management in the UI (create/edit/delete)? | No — file only | `RCP-004` |
| `Q-10` | Any access protection (PIN/password) for the web UI? | None (trusted LAN) | `IF-060` |
| `Q-11` | Show successful command replies as modal (legacy intent) or as non-blocking toast? | Modal for all replies | `UI-050` |
| `Q-12` | Over-temperature cut-off (e.g. heater off above a configurable max temperature when not boiling) — desired as additional safety? | Not included (not in legacy) | `NFR-001` |
| `Q-13` | Recipes are incomplete (end after heat-up for lautering; lautering & boil never modelled). Complete them in phase 2? | Keep as-is | `07-recipes.md` |
| `Q-14` | Should the chart persist across server restarts / be exportable (CSV)? | No | `IF-042` |
| `Q-15` | In legacy the pump is switched on by every temperature-controlling goal and only switched off by Lautering / stop / finish. Any need for pump-off phases (e.g. during mash-in)? | Legacy behaviour | `CTL-010` |
