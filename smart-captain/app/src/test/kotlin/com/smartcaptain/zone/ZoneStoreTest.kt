package com.smartcaptain.zone

import android.content.Context
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class ZoneStoreTest {

    private lateinit var context: Context
    private lateinit var store: ZoneStore

    @Before
    fun setUp() {
        context = RuntimeEnvironment.getApplication()
        store = ZoneStore(context)
        store.deleteAllZones()
    }

    @Test
    fun testSaveAndGetCircleZone() {
        val zone = Zone(
            id = "z1",
            name = "منطقة اختبار",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 500.0,
            type = ZoneType.DANGER
        )
        store.saveZone(zone)

        val retrieved = store.getZone("z1")
        assertNotNull(retrieved)
        assertEquals("z1", retrieved!!.id)
        assertEquals("منطقة اختبار", retrieved.name)
        assertEquals(ZoneShape.CIRCLE, retrieved.zoneShape)
        assertEquals(33.3152, retrieved.centerLatitude, 0.001)
        assertEquals(44.3661, retrieved.centerLongitude, 0.001)
        assertEquals(500.0, retrieved.radiusMeters, 0.001)
        assertEquals(ZoneType.DANGER, retrieved.type)
    }

    @Test
    fun testSaveAndGetPolygonZone() {
        val points = listOf(
            LatLng(33.3152, 44.3661),
            LatLng(33.3200, 44.3700),
            LatLng(33.3100, 44.3750)
        )
        val zone = Zone(
            id = "zpoly",
            name = "مضلع اختبار",
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 0.0,
            polygonPoints = points,
            type = ZoneType.FAVORITE
        )
        store.saveZone(zone)

        val retrieved = store.getZone("zpoly")
        assertNotNull(retrieved)
        assertEquals(ZoneShape.POLYGON, retrieved!!.zoneShape)
        assertEquals(3, retrieved.polygonPoints.size)
        assertEquals(33.3152, retrieved.polygonPoints[0].latitude, 0.0001)
        assertEquals(44.3661, retrieved.polygonPoints[0].longitude, 0.0001)
        assertEquals(ZoneType.FAVORITE, retrieved.type)
    }

    @Test
    fun testGetAllZones_sortedByCreatedAt() {
        val older = Zone(
            id = "old",
            name = "أقدم",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 0.0,
            centerLongitude = 0.0,
            radiusMeters = 100.0,
            createdAt = 1000L
        )
        val newer = Zone(
            id = "new",
            name = "أحدث",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 0.0,
            centerLongitude = 0.0,
            radiusMeters = 100.0,
            createdAt = 2000L
        )
        store.saveZone(older)
        store.saveZone(newer)

        val all = store.getAllZones()
        assertEquals(2, all.size)
        assertEquals("old", all[0].id) // older first (sorted ascending by createdAt)
        assertEquals("new", all[1].id)
    }

    @Test
    fun testDeleteZone() {
        val zone = Zone(
            id = "zdelete",
            name = "للحذف",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 0.0,
            centerLongitude = 0.0,
            radiusMeters = 100.0
        )
        store.saveZone(zone)
        assertNotNull(store.getZone("zdelete"))

        store.deleteZone("zdelete")
        assertNull(store.getZone("zdelete"))
    }

    @Test
    fun testDeleteAllZones() {
        store.saveZone(Zone("a", "أ", ZoneShape.CIRCLE, 0.0, 0.0, 100.0))
        store.saveZone(Zone("b", "ب", ZoneShape.CIRCLE, 0.0, 0.0, 100.0))
        assertEquals(2, store.getAllZones().size)

        store.deleteAllZones()
        assertEquals(0, store.getAllZones().size)
    }

    @Test(expected = IllegalArgumentException::class)
    fun testSaveInvalidZone_throws() {
        val invalid = Zone(
            id = "bad",
            name = "",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 0.0,
            centerLongitude = 0.0,
            radiusMeters = 0.0
        )
        store.saveZone(invalid)
    }

    @Test
    fun testSpecialCharactersInName_survivesRoundtrip() {
        val zone = Zone(
            id = "special",
            name = "منطقة \"م especiales\" | أنابيب",
            zoneShape = ZoneShape.CIRCLE,
            centerLatitude = 33.3152,
            centerLongitude = 44.3661,
            radiusMeters = 500.0,
            type = ZoneType.NEUTRAL
        )
        store.saveZone(zone)
        val retrieved = store.getZone("special")
        assertNotNull(retrieved)
        assertEquals("منطقة \"م especiales\" | أنابيب", retrieved!!.name)
    }

    @Test
    fun testGetNonExistentZone_returnsNull() {
        assertNull(store.getZone("does-not-exist"))
    }

    @Test
    fun testSaveZone_replacesExisting() {
        val v1 = Zone(id = "z1", name = "الإصدار 1", zoneShape = ZoneShape.CIRCLE, 0.0, 0.0, 100.0)
        val v2 = Zone(id = "z1", name = "الإصدار 2", zoneShape = ZoneShape.CIRCLE, 0.0, 0.0, 200.0)
        store.saveZone(v1)
        store.saveZone(v2)

        val retrieved = store.getZone("z1")
        assertNotNull(retrieved)
        assertEquals("الإصدار 2", retrieved!!.name)
        assertEquals(200.0, retrieved.radiusMeters, 0.001)
    }

    @Test
    fun testEditedPolygonGeometry_persists() {
        val original = Zone(
            id = "geo",
            name = "هندسة",
            zoneShape = ZoneShape.POLYGON,
            polygonPoints = listOf(
                LatLng(33.3152, 44.3661),
                LatLng(33.3200, 44.3700),
                LatLng(33.3100, 44.3750)
            ),
            type = ZoneType.DANGER,
            color = 0xFF112233.toInt(),
            createdAt = 777L
        )
        store.saveZone(original)

        val moved = original.copy(
            polygonPoints = listOf(
                LatLng(33.3000, 44.3000),
                LatLng(33.3200, 44.3700),
                LatLng(33.3100, 44.3750)
            )
        )
        store.saveZone(moved)

        val loaded = store.getZone("geo")
        assertNotNull(loaded)
        assertEquals(original.id, loaded!!.id)
        assertEquals(original.name, loaded.name)
        assertEquals(original.type, loaded.type)
        assertEquals(original.color, loaded.color)
        assertEquals(original.createdAt, loaded.createdAt)
        assertEquals(33.3000, loaded.polygonPoints[0].latitude, 0.0001)
        assertEquals(44.3000, loaded.polygonPoints[0].longitude, 0.0001)
    }
}
