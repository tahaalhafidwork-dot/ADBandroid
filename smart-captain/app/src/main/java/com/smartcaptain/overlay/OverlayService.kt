package com.smartcaptain.overlay

import android.app.Service
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.Settings
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import android.view.WindowManager.LayoutParams
import androidx.core.app.NotificationCompat
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.platform.ComposeView
import com.smartcaptain.domain.DriverSettings
import com.smartcaptain.domain.TripEvaluation
import com.smartcaptain.domain.VehicleSettings
import com.smartcaptain.integration.TripPipeline

/**
 * Smart Captain Floating Overlay Service.
 *
 * Displays a movable floating bubble above other applications (including Baly Driver).
 * Tapping the bubble expands an analysis panel showing live trip evaluation results.
 *
 * Runs as a foreground service so the bubble remains visible while Baly Driver is in
 * the foreground and Smart Captain is in the background.
 *
 * Architecture:
 *   BalyAccessibilityService → BalyPlatformAdapter → TripOffer → TripPipeline → TripEvaluator → OverlayService
 *
 * Permissions:
 *   - SYSTEM_ALERT_WINDOW (must be granted by user via Settings)
 *   - FOREGROUND_SERVICE (required for background operation)
 *   - FOREGROUND_SERVICE_DATA_SYNC (required on Android 14+)
 *
 * Limitations:
 *   - No automatic acceptance or rejection
 *   - No interaction with Baly controls
 *   - No OCR
 *   - No maps or geofencing
 */
class OverlayService : Service() {

    private val TAG = "OverlayService"
    private val NOTIFICATION_ID = 1001
    private val CHANNEL_ID = "smart_captain_overlay"
    private val CHANNEL_NAME = "Smart Captain Overlay"

    private lateinit var windowManager: WindowManager
    private var composeView: ComposeView? = null
    private var windowViewAdded = false

    /** Ensures all Compose UI mutations happen on the main thread. */
    private val mainHandler = Handler(Looper.getMainLooper())

    // Overlay UI state — exposed as MutableState so Compose recomposes on change
    private val _isExpanded = mutableStateOf(false)
    private val _currentEvaluation = mutableStateOf<TripEvaluation?>(null)
    private val _isProcessing = mutableStateOf(false)

    // Listener registration for pipeline updates
    private var pipelineListenerRegistration: (() -> Unit)? = null

