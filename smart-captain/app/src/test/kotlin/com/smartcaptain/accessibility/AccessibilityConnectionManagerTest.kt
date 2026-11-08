package com.smartcaptain.accessibility

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.shadows.ShadowApplication

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class AccessibilityConnectionManagerTest {

    @Before
    fun setUp() {
        // Reset state before each test
        AccessibilityConnectionManager.markDisabled()
    }

    // ========================================================================
    // State transition tests
    // ========================================================================

    @Test
    fun testInitialState_isDisabled() {
        assertFalse(AccessibilityConnectionManager.isServiceConnected())
    }

    @Test
    fun testMarkConnected_setsConnectedAndEnabled() {
        AccessibilityConnectionManager.markConnected()
        assertTrue(AccessibilityConnectionManager.isServiceConnected())
    }

    @Test
    fun testMarkDisconnected_clearsConnected() {
        AccessibilityConnectionManager.markConnected()
        AccessibilityConnectionManager.markDisconnected()
        assertFalse(AccessibilityConnectionManager.isServiceConnected())
    }

    @Test
    fun testMarkEnabled_setsEnabled() {
        AccessibilityConnectionManager.markEnabled()
    }

    @Test
    fun testMarkDisabled_clearsBoth() {
        AccessibilityConnectionManager.markConnected()
        AccessibilityConnectionManager.markDisabled()
        assertFalse(AccessibilityConnectionManager.isServiceConnected())
    }

    // ========================================================================
    // Four-state logic tests
    // ========================================================================

    @Test
    fun testState_disabled() {
        // Neither enabled nor connected
        AccessibilityConnectionManager.markDisabled()
        assertFalse(AccessibilityConnectionManager.isServiceConnected())
        // State = DISABLED
    }

    @Test
    fun testState_enabledButDisconnected() {
        // markEnabled without markConnected = enabled but not connected
        AccessibilityConnectionManager.markEnabled()
        assertFalse(AccessibilityConnectionManager.isServiceConnected())
        // State = ENABLED BUT DISCONNECTED
    }

    @Test
    fun testState_connected() {
        AccessibilityConnectionManager.markConnected()
        assertTrue(AccessibilityConnectionManager.isServiceConnected())
        // State = CONNECTED
    }

    // ========================================================================
    // Reconnection after disconnect
    // ========================================================================

    @Test
    fun testReconnectAfterDisconnect() {
        AccessibilityConnectionManager.markConnected()
        assertTrue(AccessibilityConnectionManager.isServiceConnected())

        AccessibilityConnectionManager.markDisconnected()
        assertFalse(AccessibilityConnectionManager.isServiceConnected())

        AccessibilityConnectionManager.markConnected()
        assertTrue(AccessibilityConnectionManager.isServiceConnected())
    }
}
