# Legacy Technology Notes (input for phase 2)

Purpose: help the phase-2 technology decision
([ADR-0001](../adr/0001-technology-stack.md)). This document **does not**
decide anything; it records what the legacy system used, what is obsolete, and
which hardware facts any new stack must respect.

## 1. Legacy stack

| Layer | Legacy technology | Status 2026 | Notes |
|---|---|---|---|
| Language/runtime | Java 7 (OpenJDK armhf), Eclipse project, no build tool | EOL | Classpath hand-maintained in `.classpath` and `brewberrypi.sh` |
| Web server | Embedded Jetty 7.6 (start script) / Jetty 8.1 jars (Eclipse classpath) | EOL | Mixed versions on the two classpaths |
| Real-time | CometD 2.8 (Bayeux protocol), long-polling (client sets `websocketEnabled = false`) | EOL | Server "services" on `/service/...` channels, broadcasts on normal channels |
| JSON | Jetty `JSON.Generator` with hand-built JSON strings | – | Replace with a proper serializer |
| DI / misc | Spring 3.2 — only `ClassPathResource` used to locate `webcontent/` | EOL | Not needed |
| GPIO | Pi4J 1.0-SNAPSHOT → WiringPi (native) | WiringPi deprecated; Pi4J v1 does not support Pi 4B rev ≥1.4/Pi 5 | Pin numbers in WiringPi scheme |
| Sensor | Linux 1-Wire sysfs (`/sys/bus/w1/devices/28-*/w1_slave`) read as text file | Still valid on Raspberry Pi OS | Needs `dtoverlay=w1-gpio` in `/boot/firmware/config.txt` (older: `/boot/config.txt`) |
| Buzzer (sim) | `javax.sound.sampled` 1000 Hz sine tone | – | Only in simulation mode |
| Front end | AngularJS 1.2.15, jQuery 1.11, Bootstrap 3.1.1, D3 3.5.6 + NVD3 1.8.1 + angular-nvd3 | All EOL | Scope updates via `angular.element(...).scope().$digest()` from CometD callbacks |
| Logging | `java.util.logging` (log4j/slf4j jars unused) | – | |
| Tests | JUnit 4.11, but tests are endless manual programs | – | No automated verification |
| Deployment | Copy Eclipse `bin/` + `lib/` to Pi; run `sudo ./brewberrypi.sh` | – | No service, runs as root |

## 2. Hardware facts every stack must respect

- **Relays are active-low** (heating, pump): drive HIGH = off. Provision pins with HIGH as the initial state to avoid a relay click/heater pulse at startup.
- **Buzzer is active-high**.
- **Pin mapping** (WiringPi → BCM → physical): 4 → 23 → 16 (heating), 3 → 22 → 15 (pump), 12 → 10 → 19 (buzzer; BCM 10 is SPI0 MOSI — SPI must stay disabled or the pin must be remapped).
- **1-Wire** default data pin is BCM 4 (physical 7) — not used by any relay, no conflict.
- A DS18B20 read via sysfs takes ~750 ms (12-bit conversion) and blocks → read in a background loop, cache the value.
- **Raspberry Pi 5** uses the RP1 I/O chip: GPIO access must go through the Linux GPIO character device (`/dev/gpiochip*`, libgpiod) — the old sysfs GPIO interface and WiringPi do not work. Any library chosen must support libgpiod / gpiochip.
- GPIO lines keep their last state when the process dies → consider a systemd `ExecStopPost` that resets lines, or a hardware solution (NFR-003).
- The Pi has no RTC → use monotonic clocks for timers (NFR-005).

## 3. Candidate stacks (not a decision — for ADR-0001)

| Option | GPIO | Real-time to browser | Pros | Cons |
|---|---|---|---|---|
| Java 21 + Pi4J v2 (+ Javalin/Jetty 12 or Spring Boot) | Pi4J v2 (gpiod provider for Pi 5) | WebSocket / SSE | Closest to legacy, team knows Java | JVM memory/startup on small Pis |
| Python 3 + FastAPI/Starlette | gpiozero / libgpiod | WebSocket | Most common on Pi, simple deploy, huge community | Typing/concurrency discipline needed |
| C# / .NET 8 + ASP.NET Core | System.Device.Gpio (libgpiod driver) | SignalR | Strong tooling, good perf | Larger runtime, less common on Pi |
| Node.js/TypeScript + Fastify | node-libgpiod / onoff | WebSocket / Socket.IO | One language front+back | Native GPIO bindings can be fragile |
| Go | periph.io / go-gpiocdev | WebSocket | Single static binary, tiny footprint | Less familiar |

Front end options: plain HTML + a small reactive library (e.g. Alpine.js/Preact/Svelte) with a
charting library (e.g. uPlot/Chart.js). All assets must be served locally (UI-070).

Decision criteria suggested for ADR-0001: Pi 5 GPIO support, safety of shutdown handling,
testability with a fake clock, memory footprint on Pi 3, team familiarity, long-term maintenance.

## 4. Things **not** to carry over

- Hand-written JSON, mixed Jetty versions, unused Spring/log4j dependencies.
- Singleton recipe objects reused across loads (FIX-08).
- Threads started ad hoc per beep/request without lifecycle management (FIX-12).
- Root privileges for the whole application (NFR-024).
