# Backlog diferencial — progreso

Una tarea por iteración del loop. Estado: PENDIENTE / HECHO / BLOQUEADO.
Tareas grandes: se dividen en sub-pasos dentro de cada sección.

## 1. [Firefox real] webextension-polyfill (chrome.* -> browser.*)
Estado: HECHO
Cambios de producción:
- `npm install webextension-polyfill` + `@types/webextension-polyfill` (devDependency de tipos).
- `extension/src/services/settings.ts`: `chrome.storage.sync`/`chrome.permissions` -> `browser.storage.sync`/`browser.permissions`, eliminando los wrappers manuales de `new Promise()` (la API del polyfill ya devuelve promesas).
- `extension/src/content/dom-analyzer.ts`: `chrome.runtime.onMessage`/`chrome.runtime.sendMessage` -> `browser.*`; el listener de `PHISHLENS_COLLECT_DOM` ahora retorna `Promise<...> | undefined` en vez de `sendResponse()` + `return false`.
- `extension/src/warning/overlay.ts`: mismo patrón para el listener de `PHISHLENS_SHOW_WARNING`.
- `extension/src/background/service-worker.ts`: `chrome.runtime.onInstalled`/`onMessage`/`storage.local` -> `browser.*`. `chrome.action` (namespace MV3 que el polyfill v0.12 NO envuelve, predata MV3) se llama directamente vía `browser.action` — el polyfill expone esos namespaces sin wrapear (passthrough), y tanto Chrome (soporte nativo de promesas desde MV96) como Firefox (API nativa) ya devuelven promesas ahí sin necesidad de wrapping.
- `extension/src/popup/Popup.tsx`: `chrome.tabs.query/sendMessage`, `chrome.storage.local`, `chrome.runtime.openOptionsPage`, `chrome.scripting.executeScript` -> `browser.*` equivalentes, simplificando los wrappers de callback a `await` directo. `collectDomFeatures()` ahora usa try/catch (el polyfill rechaza la promesa en vez de fijar `chrome.runtime.lastError`).
- `extension/manifest.json`: añadido `browser_specific_settings.gecko` (id + `strict_min_version`) — no-op para Chrome, requerido por Firefox para `storage.sync` estable entre actualizaciones.
- `docs/permissions.md`: documentada la nueva clave del manifest (no es un permiso, pero `pr_guardian.py` exige tocar este doc en cualquier cambio de manifest.json).
- `docs/roadmap.md` y `CHANGELOG.md`: Firefox ya no figura como "ausente"; documentado honestamente como "construido sobre la API estándar cross-browser, no verificado manualmente en un perfil real de Firefox en esta sesión" — MV3 `service_worker` en Firefox es más reciente/menos probado que en Chrome.

Hallazgo no trivial durante la verificación (documentado para que quede explícito, no oculto): `webextension-polyfill` es un módulo CJS singleton que construye su objeto `browser` envuelto UNA sola vez por proceso de test, capturando la referencia a `globalThis.chrome` y sus sub-objetos (`chrome.runtime`, `chrome.runtime.onMessage`, etc.) en ese momento. El patrón previo de `src/test/setup.ts` (`vi.stubGlobal("chrome", {...objeto nuevo...})` en cada `beforeEach`) reemplazaba el objeto `chrome` completo cada test, dejando al polyfill aferrado a una referencia obsoleta del primer test — los mocks de tests posteriores nunca eran invocados de verdad. Fix: `setup.ts` ahora crea el stub UNA vez a nivel de módulo con identidad estable, y el `beforeEach` solo reasigna las funciones `vi.fn()` hoja (no los objetos contenedores `chrome`, `chrome.runtime`, `chrome.tabs`, etc.), ya que el polyfill resuelve `target.metodo(...)` dinámicamente en cada llamada. Los listeners de `onMessage`/`onInstalled` (registrados una sola vez al cargar el módulo, igual que en producción) se dejan deliberadamente sin resetear entre tests.
Tests afectados/reescritos: `dom-analyzer.listener.test.ts` y `overlay.test.ts` migrados del patrón `vi.resetModules()` + re-import dinámico a un import estático único (mismo patrón que `dom-analyzer.spa.test.ts`), recuperando el listener registrado una sola vez vía `chrome.runtime.onMessage.addListener.mock.calls[0][0]` y usando `vi.waitFor` para esperar la resolución de la promesa antes de comprobar `sendResponse`.
Evidencia: `npx tsc --noEmit` limpio; `npx vitest run` → 155/155 tests (15 archivos); `npm run build` (vite) sin errores — `dist/assets/browser-polyfill.js` (10.19 kB) generado como chunk compartido para popup/options, y los entry points de background/content/overlay crecieron solo ~0.1 kB cada uno (el polyfill se incluye inline, sin duplicación masiva).
No verificado en esta sesión (fuera de alcance de "build pasa para Chrome"): carga real en `about:debugging` de Firefox, firma/empaquetado AMO, diferencias de comportamiento del service worker MV3 entre motores.

