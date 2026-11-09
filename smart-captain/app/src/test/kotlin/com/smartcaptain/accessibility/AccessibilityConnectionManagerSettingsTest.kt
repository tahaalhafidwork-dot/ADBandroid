package com.smartcaptain.accessibility

import android.content.ComponentName
import android.provider.Settings
import com.smartcaptain.platform.BalyAccessibilityService
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

/**
 * Robolectric tests for reading the accessibility service enabled state from
 * Settings.Secure. Android writes the fully qualified flattened component
 * ("com.smartcaptain/com.smartcaptain.platform.BalyAccessibilityService"), while
 * older code only compared the abbreviated form ("com.smartcaptain/.platform...").
 * Both must be recognised so the dashboard does not stay stuck on "not enabled".
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class AccessibilityConnectionManagerSettingsTest {

    private val app get() = RuntimeEnvironment.getApplication()
    private val fullComponent: String
        get() = ComponentName(app, BalyAccessibilityService::class.java).flattenToString()
    private val shortComponent: String
        get() = ComponentName(app, BalyAccessibilityService::class.java).flattenToShortString()

    @Before
    fun setUp() {
        Settings.Secure.putString(app.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES, "")
        Settings.Secure.putInt(app.contentResolver, Settings.Secure.ACCESSIBILITY_ENABLED, 0)
    }

    @Test
    fun `fully qualified component is recognised as enabled`() {
        Settings.Secure.putString(
            app.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
            "com.other/.Service:$fullComponent"
        )
        assertTrue(AccessibilityConnectionManager.isSmartCaptainServiceEnabled(app))
    }

    @Test
    fun `abbreviated component is recognised as enabled`() {
        Settings.Secure.putString(
            app.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
            "com.other/.Service:$shortComponent"
        )
        assertTrue(AccessibilityConnectionManager.isSmartCaptainServiceEnabled(app))
    }

    @Test
    fun `other packages do not count as enabled`() {
        Settings.Secure.putString(
            app.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
            "com.other/com.other.Service"
        )
        assertFalse(AccessibilityConnectionManager.isSmartCaptainServiceEnabled(app))
    }

    @Test
    fun `empty enabled list is not enabled`() {
        assertFalse(AccessibilityConnectionManager.isSmartCaptainServiceEnabled(app))
    }

    @Test
    fun `accessibility enabled flag follows system setting`() {
        Settings.Secure.putInt(app.contentResolver, Settings.Secure.ACCESSIBILITY_ENABLED, 1)
        assertTrue(AccessibilityConnectionManager.isAccessibilityEnabled(app))

        Settings.Secure.putInt(app.contentResolver, Settings.Secure.ACCESSIBILITY_ENABLED, 0)
        assertFalse(AccessibilityConnectionManager.isAccessibilityEnabled(app))
    }
}
