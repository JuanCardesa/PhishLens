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
Estado: PENDIENTE

## 3. [Certificate Transparency] CT log lookups en scoring TLS
Estado: PENDIENTE

## 4. [Calibración] Reliability diagram para confidence heurística
Estado: PENDIENTE

## 5. [Demo] GIF animado end-to-end en README
Estado: PENDIENTE