## 2. [Marcas dinámicas] Lista de marcas ampliable/externa
Estado: HECHO
Decisión: "ampliable/externa" implementado como archivo de configuración JSON (no endpoint en vivo). Para el backend esto es una mejora real (operadores pueden editar/sustituir el JSON o apuntar `PHISHLENS_BRAND_DOMAINS_PATH` a otro archivo sin tocar código ni redeploy de imagen, si el volumen está montado). Para la extensión se descartó deliberadamente un endpoint remoto: añadiría dependencia de red y un permiso nuevo a una señal que hoy funciona 100% offline, a cambio de actualizar una lista que cambia con poca frecuencia (se puede actualizar en cada release del bundle).
Cambios backend:
- `backend/app/data/brand_domains.json` (nuevo, 26 dominios semilla).
- `backend/app/services/brand_domains.py` (nuevo): `load_brand_domains(path=None)` lee el JSON, con fallback a `_SEED_BRAND_DOMAINS` (tupla hardcodeada idéntica) si el archivo falta, no es JSON válido, o tiene forma inválida (no es lista de strings no vacía). `KNOWN_BRAND_DOMAINS` se calcula una vez al importar el módulo, usando `Settings.brand_domains_path`.
- `backend/app/core/config.py`: nuevo campo `brand_domains_path` (`PHISHLENS_BRAND_DOMAINS_PATH`, default `app/data/brand_domains.json`), mismo patrón que `model_path`.
- `.env.example`: documentada la nueva variable.
- `backend/app/services/feature_extractor.py`: `KNOWN_BRAND_DOMAINS` ahora se importa desde `brand_domains.py` en vez de estar hardcodeado inline (sigue re-exportado bajo el mismo nombre, sin romper imports existentes).
- Tests nuevos: `backend/tests/test_brand_domains.py` (6 tests: carga del seed committeado, override con archivo custom vía `tmp_path`, fallback por archivo ausente/JSON malformado/forma inválida/lista vacía).
Cambios extensión:
- `extension/src/data/brand-domains.json` (nuevo, mismos 26 dominios).
- `extension/src/utils/url-features.ts`: `KNOWN_BRAND_DOMAINS` ahora se importa del JSON (`resolveJsonModule` ya activado en tsconfig) en vez de un array inline.
- Test nuevo en `url-features.test.ts`: confirma que el JSON se carga con los 26 dominios esperados.
Evidencia backend: `python -m pytest -q` → todos los tests pasan (incluye los 6 nuevos); `python -m ruff check app tests` limpio; `python -m mypy app` limpio.
Evidencia extensión: `npx tsc --noEmit` limpio; `npx vitest run` → 156/156 tests (15 archivos); `npm run build` (vite) sin errores.
CHANGELOG.md actualizado con la entrada correspondiente.

