package com.smartcaptain.domain

import com.smartcaptain.domain.TripDecision.*
import com.smartcaptain.domain.TripEvaluation.*
import com.smartcaptain.domain.TripOffer.*
import com.smartcaptain.domain.VehicleSettings.*
import com.smartcaptain.domain.DriverSettings.*
import org.junit.Test
import org.junit.Assert.*

class QuickTripEvaluatorTest {

    private val vehicle = VehicleSettings()
    val settings = DriverSettings()

    @Test
    fun testIncompleteData() {
        val offer = TripOffer(id = "test-1", fareIqd = 10000.0, pickupDistanceKm = null, tripDistanceKm = 10.0,
            pickupDurationMinutes = 10.0, tripDurationMinutes = 30.0)
        val eval = TripEvaluator.evaluate(offer, settings, vehicle)
        assert(eval.decision == INCOMPLETE)
    }

    @Test
    fun testNegativeFare() {
        val offer = TripOffer(id = "test-2", fareIqd = -100.0, pickupDistanceKm = 5.0, tripDistanceKm = 10.0,
            pickupDurationMinutes = 5.0, tripDurationMinutes = 10.0)
        val eval = TripEvaluator.evaluate(offer, settings, vehicle)
        assert(eval.decision == INCOMPLETE)
    }

    @Test
    fun testTripWithReasons() {
        val offer = TripOffer(id = "test-3", fareIqd = 2000.0, pickupDistanceKm = 5.0, tripDistanceKm = 10.0,
            pickupDurationMinutes = 5.0, tripDurationMinutes = 20.0)
        val eval = TripEvaluator.evaluate(offer, settings, vehicle)
        // Should have reasons about low fare
        assert(eval.reasons.any { it.contains("أقل") })
        // Decision should not be INCOMPLETE (data is valid)
        assert(eval.decision != INCOMPLETE)
    }

    @Test
    fun testHighPickupDistance() {
        val offer = TripOffer(id = "test-4", fareIqd = 10000.0, pickupDistanceKm = 10.0, tripDistanceKm = 10.0,
            pickupDurationMinutes = 5.0, tripDurationMinutes = 20.0)
        val eval = TripEvaluator.evaluate(offer, settings, vehicle)
        // Should have reason about long distance
        assert(eval.reasons.any { it.contains("طويلة") })
        // Decision: pickupDistanceExceeded is true, so should be REJECT per our logic
        assert(eval.decision == REJECT)
    }

    @Test
    fun testCannotCoverCosts() {
        val offer = TripOffer(id = "test-5", fareIqd = 100.0, pickupDistanceKm = 50.0, tripDistanceKm = 50.0,
            pickupDurationMinutes = 30.0, tripDurationMinutes = 60.0)
        val vehicle = VehicleSettings(fuelPriceIqdPerLiter = 2000.0)
        val eval = TripEvaluator.evaluate(offer, settings, vehicle)
        // Should have cannotCoverCosts issue
        assert(eval.decision == REJECT || eval.decision == MARGINAL)
    }
}