package com.smartcaptain.integration

import com.smartcaptain.domain.DriverSettings
import com.smartcaptain.domain.TripEvaluation
import com.smartcaptain.domain.TripOffer
import com.smartcaptain.domain.TripEvaluator
import com.smartcaptain.domain.VehicleSettings
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class TripPipelineOverlayIntegrationTest {

    private val settings = DriverSettings(
        minGrossIqdPerKm = 1000.0,
        minNetIqdPerKm = 0.0,
        minFareIqd = 5000.0,
        minGrossHourlyIqd = 15000.0,
        minNetHourlyIqd = 0.0,
        maxPickupDistanceKm = 3.0,
        maxPickupDurationMinutes = 15.0
    )

    private val vehicle = VehicleSettings(
        fuelConsumptionLPer100Km = 8.0,
        fuelPriceIqdPerLiter = 0.0
    )

    @Before
    fun setup() {
        TripPipeline.reset()
    }

    @Test
    fun testPipelineStoresLastOfferAndEvaluation() {
        val offer = TripOffer(
            id = "offer-1",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(offer, settings, vehicle)

        assertNotNull(result)
        assertSame(offer, TripPipeline.lastOffer)
        assertSame(result, TripPipeline.lastEvaluation)
    }

    @Test
    fun testPipelineNewOfferReplacesPrevious() {
        val offer1 = TripOffer(
            id = "offer-1",
            platformId = "baly",
            fareIqd = 10000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )
        val offer2 = TripOffer(
            id = "offer-2",
            platformId = "baly",
            fareIqd = 20000.0,
            pickupDistanceKm = 2.0,
            pickupDurationMinutes = 8.0,
            tripDistanceKm = 15.0,
            tripDurationMinutes = 30.0
        )

        TripPipeline.processOffer(offer1, settings, vehicle)
        TripPipeline.processOffer(offer2, settings, vehicle)

        assertSame(offer2, TripPipeline.lastOffer)
        assertEquals(20000.0, TripPipeline.lastEvaluation!!.estimatedNetIqd!!, 0.001)
    }

    @Test
    fun testPipelineDuplicateOfferId_createsNewEvaluation() {
        // Same offer ID but different data → new evaluation replaces old
        val offerA = TripOffer(
            id = "same-id",
            platformId = "baly",
            fareIqd = 5000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )
        val offerB = TripOffer(
            id = "same-id",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 2.0,
            pickupDurationMinutes = 8.0,
            tripDistanceKm = 15.0,
            tripDurationMinutes = 30.0
        )

        TripPipeline.processOffer(offerA, settings, vehicle)
        assertEquals(5000.0, TripPipeline.lastEvaluation!!.estimatedNetIqd!!, 0.001)

        TripPipeline.processOffer(offerB, settings, vehicle)
        assertEquals(15000.0, TripPipeline.lastEvaluation!!.estimatedNetIqd!!, 0.001)
    }

    @Test
    fun testPipelineIncompleteOffer_returnsNullAndStoresNoEvaluation() {
        val incompleteOffer = TripOffer(
            id = "incomplete-1",
            platformId = "baly",
            fareIqd = null,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(incompleteOffer, settings, vehicle)

        assertNull(result)
        assertNull(TripPipeline.lastEvaluation)
        // lastOffer IS stored even for incomplete (for reference)
        assertSame(incompleteOffer, TripPipeline.lastOffer)
    }

    @Test
    fun testPipelineIncompleteOffer_missingTripDistance_returnsNull() {
        val incompleteOffer = TripOffer(
            id = "incomplete-2",
            platformId = "baly",
            fareIqd = 10000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = null,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(incompleteOffer, settings, vehicle)

        assertNull(result)
        assertNull(TripPipeline.lastEvaluation)
    }

    @Test
    fun testPipelineNotificationListener_calledOnEvaluation() {
        var receivedEvaluation: TripEvaluation? = null
        val unregister = TripPipeline.registerEvaluationListener { eval ->
            receivedEvaluation = eval
        }

        val offer = TripOffer(
            id = "notify-test",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        TripPipeline.processOffer(offer, settings, vehicle)

        assertNotNull(receivedEvaluation)
        assertEquals(15000.0, receivedEvaluation!!.estimatedNetIqd!!, 0.001)

        // Unregister and verify no further notifications
        unregister()
        receivedEvaluation = null
        TripPipeline.processOffer(offer.copy(id = "notify-test-2"), settings, vehicle)
        assertNull(receivedEvaluation)
    }

    @Test
    fun testPipelineEvaluationCategories() {
        // EXCELLENT: high profit
        val excellentOffer = TripOffer(
            id = "excellent",
            platformId = "baly",
            fareIqd = 50000.0,
            pickupDistanceKm = 0.5,
            pickupDurationMinutes = 2.0,
            tripDistanceKm = 20.0,
            tripDurationMinutes = 25.0
        )
        val excellentEval = TripPipeline.processOffer(excellentOffer, settings, vehicle)
        assertNotNull(excellentEval)
        // Should be EXCELLENT or GOOD depending on thresholds
        assertTrue(excellentEval!!.decision == com.smartcaptain.domain.TripDecision.EXCELLENT ||
            excellentEval.decision == com.smartcaptain.domain.TripDecision.GOOD)

        // REJECT: fare too low
        val rejectOffer = TripOffer(
            id = "reject",
            platformId = "baly",
            fareIqd = 1000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )
        val rejectEval = TripPipeline.processOffer(rejectOffer, settings, vehicle)
        assertNotNull(rejectEval)
        assertEquals(com.smartcaptain.domain.TripDecision.REJECT, rejectEval!!.decision)

        // INCOMPLETE: missing data
        val incompleteEval = TripPipeline.processOffer(
            TripOffer(
                id = "inc",
                platformId = "baly",
                fareIqd = null,
                pickupDistanceKm = 1.0,
                pickupDurationMinutes = 5.0,
                tripDistanceKm = 10.0,
                tripDurationMinutes = 20.0
            ),
            settings,
            vehicle
        )
        assertNull(incompleteEval)
    }

    @Test
    fun testPipelineFinancialFields_populated() {
        val offer = TripOffer(
            id = "financial",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        val eval = TripPipeline.processOffer(offer, settings, vehicle)

        assertNotNull(eval)
        assertNotNull(eval!!.fuelCostIqd)
        assertNotNull(eval.estimatedNetIqd)
        assertNotNull(eval.netPerKmIqd)
        assertNotNull(eval.netPerHourIqd)
        assertNotNull(eval.totalDistanceKm)
        assertNotNull(eval.totalDurationMinutes)

        // Total distance = pickup + trip = 1 + 10 = 11
        assertEquals(11.0, eval.totalDistanceKm!!, 0.001)
        // Total duration = pickup + trip = 5 + 20 = 25
        assertEquals(25.0, eval.totalDurationMinutes!!, 0.001)
    }

    @Test
    fun testStatusSummary_states() {
        TripPipeline.reset()
        assertEquals("No offer extracted", TripPipeline.statusSummary())

        val offer = TripOffer(
            id = "status-test",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )
        TripPipeline.processOffer(offer, settings, vehicle)
        assertTrue(TripPipeline.statusSummary().contains("evaluated"))
    }

    @Test
    fun testReset_clearsAllState() {
        val offer = TripOffer(
            id = "reset-test",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )
        TripPipeline.processOffer(offer, settings, vehicle)
        assertNotNull(TripPipeline.lastOffer)
        assertNotNull(TripPipeline.lastEvaluation)

        TripPipeline.reset()
        assertNull(TripPipeline.lastOffer)
        assertNull(TripPipeline.lastEvaluation)
        assertFalse(TripPipeline.isProcessing)
    }
}