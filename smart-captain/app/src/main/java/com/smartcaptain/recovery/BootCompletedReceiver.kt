package com.smartcaptain.recovery

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/**
 * Boot completed receiver for Smart Captain recovery.
 *
 * After device reboot, Android may prevent automatic restart of accessibility
 * services and overlay services until the user launches the app again.
 * This receiver records the boot event and provides a clear recovery state.
 *
 * Does NOT attempt to restart the accessibility service (unsupported by Android).
 * Does NOT silently bypass user permissions.
 * Does NOT claim the app can run while the phone is powered off.
 */
class BootCompletedReceiver : BroadcastReceiver() {

    private val TAG = "BootCompletedReceiver"

    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action
        Log.d(TAG, "BootCompletedReceiver onReceive: action=$action")

        if (Intent.ACTION_BOOT_COMPLETED == action) {
            // Record that a reboot occurred so the UI can show recovery guidance
            val prefs = context.getSharedPreferences("smart_captain_recovery", Context.MODE_PRIVATE)
            prefs.edit()
                .putBoolean("reboot_occurred", true)
                .putLong("reboot_time_ms", System.currentTimeMillis())
                .apply()

            Log.d(TAG, "Reboot recorded. User must relaunch app to restore services.")
        }
    }

    companion object {
        /** Checks if a reboot has occurred since the last app launch. */
        fun hasPendingReboot(context: Context): Boolean {
            val prefs = context.getSharedPreferences("smart_captain_recovery", Context.MODE_PRIVATE)
            return prefs.getBoolean("reboot_occurred", false)
        }

        /** Clears the reboot flag after the app has been relaunched and services restored. */
        fun clearRebootFlag(context: Context) {
            val prefs = context.getSharedPreferences("smart_captain_recovery", Context.MODE_PRIVATE)
            prefs.edit().putBoolean("reboot_occurred", false).apply()
        }
    }
}
