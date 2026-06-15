Actúa como un ingeniero senior full-stack especializado en AppSec, extensiones de navegador, backend Python y Machine Learning aplicado a ciberseguridad.

Quiero que inicialices desde cero un nuevo proyecto llamado **PhishLens**, una extensión de navegador para detección de phishing en tiempo real. El proyecto debe estar pensado como producto real usable y como proyecto potente de portfolio de ciberseguridad.

# 1. Objetivo general del proyecto

Construir una extensión de Chrome que analice la página actual y calcule un nivel de riesgo de phishing combinando:

* Heurísticas de URL.
* Análisis del DOM.
* Consulta a fuentes externas de threat intelligence, empezando por PhishTank.
* Backend propio en Python/FastAPI.
* Modelo de Machine Learning explicable.
* Análisis TLS/certificado desde backend, no directamente desde la extensión.
* Interfaz clara para el usuario final.
* Documentación profesional para portfolio.

La aplicación debe priorizar:

* Privacidad.
* Explicabilidad.
* Bajo número de falsos positivos.
* Buenas prácticas de seguridad.
* Código limpio, mantenible y testeable.
* Estructura profesional de repositorio.

# 2. Restricciones de seguridad y ética

Este proyecto es exclusivamente defensivo. No implementes funcionalidades ofensivas, robo de credenciales, automatización de ataques, scraping abusivo ni recopilación de datos sensibles.

Reglas obligatorias:

* No capturar contraseñas.
* No capturar correos escritos por el usuario.
* No capturar contenido privado de formularios.
* No enviar HTML completo al backend.
* Extraer solo señales técnicas necesarias.
* No guardar datos sensibles.
* No incluir API keys en el frontend/extensión.
* No cargar código remoto en la extensión.
* Usar permisos mínimos en Chrome.
* Documentar claramente las limitaciones del sistema.

# 3. Stack técnico decidido

Usa este stack:

## Extensión

* TypeScript.
* Chrome Extension API.
* Manifest V3.
* Vite para empaquetado.
* React para el popup.
* Content scripts para análisis del DOM.
* Service worker para coordinación.
* chrome.storage para caché local.
* chrome.tabs y chrome.runtime cuando sea necesario.
* Diseño visual limpio, moderno y profesional.

## Backend

* Python.
* FastAPI.
* Pydantic.
* scikit-learn.
* pandas.
* joblib.
* httpx.
* pytest.
* Uvicorn.
* Docker.

## ML

* Baseline inicial con Logistic Regression.
* Modelo principal inicial con RandomForestClassifier.
* Métricas: accuracy, precision, recall, F1-score y matriz de confusión.
* Guardar modelo con joblib.
* Separar entrenamiento, evaluación e inferencia.
* Documentar limitaciones.

## Infraestructura y calidad

* Monorepo.
* Docker Compose.
* GitHub Actions.
* Linters y formatters.
* Tests unitarios.
* README profesional.
* Documentación técnica en `/docs`.
* Conventional Commits.
* AGENTS.md con instrucciones del proyecto.

# 4. Flujo Git obligatorio

Inicializa el repositorio Git desde cero.

Usa la siguiente estrategia:

1. Crear rama principal `main`.
2. Hacer commit inicial mínimo.
3. Crear rama `develop`.
4. Crear rama de trabajo `feature/bootstrap-project`.
5. Trabajar inicialmente en `feature/bootstrap-project`.
6. No trabajar directamente sobre `main`.
7. Usar commits pequeños y descriptivos.
8. Usar siempre Conventional Commits.

Ejemplos de commits válidos:

* `chore: initialize repository structure`
* `docs: add project architecture overview`
* `feat(extension): add manifest v3 base setup`
* `feat(backend): add initial FastAPI application`
* `test(backend): add URL feature extractor tests`
* `ci: add GitHub Actions quality workflow`

Al finalizar cada bloque lógico, haz commit.

