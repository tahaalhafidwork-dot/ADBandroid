package com.smartcaptain.overlay

import android.content.Context
import android.content.Intent
import android.provider.Settings

/**
 * Helper for SYSTEM_ALERT_WINDOW (overlay) permission handling.
 *
 * On Android 6.0+, drawing over other apps requires the user to explicitly grant
 * "Display over other apps" permission via Settings. This permission cannot be
 * requested at runtime — the app must open the system settings page.
 */
object OverlayPermissionHelper {

    /** Request code used when starting the overlay settings activity. */
    const val REQUEST_CODE_OVERLAY_PERMISSION = 1001

    /** Checks whether the app currently has overlay permission granted. */
    fun hasOverlayPermission(context: Context): Boolean =
        Settings.canDrawOverlays(context)

    /**
     * Opens the system overlay permission settings page so the user can grant
     * "Display over other apps" for Smart Captain.
     *
     * Returns an Intent suitable for startActivityForResult / ActivityResultLauncher.
     */
    fun requestOverlayPermissionIntent(context: Context): Intent {
        return Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
            .setData(android.net.Uri.parse("package:${context.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
}