# Smart Captain UI/UX and Functional Review

## Design direction
- Arabic-first, RTL, Material 3.
- Calm driver-oriented hierarchy: status > mode > daily summary > setup next step.
- Large high-contrast text, restrained color, rounded cards, no decorative charts before real data exists.
- Manual mode is the default; automatic mode is visibly marked and safety-gated.
- Use explicit empty, loading, unavailable, permission-denied, and error states.
- Do not display fabricated live metrics. Empty dashboard uses zero only for actual count and em dash for unavailable money metrics.

## Current screen
Dashboard Compose prototype:
- Header and app identity
- Connection status card (explicitly indicates Baly is not connected)
- Manual/automatic mode switch
- Daily metric placeholders
- Setup guidance
- Bottom navigation for dashboard, settings, areas, history

## UX implementation rules for KiloCode
1. Preserve the dashboard visual hierarchy and improve rather than replace it arbitrarily.
2. Make navigation destinations real screens, not dead tabs.
3. Persist mode preference, but never persist automatic acceptance as enabled across process/device restart without a fresh safety validation. Start in manual after restart.
4. Settings must use validated fields with units and clear defaults.
5. Show fuel cost separately from estimated net fare; label estimates.
6. Missing extraction fields display “غير متوفر”, not 0.
7. The offer card must explain why it was rated/blocked.
8. Accessibility service, overlay, location, and map permissions each need explanatory onboarding and status.
9. Automatic acceptance must have a persistent, prominent stop action and be disabled when offer confidence, screen state, or acceptance node is uncertain.
10. Avoid tiny floating controls and avoid overlays covering Baly accept/reject actions.
11. Use loading placeholders only while actual operations are underway; do not animate fake analysis.
12. Provide Arabic locale and RTL; format IQD and Arabic/Western numerals consistently, with user preference if possible.
13. Add UI previews for key states and focused tests for calculations/settings.
14. Test on small screens and Android 12+ permission flows.

## Functional caveats
The current Compose dashboard is UI scaffolding only. The mode switch is local UI state and does not execute trip automation. Baly detection, map/geofence, persistence, OCR, history, and acceptance are not yet wired. Keep status copy truthful until these services are implemented and device-tested.
