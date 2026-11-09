package com.smartcaptain.zone

import org.junit.Assert.*
import org.junit.Test

class ZoneSerializerTest {

    // ========================================================================
    // JSON serialization (version 2)
    // ========================================================================

    @Test
    fun testSerializeCircleZone() {
        val zone = Zone(
            id = "zone-1",
            name = "منطقة اختبار",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 500.0,
            type = ZoneType.DANGER,
            color = 0xFF315FE8.toInt(),
            createdAt = 1000000L
        )
        val json = ZoneSerializer.serialize(zone)
        assertNotNull(json)
        assertTrue(json.contains("\"v\":2"))
        assertTrue(json.contains("\"id\":\"zone-1\""))
        assertTrue(json.contains("\"n\":\"منطقة اختبار\""))
        assertTrue(json.contains("\"s\":0")) // CIRCLE = 0
        assertTrue(json.contains("\"clat\":33.3152"))
        assertTrue(json.contains("\"clon\":44.3661"))
        assertTrue(json.contains("\"rad\":500.0"))
        assertTrue(json.contains("\"t\":0")) // DANGER = 0
        assertTrue(json.contains("\"c\":${0xFF315FE8.toInt()}")) // 0xFF315FE8.toInt()
        assertTrue(json.contains("\"ct\":1000000"))
        assertTrue(json.contains("\"pts\":[]"))
    }

    @Test
    fun testSerializePolygonZone() {
        val points = listOf(
            LatLng(33.3152, 44.3661),
            LatLng(33.3200, 44.3700),
            LatLng(33.3100, 44.3750)
        )
        val zone = Zone(
            id = "zone-poly-1",
            name = "مضلع تجريبي",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0,
            polygonPoints = points,
            type = ZoneType.FAVORITE,
            color = 0xFF16845B.toInt(),
            createdAt = 2000000L
        )
        val json = ZoneSerializer.serialize(zone)
        assertNotNull(json)
        assertTrue(json.contains("\"s\":1")) // POLYGON = 1
        assertTrue(json.contains("\"t\":1")) // FAVORITE = 1
        assertTrue(json.contains("33.3152"))
        assertTrue(json.contains("44.3661"))
        assertTrue(json.contains("33.32"))
        assertTrue(json.contains("44.37"))
    }

    @Test
    fun testSerializeSpecialCharactersInName() {
        val zone = Zone(
            id = "zone-special",
            name = "منطقة \"مع\" رموز خاصة | أنابيب",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 0.0,
            centerLongitude = 0.0,
            radiusMeters = 100.0,
            type = ZoneType.FAVORITE,
            color = 0xFF000000.toInt(),
            createdAt = 0L
        )
        val json = ZoneSerializer.serialize(zone)
        // Should not crash and should contain escaped quotes
        assertNotNull(json)
        val deserialized = ZoneSerializer.deserialize(json)
        assertNotNull(deserialized)
        assertEquals("منطقة \"مع\" رموز خاصة | أنابيب", deserialized!!.name)
    }

    // ========================================================================
    // JSON deserialization
    // ========================================================================

    @Test
    fun testDeserializeCircleZone() {
        val json = "{\"v\":2,\"id\":\"z1\",\"n\":\"اختبار\",\"s\":0,\"clat\":33.3152,\"clon\":44.3661,\"rad\":500.0,\"t\":0,\"c\":8388536,\"ct\":1000000,\"pts\":[]}"
        val zone = ZoneSerializer.deserialize(json)
        assertNotNull(zone)
        assertEquals("z1", zone!!.id)
        assertEquals("اختبار", zone.name)
        assertEquals(ZoneShape.CIRCLE, zone.zoneShape)
        assertEquals(33.3152, zone.centerLatitude, 0.001)
        assertEquals(44.3661, zone.centerLongitude, 0.001)
        assertEquals(500.0, zone.radiusMeters, 0.001)
        assertEquals(ZoneType.DANGER, zone.type)
        assertEquals(8388536, zone.color)
        assertEquals(1000000L, zone.createdAt)
        assertTrue(zone.polygonPoints.isEmpty())
    }