No hagas merge automático a `main` salvo que yo lo pida. Deja las ramas preparadas y documenta qué se ha hecho.

# 5. Estructura esperada del repositorio

Crea esta estructura base:

```text
phishlens/
│
├── extension/
│   ├── manifest.json
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── public/
│   │   └── icons/
│   └── src/
│       ├── background/
│       │   └── service-worker.ts
│       ├── content/
│       │   └── dom-analyzer.ts
│       ├── popup/
│       │   ├── Popup.tsx
│       │   ├── popup.html
│       │   └── main.tsx
│       ├── warning/
│       │   └── overlay.ts
│       ├── services/
│       │   └── analysis-api.ts
│       ├── utils/
│       │   ├── url-features.ts
│       │   └── risk-score.ts
│       └── types/
│           └── analysis.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── routers/
│   │   │   ├── analyze.py
│   │   │   ├── report.py
│   │   │   └── health.py
│   │   ├── schemas/
│   │   │   └── analysis.py
│   │   ├── services/
│   │   │   ├── feature_extractor.py
│   │   │   ├── phishtank_service.py
│   │   │   ├── tls_service.py
│   │   │   ├── ml_service.py
│   │   │   └── scoring_service.py
│   │   └── models/
│   │       └── placeholder.txt
│   ├── tests/
│   │   ├── test_feature_extractor.py
│   │   ├── test_scoring_service.py
│   │   └── test_health.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
│
├── ml/
│   ├── datasets/
│   │   └── .gitkeep
│   ├── notebooks/
│   │   └── .gitkeep
│   ├── models/
│   │   └── .gitkeep
│   ├── train_model.py
│   ├── evaluate_model.py
│   └── README.md
│
├── docs/
│   ├── architecture.md
│   ├── threat-model.md
│   ├── privacy.md
│   ├── ml-methodology.md
│   ├── roadmap.md
│   └── demo-script.md
│
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       └── extension-ci.yml
│
├── .gitignore
├── .editorconfig
├── .env.example
├── docker-compose.yml
├── AGENTS.md
├── README.md
└── LICENSE
```

# 6. Implementación inicial esperada

No te limites a crear carpetas vacías. Quiero un primer MVP técnico funcional.

## 6.1. Extensión

Implementa una extensión básica con Manifest V3 que haga lo siguiente:

* Leer la URL activa.
* Extraer señales heurísticas básicas de la URL.
* Ejecutar análisis local inicial.
* Mostrar un popup con:

  * URL actual.
  * Risk score de 0 a 100.
  * Estado: `safe`, `suspicious` o `dangerous`.
  * Lista de razones.
* Cambiar visualmente el estado con clases CSS.
* Preparar llamada al backend `/analyze`.
* Si el backend no está disponible, usar solo análisis local.
* Añadir content script para extraer señales del DOM sin recopilar datos sensibles.

Features mínimas de URL:

* Longitud de URL.
* Número de puntos.
* Número de guiones.
* Uso de IP como dominio.
* Presencia de `@`.
* Uso de HTTPS.
* Número de subdominios.
* Palabras sospechosas: `login`, `verify`, `account`, `secure`, `update`, `password`, `bank`, `wallet`.
* Detección básica de punycode.
* Entropía aproximada del dominio.

Features mínimas del DOM:

* Número de formularios.
* Presencia de campo password.
* Formularios con action externo.
* Número de iframes.
* Ratio aproximado de enlaces externos.
* Presencia de inputs ocultos.
* No leer valores escritos por el usuario.

## 6.2. Backend

Implementa una API FastAPI con estos endpoints:

### `GET /health`

Devuelve:

```json
{
  "status": "ok",
  "service": "phishlens-api"
}
```

### `POST /analyze`

Recibe:

```json
{
  "url": "https://example.com/login",
  "dom_features": {
    "has_password_field": true,
    "num_forms": 1,
    "external_form_action": false,
    "num_iframes": 0,
    "external_links_ratio": 0.2,
    "has_hidden_inputs": true
  }
}
```

