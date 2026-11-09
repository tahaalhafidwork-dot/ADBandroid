package com.smartcaptain.accessibility

import android.content.Context
import android.content.Intent
import android.provider.Settings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Tracks the actual Accessibility service connection state.
 *
 * Distinguishes between:
 * - Accessibility service enabled in Android Settings (system-wide toggle)
 * - Smart Captain's accessibility service specifically enabled
 * - Service actually connected and running (system bound to it)
 *
 * The UI must only show "connected" when the service is genuinely bound,
 * not merely when the user enabled the toggle in Settings.
 */
object AccessibilityConnectionManager {

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected

    private val _isEnabled = MutableStateFlow(false)
    val isEnabled: StateFlow<Boolean> = _isEnabled

    /** Marks the service as connected (system bound to it). */
    fun markConnected() {
        _isConnected.value = true
        _isEnabled.value = true
    }

    /** Marks the service as disconnected (system unbound or service stopped). */
    fun markDisconnected() {
        _isConnected.value = false
    }

    /** Marks the service as enabled in Settings (user toggled it on). */
    fun markEnabled() {
        _isEnabled.value = true
    }

    /** Marks the service as disabled in Settings. */
    fun markDisabled() {
        _isEnabled.value = false
        _isConnected.value = false
    }

    /**
     * Returns true only when the service is genuinely connected and running.
     */
    fun isServiceConnected(): Boolean = _isConnected.value

    /**
     * Checks whether the accessibility service is enabled in system settings.
     */
    fun isAccessibilityEnabled(context: Context): Boolean {
        return try {
            Settings.Secure.getInt(context.contentResolver, Settings.Secure.ACCESSIBILITY_ENABLED, 0) == 1
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Checks whether Smart Captain's accessibility service is specifically enabled.
     * Compares the enabled services list against this package's service name.
     */
    fun isSmartCaptainServiceEnabled(context: Context): Boolean {
        return try {
            val enabledServices = Settings.Secure.getString(
                context.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: ""
            // The system stores the fully qualified component
            // (com.smartcaptain/com.smartcaptain.platform.BalyAccessibilityService).
            // Checking only the abbreviated form (com.smartcaptain/.platform...) never
            // matches, so the UI would stay stuck on "not enabled". Accept both forms.
            val component = android.content.ComponentName(
                context,
                com.smartcaptain.platform.BalyAccessibilityService::class.java
            )
            enabledServices.contains(component.flattenToString(), ignoreCase = true) ||
                enabledServices.contains(component.flattenToShortString(), ignoreCase = true)
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Refreshes the enabled state from system settings.
     * Call this when the Activity resumes to reflect the current system state.
     */
    fun refreshEnabledState(context: Context) {
        val systemEnabled = isAccessibilityEnabled(context)
        val serviceEnabled = isSmartCaptainServiceEnabled(context)
        _isEnabled.value = systemEnabled && serviceEnabled
        if (!_isEnabled.value) {
            _isConnected.value = false
        }
    }

    /**
     * Opens the Android Accessibility settings page so the user can
     * enable Smart Captain's accessibility service.
     */
    fun openAccessibilitySettings(context: android.content.Context) {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }
}
