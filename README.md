# WAI Collector

Microservice zur Erfassung, Normalisierung und Speicherung von On-Chain-Daten.
Ruft APIs wie Glassnode, CryptoQuant, Arkham oder Dune ab und schreibt Werte ins Backend bzw. direkt in die Datenbank.

## Features
- Periodische Datenerfassung (Cron Jobs)
- Normalisierung der Metriken
- Berechnung von Basiselementen für den WAI
- Retry-/Rate-Limit Handling
- Übergabe an das Backend per REST oder DB-Write

## Tech Stack
- Node.js (Axios, Cron, dotenv)
oder
- Python (Requests, schedule)

## Entwicklung
npm install  
npm run dev

## ENV Variablen
GLASSNODE_API_KEY=xxx
BACKEND_API_URL=http://localhost:3000
DATABASE_URL=postgresql://user:pass@localhost:5432/wai

## Jobs starten
npm run start
