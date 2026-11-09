package com.smartcaptain.map

import com.smartcaptain.zone.LatLng

/**
 * Pure geometry helpers used by the polygon drawing/editing UI.
 *
 * This object deliberately has no Android or osmdroid dependency so the
 * point-manipulation logic can be exercised by plain JVM unit tests.
 */
object PolygonDrawing {

    /** Removes only the most recently added point. Safe for an empty list. */
    fun undoLastPoint(points: List<LatLng>): List<LatLng> {
        if (points.isEmpty()) return points
        return points.subList(0, points.size - 1).toList()
    }

    /** Counts distinct, valid vertices. */
    fun distinctPointCount(points: List<LatLng>): Int =
        points.filter { it.isValid() }.distinct().size

    /**
     * A polygon may be saved only when it contains at least [minPoints]
     * distinct valid vertices.
     */
    fun canSavePolygon(points: List<LatLng>, minPoints: Int = 3): Boolean =
        points.all { it.isValid() } && distinctPointCount(points) >= minPoints

    /**
     * Returns the index of the vertex within [toleranceDegrees] of [target],
     * choosing the closest match, or null when no vertex is close enough.
     */
    fun findVertexIndex(
        points: List<LatLng>,
        target: LatLng,
        toleranceDegrees: Double = 0.002
    ): Int? {
        var bestIndex: Int? = null
        var bestDistance = Double.MAX_VALUE
        points.forEachIndexed { index, point ->
            val distance = distanceDegrees(
                point.latitude, point.longitude,
                target.latitude, target.longitude
            )
            if (distance <= toleranceDegrees && distance < bestDistance) {
                bestDistance = distance
                bestIndex = index
            }
        }
        return bestIndex
    }

    /** Replaces the vertex at [index] with [newPoint]. Invalid indexes are ignored. */
    fun moveVertex(points: List<LatLng>, index: Int, newPoint: LatLng): List<LatLng> {
        if (index !in points.indices) return points
        return points.toMutableList().also { it[index] = newPoint }
    }

    /** Deletes the vertex at [index]. Invalid indexes are ignored. */
    fun deleteVertex(points: List<LatLng>, index: Int): List<LatLng> {
        if (index !in points.indices) return points
        return points.toMutableList().also { it.removeAt(index) }
    }

    /** Approximate distance in degrees, longitude scaled by latitude. */
    fun distanceDegrees(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val dLat = Math.abs(lat1 - lat2)
        val dLon = Math.abs(lon1 - lon2) * Math.cos(Math.toRadians((lat1 + lat2) / 2.0))
        return Math.sqrt(dLat * dLat + dLon * dLon)
    }
}
