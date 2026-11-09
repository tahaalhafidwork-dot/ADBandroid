package com.smartcaptain.zone

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ZoneBrushSerializationTest {

    @Test
    fun testBrushZoneRoundtrip_preservesGeometryHolesStrokesAndState() {
        val exterior = listOf(
            LatLng(24.7136, 46.6753),
            LatLng(24.7146, 46.6753),
            LatLng(24.7146, 46.6763),
            LatLng(24.7136, 46.6763)
        )
        val hole = listOf(
            LatLng(24.7140, 46.6757),
            LatLng(24.7142, 46.6757),
            LatLng(24.7142, 46.6759)
        )
        val extra = listOf(
            LatLng(24.7150, 46.6770),
            LatLng(24.7155, 46.6770),
            LatLng(24.7155, 46.6775)
        )
        val strokes = listOf(
            BrushStroke(
                points = listOf(LatLng(24.7136, 46.6753), LatLng(24.7145, 46.6760)),
                radiusMeters = 200.0
            ),
            BrushStroke(
                points = listOf(LatLng(24.7140, 46.6758)),
                radiusMeters = 90.0,
                erase = true
            )
        )
        val original = Zone(
            id = "brush-1",
            name = "رسم حر",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 24.7140,
            centerLongitude = 46.6758,
            polygonPoints = exterior,
            type = ZoneType.DANGER,
            color = 0xFFDC2626.toInt(),
            createdAt = 777L,
            polygonHoles = listOf(hole),
            extraPolygons = listOf(ZonePolygon(extra)),
            brushStrokes = strokes,
            isActive = false
        )

        val json = ZoneSerializer.serialize(original)
        val restored = ZoneSerializer.deserialize(json)

        assertNotNull(restored)
        restored!!
        assertEquals(original.id, restored.id)
        assertEquals(original.name, restored.name)
        assertEquals(original.zoneShape, restored.zoneShape)
        assertEquals(original.polygonPoints.size, restored.polygonPoints.size)
        assertEquals(original.polygonHoles.size, restored.polygonHoles.size)
        assertEquals(original.polygonHoles.first().size, restored.polygonHoles.first().size)
        assertEquals(original.extraPolygons.size, restored.extraPolygons.size)
        assertEquals(original.extraPolygons.first().exterior.size, restored.extraPolygons.first().exterior.size)
        assertEquals(2, restored.brushStrokes.size)
        assertEquals(200.0, restored.brushStrokes[0].radiusMeters, 0.001)
        assertFalse(restored.brushStrokes[0].erase)
        assertTrue(restored.brushStrokes[1].erase)
        assertEquals(2, restored.brushStrokes[0].points.size)
        assertFalse(restored.isActive)
    }

    @Test
    fun testLegacyV2Json_withoutNewFields_defaultsToActiveAndNoBrushData() {
        val json = "{\"v\":2,\"id\":\"z2\",\"n\":\"مضلع\",\"s\":1,\"clat\":33.3152," +
            "\"clon\":44.3661,\"rad\":0.0,\"t\":1,\"c\":14737627,\"ct\":2000000," +
            "\"pts\":[[33.3152,44.3661],[33.32,44.37],[33.31,44.375]]}"

        val zone = ZoneSerializer.deserialize(json)

        assertNotNull(zone)
        zone!!
        assertTrue(zone.isActive)
        assertTrue(zone.brushStrokes.isEmpty())
        assertTrue(zone.polygonHoles.isEmpty())
        assertTrue(zone.extraPolygons.isEmpty())
        assertEquals(3, zone.polygonPoints.size)
    }

    @Test
    fun testSerializedZone_keepsBackwardCompatiblePtsField() {
        val zone = Zone(
            id = "z",
            name = "z",
            zoneShape = ZoneShape.POLYGON,
            polygonPoints = listOf(
                LatLng(1.0, 2.0),
                LatLng(1.1, 2.0),
                LatLng(1.1, 2.1)
            )
        )

        val json = ZoneSerializer.serialize(zone)

        assertTrue(json.contains("\"pts\":[[1.0,2.0],[1.1,2.0],[1.1,2.1]]"))
        assertTrue(json.contains("\"act\":1"))
    }
}
