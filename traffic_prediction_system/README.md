# Probability Reasoning System for Traffic Prediction — Smart Traffic Intelligence Platform V2

A runnable B.Tech CSE-AIML Phase-1 Smart Traffic Intelligence Platform built by upgrading the original Flask + SQLite project. Existing authentication, prediction history, database and core probability reasoning are preserved and extended.

## V2 features

- Existing Flask/SQLite user and admin authentication
- Transparent four-state probability reasoning: Low / Moderate / High / Severe
- Browser GPS with permission handling and manual map selection
- Leaflet + OpenStreetMap interactive maps
- Nominatim address search and reverse geocoding
- Open-Meteo current weather integration
- Evidence-strength explainability and natural-language reasoning
- Next-60-minute model projection
- Interactive what-if scenarios
- OSRM route comparison and route visualization
- Admin-managed incident intelligence
- In-app smart congestion alerts and alert history
- Searchable prediction history and prediction details/reopen
- Actual-traffic feedback and evaluation accuracy
- Admin analytics for states, activity, incidents and predicted-vs-actual evaluation
- Responsive dashboard, intelligence page, map, history and reports
- Additive SQLite migration for the original V1 database
- Error handling for external API failures and invalid input
- CSRF protection on state-changing authenticated forms/APIs
- No fabricated live traffic feed, accidents, accuracy or weather

## Technology stack

Python 3.11+ · Flask 3.1 · Flask-SQLAlchemy · Flask-Login · SQLite · Leaflet · OpenStreetMap · Nominatim · Open-Meteo · OSRM · Chart.js

External services are accessed from the browser/backend over the internet. No paid API key is required for the Phase-1 integrations.

## Architecture

```text
traffic_prediction_system/
├── app/
│   ├── __init__.py          # Flask factory, DB setup, migration, CSRF
│   ├── models.py            # Existing + V2 SQLAlchemy models
│   ├── auth.py              # Registration/login/logout
│   ├── main.py              # Pages + V2 JSON APIs
│   ├── admin.py             # Role-protected administration
│   ├── predictor.py         # Transparent probability/evidence engine
│   ├── services.py          # Nominatim/Open-Meteo/OSRM adapters
│   ├── templates/
│   └── static/
├── instance/traffic.db     # Created automatically on first run
├── run.py
├── start_windows.bat
├── requirements.txt
└── README.md
```

## Probability reasoning methodology

The project deliberately uses an interpretable Bayesian-style likelihood-ratio model rather than claiming to be a trained city-scale ML forecasting model.

1. Start with prior probabilities for four traffic states.
2. Convert each evidence input into state-specific likelihood factors.
3. Multiply the factors against the prior score.
4. Add optional visibility, humidity and wind evidence.
5. Normalize the four scores to approximately exactly 100%.
6. Select the highest probability as the predicted state.
7. Expose evidence strengths and a natural-language explanation.

This makes the algorithm easy to defend in a college viva: the same input always produces the same reasoning result, and the contribution of each factor can be inspected.

## API integrations

### OpenStreetMap / Nominatim
Used for address search and reverse geocoding. Requests use a descriptive User-Agent and are debounced on the client. Search failures fall back to manual map selection.

### Open-Meteo
Used for current temperature, humidity, wind, visibility and weather code. Weather codes are converted to readable categories. Weather failure never blocks manual prediction.

### OSRM
Used for driving-route geometry, distance and estimated duration. Route results are not described as live congestion-aware results.

## Important academic limitation

This system does **not** claim real-time traffic everywhere. It has no paid/live city traffic provider connected.

**Real external data:** GPS, OpenStreetMap map/geocoding, Open-Meteo weather, OSRM routing.

**User/recorded evidence:** vehicle count, average speed, incident and road condition.

**Project intelligence:** probability reasoning, explainability, trend projection, what-if simulation, alerts and historical evaluation.

Prediction accuracy is calculated only from predictions where a user/admin has recorded the actual traffic outcome. It is never fabricated.

## Installation — Windows / VS Code

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open:

- http://127.0.0.1:5000
- http://127.0.0.1:5000/intelligence

The first run creates the SQLite database automatically. If an older V1 database is already present, additive migrations add only the new fields/tables.

## Default admin

If unchanged:

- Email: `admin@traffic.local`
- Password: `Admin@12345`

Change the password before any real deployment.

## Demo / viva flow

1. Register a normal account or sign in as admin.
2. Open Intelligence.
3. Search a real road/city or use browser GPS.
4. Select a point on the Leaflet map.
5. Observe Open-Meteo weather.
6. Enter/confirm vehicle count, speed, period, incident and road condition.
7. Run the probability reasoning engine.
8. Explain the probability bars and evidence strengths.
9. Run a what-if scenario such as Vehicles +30% or Accident.
10. Compare two real route locations through OSRM.
11. Use Admin → Incidents to record an academic incident scenario.
12. Save predictions and later record actual traffic.
13. Show evaluation accuracy and admin analytics.

## Future scope

The architecture leaves clear adapters and model boundaries for a future paid/live traffic feed such as TomTom/HERE/Google, IoT vehicle sensors, CCTV vehicle detection, Raspberry Pi/ESP32 data, Kafka streams, trained ML forecasting, cloud deployment and push/email/SMS notifications. These are intentionally not faked in V2.
