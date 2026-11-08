package com.smartcaptain.domain

import kotlin.math.max

object TripEvaluator {
    fun evaluate(offer: TripOffer, settings: DriverSettings, vehicle: VehicleSettings): TripEvaluation {
        val reasons = mutableListOf<String>()
        val fare = offer.fareIqd
        val pickupKm = offer.pickupDistanceKm
        val tripKm = offer.tripDistanceKm
        val pickupMin = offer.pickupDurationMinutes
        val tripMin = offer.tripDurationMinutes

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
        val net = fare - fuelCost - platformFee - maintenance
        val netKm = net / distance
        val netHour = net / duration * 60.0

        if (fare < settings.minFareIqd) reasons += "السعر أقل من الحد الأدنى"
        if (grossKm < settings.minGrossIqdPerKm) reasons += "السعر لكل كم أقل من المطلوب"
        if (grossHour < settings.minGrossHourlyIqd) reasons += "العائد الإجمالي بالساعة منخفض"
        if (pickupKm > settings.maxPickupDistanceKm) reasons += "مسافة الوصول للراكب طويلة"
        if (pickupMin > settings.maxPickupDurationMinutes) reasons += "وقت الوصول للراكب طويل"
        if (settings.minNetIqdPerKm > 0 && netKm < settings.minNetIqdPerKm) reasons += "صافي الربح لكل كم منخفض"
        if (settings.minNetHourlyIqd > 0 && netHour < settings.minNetHourlyIqd) reasons += "صافي الربح بالساعة منخفض"
        if (settings.maxTotalDistanceKm != null && distance > settings.maxTotalDistanceKm) reasons += "المسافة الإجمالية تتجاوز الحد"
        if (settings.maxTotalDurationMinutes != null && duration > settings.maxTotalDurationMinutes) reasons += "الوقت الإجمالي يتجاوز الحد"

        val decision = when {
            reasons.any { it.contains("أقل") || it.contains("منخفض") || it.contains("طويل") || it.contains("تتجاوز") } -> TripDecision.REJECT
            netKm >= max(settings.minNetIqdPerKm, 1.0) && netHour >= max(settings.minNetHourlyIqd, 1.0) -> TripDecision.GOOD
            else -> TripDecision.MARGINAL
        }
        return TripEvaluation(decision, distance, duration, grossKm, grossHour, fuelLiters, fuelCost, net, netKm, netHour, reasons)
    }
}
