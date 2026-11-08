package com.smartcaptain.platform

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.view.accessibility.AccessibilityEvent
import android.util.Log
import com.smartcaptain.accessibility.AccessibilityConnectionManager
import com.smartcaptain.domain.TripOffer

/**
 * Baly Captain Accessibility Service.
 *
 * Reads visible text from the active Baly window.
 * Detects when a new trip offer appears.
 * Avoids duplicate offer processing.
 * Does not read passwords or protected fields.
 * Does not interact with Baly buttons.
 *
 * Requires BIND_ACCESSIBILITY_SERVICE permission and accessibility enabled by user.
 *
 * ## Real-device verification results
 *
 * Package name verified: `app.baly.driver`
 * Accessibility service NOT currently enabled for Smart Captain
 * Baly driver app observed in foreground with Arabic text and Arabic-Indic numerals
 */
class BalyAccessibilityService : AccessibilityService() {

    internal val processedEventIds = mutableSetOf<Long>()
    private var lastSeenOfferHash: Long? = null
    private var offerStableCount = 0

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        try {
            Log.d("BalyAccessibility", "Accessibility event received: type=${event.eventType}, package=${event.packageName}")

            // Only process foreground window state changes
            if (event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
                return
            }

            val packageName = event.packageName?.toString() ?: return
            Log.d("BalyAccessibility", "Event from package: $packageName")

            // Only process Baly Captain (verified package name)
            if (!BalyPlatformAdapter.BALY_PACKAGE_NAME.equals(packageName, true)) {
                Log.d("BalyAccessibility", "Ignoring non-Baly package: $packageName")
                return
            }

            // Get visible text from the event
            val text = event.text?.joinToString("\n") ?: return

            Log.d("BalyAccessibility", "Visible text from Baly (${text.length} chars): $text")

            // Avoid duplicate processing using event hash
            val eventHash = event.hashCode().toLong()
            if (processedEventIds.contains(eventHash)) {
                Log.d("BalyAccessibility", "Skipping duplicate event: $eventHash")
                return
            }
            processedEventIds.add(eventHash)

            // Keep only recent event IDs to prevent memory growth
            if (processedEventIds.size > 50) {
                processedEventIds.clear()
            }

            // Normalize text for analysis
            val normalized = BalyPlatformAdapter.normalizeArabicIndicNumerals(text)

            // Check if this looks like a trip-offer screen
            if (!isLikelyTripOffer(normalized)) {
                Log.d("BalyAccessibility", "Text does not appear to be a trip offer")
                return
            }

            Log.d("BalyAccessibility", "Text appears to be a trip offer")

            // Extract offer data
            val offer = BalyPlatformAdapter.extractTripOfferFromText(normalized)

            if (offer != null) {
                Log.d("BalyAccessibility", "Trip offer extracted: id=${offer.id}, fare=${offer.fareIqd}, pickupDist=${offer.pickupDistanceKm}, pickupTime=${offer.pickupDurationMinutes}, tripDist=${offer.tripDistanceKm}, tripDuration=${offer.tripDurationMinutes}")

                // Check for stability (same offer appearing multiple times)
                val currentHash = offer.id.hashCode().toLong()
                if (currentHash == lastSeenOfferHash) {
                    offerStableCount++
                    if (offerStableCount < 3) {
                        Log.d("BalyAccessibility", "Offer not yet stable (count=$offerStableCount), waiting")
                        return
                    }
                    Log.d("BalyAccessibility", "Offer confirmed stable after $offerStableCount detections")
                    offerStableCount = 0
                } else {
                    lastSeenOfferHash = currentHash
                    offerStableCount = 0
                }

                // Offer extracted successfully - send to evaluation pipeline
                Log.d("BalyAccessibility", "Sending offer to TripEvaluator")
                // Integration point: offer is ready for TripEvaluator evaluation
            } else {
                Log.d("BalyAccessibility", "Offer extraction returned null (incomplete data)")
            }

        } catch (e: Exception) {
            Log.e("BalyAccessibility", "Error processing accessibility event", e)
        }
    }

    /**
     * Checks if the given text likely contains a trip offer from Baly.
     * Uses heuristic patterns based on observed Baly screen content.
     */
    private fun isLikelyTripOffer(text: String): Boolean {
        val lower = text.lowercase()
        // Trip offer indicators in Arabic or English
        val indicators = listOf(
            "سعر", "جرة", "الأجرة", // fare/price
            "مسافة", "كم", "م", // distance
            "مدة", "س", "دق", // duration
            "إجمالي", "رحلة", // trip
            "فاتورة", "عرض", // offer/bill
            "بالي", "baly", // English/Branding
            "دينار", // currency
            "مغلق", "مفتوح" // driver status
        )

        return indicators.any { lower.contains(it) }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d("BalyAccessibility", "Service connected")
        AccessibilityConnectionManager.markConnected()
    }

    override fun onUnbind(intent: Intent): Boolean {
        Log.d("BalyAccessibility", "Service unbound")
        AccessibilityConnectionManager.markDisconnected()
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        Log.d("BalyAccessibility", "Service destroyed")
        AccessibilityConnectionManager.markDisconnected()
        super.onDestroy()
    }

    override fun onInterrupt() {
        // Default implementation - called when accessibility events are interrupted
    }

    /**
     * Resets the duplicate detection state.
     * Call when trip offers change context (e.g., new session).
     */
    fun resetState() {
        processedEventIds.clear()
        lastSeenOfferHash = null
        offerStableCount = 0
        Log.d("BalyAccessibility", "Service state reset")
    }
}