    @Test
    fun testDeserializePolygonZone() {
        val json = "{\"v\":2,\"id\":\"z2\",\"n\":\"مضلع\",\"s\":1,\"clat\":33.3152,\"clon\":44.3661,\"rad\":0.0,\"t\":1,\"c\":14737627,\"ct\":2000000,\"pts\":[[33.3152,44.3661],[33.32,44.37],[33.31,44.375]]}"
        val zone = ZoneSerializer.deserialize(json)
        assertNotNull(zone)
        assertEquals(ZoneShape.POLYGON, zone!!.zoneShape)
        assertEquals(3, zone.polygonPoints.size)
        assertEquals(33.3152, zone.polygonPoints[0].latitude, 0.001)
        assertEquals(44.3661, zone.polygonPoints[0].longitude, 0.001)
        assertEquals(ZoneType.FAVORITE, zone.type)
    }

    @Test
    fun testDeserializeInvalidJson_returnsNull() {
        assertNull(ZoneSerializer.deserialize(""))
        assertNull(ZoneSerializer.deserialize("not json at all"))
        assertNull(ZoneSerializer.deserialize("{}"))
        assertNull(ZoneSerializer.deserialize("{\"v\":1,\"id\":\"x\"}")) // wrong version
    }

    // ========================================================================
    // Legacy pipe-delimited backward compatibility
    // ========================================================================

    @Test
    fun testDeserializeLegacyPipeFormat() {
        // Old format: id|name|lat|lon|radius|typeOrdinal|color|createdAt
        val pipeData = "old-zone|منطقة قديمة|33.3152|44.3661|500.0|0|8388536|1000000"
        val zone = ZoneSerializer.deserialize(pipeData)
        assertNotNull(zone)
        assertEquals("old-zone", zone!!.id)
        assertEquals("منطقة قديمة", zone.name)
        assertEquals(ZoneShape.CIRCLE, zone.zoneShape)
        assertEquals(33.3152, zone.centerLatitude, 0.001)
        assertEquals(ZoneType.DANGER, zone.type)
    }

    @Test
    fun testDeserializeLegacyTypeOrdinals_mapToFavorite() {
        // Older builds stored NEUTRAL (2) and NONE (3) ordinals. They must
        // deserialize as FAVORITE after the type model was reduced.
        listOf("2", "3").forEach { ordinal ->
            val pipeData = "old-zone|منطقة قديمة|33.3152|44.3661|500.0|$ordinal|8388536|1000000"
            val zone = ZoneSerializer.deserialize(pipeData)
            assertNotNull("ordinal=$ordinal should deserialize", zone)
            assertEquals("ordinal=$ordinal", ZoneType.FAVORITE, zone!!.type)
        }
    }

    @Test
    fun testSerializeThenDeserializeRoundtrip() {
        val original = Zone(
            id = "rt-1",
            name = "رحلة ذهاب وإياب",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0,
            polygonPoints = listOf(
                LatLng(33.3152, 44.3661),
                LatLng(33.3200, 44.3700),
                LatLng(33.3100, 44.3750)
            ),
            type = ZoneType.FAVORITE,
            color = 0xFF315FE8.toInt(),
            createdAt = 1234567890L
        )
        val json = ZoneSerializer.serialize(original)
        val deserialized = ZoneSerializer.deserialize(json)
        assertNotNull(deserialized)
        assertEquals(original.id, deserialized!!.id)
        assertEquals(original.name, deserialized.name)
        assertEquals(original.zoneShape, deserialized.zoneShape)
        assertEquals(original.centerLatitude, deserialized.centerLatitude, 0.001)
        assertEquals(original.centerLongitude, deserialized.centerLongitude, 0.001)
        assertEquals(original.radiusMeters, deserialized.radiusMeters, 0.001)
        assertEquals(original.type, deserialized.type)
        assertEquals(original.color, deserialized.color)
        assertEquals(original.createdAt, deserialized.createdAt)
        assertEquals(original.polygonPoints.size, deserialized.polygonPoints.size)
        for (i in original.polygonPoints.indices) {
            assertEquals(original.polygonPoints[i].latitude, deserialized.polygonPoints[i].latitude, 0.0001)
            assertEquals(original.polygonPoints[i].longitude, deserialized.polygonPoints[i].longitude, 0.0001)
        }
    }
}
