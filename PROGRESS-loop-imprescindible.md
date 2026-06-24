# Backlog imprescindible — progreso

Una tarea por iteración del loop. Estado: PENDIENTE / EN CURSO / HECHO / BLOQUEADO.

## 1. [CRÍTICO doc-código] docs/privacy.md vs envío real de URL completa
Estado: HECHO
Decisión: la fragment (#...) nunca aporta valor analítico al backend y puede llevar tokens OAuth/reset — se decidió sanitizarla en código (no solo documentar). El query string SÍ se mantiene porque es parte real de la superficie de heurísticas (longitud, caracteres especiales, palabras sospechosas).
Cambios:
- `extension/src/utils/risk-score.ts`: se exporta `stripFragment()` (ya existía internamente para `analyzeLocally`).
- `extension/src/popup/Popup.tsx`: se computa `networkUrl = stripFragment(url)` y se usa para `requestBackendAnalysis`, `toPopupAnalysis` (de donde sale `analysis.url`, usado también en el feedback `/report`). La caché local sigue usando la `url` cruda solo para la clave hash (nunca transmitida) y sigue aplicando `stripSensitiveUrlParts` (quita también el query) antes de persistir en `chrome.storage.local`.
- `docs/privacy.md`: añadido un bloque que precisa exactamente qué cruza la red al backend propio (URL completa MENOS fragment: scheme+host+path+query) y por qué, distinguiéndolo de RDAP/PhishTank (solo hostname) y aclarando que el backend configurado no es necesariamente un tercero.
- Test nuevo: `Popup.render.test.tsx` ("strips the URL fragment before sending it to the backend or in feedback reports") verifica que con una URL con `#access_token=secret`, ni `requestBackendAnalysis` ni `submitFeedbackReport` reciben el fragment.
Evidencia: `npx tsc --noEmit` limpio; `npx vitest run` → 147/147 tests pasan (13 archivos), incluyendo el nuevo test.

## 2. [CRÍTICO mismatch train/inference ML]
Estado: HECHO
Decisión: no se añadió un holdout con DOM sintético — fabricar valores DOM falsos sin una página real sería una segunda suposición no validada apilada sobre la primera (haría las métricas parecer más completas sin probar nada real). En su lugar: (a) documentación explícita del mismatch, (b) la señal DOM ya vive de forma transparente y testeada en la capa de scoring basado en reglas (`scoring_service._score_dom`), tratando el ajuste ML como señal URL-only hasta que exista un dataset etiquetado con snapshots DOM reales.
Cambios:
- `docs/ml-methodology.md`: nueva sección "Train/inference feature mismatch" explicando que las 6 columnas DOM están fijas a 0 en el CSV de entrenamiento (`build_dataset.py`) mientras `ml_service.py::_feature_values` alimenta DOM real en producción; aclara que los splits de RandomForest sobre una columna constante no pueden codificar relación real con la etiqueta (gap de capacidad silencioso, no un bug de corrección). Enlazada desde la nota de limitación DOM=0 existente.
- `docs/ml-methodology.md`: matriz de confusión real (no inventada) añadida en formato tabla: TN=197, FP=1, FN=29, TP=169 (orden legítimo/phishing), obtenida ejecutando `python ml/train_model.py` contra el CSV committeado.
- `README.md` (sección Limitations): el bullet de ML ahora incluye precision/recall/confusion matrix reales y la misma aclaración explícita de que estas métricas no describen el comportamiento de producción (URL-only vs. vector de 16 features real).
Evidencia: `python ml/train_model.py` ejecutado para obtener los números reales (CV 0.907±0.008, hold-out 0.92, matriz [[197,1],[29,169]] — coincide exactamente con los números ya documentados, confirmando reproducibilidad). El run sobrescribió `backend/app/models/phishlens_model.joblib` como efecto secundario del entrenamiento; revertido con `git checkout -- backend/app/models/phishlens_model.joblib` para no tocar el artefacto de producción fuera del alcance de esta tarea. `git status --porcelain` confirma que solo quedan cambios en README.md y docs/ (más los de la tarea 1, ya committeable por separado).

## 3. [Codecov] Verificar CODECOV_TOKEN
Estado: HECHO (no requirió cambios de código/doc — el badge ya funciona)
Evidencia:
- `gh auth status` → autenticado como JuanCardesa con scope `repo`.
- `gh secret list --repo JuanCardesa/PhishLens` → `CODECOV_TOKEN` existe (creado 2026-06-22).
- `gh run list --workflow=backend-ci.yml --limit 3` → últimas 3 ejecuciones `success`.
- `gh run view 28089678389 --log | grep -i codecov` en el run más reciente (main, 2026-06-24): el paso "Upload coverage to Codecov" termina con `Upload queued for processing complete` y un link válido a `https://app.codecov.io/github/juancardesa/phishlens/commit/...` — el token es válido y la subida se procesa correctamente, no solo "no rompe el CI" por `fail_ci_if_error: false`.
Conclusión: el badge de Codecov en README.md:6 no está roto; no se modifica nada.

## 4. [SPA] Re-análisis tras navegación SPA
Estado: HECHO (implementación distinta a la sugerida originalmente, justificada abajo)
Decisión: NO se añadió `chrome.webNavigation.onHistoryStateUpdated` en `service-worker.ts` como sugería el ítem original, porque eso requiere el permiso `webNavigation` en el manifest — `scripts/ci/pr_guardian.py:22` (`ALLOWED_EXTENSION_PERMISSIONS = {"activeTab","scripting","storage"}`) tiene una whitelist estricta de permisos que el propio proyecto se ha esforzado en mantener mínima (confirmado por la auditoría: "permisos mínimos con patrón runtime-request" es una de las fortalezas citadas). Añadir un permiso nuevo solo para esto habría sido una regresión de superficie de privacidad para resolver un bug de UX. En su lugar, el re-análisis SPA se implementó enteramente en el content script (`dom-analyzer.ts`), sin tocar el manifest ni pedir permisos nuevos.
Cambios:
- `extension/src/content/dom-analyzer.ts`: extraído `notifyPageReady()` como función nombrada (antes era una IIFE anónima inline). Añadida `watchSpaNavigation()` que parchea `history.pushState`/`replaceState` y escucha `popstate`; en cualquiera de los tres compara `location.href` contra el último valor visto y solo si cambió llama a `notifyPageReady()` de nuevo — así el badge se actualiza en SPAs (React Router, etc.) sin recarga completa de página.
- Test nuevo: `extension/src/content/dom-analyzer.spa.test.ts` (4 tests): pushState re-notifica, replaceState re-notifica, popstate sin cambio de URL no re-notifica (idempotencia), pushState a la misma URL no re-notifica.
Evidencia: `npx tsc --noEmit` limpio; `npx vitest run` → 151/151 tests (14 archivos); `npm run build` (vite) completa sin errores, `dist/content/dom-analyzer.js` generado correctamente.

## 5. [Métricas ML en README] precision/recall/F1/matriz de confusión
Estado: HECHO (resuelto en gran parte como efecto colateral correcto de la tarea 2, completado aquí con F1 explícito)
Cambios:
- `README.md` (bullet de Limitations) y `docs/ml-methodology.md` ("Measured performance"): ahora incluyen precision, recall, **F1** y la matriz de confusión completa para ambas clases (legítimo: precision 0.87/recall 0.99/F1 0.93; phishing: precision 0.99/recall 0.85/F1 0.92; matriz `[[197,1],[29,169]]`).
- Todos los números provienen de la ejecución real de `python ml/train_model.py` documentada en la tarea 2 (no inventados); el F1 añadido aquí es el que imprime `classification_report` en esa misma salida, ya capturada.
Evidencia: mismo run de `python ml/train_model.py` citado en la tarea 2 (ver su salida de `classification_report`, columna f1-score: 0.93 y 0.92). Solo cambios de documentación, `git status --porcelain` confirma que no se tocó código fuente en esta tarea.

---

## Resumen final

Las 5 tareas del backlog imprescindible están **HECHO**. Ninguna quedó BLOQUEADA: `gh` estaba autenticado y permitió verificar Codecov directamente (tarea 3), y la tarea 4 se resolvió con una implementación alternativa sin permisos nuevos en vez de la sugerida originalmente (justificado en su entrada).

Archivos modificados en total: `docs/privacy.md`, `docs/ml-methodology.md`, `README.md`, `extension/src/utils/risk-score.ts`, `extension/src/popup/Popup.tsx`, `extension/src/popup/Popup.render.test.tsx`, `extension/src/content/dom-analyzer.ts`. Archivo nuevo: `extension/src/content/dom-analyzer.spa.test.ts`.

Verificación acumulada: `npx tsc --noEmit` limpio, `npx vitest run` → 151/151 tests (14 archivos) en extensión, `npm run build` (vite) sin errores. No se tocó código Python en ninguna tarea (solo se ejecutó `ml/train_model.py` para obtener números reales, y su efecto secundario sobre el artefacto del modelo fue revertido con `git checkout`).

Nada pendiente de decisión del usuario salvo revisar y mergear los cambios.
