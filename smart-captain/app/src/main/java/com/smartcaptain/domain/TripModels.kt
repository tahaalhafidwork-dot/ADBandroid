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

data class VehicleSettings(
    val fuelConsumptionLPer100Km: Double = 8.0,
    val fuelPriceIqdPerLiter: Double = 1000.0,
    val platformFeePercent: Double? = null,
    val platformFeeFixedIqd: Double? = null,
    val maintenanceIqdPerKm: Double = 0.0
)

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
)

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
