package com.smartcaptain.map

import com.smartcaptain.zone.LatLng
import org.junit.Assert.*
import org.junit.Test

class PolygonDrawingTest {

    private val a = LatLng(33.3152, 44.3661)
    private val b = LatLng(33.3200, 44.3700)
    private val c = LatLng(33.3100, 44.3750)
    private val d = LatLng(33.3050, 44.3600)

    // ========================================================================
    // Undo
    // ========================================================================

    @Test
    fun testUndo_removesOnlyLastPoint() {
        val points = listOf(a, b, c)
        val result = PolygonDrawing.undoLastPoint(points)
        assertEquals(listOf(a, b), result)
    }

    @Test
    fun testUndo_doesNotClearAllPoints() {
        val points = listOf(a, b, c, d)
        val result = PolygonDrawing.undoLastPoint(points)
        assertEquals(3, result.size)
        assertTrue(result.containsAll(listOf(a, b, c)))
    }

    @Test
    fun testUndo_onEmptyList_returnsEmpty() {
        assertTrue(PolygonDrawing.undoLastPoint(emptyList()).isEmpty())
    }

    @Test
    fun testUndo_onSinglePoint_returnsEmpty() {
        assertTrue(PolygonDrawing.undoLastPoint(listOf(a)).isEmpty())
    }

    @Test
    fun testUndo_isRepeatableUntilEmpty() {
        var points = listOf(a, b, c)
        points = PolygonDrawing.undoLastPoint(points)
        points = PolygonDrawing.undoLastPoint(points)
        points = PolygonDrawing.undoLastPoint(points)
        assertTrue(points.isEmpty())
        points = PolygonDrawing.undoLastPoint(points)
        assertTrue(points.isEmpty())
    }

    // ========================================================================
    // Distinct-point validation
    // ========================================================================

    @Test
    fun testCanSave_threeDistinctPoints() {
        assertTrue(PolygonDrawing.canSavePolygon(listOf(a, b, c)))
    }

    @Test
    fun testCannotSave_twoPoints() {
        assertFalse(PolygonDrawing.canSavePolygon(listOf(a, b)))
    }

    @Test
    fun testCannotSave_threePointsButOnlyTwoDistinct() {
        assertFalse(PolygonDrawing.canSavePolygon(listOf(a, b, a)))
    }

    @Test
    fun testCannotSave_invalidCoordinate() {
        assertFalse(PolygonDrawing.canSavePolygon(listOf(a, b, LatLng(91.0, 44.0))))
    }

    @Test
    fun testCannotSave_empty() {
        assertFalse(PolygonDrawing.canSavePolygon(emptyList()))
    }

    @Test
    fun testDistinctPointCount_ignoresDuplicates() {
        assertEquals(2, PolygonDrawing.distinctPointCount(listOf(a, a, b)))
    }

    // ========================================================================
    // Vertex selection / move / delete
    // ========================================================================

    @Test
    fun testFindVertexIndex_findsNearbyVertex() {
        val nearB = LatLng(33.32001, 44.37001)
        assertEquals(1, PolygonDrawing.findVertexIndex(listOf(a, b, c), nearB))
    }

    @Test
    fun testFindVertexIndex_returnsNullWhenFar() {
        assertNull(PolygonDrawing.findVertexIndex(listOf(a, b, c), d))
    }

    @Test
    fun testMoveVertex_replacesOnlySelected() {
        val moved = PolygonDrawing.moveVertex(listOf(a, b, c), 1, d)
        assertEquals(a, moved[0])
        assertEquals(d, moved[1])
        assertEquals(c, moved[2])
    }

    @Test
    fun testMoveVertex_invalidIndexIgnored() {
        val points = listOf(a, b, c)
        assertEquals(points, PolygonDrawing.moveVertex(points, 99, d))
    }

    @Test
    fun testDeleteVertex_removesSelected() {
        val result = PolygonDrawing.deleteVertex(listOf(a, b, c), 1)
        assertEquals(listOf(a, c), result)
    }

    @Test
    fun testDeleteVertex_invalidIndexIgnored() {
        val points = listOf(a, b, c)
        assertEquals(points, PolygonDrawing.deleteVertex(points, -1))
    }

    @Test
    fun testDeleteVertex_canMakePolygonUnsavable() {
        var points = listOf(a, b, c)
        points = PolygonDrawing.deleteVertex(points, 2)
        assertFalse(PolygonDrawing.canSavePolygon(points))
    }
}
