# KiloCode handoff

## Current scaffold
- Standalone Gradle Android project under `smart-captain/`
- Kotlin domain models
- Basic fare/distance/time/fuel evaluation
- Platform adapter contract
- Arabic starter Activity

## Next implementation tasks
1. Replace starter Activity with Material UI or project-compatible UI.
2. Add settings persistence (DataStore or Room) and validation.
3. Add accessibility service metadata and opt-in service.
4. Implement Baly Captain adapter after inspecting installed app accessibility tree.
5. Add OCR fallback and field confidence.
6. Add overlay service and explicit permission workflow.
7. Add geofence models, map provider configuration, polygon/circle editor.
8. Add manual evaluation history and statistics.
9. Add acceptance controller in manual-safe state; automatic mode remains disabled until real integration is verified.
10. Add focused unit tests and README evidence.

## Constraints
- No invented Baly API or package assumptions.
- No fixed coordinate taps.
- Missing values are not zero.
- Automatic acceptance defaults OFF.
- Never claim acceptance without confirmation.
- Preserve the repository's existing applications and files.
