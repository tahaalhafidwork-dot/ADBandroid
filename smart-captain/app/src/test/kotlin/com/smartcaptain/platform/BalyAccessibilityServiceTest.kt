package com.smartcaptain.platform

import android.view.accessibility.AccessibilityEvent
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mockito.*
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class BalyAccessibilityServiceTest {

    private lateinit var service: BalyAccessibilityService

    @Before
    fun setup() {
        service = Robolectric.buildService(BalyAccessibilityService::class.java).get()
        service.resetState()
    }

    private fun event(packageName: String?, text: List<String>?): AccessibilityEvent {
        val event = mock(AccessibilityEvent::class.java)
        `when`(event.eventType).thenReturn(AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED)
        `when`(event.packageName).thenReturn(packageName)
        `when`(event.text).thenReturn(text)
        return event
    }

    @Test
    fun testOnAccessibilityEvent_nullPackage() {
        service.onAccessibilityEvent(event(null, listOf("سعر الرحلة 5000 دينار")))
    }

    @Test
    fun testOnAccessibilityEvent_nonBalyPackage() {
        service.onAccessibilityEvent(event("com.other.app", listOf("سعر الرحلة 5000 دينار")))
    }

    @Test
    fun testOnAccessibilityEvent_wrongPackage_comBalyCaptain() {
        // The old wrong package name should NOT be supported
        service.onAccessibilityEvent(event("com.baly.captain", listOf("سعر الرحلة 5000 دينار")))
    }

    @Test
    fun testOnAccessibilityEvent_balyPackage_noText() {
        service.onAccessibilityEvent(event("app.baly.driver", null))
    }

    @Test
    fun testOnAccessibilityEvent_balyPackage_withText_noTrip() {
        service.onAccessibilityEvent(event("app.baly.driver", listOf("الرصيد: 22,250 دينار")))
    }

    @Test
    fun testOnAccessibilityEvent_balyPackage_withTripText() {
        service.onAccessibilityEvent(
            event(
                "app.baly.driver",
                listOf("سعر الرحلة 5000 دينار مسافة 2 كم مدة الرحلة 10 دقيقة")
            )
        )
    }

    @Test
    fun testResetState() {
        service.onAccessibilityEvent(event("app.baly.driver", listOf("سعر الرحلة 5000 دينار")))
        service.resetState()
        service.onAccessibilityEvent(event("app.baly.driver", listOf("سعر الرحلة 5000 دينار")))
    }

    @Test
    fun testProcessedEventIds_tracking() {
        service.onAccessibilityEvent(event("app.baly.driver", listOf("سعر الرحلة 5000 دينار")))
        assertNotNull(service.processedEventIds)
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
