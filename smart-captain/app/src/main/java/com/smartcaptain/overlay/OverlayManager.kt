package com.smartcaptain.overlay

import android.app.Activity
import android.app.Application
import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContract
import com.smartcaptain.domain.DriverSettings
import com.smartcaptain.domain.TripEvaluation
import com.smartcaptain.domain.TripOffer
import com.smartcaptain.domain.VehicleSettings
import com.smartcaptain.integration.TripPipeline

/**
 * OverlayManager coordinates the floating overlay lifecycle and integrates
 * with TripPipeline for live offer updates.
 *
 * The overlay visibility state is tracked as a [MutableStateFlow] so that UI
 * components can observe the actual service/window state rather than a local
 * boolean that may drift out of sync.
 *
 * Usage from MainActivity or settings screen:
 *   val overlayManager = OverlayManager(context)
 *   overlayManager.overlayVisible.collect { visible -> ... }
 *   overlayManager.showOverlay()  // requires overlay permission
 */
class OverlayManager(private val context: Context) {

    private val permissionHelper = OverlayPermissionHelper

    /** Tracks whether the overlay window is currently added to WindowManager. */
    private val _overlayVisible = androidx.lifecycle.MutableLiveData<Boolean>(false)
    val overlayVisible: androidx.lifecycle.LiveData<Boolean> = _overlayVisible

    /**
     * Whether the overlay permission is currently granted.
     */
    fun hasOverlayPermission(): Boolean =
        permissionHelper.hasOverlayPermission(context)

    /**
     * Whether the overlay window is currently visible.
     */
    fun isOverlayVisible(): Boolean = _overlayVisible.value == true

    /**
     * Requests overlay permission by opening system settings.
     */
    fun requestOverlayPermission(): Intent =
        permissionHelper.requestOverlayPermissionIntent(context)

    /**
     * Starts the floating overlay service.
     * Caller should verify hasOverlayPermission() == true before calling.
     */
    fun showOverlay() {
        if (isOverlayVisible()) return
        _overlayVisible.value = true
        context.startService(OverlayService.createStartIntent(context))
    }

    /**
     * Stops the floating overlay service.
     * Only stops OverlayService — does not affect the host Activity.
     */
    fun hideOverlay() {
        if (!isOverlayVisible()) return
        _overlayVisible.value = false
        context.stopService(OverlayService.createStopIntent(context))
    }

    /**
     * Toggles the overlay visibility.
     */
    fun toggleOverlay() {
        if (isOverlayVisible()) {
            hideOverlay()
        } else {
            showOverlay()
        }
    }

    /**
     * Called by OverlayService when the window view is successfully added.
     * Keeps the visibility state in sync with the actual window state.
     */
    fun onWindowAdded() {
        _overlayVisible.value = true
    }

    /**
     * Called by OverlayService when the window view is removed.
     * Keeps the visibility state in sync with the actual window state.
     */
    fun onWindowRemoved() {
        _overlayVisible.value = false
    }

    /**
     * Processes an extracted TripOffer through TripPipeline and updates the overlay.
     * This is the main integration entry point from BalyAccessibilityService.
     */
    fun processExtractedOffer(offer: TripOffer) {
        TripPipeline.processOffer(offer, DriverSettings(), VehicleSettings())
    }

    /**
     * Registers an evaluation listener (e.g., from MainActivity) to react to
     * new evaluations in the main app UI.
     */
    fun registerMainAppListener(listener: (TripEvaluation) -> Unit): () -> Unit {
        return TripPipeline.registerEvaluationListener(listener)
    }

    /**
     * Resets the pipeline state (clears last offer/evaluation).
     */
    fun resetPipeline() {
        TripPipeline.reset()
    }

    /**
     * Creates an ActivityResultContract for overlay permission requests.
     * The contract captures [context] so parseResult can check the grant status.
     */
    fun overlayPermissionContract(): ActivityResultContract<Unit, Boolean> =
        object : ActivityResultContract<Unit, Boolean>() {
            override fun createIntent(context: Context, input: Unit): Intent =
                permissionHelper.requestOverlayPermissionIntent(context)

            override fun parseResult(resultCode: Int, intent: Intent?): Boolean =
                Settings.canDrawOverlays(context)
        }
}

/**
 * Registers an overlay permission launcher on a ComponentActivity.
 * MainActivity must extend ComponentActivity to use this.
 */
fun ComponentActivity.registerOverlayPermissionLauncher(
    context: Context,
    onResult: (Boolean) -> Unit
): ActivityResultLauncher<Unit> {
    val contract = object : ActivityResultContract<Unit, Boolean>() {
        override fun createIntent(context: Context, input: Unit): Intent =
            Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                .setData(android.net.Uri.parse("package:${context.packageName}"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        override fun parseResult(resultCode: Int, intent: Intent?): Boolean =
            Settings.canDrawOverlays(context)
    }
    return registerForActivityResult(contract) { granted ->
        onResult(granted)
    }
}