## 3. [Certificate Transparency] CT log lookups en scoring TLS
Estado: HECHO
Diseño: la consulta a `crt.sh` (sin API key, host fijo, igual que RDAP) corre en PARALELO con la inspección TLS por socket existente vía `asyncio.gather` dentro de `inspect_tls()`, fusionando el resultado en el mismo `TLSResult` (no se creó una categoría de scoring nueva ni un segundo caché — se reutiliza `TLS_CACHE`). La señal de scoring usa la fecha de la entrada CT MÁS ANTIGUA del dominio (`ct_first_seen_days_ago`, cuándo empezó su historial de certificados), no la más reciente — un dominio cuyo primer certificado tiene menos de una semana es la señal de phishing relevante (no cuántos certificados nuevos tiene).
Cambios backend:
- `backend/app/services/tls_service.py`: `TLSResult` ganó `ct_logs_checked`, `ct_first_seen_days_ago`, `ct_error`. Nuevas funciones `_check_ct_logs()` (orquesta, best-effort, nunca bloquea el resto del resultado TLS), `_fetch_ct_log_payload()` (httpx GET a `crt.sh/?q=<domain>&output=json`), `_earliest_ct_entry_days_ago()` (parsea `not_before` de todas las entradas, toma la mínima fecha).
- `backend/app/services/scoring_service.py`: `_score_tls` añade +6 puntos (dentro del cap existente `TLS_SCORE_CAP=15`) si `ct_first_seen_days_ago < 7`, de forma ADITIVA junto a expired/expiring/invalid (no mutuamente exclusivo con esos, ya que es una señal independiente).
- `backend/app/core/config.py` + `.env.example`: nuevo `PHISHLENS_ENABLE_CT_LOG_LOOKUP` (default `true`), mismo patrón que `enable_domain_age_lookup`.
- `backend/tests/conftest.py`: deshabilitado por defecto en toda la suite (`PHISHLENS_ENABLE_CT_LOG_LOOKUP=false`), mismo patrón que RDAP, para que ningún test golpee la red real; `test_tls_service.py` lo reactiva explícitamente en sus propios `Settings(...)`.
- `backend/app/routers/diagnostics.py` + `extension/src/types/analysis.ts` + `extension/src/options/Options.tsx`: nueva capability `ct_log_lookup_enabled` expuesta en `/diagnostics` y en la grid de Options ("CT logs"), con tooltip en `glossary.ts`, consistente con el resto de capacidades (Threat intel/TLS/ML/Domain age).
- `docs/threat-model.md`: documentada la misma propiedad anti-SSRF de RDAP (host fijo de terceros, el hostname va como query param, no como destino de conexión) y que un fallo de crt.sh degrada sin bloquear el resto del análisis TLS.
- Tests nuevos backend: 4 en `test_tls_service.py` (entrada CT más antigua reportada correctamente, lookup deshabilitado, fallo de red no bloquea el resultado TLS, lista de entradas vacía) + 3 en `test_scoring_service.py` (+6 puntos con entrada reciente, 0 puntos con entrada antigua, combinación con expired respetando el cap).
- Test nuevo extensión: 1 assertion añadida a `Options.render.test.tsx` (tooltip de "CT logs").
Evidencia backend: `python -m pytest -q` → toda la suite pasa (incluye los 7 tests nuevos); `python -m ruff check app tests` limpio; `python -m mypy app` limpio.
Evidencia extensión: `npx tsc --noEmit` limpio; `npx vitest run` → 156/156 tests (15 archivos); `npm run build` (vite) sin errores.
CHANGELOG.md actualizado.

## 4. [Calibración] Reliability diagram para confidence heurística
Estado: HECHO
Decisión: NO se recalibró la fórmula (`0.55 + abs(score-50)/100`, cap 0.9) en esta ronda — hacerlo contra un dataset que no puede ejercitar typosquat/homograph/DOM/TLS/domain-age/threat-intel calibraría la fórmula a los puntos ciegos de ESTE benchmark offline, no a precisión real. Se documentó como limitación conocida en vez de "arreglarla" superficialmente, siguiendo el mismo criterio que otros hallazgos de Lessons Learned del proyecto.
Hallazgo real (no inventado, ejecutado contra el dataset committeado de 1200 filas): la confidence heurística NO es solo "no calibrada" en el sentido inocuo — está sistemáticamente SOBRECONFIADA. Los 5 bins con datos quedan todos por debajo de la diagonal de calibración perfecta; el bin que contiene el 96% de las filas (confidence≈0.90) solo tiene ~52% de accuracy empírica (casi una moneda al aire). Error de calibración medio ponderado: 0.397.
Cambios:
- `ml/evaluate_confidence_calibration.py` (nuevo): reconstruye el score heurístico URL-only por fila (misma limitación que `evaluate_heuristics.py`: sin typosquat/homograph, DOM=0), escala a 0-100 igual que `risk-score.ts`'s `LOCAL_MAX_SCORE`, calcula `_confidence()`, bins por confidence (aritmética en céntimos enteros para evitar bugs de límites de bin por precisión de floats — encontrado y corregido durante esta misma tarea), genera tabla + diagrama de fiabilidad (`matplotlib`, backend "Agg") en `ml/calibration_reliability_diagram.png`.
- Bug encontrado y corregido en el propio script durante la verificación: el primer intento de binning duplicaba filas en bins adyacentes por imprecisión de floats en el límite superior (`start+BIN_WIDTH`); resuelto comparando en céntimos como enteros.
- `backend/requirements-dev.txt`: añadido `matplotlib` (solo herramienta de análisis, no dependencia de runtime del backend — no toca `requirements.txt` ni el CI de mypy/ruff, que no incluye `ml/` en su scope).
- `docs/ml-methodology.md`: nueva sección "Heuristic-only confidence calibration (reliability diagram)" con la tabla real, la imagen embebida, y el hallazgo explicado.
- `README.md` "Lessons Learned": nueva entrada con el hallazgo, enlazando a la sección de la doc.
- `CHANGELOG.md`: entrada correspondiente.
Evidencia: `python ml/evaluate_confidence_calibration.py` ejecutado con éxito, tabla y PNG generados y verificados (imagen revisada visualmente: todos los puntos por debajo de la diagonal). `python -m pytest -q` (suite completa backend) sin fallos; `python -m ruff check app tests` y `python -m mypy app` limpios; `python -m ruff check ml/evaluate_confidence_calibration.py` limpio (aunque `ml/` no está en el scope del CI).

