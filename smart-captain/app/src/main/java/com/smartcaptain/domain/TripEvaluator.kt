package com.smartcaptain.domain

import kotlin.math.max

object TripEvaluator {
    /** Clear rejection criteria – if any of these are triggered the trip is REJECTed. */
    private data class RejectionCriteria(
        val fareTooLow: Boolean,
        val pickupDistanceExceeded: Boolean,
        val pickupTimeExceeded: Boolean,
        val cannotCoverCosts: Boolean
    )

    fun evaluate(offer: TripOffer, settings: DriverSettings, vehicle: VehicleSettings): TripEvaluation {
        val reasons = mutableListOf<String>()

        val fare = offer.fareIqd
        val pickupKm = offer.pickupDistanceKm
        val tripKm = offer.tripDistanceKm
        val pickupMin = offer.pickupDurationMinutes
        val tripMin = offer.tripDurationMinutes

        // --- Validity check: must have all values, be finite, non-negative, and meaningful ---
        val valid = listOf(fare, pickupKm, tripKm, pickupMin, tripMin).all { it != null && it.isFinite() && it >= 0.0 }
        if (!valid || fare == null || pickupKm == null || tripKm == null || pickupMin == null || tripMin == null ||
            offer.confidence < settings.minConfidence || fare <= 0.0 || pickupKm + tripKm <= 0.0 || pickupMin + tripMin <= 0.0) {
            return TripEvaluation(TripDecision.INCOMPLETE, null, null, null, null, null, null, null, null, null,
                listOf("بيانات الرحلة غير مكتملة أو غير موثوقة"))
        }

        val distance = pickupKm + tripKm
        val duration = pickupMin + tripMin
        val grossKm = fare / distance
        val grossHour = fare / duration * 60.0
        val fuelLiters = distance * vehicle.fuelConsumptionLPer100Km / 100.0
        val fuelCost = fuelLiters * vehicle.fuelPriceIqdPerLiter
        val platformFee = (vehicle.platformFeePercent?.let { fare * it / 100.0 } ?: 0.0) +
            (vehicle.platformFeeFixedIqd ?: 0.0)
        val maintenance = distance * vehicle.maintenanceIqdPerKm
        val extraCost = vehicle.extraCostIqd
        val net = fare - fuelCost - platformFee - maintenance - extraCost
        val netKm = net / distance
        val netHour = net / duration * 60.0

        // --- Collect reasons (always collected, but do NOT determine decision level) ---
        if (fare < settings.minFareIqd) reasons += "السعر أقل من الحد الأدنى"
        if (grossKm < settings.minGrossIqdPerKm) reasons += "السعر لكل كم أقل من المطلوب"
        if (grossHour < settings.minGrossHourlyIqd) reasons += "العائد الإجمالي بالساعة منخفض"
        if (pickupKm > settings.maxPickupDistanceKm) reasons += "مسة الوصول للراكب طويلة"
        if (pickupMin > settings.maxPickupDurationMinutes) reasons += "وقت الوصول للراكب طويلة"
        if (settings.minNetIqdPerKm > 0 && netKm < settings.minNetIqdPerKm) reasons += "صافي الربح لكل كم منخفض"
        if (settings.minNetHourlyIqd > 0 && netHour < settings.minNetHourlyIqd) reasons += "صافي الربح بالساعة منخفض"
        if (settings.maxTotalDistanceKm != null && distance > settings.maxTotalDistanceKm) reasons += "المسة الإجمالية ت超越 الحد"
        if (settings.maxTotalDurationMinutes != null && duration > settings.maxTotalDurationMinutes) reasons += "الوقت الإجمالي ي超越 الحد"

        // --- Clear rejection criteria – specific, significant violations only ---
        val rejection = RejectionCriteria(
            fareTooLow = fare < settings.minFareIqd,
            pickupDistanceExceeded = pickupKm > settings.maxPickupDistanceKm,
            pickupTimeExceeded = pickupMin > settings.maxPickupDurationMinutes,
            cannotCoverCosts = net < 0.0
        )

        // --- Decision logic ---
        // 1. INCOMPLETE already returned above; now check clear rejection criteria
        val clearRejection = rejection.fareTooLow ||
            rejection.pickupDistanceExceeded ||
            rejection.pickupTimeExceeded ||
            rejection.cannotCoverCosts

        // 2. EXCELLENT: significantly above all minimum thresholds (50% margin)
        val excellent = netKm >= max(settings.minNetIqdPerKm, 1.0) * 1.5 &&
            netHour >= max(settings.minNetHourlyIqd, 1.0) * 1.5 &&
            !clearRejection

        // 3. GOOD: meets minimum acceptable thresholds
        val good = netKm >= max(settings.minNetIqdPerKm, 1.0) &&
            netHour >= max(settings.minNetHourlyIqd, 1.0) &&
            !clearRejection

        // 4. MARGINAL: close to thresholds but not meeting GOOD, and no clear rejection
        val marginal = !clearRejection && !excellent && !good

        // 5. REJECT: one or more clear rejection criteria triggered
        val decision = when {
            clearRejection -> TripDecision.REJECT
            excellent -> TripDecision.EXCELLENT
            good -> TripDecision.GOOD
            marginal -> TripDecision.MARGINAL
            else -> TripDecision.INCOMPLETE // fallback, should not reach here
        }

        return TripEvaluation(decision, distance, duration, grossKm, grossHour, fuelLiters, fuelCost, net, netKm, netHour, reasons)
    }
}