    // Default driver/vehicle settings for evaluation (driver-configurable in settings screen)
    private val defaultSettings = DriverSettings()
    private val defaultVehicle = VehicleSettings()

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "OverlayService created")
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        Log.d(TAG, "OverlayService start command received: action=$action")

        // Start as foreground service so the overlay remains visible
        // when Smart Captain is in the background and Baly is in the foreground.
        startForeground(NOTIFICATION_ID, buildNotification())

        when (action) {
            ACTION_TOGGLE_OVERLAY -> {
                if (windowViewAdded) {
                    stopOverlay()
                } else {
                    startOverlay()
                }
            }
            ACTION_STOP_OVERLAY -> {
                stopOverlay()
                stopSelf(startId)
            }
            else -> startOverlay()
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        Log.d(TAG, "OverlayService destroyed")
        stopOverlay()
        pipelineListenerRegistration?.invoke()
        pipelineListenerRegistration = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    /** Shows the floating bubble overlay. */
    private fun startOverlay() {
        if (windowViewAdded) {
            Log.d(TAG, "Overlay already visible")
            return
        }

        // Verify overlay permission before attempting to add the window
        if (!Settings.canDrawOverlays(this)) {
            Log.e(TAG, "Cannot start overlay: SYSTEM_ALERT_WINDOW permission not granted")
            return
        }

        // Register pipeline listener to receive live evaluations.
        // All state mutations are posted to the main thread for Compose safety.
        pipelineListenerRegistration = TripPipeline.registerEvaluationListener { evaluation ->
            mainHandler.post {
                _currentEvaluation.value = evaluation
                _isProcessing.value = false
            }
        }

        // Initialize Compose UI and add to window on the main thread
        try {
            composeView = ComposeView(this@OverlayService)
            composeView?.setContent {
                SmartCaptainOverlay(
                    onClose = { stopOverlay() },
                    onCollapse = { _isExpanded.value = false },
                    onExpand = { _isExpanded.value = true },
                    onDrag = { dx, dy ->
                        val params = composeView?.layoutParams as? LayoutParams
                        if (params != null) {
                            params.x += dx.toInt()
                            params.y += dy.toInt()
                            windowManager.updateViewLayout(composeView, params)
                        }
                    },
                    isExpanded = _isExpanded.value,
                    evaluation = _currentEvaluation.value,
                    isProcessing = _isProcessing.value
                )
            }

            // WindowManager params for floating overlay
            // Use WRAP_CONTENT so the window only covers the bubble area, not the entire screen.
            // Positioning is handled via params.x / params.y rather than Compose offset(),
            // so the window itself stays compact and doesn't interfere with underlying apps.
            val params = LayoutParams().apply {
                type = LayoutParams.TYPE_APPLICATION_OVERLAY
                flags = LayoutParams.FLAG_NOT_FOCUSABLE or
                    LayoutParams.FLAG_NOT_TOUCH_MODAL or
                    LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH or
                    LayoutParams.FLAG_LAYOUT_NO_LIMITS
                format = PixelFormat.TRANSLUCENT
                gravity = Gravity.TOP or Gravity.START
                x = 50
                y = 200
                width = LayoutParams.WRAP_CONTENT
                height = LayoutParams.WRAP_CONTENT
            }

            windowManager.addView(composeView, params)
            windowViewAdded = true
            // Notify OverlayManager that the window is now visible (source of truth)
            OverlayManagerInstance.get()?.onWindowAdded()
            Log.d(TAG, "Overlay bubble added to window successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to add overlay view", e)
            composeView = null
            pipelineListenerRegistration?.invoke()
            pipelineListenerRegistration = null
            throw e
        }
    }

    /** Hides and removes the floating overlay. */
    private fun stopOverlay() {
        if (!windowViewAdded) {
            Log.d(TAG, "Overlay not visible, nothing to stop")
            return
        }

        try {
            composeView?.let { view ->
                windowManager.removeView(view)
                Log.d(TAG, "Overlay removed from window")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to remove overlay view", e)
        } finally {
            composeView = null
            windowViewAdded = false
            // Notify OverlayManager that the window is now removed (source of truth)
            OverlayManagerInstance.get()?.onWindowRemoved()
            pipelineListenerRegistration?.invoke()
            pipelineListenerRegistration = null
            _isExpanded.value = false
            _currentEvaluation.value = null
            _isProcessing.value = false
        }
    }

    /**
     * Called by BalyAccessibilityService when a new offer is extracted and evaluated.
     * Updates the overlay panel with the latest evaluation on the main thread.
     */
    fun onNewEvaluation(evaluation: TripEvaluation) {
        mainHandler.post {
            _currentEvaluation.value = evaluation
            _isProcessing.value = false
        }
    }

    /**
     * Called by BalyAccessibilityService when offer processing begins.
     */
    fun onProcessingStarted() {
        mainHandler.post {
            _isProcessing.value = true
        }
    }

    /** Create the notification channel required for Android 8+. */
    private fun createNotificationChannel() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                android.app.NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Smart Captain floating overlay service"
                enableLights(false)
                enableVibration(false)
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    /** Build the foreground service notification. */
    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Smart Captain")
            .setContentText("النافذة العائمة نشطة")
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()
    }

    companion object {
        /** Intent action to toggle the overlay on/off. */
        const val ACTION_TOGGLE_OVERLAY = "com.smartcaptain.action.TOGGLE_OVERLAY"
        /** Intent action to stop the overlay. */
        const val ACTION_STOP_OVERLAY = "com.smartcaptain.action.STOP_OVERLAY"

        /**
         * Creates an intent to start the overlay service.
         */
        fun createStartIntent(context: Context): Intent =
            Intent(context, OverlayService::class.java).apply {
                action = ACTION_TOGGLE_OVERLAY
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

        /**
         * Creates an intent to stop the overlay service.
         */
        fun createStopIntent(context: Context): Intent =
            Intent(context, OverlayService::class.java).apply {
                action = ACTION_STOP_OVERLAY
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
    }
}

/**
 * Singleton holder for OverlayManager instance so OverlayService can
 * report window added/removed events back to the UI layer.
 */
object OverlayManagerInstance {
    private var instance: OverlayManager? = null

    fun set(instance: OverlayManager) {
        this.instance = instance
    }

    fun get(): OverlayManager? = instance
}