## 5. [Demo] GIF animado end-to-end en README
Estado: HECHO (el usuario autorizó explícitamente completar la grabación, no solo prepararla)
Decisión de método: en vez de grabación manual de pantalla, se automatizó con Playwright (ya devDependency) controlando un Chromium real con la extensión cargada, capturando screenshots reales de cada paso, y componiendo el GIF final con Pillow (Python). Esto es reproducible y queda commiteado como herramienta reutilizable, no solo como un GIF estático.

**Hallazgo crítico durante la grabación (no relacionado con el GIF en sí, bug de producción real):** al intentar que el content script respondiera a `chrome.tabs.sendMessage`, fallaba con "Could not establish connection. Receiving end does not exist." en un Chromium real, pese a que `tsc`/`vitest`/`vite build` estaban todos en verde. Causa: la migración a Firefox/`webextension-polyfill` (tarea 1 de este mismo backlog) introdujo `import browser from "webextension-polyfill"` en `dom-analyzer.ts` y `overlay.ts` — pero ambos se ejecutan como scripts clásicos (content scripts MV3 no soportan `"type":"module"`; lo mismo aplica a archivos inyectados vía `chrome.scripting.executeScript`). Vite compilaba el polyfill como un chunk ES compartido, generando `import{...}from"../assets/browser-polyfill.js"` en ambos bundles — sintácticamente inválido fuera de un módulo. Esto significa que **la extensión real lleva roto el análisis DOM y el overlay de peligro desde la sesión anterior**, sin que ningún test lo detectara (Vitest mockea módulos, Vite no valida compatibilidad de formato de módulo en runtime).
Fix: `extension/vite.config.ts` reestructurado en dos pasadas controladas por `BUILD_TARGET` (`scripts/build.mjs` las encadena): una pasada ES-module para popup/options/service-worker (sin cambios), y pasadas IIFE separadas para `content/dom-analyzer.js` y `warning/overlay.js` (Rollup no soporta múltiples entradas con `codeSplitting:false`, así que cada IIFE es su propia pasada) — IIFE no tiene module loader, así que Rollup inlina las dependencias compartidas (el polyfill) directamente en cada archivo en vez de extraer un chunk común.
Verificado tras el fix: `chrome.tabs.sendMessage` al content script ahora devuelve DOM features reales (`has_password_field:true, num_forms:1, ...`); la página "dangerous" demo pasó de puntuar 64/100 ("Suspicious", sin contribución DOM) a 94/100 ("Dangerous", PAGE STRUCTURE 30/30) y el overlay de peligro se dispara correctamente.
Documentado en `CHANGELOG.md` (### Fixed, marcado "critical") y en README "Lessons Learned".

Cambios de la grabación en sí:
- `extension/scripts/record-demo.mjs` (nuevo, commiteado): construye una copia temporal de `dist/` con tres ajustes SOLO de prueba (nunca se envían): permiso `tabs`, `web_accessible_resources` para `popup.html`, host permission extra para el origen del demo — necesarios porque no existe forma de "click real en el icono de la barra" desde Playwright, así que el popup se abre como pestaña real vía `window.open()`, lo cual rompe `chrome.tabs.query({active:true,currentWindow:true})` (resolvería al propio popup en vez de a la página). Se parchea ESA llamada específica mediante un init-script que la redirige a la pestaña real (obtenida desde el service worker antes de abrir el popup); el resto de llamadas `chrome.*` pasan sin tocar.
- `extension/scripts/compose_demo_gif.py` (nuevo, commiteado, requiere Pillow vía `pip install Pillow`, no añadido como dependencia del proyecto): compone 5 frames (safe+popup, suspicious+popup, overlay de peligro x2, detalle del popup dangerous) en `docs/screenshots/demo.gif`, 960×600, ~13s de loop, 166 KB.
- `docs/demo-gif-script.md`: añadida sección "Automated capture" documentando el método y el hallazgo del bug, manteniendo el guion manual original como alternativa.
- `README.md`: quitada la línea "Recording pending..."; el GIF real ya está enlazado.
- `docs/screenshots/demo.gif` (nuevo, 166 KB).
Limpieza tras la grabación: procesos de backend/demo-server detenidos por PID (no se mató ningún proceso `chrome.exe`/`python.exe` indiscriminadamente, solo los PIDs específicos confirmados vía `netstat`/`Get-CimInstance`), directorios temporales borrados, y un lote de directorios basura que quedaron mal creados dentro de `extension/` por un escape de backslashes en un comando anterior fue detectado y eliminado.

---

## Resumen final

Backlog diferencial completo: **5/5 HECHO** (la tarea 5 se completó tras autorización explícita del usuario para grabar el GIF él mismo vía automatización, no solo prepararlo).

Archivos nuevos en total: `backend/app/data/brand_domains.json`, `backend/app/services/brand_domains.py`, `backend/tests/test_brand_domains.py`, `extension/src/data/brand-domains.json`, `ml/evaluate_confidence_calibration.py`, `ml/calibration_reliability_diagram.png`, `docs/demo-gif-script.md`, `docs/screenshots/demo.gif`, `extension/scripts/build.mjs`, `extension/scripts/record-demo.mjs`, `extension/scripts/compose_demo_gif.py`. Más los cambios de la tarea 1 (Firefox/webextension-polyfill) y 3 (CT logs) ya detallados arriba en sus propias entradas.

Hallazgos no triviales encontrados y corregidos durante la verificación de este backlog (no solo "se implementó", se verificó de verdad):
- Bug de identidad de objeto stub en `webextension-polyfill` + Vitest (tarea 1) — los mocks por-test dejaban de invocarse tras el primer test.
- Bug de precisión de floats en el binning del reliability diagram (tarea 4) — corregido a aritmética de céntimos enteros.
- Hallazgo de producto real (no técnico): la confidence heurística está sistemáticamente sobreconfiada, no solo "sin probar" — documentado honestamente en vez de maquillado.
- **Bug crítico de producción (tarea 5): el content script y el overlay de peligro estaban rotos en cualquier navegador real** desde la migración a Firefox de la tarea 1, sin que ningún test lo detectara — encontrado únicamente porque la grabación del GIF usó un navegador real de verdad en vez de mocks. Corregido con un pipeline de build de dos formatos.

Verificación final acumulada: backend (`pytest`, `ruff`, `mypy`) limpio; extensión (`tsc`, `vitest` 156/156, `npm run build` con las 3 pasadas) limpio. Nada pendiente salvo que el usuario revise y decida si commitear/pushear este lote de cambios (no se ha hecho commit todavía en esta ronda).

Verificación acumulada de todo el backlog: backend (`pytest`, `ruff`, `mypy`) limpio en cada tarea; extensión (`tsc`, `vitest`, `vite build`) limpio en cada tarea. No se tocó código fuera del alcance de cada tarea salvo lo estrictamente necesario para que los cambios fueran coherentes (ej. exponer la nueva capability de CT logs en Options, ya que el patrón existente lo exige para todas las demás capacidades).

Nada más pendiente de decisión salvo: (a) que el usuario grabe el GIF de la tarea 5, y (b) revisar/mergear estos cambios.
