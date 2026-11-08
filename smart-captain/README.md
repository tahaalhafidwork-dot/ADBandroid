# Smart Captain

Standalone Android Kotlin driver trip-evaluation assistant. Initial platform target: Baly Captain (Iraq); adapter architecture supports additional platforms later.

## Status
This is a scaffold for KiloCode to continue. Trip evaluation, settings, sample data, and the Arabic-first UI are designed for local implementation. Live Baly screen extraction, OCR calibration, geofence map provider configuration, and automatic acceptance require testing on a real device with Baly Captain installed.

## Build
Open this folder in Android Studio or build from the command line:
```bash
gradle assembleDebug
```
Android SDK and a compatible JDK/Gradle installation are required.

## Permissions and safety
Overlay and Accessibility are user-enabled from Android Settings. Monitoring is opt-in. Automatic acceptance is OFF by default and must remain disabled unless a supported, reliable acceptance control is identified and the user explicitly enables it. No fixed-coordinate taps.

## Initial implementation scope
- Kotlin Android app scaffold
- Arabic RTL dashboard
- Domain models and trip calculation engine
- Fuel and fee estimates
- Configurable settings
- Adapter interface for Baly and future platforms
- Manual mode by default
- Safe automation controller contract
- Local trip history architecture

## Known limitations
No public Baly API is assumed. Screen extraction, OCR, route-based geofence checking, and acceptance must be verified against the installed Baly Captain version. Unknown fields remain unknown; never treat them as zero.