Devuelve:

```json
{
  "risk_score": 65,
  "label": "suspicious",
  "confidence": 0.72,
  "reasons": [
    "The page contains a password field",
    "The URL contains suspicious keywords"
  ],
  "sources": {
    "heuristics": true,
    "ml": false,
    "phishtank": false,
    "tls": false
  }
}
```

### `POST /report`

Recibe un posible falso positivo o falso negativo. No hace falta persistencia real al principio; puede registrar en logs o devolver confirmación.

## 6.3. PhishTank

Crea el servicio `phishtank_service.py` preparado para consultar PhishTank, pero no pongas ninguna API key real.

Debe:

* Leer la API key desde variable de entorno.
* Tener timeout.
* Gestionar errores.
* Tener modo fallback si no hay API key.
* No romper el análisis si PhishTank falla.

## 6.4. TLS / Certificados

Crea `tls_service.py` con una primera implementación defensiva y sencilla.

Debe intentar extraer:

* Si TLS parece válido.
* Días hasta expiración.
* Issuer, si es posible.
* Si el certificado está expirado.
* Errores controlados.

Importante: documenta que este análisis se realiza desde el backend y puede no representar exactamente lo que ve el navegador del usuario en redes con proxy o inspección TLS.

## 6.5. ML

Crea estructura inicial para ML:

* `ml/train_model.py`
* `ml/evaluate_model.py`
* `backend/app/services/ml_service.py`

No inventes un dataset real. Crea un dataset pequeño de ejemplo solo para validar el pipeline, marcado claramente como demo.

El código debe estar preparado para sustituir después el dataset por uno real.

El modelo debe poder:

* Cargar features.
* Entrenar baseline.
* Guardar modelo en `ml/models/phishlens_model.joblib`.
* Cargar modelo desde backend si existe.
* Si no existe modelo, usar solo scoring heurístico.

# 7. Sistema de scoring

Implementa un sistema híbrido:

```text
risk_score = heuristics_score + dom_score + threat_intel_score + tls_score + ml_adjustment
```

Primera versión aproximada:

* URL sospechosa: hasta 35 puntos.
* DOM sospechoso: hasta 30 puntos.
* Threat intelligence: hasta 40 puntos.
* TLS/certificado: hasta 15 puntos.
* ML adjustment: entre -10 y +20 puntos cuando exista modelo.

Normaliza siempre entre 0 y 100.

Labels:

* `safe`: 0-34.
* `suspicious`: 35-69.
* `dangerous`: 70-100.

Cada incremento importante debe generar una razón explicable.

Ejemplo:

* `URL is unusually long`
* `Domain contains suspicious keywords`
* `Page contains a password field`
* `Form submits data to an external domain`
* `URL uses punycode`
* `TLS certificate appears to be expired`
* `URL appears in a phishing intelligence feed`

# 8. Documentación obligatoria

Genera documentación profesional.

## README principal

Debe incluir:

* Nombre del proyecto.
* Descripción.
* Captura o placeholder de demo.
* Arquitectura.
* Stack.
* Instalación.
* Uso en desarrollo.
* Cómo cargar la extensión en Chrome.
* Cómo levantar backend.
* Cómo ejecutar tests.
* Roadmap.
* Limitaciones.
* Aviso ético.
* Privacidad.
* Estado actual del proyecto.

## `docs/architecture.md`

Debe explicar:

* Arquitectura general.
* Flujo de análisis.
* Comunicación extensión-backend.
* Por qué los certificados se analizan en backend.
* Diagrama textual.

## `docs/threat-model.md`

Debe incluir:

* Activos protegidos.
* Riesgos.
* Supuestos.
* Posibles abusos.
* Medidas de mitigación.

## `docs/privacy.md`

Debe dejar claro:

