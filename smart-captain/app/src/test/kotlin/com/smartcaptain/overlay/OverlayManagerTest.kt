package com.smartcaptain.overlay

import android.content.Context
import android.provider.Settings
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class OverlayManagerTest {

    private lateinit var context: Context
    private lateinit var manager: OverlayManager

    @Before
    fun setUp() {
        context = RuntimeEnvironment.getApplication()
        manager = OverlayManager(context)
    }

    @Test
    fun testInitialOverlayVisible_isFalse() {
        assertFalse(manager.isOverlayVisible())
    }

    @Test
    fun testOnWindowAdded_setsVisible() {
        manager.onWindowAdded()
        assertTrue(manager.isOverlayVisible())
    }

    @Test
    fun testOnWindowRemoved_setsNotVisible() {
        manager.onWindowAdded()
        assertTrue(manager.isOverlayVisible())

        manager.onWindowRemoved()
        assertFalse(manager.isOverlayVisible())
    }

    @Test
    fun testRepeatedAddRemoveStaysConsistent() {
        manager.onWindowAdded()
        assertTrue(manager.isOverlayVisible())

        manager.onWindowRemoved()
        assertFalse(manager.isOverlayVisible())

        manager.onWindowAdded()
        assertTrue(manager.isOverlayVisible())

        manager.onWindowRemoved()
        assertFalse(manager.isOverlayVisible())
    }

    @Test
    fun testShowOverlay_withoutPermission_doesNotChangeState() {
        // No overlay permission granted in test environment
        assertFalse(manager.hasOverlayPermission())
        manager.showOverlay()
        // State should remain false (not optimistically set)
        assertFalse(manager.isOverlayVisible())
    }

    @Test
    fun testHideOverlay_whenNotVisible_doesNotCrash() {
        manager.hideOverlay()
        assertFalse(manager.isOverlayVisible())
    }

    @Test
    fun testToggleOverlay_withoutPermission_staysHidden() {
        manager.toggleOverlay()
        assertFalse(manager.isOverlayVisible())
    }

    @Test
    fun testOverlayPermissionContract_returnsIntent() {
        val contract = manager.overlayPermissionContract()
        val intent = contract.createIntent(context, Unit)
        assertNotNull(intent)
        assertEquals(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, intent.action)
    }
}
