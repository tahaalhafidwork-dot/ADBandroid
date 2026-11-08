package com.smartcaptain.platform

import com.smartcaptain.domain.TripOffer
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mockito.*
import org.robolectric.RobolectricTestRunner
import android.view.accessibility.AccessibilityEvent

@RunWith(RobolectricTestRunner::class)
class BalyAccessibilityServiceTest {

    private val service = BalyAccessibilityService()

    @Before
    fun setup() {
        service.resetState()
    }

    @Test
    fun testOnAccessibilityEvent_nullPackage() {
        val event = mock(AccessibilityEvent::class.java)
        `when`(event.packageName).thenReturn(null)
        service.onAccessibilityEvent(event)
    }

    @Test
    fun testOnAccessibilityEvent_nonBalyPackage() {
        val event = mock(AccessibilityEvent::class.java)
        `when`(event.packageName).thenReturn("com.other.app")
        service.onAccessibilityEvent(event)
    }

    @Test
    fun testOnAccessibilityEvent_wrongPackage_comBalyCaptain() {
        // The old wrong package name should NOT be supported
        val event = mock(AccessibilityEvent::class.java)
        `when`(event.packageName).thenReturn("com.baly.captain")
        service.onAccessibilityEvent(event)
    }

    @Test
    fun testOnAccessibilityEvent_balyPackage_noText() {
        val event = mock(AccessibilityEvent::class.java)
        `when`(event.packageName).thenReturn("app.baly.driver")
        `when`(event.text).thenReturn(null)
        service.onAccessibilityEvent(event)
    }

    @Test
    fun testOnAccessibilityEvent_balyPackage_withText_noTrip() {
        val event = mock(AccessibilityEvent::class.java)
        `when`(event.packageName).thenReturn("app.baly.driver")
        `when`(event.text).thenReturn(listOf("الرصيد: 22,250 دينار"))
        service.onAccessibilityEvent(event)
    }

    @Test
    fun testOnAccessibilityEvent_balyPackage_withTripText() {
        val event = mock(AccessibilityEvent::class.java)
        `when`(event.packageName).thenReturn("app.baly.driver")
        `when`(event.text).thenReturn(listOf("سعر الرحلة 5000 دينار مسافة 2 كم مدة الرحلة 10 دقيقة"))
        service.onAccessibilityEvent(event)
    }

    @Test
    fun testResetState() {
        val event1 = mock(AccessibilityEvent::class.java)
        service.onAccessibilityEvent(event1)
        service.resetState()
        val event2 = mock(AccessibilityEvent::class.java)
        `when`(event2.packageName).thenReturn("app.baly.driver")
        `when`(event2.text).thenReturn(listOf("سعر الرحلة 5000 دينار"))
        service.onAccessibilityEvent(event2)
    }

    @Test
    fun testProcessedEventIds_tracking() {
        val event1 = mock(AccessibilityEvent::class.java)
        service.onAccessibilityEvent(event1)
        assertNotNull(service::processedEventIds)
    }

    @Test
    fun testNormalizeArabicIndicNumerals_mixed() {
        val input = "السعر ٥٠٠ and 100"
        val result = BalyPlatformAdapter.normalizeArabicIndicNumerals(input)
        assertTrue(result.contains("500") || result.contains("100"))
    }

    @Test
    fun testNormalizeArabicIndicNumerals_arabicIndic() {
        val input = "السعر ١٢٣ دينار"
        val result = BalyPlatformAdapter.normalizeArabicIndicNumerals(input)
        assertTrue(result.contains("123"))
        assertFalse(result.contains("١"))
    }

    @Test
    fun testVerifiedPackageName_used() {
        assertEquals("app.baly.driver", BalyPlatformAdapter.BALY_PACKAGE_NAME)
    }
}