* Qué datos se procesan.
* Qué datos no se recogen.
* Que no se almacenan credenciales.
* Que no se leen valores de inputs.
* Que solo se procesan señales técnicas.

## `docs/ml-methodology.md`

Debe explicar:

* Objetivo del modelo.
* Features previstas.
* Dataset demo.
* Futuras fuentes de datos.
* Métricas.
* Riesgos de falsos positivos.
* Limitaciones.

## `docs/roadmap.md`

Debe dividir el proyecto en fases:

1. Bootstrap del repo.
2. MVP extensión.
3. Backend FastAPI.
4. DOM analyzer.
5. PhishTank.
6. TLS analyzer.
7. ML baseline.
8. UI avanzada.
9. Publicación.
10. Mejora continua.

# 9. AGENTS.md

Crea un archivo `AGENTS.md` con instrucciones para futuros agentes de IA que trabajen en el repositorio.

Debe indicar:

* No introducir código ofensivo.
* No capturar credenciales.
* Seguir Conventional Commits.
* Mantener separación entre extensión, backend, ML y docs.
* Añadir tests cuando se añadan servicios.
* No meter claves reales.
* Priorizar privacidad.
* Documentar decisiones importantes.
* No trabajar directamente en `main`.

# 10. CI/CD

Crea GitHub Actions básicos.

## Backend CI

Debe:

* Instalar Python.
* Instalar dependencias.
* Ejecutar tests con pytest.
* Comprobar imports principales.

## Extension CI

Debe:

* Instalar Node.
* Instalar dependencias.
* Ejecutar build.
* Ejecutar lint si se configura.

# 11. Docker

Crea:

* `backend/Dockerfile`
* `docker-compose.yml`

El `docker-compose.yml` debe levantar al menos:

* Backend FastAPI.
* Servicio opcional de Redis comentado o preparado para futuro.

# 12. Criterios de aceptación

Al terminar esta primera implementación, debe cumplirse:

* El repositorio Git está inicializado.
* Existen las ramas `main`, `develop` y `feature/bootstrap-project`.
* El trabajo está en `feature/bootstrap-project`.
* Hay commits con Conventional Commits.
* Existe estructura monorepo completa.
* La extensión se puede instalar en modo desarrollo.
* El popup muestra análisis local de la URL.
* El content script extrae features básicas del DOM.
* El backend arranca con FastAPI.
* `/health` funciona.
* `/analyze` devuelve un score explicable.
* Los tests backend pasan.
* Hay documentación suficiente para entender y continuar el proyecto.
* No hay secretos ni claves reales.
* No se recopilan datos sensibles.
* El README explica cómo ejecutar todo.

# 13. Forma de trabajar

Antes de escribir código:

1. Inspecciona el directorio actual.
2. Comprueba si ya existe un repo Git.
3. Si no existe, inicialízalo.
4. Crea la estructura de ramas descrita.
5. Explica brevemente el plan de ejecución.
6. Implementa por bloques.
7. Ejecuta pruebas y builds cuando sea posible.
8. Corrige errores encontrados.
9. Haz commits pequeños.
10. Al final, entrega un resumen claro.

Durante la implementación:

* No preguntes por detalles que puedas resolver con una decisión razonable.
* Toma decisiones técnicas prácticas y documenta las más importantes.
* No dejes código roto.
* No crees archivos innecesarios.
* No uses dependencias excesivas.
* No incluyas claves reales.
* No implementes funcionalidades ofensivas.
* No hagas merge a `main`.

# 14. Resultado final esperado

Cuando termines, proporciona un resumen con:

* Ramas creadas.
* Commits realizados.
* Archivos principales creados.
* Cómo ejecutar backend.
* Cómo cargar la extensión.
* Cómo ejecutar tests.
* Qué partes están implementadas.
* Qué partes quedan como roadmap.
* Riesgos o limitaciones técnicas detectadas.

Empieza ahora desde cero con la inicialización del repositorio y la implementación del MVP técnico inicial de PhishLens.
