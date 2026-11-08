package com.smartcaptain.zone

import org.junit.Assert.*
import org.junit.Test

class ZoneValidationTest {

    // ========================================================================
    // Circle zone validation
    // ========================================================================

    @Test
    fun testValidCircleZone() {
        val zone = Zone(
            id = "z1",
            name = "منطقة صالحة",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 500.0,
            type = ZoneType.NEUTRAL
        )
        assertTrue(zone.isValid())
    }

    @Test
    fun testInvalidCircle_blankName() {
        val zone = Zone(
            id = "z1",
            name = "   ",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 500.0
        )
        assertFalse(zone.isValid())
    }

    @Test
    fun testInvalidCircle_latOutOfRange() {
        val zone = Zone(
            id = "z1",
            name = "اختبار",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 91.0,
            centerLongitude = 44.3661,
            radiusMeters = 500.0
        )
        assertFalse(zone.isValid())
    }

    @Test
    fun testInvalidCircle_lonOutOfRange() {
        val zone = Zone(
            id = "z1",
            name = "اختبار",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 181.0,
            radiusMeters = 500.0
        )
        assertFalse(zone.isValid())
    }

    @Test
    fun testInvalidCircle_zeroRadius() {
        val zone = Zone(
            id = "z1",
            name = "اختبار",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0
        )
        assertFalse(zone.isValid())
    }

    @Test
    fun testInvalidCircle_negativeRadius() {
        val zone = Zone(
            id = "z1",
            name = "اختبار",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = -100.0
        )
        assertFalse(zone.isValid())
    }

    // ========================================================================
    // Polygon zone validation
    // ========================================================================

    @Test
    fun testValidPolygonZone() {
        val zone = Zone(
            id = "z1",
            name = "مضلع صالح",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0,
            polygonPoints = listOf(
                LatLng(33.3152, 44.3661),
                LatLng(33.3200, 44.3700),
                LatLng(33.3100, 44.3750)
            ),
            type = ZoneType.DANGER
        )
        assertTrue(zone.isValid())
    }

    @Test
    fun testInvalidPolygon_tooFewPoints() {
        val zone = Zone(
            id = "z1",
            name = "مضلع",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0,
            polygonPoints = listOf(
                LatLng(33.3152, 44.3661),
                LatLng(33.3200, 44.3700)
            ),
            type = ZoneType.DANGER
        )
        assertFalse(zone.isValid())
    }

    @Test
    fun testInvalidPolygon_emptyPoints() {
        val zone = Zone(
            id = "z1",
            name = "مضلع",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0,
            polygonPoints = emptyList(),
            type = ZoneType.DANGER
        )
        assertFalse(zone.isValid())
    }

    @Test
    fun testInvalidPolygon_invalidPoint() {
        val zone = Zone(
            id = "z1",
            name = "مضلع",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0,
            polygonPoints = listOf(
                LatLng(33.3152, 44.3661),
                LatLng(33.3200, 44.3700),
                LatLng(91.0, 44.3750) // invalid latitude
            ),
            type = ZoneType.DANGER
        )
        assertFalse(zone.isValid())
    }

    // ========================================================================
    // centerPoint()
    // ========================================================================

    @Test
    fun testCenterPoint_circle() {
        val zone = Zone(
            id = "z1",
            name = "دائرة",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 500.0
        )
        val center = zone.centerPoint()
        assertEquals(33.3152, center.latitude, 0.0001)
        assertEquals(44.3661, center.longitude, 0.0001)
    }

    @Test
    fun testCenterPoint_polygon() {
        val zone = Zone(
            id = "z1",
            name = "مضلع",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 0.0,
            centerLongitude = 0.0,
            radiusMeters = 0.0,
            polygonPoints = listOf(
                LatLng(0.0, 0.0),
                LatLng(2.0, 0.0),
                LatLng(0.0, 2.0)
            )
        )
        val center = zone.centerPoint()
        assertEquals(0.6667, center.latitude, 0.0001)
        assertEquals(0.6667, center.longitude, 0.0001)
    }

    @Test
    fun testCenterPoint_emptyPolygon() {
        val zone = Zone(
            id = "z1",
            name = "مضلع فارغ",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 0.0,
            centerLongitude = 0.0,
            radiusMeters = 0.0,
            polygonPoints = emptyList()
        )
        val center = zone.centerPoint()
        assertEquals(0.0, center.latitude, 0.0001)
        assertEquals(0.0, center.longitude, 0.0001)
    }

    // ========================================================================
    // typeLabel()
    // ========================================================================

    @Test
    fun testTypeLabel_danger() {
        val zone = Zone(id = "z1", name = "أ", type = ZoneType.DANGER)
        assertEquals("منطقة خطرة", zone.typeLabel())
    }

    @Test
    fun testTypeLabel_favorite() {
        val zone = Zone(id = "z1", name = "أ", type = ZoneType.FAVORITE)
        assertEquals("منطقة مفضلة", zone.typeLabel())
    }

    @Test
    fun testTypeLabel_neutral() {
        val zone = Zone(id = "z1", name = "أ", type = ZoneType.NEUTRAL)
        assertEquals("منطقة", zone.typeLabel())
    }
}
