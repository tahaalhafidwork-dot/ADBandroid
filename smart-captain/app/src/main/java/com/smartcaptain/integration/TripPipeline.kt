package com.smartcaptain.integration

import com.smartcaptain.domain.DriverSettings
import com.smartcaptain.domain.TripEvaluation
import com.smartcaptain.domain.TripOffer
import com.smartcaptain.domain.TripEvaluator
import com.smartcaptain.domain.VehicleSettings

/**
 * Integration pipeline connecting Baly offer extraction to TripEvaluator.
 *
 * Receives extracted TripOffer instances from BalyPlatformAdapter,
 * validates completeness, and evaluates them using TripEvaluator.
 *
 * Incomplete offers remain INCOMPLETE — never evaluated with missing data treated as zero.
 */
object TripPipeline {

    /** Last evaluated result, or null if no evaluation has been performed. */
    var lastEvaluation: TripEvaluation? = null
        private set

    /** Last extracted offer, or null if no offer has been extracted. */
    var lastOffer: TripOffer? = null
        private set

    /** Whether an offer is currently being processed. */
    var isProcessing: Boolean = false
        private set

    /** Registered evaluation listeners notified when a new evaluation completes. */
    private val evaluationListeners = mutableListOf<(TripEvaluation) -> Unit>()

    /**
     * Register a listener to be notified when a new TripEvaluation completes.
     * Returns a disposable registration that removes the listener when called.
     */
    fun registerEvaluationListener(listener: (TripEvaluation) -> Unit): () -> Unit {
        evaluationListeners.add(listener)
        return { evaluationListeners.remove(listener) }
    }

    /**
     * Process an extracted offer through the full pipeline:
     * extraction → validation → evaluation.
     *
     * Returns the TripEvaluation result, or null if the offer was incomplete.
     */
    fun processOffer(offer: TripOffer, settings: DriverSettings, vehicle: VehicleSettings): TripEvaluation? {
        lastOffer = offer
        isProcessing = true

        try {
            // Validate that all required fields are present
            val requiredFieldsMissing = mutableListOf<String>()
            if (offer.fareIqd == null) requiredFieldsMissing.add("fareIqd")
            if (offer.pickupDistanceKm == null) requiredFieldsMissing.add("pickupDistanceKm")
            if (offer.pickupDurationMinutes == null) requiredFieldsMissing.add("pickupDurationMinutes")
            if (offer.tripDistanceKm == null) requiredFieldsMissing.add("tripDistanceKm")
            if (offer.tripDurationMinutes == null) requiredFieldsMissing.add("tripDurationMinutes")

            if (requiredFieldsMissing.isNotEmpty()) {
                // Incomplete offers remain INCOMPLETE — do not evaluate
                return null
            }

            // Evaluate using TripEvaluator
            val evaluation = TripEvaluator.evaluate(offer, settings, vehicle)
            lastEvaluation = evaluation

            // Notify all registered listeners
            evaluationListeners.forEach { listener ->
                try {
                    listener(evaluation)
                } catch (e: Exception) {
                    // Listener errors are isolated — they must not break the pipeline
                }
            }

            return evaluation
        } catch (e: Exception) {
            return null
        } finally {
            isProcessing = false
        }
    }

    /** Reset pipeline state. */
    fun reset() {
        lastOffer = null
        lastEvaluation = null
        isProcessing = false
        evaluationListeners.clear()
    }

    /** Get a human-readable status summary. */
    fun statusSummary(): String {
        return when {
            lastOffer == null -> "No offer extracted"
            lastEvaluation == null -> "Offer extracted but not yet evaluated (or incomplete)"
            else -> "Offer evaluated: ${lastEvaluation!!.decision}"
        }
    }
}

/**
 * Integration status model for UI display.
 *
 * Tracks the integration state across Baly detection, accessibility connection,
 * offer detection, parsing, and evaluation.
 */
data class IntegrationStatus(
    /** Whether Baly Captain package was detected on the device. */
    val balyDetected: Boolean = false,

    /** Whether the accessibility service is connected/enabled. */
    val accessibilityConnected: Boolean = false,

    /** Whether a trip offer has been detected. */
    val offerDetected: Boolean = false,

    /** Whether the offer was successfully parsed into a TripOffer. */
    val offerParsed: Boolean = false,

    /** Whether the evaluation has been completed. */
    val evaluationCompleted: Boolean = false,

    /** Last parsing error message, if any. */
    val parsingError: String? = null,

    /** Last verified package name observed. */
    val verifiedPackageName: String? = null
) {
    /** Returns overall integration readiness (all critical stages complete). */
    fun isReady(): Boolean =
        balyDetected && accessibilityConnected && offerDetected && offerParsed && evaluationCompleted

    /** Returns a human-readable status string. */
    fun statusText(): String {
        return when {
            !balyDetected -> "Baly Captain not detected"
            !accessibilityConnected -> "Accessibility not connected"
            !offerDetected -> "No offer detected"
            parsingError != null -> "Error: $parsingError"
            !offerParsed -> "Offer parsing failed"
            !evaluationCompleted -> "Evaluation pending"
            else -> "Integrated and ready"
        }
    }
}