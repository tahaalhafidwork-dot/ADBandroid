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
 * - Service enabled in Android Settings (user toggled it on)
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
     * Opens the Android Accessibility settings page so the user can
     * enable Smart Captain's accessibility service.
     */
    fun openAccessibilitySettings(context: android.content.Context) {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }
}