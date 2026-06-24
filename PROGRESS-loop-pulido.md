# Backlog pulido — progreso

Una tarea por iteración del loop. Estado: PENDIENTE / HECHO / BLOQUEADO.

## 1. [UX seguridad] Copy accionable en overlay de peligro
Estado: HECHO
Cambios:
- `extension/src/warning/overlay.ts`: añadido un párrafo en negrita justo bajo el título ("Do not enter your password, card details, or any personal information on this page."), antes del risk score y de las razones técnicas. Mismo tono/estilo que el resto del overlay (mismas variables de color dark/light, misma tipografía del sistema).
- Refactor mínimo necesario para testear: se exporta `PHISHLENS_WARNING_OVERLAY_ID` (antes el id "phishlens-warning-overlay" era un literal repetido inline); esto también convierte el archivo en un módulo ES real, requerido para poder re-importarlo de forma aislada en tests con `vi.resetModules()`.
- Test nuevo: `extension/src/warning/overlay.test.ts` (2 tests) — verifica que la instrucción accionable aparece junto al score y las razones, y que mensajes no relacionados no crean el overlay.
Evidencia: `npx tsc --noEmit` limpio; `npx vitest run` → 153/153 tests (15 archivos); `npm run build` (vite) sin errores, `dist/warning/overlay.js` generado.

## 2. [Lenguaje] Reducir jerga en popup/options
Estado: HECHO
Decisión: en vez de un glosario aparte o reescribir las etiquetas técnicas (TLS, ML, threat intelligence se mantienen como nombres de señal, ya que son los términos que un usuario podría buscar/reconocer), se añadió un tooltip nativo (`title` attr) con explicación en lenguaje llano sobre los términos jerga. No se eliminó info técnica, solo se hizo accesible al pasar el cursor/foco.
Cambios:
- `extension/src/utils/glossary.ts` (nuevo): `SIGNAL_GLOSSARY` (por `SignalCategoryId`: threat-intel, tls, ml, domain-age) y `CAPABILITY_GLOSSARY` (mapeado a las mismas etiquetas que usa Options: "Threat intel", "TLS", "ML", "Domain age").
- `extension/src/popup/Popup.tsx`: el `<span>` del título de cada grupo de señales ahora tiene `title={SIGNAL_GLOSSARY[group.id]}`.
- `extension/src/options/Options.tsx`: `StatusItem` ahora acepta el glosario vía `CAPABILITY_GLOSSARY[label]` y lo pone en `title` del label (sin tooltip para labels no técnicos como "Service"/"Diagnostics", ya que no están en el mapa).
- Tests nuevos: `Options.render.test.tsx` (1 test, verifica tooltips en "TLS"/"ML"/"Threat intel") y `Popup.render.test.tsx` (1 test, verifica tooltips en "TLS"/"ML" de los grupos de señales).
No se tocó el banner de modo `backend-unavailable` (lista "TLS, threat intelligence... not checked") porque es una oración concatenada en texto plano, no elementos individuales — tooltips ahí requerirían restructurar el banner a JSX con spans separados, fuera del alcance de un cambio mínimo; queda como posible mejora futura, no crítica (esa frase es secundaria, los títulos de las secciones de señales son el punto de contacto principal con la jerga).
Evidencia: `npx tsc --noEmit` limpio; `npx vitest run` → 155/155 tests (15 archivos); `npm run build` (vite) sin errores.

## 3. [Scoring TLS] Señal CA self-signed/gratuita + antigüedad de dominio
Estado: PENDIENTE

## 4. [feedback_store] Purga periódica durante la vida del proceso
Estado: PENDIENTE

## 5. [Log] ml_service.py:99 — loguear solo nombre de archivo, no ruta absoluta
Estado: PENDIENTE
