package com.smartcaptain.map

import com.smartcaptain.zone.BrushStroke
import com.smartcaptain.zone.LatLng
import com.smartcaptain.zone.Zone
import com.smartcaptain.zone.ZonePolygon
import com.smartcaptain.zone.ZoneShape
import com.smartcaptain.zone.ZoneType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI

class BrushGeometryTest {

    private val riyadh = LatLng(24.7136, 46.6753)

    @Test
    fun testSingleStamp_producesPolygonAndApproximateArea() {
        val result = BrushGeometry.build(
            listOf(BrushStroke(points = listOf(riyadh), radiusMeters = 200.0))
        )

        assertFalse(result.isEmpty())
        assertEquals(1, result.polygons.size)
        assertTrue(result.polygons.first().exterior.size >= 3)

        val expected = PI * 200.0 * 200.0
        assertEquals(expected, result.areaSqMeters, expected * 0.12)
        assertTrue(result.pointCount >= 3)

        val zone = zoneFrom(result)
        assertTrue(BrushGeometry.contains(zone, riyadh))
        assertFalse(BrushGeometry.contains(zone, LatLng(24.80, 46.80)))
    }

    @Test
    fun testPath_isBufferedIntoAContinuousPolygon() {
        val points = (0..20).map { index ->
            LatLng(riyadh.latitude, riyadh.longitude + index * 0.00005)
        }
        val result = BrushGeometry.build(
            listOf(BrushStroke(points = points, radiusMeters = 100.0))
        )

        assertFalse(result.isEmpty())
        val expectedMinimum = PI * 100.0 * 100.0
        assertTrue(result.areaSqMeters > expectedMinimum)
        // The brush stroke must cover the middle of the path, not only endpoints.
        val middle = points[points.size / 2]
        assertTrue(BrushGeometry.contains(zoneFrom(result), middle))
    }

    @Test
    fun testEraser_removesAreaAndCanCutAHole() {
        val points = (0..12).map { index ->
            LatLng(riyadh.latitude, riyadh.longitude + index * 0.0001)
        }
        val painted = BrushGeometry.build(
            listOf(BrushStroke(points = points, radiusMeters = 140.0))
        )
        val erased = BrushGeometry.build(
            listOf(
                BrushStroke(points = points, radiusMeters = 140.0),
                BrushStroke(points = listOf(points[points.size / 2]), radiusMeters = 180.0, erase = true)
            )
        )

        assertTrue(painted.areaSqMeters > 0.0)
        assertTrue(erased.areaSqMeters > 0.0)
        assertTrue(erased.areaSqMeters < painted.areaSqMeters)
        assertFalse(BrushGeometry.contains(zoneFrom(erased), points[points.size / 2]))
    }

    @Test
    fun testUndoOfLastStroke_isRepresentedByRebuildingFromRemainingStrokes() {
        val first = BrushStroke(listOf(riyadh), 100.0)
        val second = BrushStroke(
            listOf(LatLng(riyadh.latitude + 0.005, riyadh.longitude + 0.005)),
            100.0
        )

        val withBoth = BrushGeometry.build(listOf(first, second))
        val withoutSecond = BrushGeometry.build(listOf(first))

        assertTrue(withBoth.areaSqMeters > withoutSecond.areaSqMeters)
        assertEquals(1, withoutSecond.polygons.size)
    }

    @Test
    fun testEmptyAndEraserOnlyDrawings_areEmpty() {
        assertTrue(BrushGeometry.build(emptyList()).isEmpty())
        assertTrue(
            BrushGeometry.build(
                listOf(BrushStroke(listOf(riyadh), 100.0, erase = true))
            ).isEmpty()
        )
    }

    @Test
    fun testInvalidPoints_areIgnored() {
        val result = BrushGeometry.build(
            listOf(
                BrushStroke(
                    points = listOf(LatLng(999.0, 999.0), riyadh),
                    radiusMeters = 80.0
                )
            )
        )
        assertFalse(result.isEmpty())
    }

    @Test
    fun testRingArea_ofKnownRectangle() {
        val latitude = 24.7136
        val longitude = 46.6753
        val ring = listOf(
            LatLng(latitude, longitude),
            LatLng(latitude + 0.001, longitude),
            LatLng(latitude + 0.001, longitude + 0.001),
            LatLng(latitude, longitude + 0.001)
        )

        val expected = 111_320.0 * 111_320.0 * kotlin.math.cos(Math.toRadians(latitude)) * 0.001 * 0.001
        assertEquals(expected, BrushGeometry.ringAreaSqMeters(ring), expected * 0.01)
    }

    @Test
    fun testTouchThrottle_dropsTooClosePoints() {
        val last = LatLng(24.7136, 46.6753)
        val close = LatLng(24.713601, 46.675301)
        val far = LatLng(24.7150, 46.6753)

        assertFalse(BrushGeometry.shouldAppendPoint(last, close, 200.0))
        assertTrue(BrushGeometry.shouldAppendPoint(last, far, 200.0))
        assertTrue(BrushGeometry.shouldAppendPoint(null, far, 200.0))
    }

    @Test
    fun testLongPath_isSimplifiedBelowPointBudget() {
        val points = (0..2_000).map { index ->
            LatLng(
                riyadh.latitude + kotlin.math.sin(index / 20.0) * 0.0004,
                riyadh.longitude + index * 0.00002
            )
        }
        val result = BrushGeometry.build(
            listOf(BrushStroke(points = points, radiusMeters = 50.0))
        )

        assertFalse(result.isEmpty())
        assertTrue(result.pointCount <= 5_000)
        assertTrue(result.polygons.first().exterior.size >= 3)
    }

    private fun zoneFrom(result: BrushBuildResult): Zone {
        val primary = result.polygons.first()
        return Zone(
            id = "test",
            name = "test",
            zoneShape = ZoneShape.POLYGON,
            polygonPoints = primary.exterior,
            polygonHoles = primary.holes,
            extraPolygons = result.polygons.drop(1),
            type = ZoneType.DANGER
        )
    }

    private fun zoneFrom(polygons: List<ZonePolygon>): Zone {
        val primary = polygons.first()
        return Zone(
            id = "test",
            name = "test",
            zoneShape = ZoneShape.POLYGON,
            polygonPoints = primary.exterior,
            polygonHoles = primary.holes,
            extraPolygons = polygons.drop(1)
        )
    }
}
