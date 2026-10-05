# Semicon Risk Intelligence — UI Phase 1

Premium frontend shell for the Semiconductor Credit-Risk Decision-Support Framework.

## What is built

- High-end dark institutional design system
- Responsive sidebar and navigation
- Command Center
- Real project milestone strip: 36 projects, 10,000 MC runs, 162 scenario tests, Phase 13J PASS, 0 hard failures
- Portfolio Intelligence Map **with clearly-labelled UI placeholder coordinates**
- Validation & Governance panel
- Methodology-decision panel explaining why supervised default classification was withheld
- Research development timeline
- Presentation Mode / Research Mode toggle
- API adapter file ready for a future FastAPI bridge

## Research-safety rule

This frontend does not modify the validated research engine. The portfolio-map coordinates are UI demonstration placeholders only and are explicitly marked as such. No calibrated PD, LGD, EAD, loss, risk score, or project-specific financial value is fabricated.

## Run locally

```bash
npm install
npm run dev
```

Then open the local address shown by Vite (normally `http://localhost:5173`).

## Production build check

```bash
npm run build
```

## Next UI phase

1. Project Intelligence page
2. Real canonical-project API mapping
3. Evidence-confidence components
4. PCA / cluster explorer
5. Stress Lab
6. Monte Carlo Studio
7. Credit Optimizer
8. Scenario Compare
9. Governance drill-down
10. Panel presentation flow

## Integration note

The current validated research logic should remain unchanged. The recommended next backend step is to expose read-only outputs through a thin FastAPI adapter, then connect `src/lib/api.js` to those endpoints.
