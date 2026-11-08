package com.smartcaptain.integration

import com.smartcaptain.domain.DriverSettings
import com.smartcaptain.domain.TripOffer
import com.smartcaptain.domain.TripEvaluator
import com.smartcaptain.domain.VehicleSettings
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class TripPipelineTest {

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
        fuelPriceIqdPerLiter = 1000.0
    )

    @Before
    fun setup() {
        TripPipeline.reset()
    }

    @Test
    fun testProcessOffer_completeOffer_returnsEvaluation() {
        val offer = TripOffer(
            id = "test-1",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(offer, settings, vehicle)

        assertNotNull(result)
        assertNotNull(result!!.decision)
        assertNotNull(result.estimatedNetIqd)
        assertNotNull(result.netPerKmIqd)
        assertNotNull(result.netPerHourIqd)
        assertTrue(TripPipeline.lastOffer == offer)
    }

    @Test
    fun testProcessOffer_incompleteOffer_missingFare_returnsNull() {
        val offer = TripOffer(
            id = "test-2",
            platformId = "baly",
            fareIqd = null,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(offer, settings, vehicle)

        assertNull(result)
        assertNull(TripPipeline.lastEvaluation)
    }

    @Test
    fun testProcessOffer_incompleteOffer_missingDistance_returnsNull() {
        val offer = TripOffer(
            id = "test-3",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = null,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(offer, settings, vehicle)

        assertNull(result)
        assertNull(TripPipeline.lastEvaluation)
    }

    @Test
    fun testProcessOffer_incompleteOffer_missingTripDistance_returnsNull() {
        val offer = TripOffer(
            id = "test-4",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = null,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(offer, settings, vehicle)

        assertNull(result)
        assertNull(TripPipeline.lastEvaluation)
    }

    @Test
    fun testProcessOffer_incompleteOffer_missingPickupTime_returnsNull() {
        val offer = TripOffer(
            id = "test-5",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = null,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )

        val result = TripPipeline.processOffer(offer, settings, vehicle)

        assertNull(result)
        assertNull(TripPipeline.lastEvaluation)
    }

    @Test
    fun testProcessOffer_incompleteOffer_missingTripDuration_returnsNull() {
        val offer = TripOffer(
            id = "test-6",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = null
        )

        val result = TripPipeline.processOffer(offer, settings, vehicle)

        assertNull(result)
        assertNull(TripPipeline.lastEvaluation)
    }

    @Test
    fun testStatusSummary_initialState() {
        TripPipeline.reset()
        assertEquals("No offer extracted", TripPipeline.statusSummary())
    }

    @Test
    fun testStatusSummary_afterOfferExtracted() {
        TripPipeline.reset()
        val offer = TripOffer(
            id = "test-7",
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
    fun testReset_clearsState() {
        TripPipeline.reset()
        val offer = TripOffer(
            id = "test-8",
            platformId = "baly",
            fareIqd = 15000.0,
            pickupDistanceKm = 1.0,
            pickupDurationMinutes = 5.0,
            tripDistanceKm = 10.0,
            tripDurationMinutes = 20.0
        )
        TripPipeline.processOffer(offer, settings, vehicle)
        assertNotNull(TripPipeline.lastOffer)
        TripPipeline.reset()
        assertNull(TripPipeline.lastOffer)
        assertNull(TripPipeline.lastEvaluation)
    }

    @Test
    fun testIntegrationStatus_initialState() {
        val status = IntegrationStatus()
        assertFalse(status.balyDetected)
        assertFalse(status.accessibilityConnected)
        assertFalse(status.offerDetected)
        assertFalse(status.offerParsed)
        assertFalse(status.evaluationCompleted)
        assertFalse(status.isReady())
        assertEquals("Baly Captain not detected", status.statusText())
    }

    @Test
    fun testIntegrationStatus_allComplete() {
        val status = IntegrationStatus(
            balyDetected = true,
            accessibilityConnected = true,
            offerDetected = true,
            offerParsed = true,
            evaluationCompleted = true
        )
        assertTrue(status.isReady())
        assertEquals("Integrated and ready", status.statusText())
    }

    @Test
    fun testIntegrationStatus_withParsingError() {
        val status = IntegrationStatus(
            balyDetected = true,
            accessibilityConnected = true,
            offerDetected = true,
            offerParsed = false,
            evaluationCompleted = false,
            parsingError = "Failed to parse fare"
        )
        assertFalse(status.isReady())
        assertEquals("Error: Failed to parse fare", status.statusText())
    }
}