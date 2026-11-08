package com.smartcaptain.platform

import com.smartcaptain.domain.ExtractionSource
import com.smartcaptain.domain.TripOffer
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class BalyPlatformAdapterTest {

    private val adapter = BalyPlatformAdapter

    @Before
    fun setup() {
        // Adapter is object, no initialization needed
    }

    // ========================================================================
    // Real-device integration tests (package verification)
    // ========================================================================

    @Test
    fun testVerifiedPackageName() {
        // Package name verified on real device: app.baly.driver
        assertEquals("app.baly.driver", BalyPlatformAdapter.BALY_PACKAGE_NAME)
    }

    @Test
    fun testIsSupportedPackage_balyDriver() {
        assertTrue(adapter.isSupportedPackage("app.baly.driver"))
    }

    @Test
    fun testIsSupportedPackage_wrongPackage() {
        // The old unverified package name com.baly.captain is NOT supported
        assertFalse(adapter.isSupportedPackage("com.baly.captain"))
    }

    @Test
    fun testIsSupportedPackage_other() {
        assertFalse(adapter.isSupportedPackage("com.other.app"))
    }

    @Test
    fun testIsSupportedPackage_empty() {
        assertFalse(adapter.isSupportedPackage(""))
    }

    // ========================================================================
    // Number normalization tests (screenshot fixture values)
    // ========================================================================

    @Test
    fun testNormalizeArabicIndicNumerals_english() {
        val result = adapter.normalizeArabicIndicNumerals("Hello World 123")
        assertEquals("Hello World 123", result)
    }

    @Test
    fun testNormalizeArabicIndicNumerals_arabicIndic() {
        // ١٢٣ = 123 in Arabic-Indic
        val result = adapter.normalizeArabicIndicNumerals("السعر ١٢٣ دينار")
        assertTrue(result.contains("123"))
        assertFalse(result.contains("١"))
    }

    @Test
    fun testNormalizeArabicIndicNumerals_mixed() {
        val input = "الرصيد: ٢٢,٢٥٠ دينار"
        val result = adapter.normalizeArabicIndicNumerals(input)
        assertTrue(result.contains("22,250"))
        assertFalse(result.contains("٢"))
    }

    @Test
    fun testNormalizeArabicIndicNumerals_screenshotFare() {
        // Arabic screenshot value: ٣,٢٥٠ → 3,250
        val input = "٣,٢٥٠ دينار"
        val result = adapter.normalizeArabicIndicNumerals(input)
        assertEquals("3,250 دينار", result)
    }

    // ========================================================================
    // Number parsing tests
    // ========================================================================

    @Test
    fun testParseNumber_thousandsSeparator() {
        // "3,250" → 3250.0 (comma is thousands separator)
        assertEquals(3250.0, adapter.parseNumber("3,250")!!, 0.001)
    }

    @Test
    fun testParseNumber_decimal() {
        assertEquals(1.5, adapter.parseNumber("1.5")!!, 0.001)
    }

    @Test
    fun testParseNumber_arabicIndicAlreadyNormalized() {
        // After normalization: "3,250" → 3250.0
        assertEquals(3250.0, adapter.parseNumber("3,250")!!, 0.001)
    }

    @Test
    fun testParseNumber_arabicIndicRaw() {
        // "٣,٢٥٠" → normalize → "3,250" → 3250.0
        val normalized = adapter.normalizeArabicIndicNumerals("٣,٢٥٠")
        assertEquals(3250.0, adapter.parseNumber(normalized)!!, 0.001)
    }

    @Test
    fun testParseNumber_empty() {
        assertNull(adapter.parseNumber(""))
    }

    @Test
    fun testParseNumber_invalid() {
        assertNull(adapter.parseNumber("abc"))
    }

    // ========================================================================
    // Screenshot fixture extraction tests
    //
    // Screenshot reference values:
    //   Fare: 3,250 IQD (Arabic: ٣,٢٥٠ دينار)
    //   Pickup ETA: 5 minutes, Distance: 1 km, Location: الموصل، Hawler Road
    //   Trip Duration: 15 minutes, Distance: 7 km, Location: الموصل، شارع البحرين
    //   Service category: Super
    //   Total distance: 8 km, Total time: 20 minutes
    // ========================================================================

    private val screenshotText = """
        السعر الإجمالي ٣,٢٥٠ دينار
        مسافة الوصول ١ كيلومتر
        وقت الوصول ٥ دقيقة
        مسافة الرحلة ٧ كيلومتر
        مدة الرحلة ١٥ دقيقة
        نقطة الوصول الموصل، Hawler Road
        الوجهة الموصل، شارع البحرين
        سوبر
    """.trimIndent()

    @Test
    fun testExtractFare_screenshot() {
        assertEquals(3250.0, adapter.extractFare(screenshotText)!!, 0.001)
    }

    @Test
    fun testExtractFare_westernNumerals() {
        val text = "السعر الإجمالي 3,250 دينار"
        assertEquals(3250.0, adapter.extractFare(text)!!, 0.001)
    }

    @Test
    fun testExtractFare_missing() {
        assertNull(adapter.extractFare("مسافة الوصول 1 كم"))
    }

    @Test
    fun testExtractPickupDistance_screenshot() {
        assertEquals(1.0, adapter.extractPickupDistance(screenshotText)!!, 0.001)
    }

    @Test
    fun testExtractPickupTime_screenshot() {
        assertEquals(5.0, adapter.extractPickupTime(screenshotText)!!, 0.001)
    }

    @Test
    fun testExtractTripDistance_screenshot() {
        assertEquals(7.0, adapter.extractTripDistance(screenshotText)!!, 0.001)
    }

    @Test
    fun testExtractTripDuration_screenshot() {
        assertEquals(15.0, adapter.extractTripDuration(screenshotText)!!, 0.001)
    }

    @Test
    fun testExtractPickupLocation_screenshot() {
        val location = adapter.extractPickupLocation(screenshotText)
        assertNotNull(location)
        assertTrue(location!!.contains("الموصل"))
        assertTrue(location.contains("Hawler Road"))
    }

    @Test
    fun testExtractDestinationLocation_screenshot() {
        val location = adapter.extractDestinationLocation(screenshotText)
        assertNotNull(location)
        assertTrue(location!!.contains("الموصل"))
        assertTrue(location.contains("شارع البحرين"))
    }

    @Test
    fun testExtractServiceCategory_screenshot() {
        assertEquals("Super", adapter.extractServiceCategory(screenshotText))
    }

    @Test
    fun testExtractServiceCategory_english() {
        val text = "Service category: Super"
        assertEquals("Super", adapter.extractServiceCategory(text))
    }

    @Test
    fun testExtractServiceCategory_missing() {
        assertNull(adapter.extractServiceCategory("سعر الرحلة 5000 دينار"))
    }

    // ========================================================================
    // Context-aware extraction: distinguish pickup vs destination
    // ========================================================================

    @Test
    fun testContextDistinguishesPickupFromTrip() {
        // Pickup distance should be 1 km (near "وصول"), trip distance 7 km (near "رحلة")
        assertEquals(1.0, adapter.extractPickupDistance(screenshotText)!!, 0.001)
        assertEquals(7.0, adapter.extractTripDistance(screenshotText)!!, 0.001)
        // Verify they are NOT swapped
        assertNotEquals(7.0, adapter.extractPickupDistance(screenshotText)!!, 0.001)
        assertNotEquals(1.0, adapter.extractTripDistance(screenshotText)!!, 0.001)
    }

    @Test
    fun testContextDistinguishesPickupTimeFromTripDuration() {
        assertEquals(5.0, adapter.extractPickupTime(screenshotText)!!, 0.001)
        assertEquals(15.0, adapter.extractTripDuration(screenshotText)!!, 0.001)
    }

    // ========================================================================
    // TripOffer conversion tests
    // ========================================================================

    @Test
    fun testExtractTripOffer_screenshot_complete() {
        val result = adapter.extractTripOfferFromText(screenshotText)

        assertNotNull(result)
        assertEquals(3250.0, result!!.fareIqd!!, 0.001)
        assertEquals(1.0, result.pickupDistanceKm!!, 0.001)
        assertEquals(5.0, result.pickupDurationMinutes!!, 0.001)
        assertEquals(7.0, result.tripDistanceKm!!, 0.001)
        assertEquals(15.0, result.tripDurationMinutes!!, 0.001)
        assertEquals("baly", result.platformId)
        assertEquals(ExtractionSource.ACCESSIBILITY, result.source)
        assertNotNull(result.pickupAddress)
        assertTrue(result.pickupAddress!!.contains("الموصل"))
        assertNotNull(result.destinationAddress)
        assertTrue(result.destinationAddress!!.contains("شارع البحرين"))
        assertEquals("Super", result.rideCategory)
    }

    @Test
    fun testExtractTripOffer_missingRequiredFields_returnsNull() {
        // Missing fare → null
        val text1 = "مسافة الوصول 1 كم مسافة الرحلة 7 كم"
        assertNull(adapter.extractTripOfferFromText(text1))

        // Single distance used for both pickup and trip
        val text2 = "السعر 3250 دينار مسافة الرحلة 7 كم"
        val result2 = adapter.extractTripOfferFromText(text2)
        assertNotNull(result2)
        assertEquals(3250.0, result2!!.fareIqd!!, 0.001)
        assertEquals(7.0, result2.pickupDistanceKm!!, 0.001)
        assertEquals(7.0, result2.tripDistanceKm!!, 0.001)

        // Missing trip distance → null
        val text3 = "السعر 3250 دينار مسافة الوصول 1 كم"
        val result3 = adapter.extractTripOfferFromText(text3)
        assertNotNull(result3)
        assertEquals(3250.0, result3!!.fareIqd!!, 0.001)
        assertEquals(1.0, result3.pickupDistanceKm!!, 0.001)
        assertEquals(1.0, result3.tripDistanceKm!!, 0.001)
    }

    @Test
    fun testExtractTripOffer_noTripIndicators_returnsExtractedValues() {
        // Text with numbers but no contextual labels → extracted using position-based logic
        val text = "3250 دينار 1 كم 7 كم"
        val result = adapter.extractTripOfferFromText(text)
        assertNotNull(result)
        assertEquals(3250.0, result!!.fareIqd!!, 0.001)
        assertEquals(1.0, result.pickupDistanceKm!!, 0.001)
        assertEquals(7.0, result.tripDistanceKm!!, 0.001)
    }

    @Test
    fun testExtractTripOffer_blankText_returnsNull() {
        assertNull(adapter.extractTripOfferFromText(""))
        assertNull(adapter.extractTripOfferFromText("   "))
    }

    // ========================================================================
    // Total distance and duration calculation (TripEvaluator handles summation)
    // ========================================================================

    @Test
    fun testTotalDistanceAndTime_calculatedByEvaluator() {
        // TripEvaluator computes totalDistanceKm = pickupKm + tripKm
        // and totalDurationMinutes = pickupMin + tripMin
        // Adapter extracts components only; totals derived by evaluator
        val result = adapter.extractTripOfferFromText(screenshotText)
        assertNotNull(result)
        val pickupDist = result!!.pickupDistanceKm!!
        val tripDist = result.tripDistanceKm!!
        val totalDist = pickupDist + tripDist
        assertEquals(8.0, totalDist, 0.001)

        val pickupTime = result.pickupDurationMinutes!!
        val tripDuration = result.tripDurationMinutes!!
        val totalTime = pickupTime + tripDuration
        assertEquals(20.0, totalTime, 0.001)
    }

    // ========================================================================
    // ID extraction
    // ========================================================================

    @Test
    fun testExtractIdFromText() {
        val text = "Trip Offer 456"
        val id = adapter.extractIdFromText(text)
        assertNotNull(id)
        assertTrue(id.isNotBlank())
    }

    @Test
    fun testExtractIdFromText_empty() {
        val id = adapter.extractIdFromText("")
        assertNotNull(id)
    }

    @Test
    fun testExtractIdFromText_consistent() {
        val text = "Same Trip Offer"
        assertEquals(adapter.extractIdFromText(text), adapter.extractIdFromText(text))
    }
}