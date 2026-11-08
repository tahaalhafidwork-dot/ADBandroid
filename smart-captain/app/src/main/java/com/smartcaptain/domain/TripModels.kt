package com.smartcaptain.domain

enum class ExtractionSource { ACCESSIBILITY, OCR, MANUAL }
enum class TripDecision { EXCELLENT, GOOD, MARGINAL, REJECT, INCOMPLETE }

data class TripOffer(
    val id: String,
    val platformId: String = "baly",
    val fareIqd: Double?,
    val pickupDistanceKm: Double?,
    val pickupDurationMinutes: Double?,
    val tripDistanceKm: Double?,
    val tripDurationMinutes: Double?,
    val pickupAddress: String? = null,
    val destinationAddress: String? = null,
    val rideCategory: String? = null,
    val detectedAt: Long = System.currentTimeMillis(),
    val expiresAt: Long? = null,
    val confidence: Float = 1f,
    val source: ExtractionSource = ExtractionSource.MANUAL
)

/**
 * Vehicle-level cost settings. All values are driver-configurable.
 *
 * Defaults are placeholders only: they are never treated as measured data.
 * A negative or non-finite value is rejected by [TripEvaluator.evaluate] and
 * forces an [TripDecision.INCOMPLETE] result rather than silently corrupting
 * the cost estimate.
 */
data class VehicleSettings(
    val fuelConsumptionLPer100Km: Double = 8.0,
    val fuelPriceIqdPerLiter: Double = 1000.0,
    val platformFeePercent: Double? = null,
    val platformFeeFixedIqd: Double? = null,
    val maintenanceIqdPerKm: Double = 0.0,
    val extraCostIqd: Double = 0.0
) {
    init {
        require(fuelConsumptionLPer100Km > 0.0) { "fuelConsumptionLPer100Km must be positive" }
        require(fuelPriceIqdPerLiter >= 0.0) { "fuelPriceIqdPerLiter must be non-negative" }
        require(platformFeePercent == null || platformFeePercent in 0.0..100.0) {
            "platformFeePercent must be null or in [0, 100]"
        }
        require(platformFeeFixedIqd == null || platformFeeFixedIqd >= 0.0) {
            "platformFeeFixedIqd must be null or non-negative"
 }
        require(maintenanceIqdPerKm >= 0.0) { "maintenanceIqdPerKm must be non-negative" }
        require(extraCostIqd >= 0.0) { "extraCostIqd must be non-negative" }
    }
}

/**
 * Driver-level acceptance thresholds.
 *
 * A `null` / zero minimum means "no constraint". Positive values are hard
 * floors; negative values are invalid and force INCOMPLETE.
 */
data class DriverSettings(
    val minGrossIqdPerKm: Double = 1000.0,
    val minNetIqdPerKm: Double = 0.0,
    val minFareIqd: Double = 5000.0,
    val minGrossHourlyIqd: Double = 15000.0,
    val minNetHourlyIqd: Double = 0.0,
    val maxPickupDistanceKm: Double = 3.0,
    val maxPickupDurationMinutes: Double = 15.0,
    val maxTotalDistanceKm: Double? = null,
    val maxTotalDurationMinutes: Double? = null,
    val minConfidence: Float = 0.85f
) {
    init {
        require(minGrossIqdPerKm >= 0.0) { "minGrossIqdPerKm must be non-negative" }
        require(minNetIqdPerKm >= 0.0) { "minNetIqdPerKm must be non-negative" }
        require(minFareIqd >= 0.0) { "minFareIqd must be non-negative" }
        require(minGrossHourlyIqd >= 0.0) { "minGrossHourlyIqd must be non-negative" }
        require(minNetHourlyIqd >= 0.0) { "minNetHourlyIqd must be non-negative" }
        require(maxPickupDistanceKm >= 0.0) { "maxPickupDistanceKm must be non-negative" }
        require(maxPickupDurationMinutes >= 0.0) { "maxPickupDurationMinutes must be non-negative" }
        require(maxTotalDistanceKm == null || maxTotalDistanceKm >= 0.0) {
            "maxTotalDistanceKm must be null or non-negative"
        }
        require(maxTotalDurationMinutes == null || maxTotalDurationMinutes >= 0.0) {
            "maxTotalDurationMinutes must be null or non-negative"
        }
        require(minConfidence in 0.0f..1.0f) { "minConfidence must be in [0, 1]" }
    }
}

data class TripEvaluation(
    val decision: TripDecision,
    val totalDistanceKm: Double?,
    val totalDurationMinutes: Double?,
    val grossPerKmIqd: Double?,
    val grossPerHourIqd: Double?,
    val fuelLiters: Double?,
    val fuelCostIqd: Double?,
    val estimatedNetIqd: Double?,
    val netPerKmIqd: Double?,
    val netPerHourIqd: Double?,
    val reasons: List<String>
)