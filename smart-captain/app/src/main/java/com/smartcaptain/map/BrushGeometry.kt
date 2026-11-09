package com.smartcaptain.map

import com.smartcaptain.zone.BrushStroke
import com.smartcaptain.zone.LatLng
import com.smartcaptain.zone.Zone
import com.smartcaptain.zone.ZonePolygon
import com.smartcaptain.zone.ZoneShape
import java.util.Locale
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** The active tool in the freehand brush editor. */
enum class BrushTool { BRUSH, ERASER }

/**
 * Result of converting freehand strokes into polygon geometry.
 *
 * [polygons] always contains at least one outer ring when the result is not
 * empty. [areaSqMeters] is the net painted area (outer rings minus holes).
 */
data class BrushBuildResult(
    val polygons: List<ZonePolygon>,
    val areaSqMeters: Double,
    val pointCount: Int
) {
    fun isEmpty(): Boolean = polygons.isEmpty() || areaSqMeters <= 0.5

    companion object {
        val EMPTY = BrushBuildResult(emptyList(), 0.0, 0)
    }
}

/**
 * Pure-Kotlin brush geometry engine.
 *
 * Freehand strokes are buffered (each stamp is a real-world circle of
 * [BrushStroke.radiusMeters]), unioned, erased and finally simplified. The
 * implementation uses a small local metric raster instead of pulling a heavy
 * GIS library into an app that only needs zone outlines:
 *
 *  1. project lat/lon to metres around the drawing origin,
 *  2. rasterise every brush stamp into a boolean grid (union / subtract),
 *  3. trace the boundary edges of the filled cells into rings,
 *  4. simplify each ring with Ramer–Douglas–Peucker,
 *  5. convert back to lat/lon and attach holes to their outer ring.
 *
 * Accuracy is roughly one grid cell (a few metres for typical zones), which is
 * far below what is visually meaningful on a phone map. No Android classes are
 * referenced here, so the whole pipeline is unit-testable on the JVM.
 */
object BrushGeometry {

    const val MIN_RADIUS_METERS = 50.0
    const val MAX_RADIUS_METERS = 2_000.0
    const val DEFAULT_RADIUS_METERS = 200.0

    private const val METERS_PER_DEGREE = 111_320.0
    private const val MAX_GRID_DIMENSION = 720
    private const val MAX_GRID_CELLS = 3_500_000
    private const val MAX_RESULT_POINTS = 5_000
    private const val MIN_CELL_METERS = 1.0

    private data class LocalPoint(val x: Double, val y: Double)

    private data class LocalProjection(
        val latitude0: Double,
        val longitude0: Double,
        val longitudeScale: Double
    ) {
        fun toLocal(point: LatLng): LocalPoint = LocalPoint(
            x = (point.longitude - longitude0) * longitudeScale,
            y = (point.latitude - latitude0) * METERS_PER_DEGREE
        )

        fun toLatLng(point: LocalPoint): LatLng = LatLng(
            latitude = latitude0 + point.y / METERS_PER_DEGREE,
            longitude = longitude0 + point.x / longitudeScale
        )
    }

    private data class GridEdge(
        val startX: Int,
        val startY: Int,
        val endX: Int,
        val endY: Int
    )

    private data class RingInfo(
        val points: List<LocalPoint>,
        val area: Double
    )

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    fun build(strokes: List<BrushStroke>): BrushBuildResult {
        val normalized = strokes.mapNotNull(::normalizeStroke)
        val paintStrokes = normalized.filter { !it.erase }
        if (paintStrokes.isEmpty()) return BrushBuildResult.EMPTY

        val origin = paintStrokes.first().points.first()
        val projection = LocalProjection(
            latitude0 = origin.latitude,
            longitude0 = origin.longitude,
            longitudeScale = METERS_PER_DEGREE *
                cos(Math.toRadians(origin.latitude)).coerceAtLeast(0.01)
        )

        // Bounding box of every painted stamp.
        var minX = Double.MAX_VALUE
        var minY = Double.MAX_VALUE
        var maxX = -Double.MAX_VALUE
        var maxY = -Double.MAX_VALUE
        for (stroke in paintStrokes) {
            for (point in stroke.points) {
                val local = projection.toLocal(point)
                minX = min(minX, local.x - stroke.radiusMeters)
                minY = min(minY, local.y - stroke.radiusMeters)
                maxX = max(maxX, local.x + stroke.radiusMeters)
                maxY = max(maxY, local.y + stroke.radiusMeters)
            }
        }
        if (!minX.isFinite() || !minY.isFinite() || maxX <= minX || maxY <= minY) {
            return BrushBuildResult.EMPTY
        }

        val minimumRadius = paintStrokes.minOf { it.radiusMeters }
        val extent = max(maxX - minX, maxY - minY)
        var cell = max(
            MIN_CELL_METERS,
            min(minimumRadius / 6.0, extent / MAX_GRID_DIMENSION)
        )

        val padding = 1
        var width: Int
        var height: Int
        do {
            width = ceil((maxX - minX) / cell).toInt() + padding * 2 + 1
            height = ceil((maxY - minY) / cell).toInt() + padding * 2 + 1
            if (width.toLong() * height.toLong() > MAX_GRID_CELLS) {
                cell *= 1.25
            } else {
                break
            }
        } while (cell < extent)

        val originX = minX - padding * cell
        val originY = minY - padding * cell
        val grid = ByteArray(width * height)

        fun stamp(center: LocalPoint, radius: Double, paint: Boolean) {
            val radiusSquared = radius * radius
            val startY = floor((center.y - radius - originY) / cell).toInt()
                .coerceAtLeast(0)
            val endY = floor((center.y + radius - originY) / cell).toInt()
                .coerceAtMost(height - 1)
            for (gy in startY..endY) {
                val cellCenterY = originY + (gy + 0.5) * cell
                val dy = cellCenterY - center.y
                val remainder = radiusSquared - dy * dy
                if (remainder < 0.0) continue
                val halfWidth = sqrt(remainder)
                val startX = floor((center.x - halfWidth - originX) / cell).toInt()
                    .coerceAtLeast(0)
                val endX = floor((center.x + halfWidth - originX) / cell).toInt()
                    .coerceAtMost(width - 1)
                for (gx in startX..endX) {
                    grid[gy * width + gx] = if (paint) 1 else 0
                }
            }
        }

        for (stroke in normalized) {
            val localPoints = stroke.points.map(projection::toLocal)
            val radius = stroke.radiusMeters
            val paint = !stroke.erase
            val step = max(radius * 0.35, cell * 0.75)
            stamp(localPoints.first(), radius, paint)
            for (index in 1 until localPoints.size) {
                val from = localPoints[index - 1]
                val to = localPoints[index]
                val distance = hypot(to.x - from.x, to.y - from.y)
                if (distance <= 0.0) continue
                val steps = ceil(distance / step).toInt().coerceIn(1, 4_000)
                for (s in 1..steps) {
                    val fraction = s.toDouble() / steps
                    stamp(
                        LocalPoint(
                            x = from.x + (to.x - from.x) * fraction,
                            y = from.y + (to.y - from.y) * fraction
                        ),
                        radius,
                        paint
                    )
                }
            }
        }

        val rawRings = traceBoundaryRings(grid, width, height, originX, originY, cell)
        if (rawRings.isEmpty()) return BrushBuildResult.EMPTY

        // Simplify, increasing tolerance if the drawing generated an excessive
        // number of vertices (performance guard for very long paths).
        var tolerance = max(cell * 1.25, 1.5)
        var simplified = rawRings.map { simplifyRing(it, tolerance) }
        var guard = 0
        while (simplified.sumOf { it.size } > MAX_RESULT_POINTS && guard++ < 8) {
            tolerance *= 1.6
            simplified = rawRings.map { simplifyRing(it, tolerance) }
        }

        val infos = simplified
            .map { RingInfo(it, abs(signedArea(it))) }
            .filter { it.points.size >= 3 && it.area > cell * cell * 0.5 }
        if (infos.isEmpty()) return BrushBuildResult.EMPTY

        val outerRings = mutableListOf<RingInfo>()
        val holeRings = mutableListOf<RingInfo>()
        for (info in infos) {
            var depth = 0
            for (other in infos) {
                if (other === info) continue
                if (other.area <= info.area) continue
                if (pointInRing(info.points.first(), other.points)) depth++
            }
            if (depth % 2 == 0) outerRings.add(info) else holeRings.add(info)
        }
        if (outerRings.isEmpty()) {
            // Degenerate self-intersection fallback: keep the largest ring.
            outerRings.add(infos.maxBy { it.area })
            holeRings.clear()
        }

        val holesByOuter = HashMap<RingInfo, MutableList<RingInfo>>()
        for (hole in holeRings) {
            val container = outerRings
                .filter { pointInRing(hole.points.first(), it.points) }
                .minByOrNull { it.area }
                ?: continue
            holesByOuter.getOrPut(container) { mutableListOf() }.add(hole)
        }

        val polygons = outerRings
            .sortedByDescending { it.area }
            .map { outer ->
                ZonePolygon(
                    exterior = outer.points.map(projection::toLatLng),
                    holes = (holesByOuter[outer] ?: emptyList())
                        .sortedByDescending { it.area }
                        .map { hole -> hole.points.map(projection::toLatLng) }
                )
            }

        val netArea = outerRings.sumOf { it.area } - holeRings.sumOf { it.area }
        val pointCount = polygons.sumOf { polygon ->
            polygon.exterior.size + polygon.holes.sumOf { it.size }
        }

        return BrushBuildResult(
            polygons = polygons,
            areaSqMeters = netArea.coerceAtLeast(0.0),
            pointCount = pointCount
        )
    }

    /** True when [point] falls inside the zone (circle or any polygon part). */
    fun contains(zone: Zone, point: LatLng): Boolean {
        if (!point.isValid()) return false
        return when (zone.zoneShape) {
            ZoneShape.CIRCLE -> distanceMeters(
                zone.centerLatitude,
                zone.centerLongitude,
                point.latitude,
                point.longitude
            ) <= zone.radiusMeters

            ZoneShape.POLYGON -> zone.polygons().any { part ->
                pointInRing(point, part.exterior) &&
                    part.holes.none { hole -> pointInRing(point, hole) }
            }
        }
    }

    /** Net area of a zone in square metres. */
    fun areaSqMeters(zone: Zone): Double = when (zone.zoneShape) {
        ZoneShape.CIRCLE -> PI * zone.radiusMeters * zone.radiusMeters
        ZoneShape.POLYGON -> zone.polygons().sumOf { part ->
            ringAreaSqMeters(part.exterior) -
                part.holes.sumOf { hole -> ringAreaSqMeters(hole) }
        }.coerceAtLeast(0.0)
    }

    /** Net area of one lat/lon ring in square metres (shoelace formula). */
    fun ringAreaSqMeters(ring: List<LatLng>): Double {
        if (ring.size < 3) return 0.0
        val projection = LocalProjection(
            latitude0 = ring.first().latitude,
            longitude0 = ring.first().longitude,
            longitudeScale = METERS_PER_DEGREE *
                cos(Math.toRadians(ring.first().latitude)).coerceAtLeast(0.01)
        )
        val points = ring.map(projection::toLocal)
        return abs(signedArea(points))
    }

    /** Human readable area for cards and the save sheet. */
    fun formatArea(areaSqMeters: Double): String = when {
        areaSqMeters < 10_000 ->
            "${areaSqMeters.toLong()} م²"

        areaSqMeters < 1_000_000 ->
            String.format(Locale.US, "%.1f ألف م²", areaSqMeters / 1_000.0)

        else ->
            String.format(Locale.US, "%.2f كم²", areaSqMeters / 1_000_000.0)
    }

    fun formatRadius(radiusMeters: Double): String =
        if (radiusMeters >= 1_000.0) {
            String.format(Locale.US, "%.1f كم", radiusMeters / 1_000.0)
        } else {
            "${radiusMeters.toInt()} م"
        }

    /** Touch throttling: keeps the stored path small without visible gaps. */
    fun shouldAppendPoint(
        lastPoint: LatLng?,
        nextPoint: LatLng,
        radiusMeters: Double
    ): Boolean {
        if (!nextPoint.isValid()) return false
        if (lastPoint == null) return true
        val minimumStep = max(2.5, radiusMeters * 0.16)
        return distanceMeters(
            lastPoint.latitude,
            lastPoint.longitude,
            nextPoint.latitude,
            nextPoint.longitude
        ) >= minimumStep
    }

    fun distanceMeters(
        latitude1: Double,
        longitude1: Double,
        latitude2: Double,
        longitude2: Double
    ): Double {
        val earthRadius = 6_371_000.0
        val dLat = Math.toRadians(latitude2 - latitude1)
        val dLon = Math.toRadians(longitude2 - longitude1)
        val a = kotlin.math.sin(dLat / 2) * kotlin.math.sin(dLat / 2) +
            cos(Math.toRadians(latitude1)) * cos(Math.toRadians(latitude2)) *
            kotlin.math.sin(dLon / 2) * kotlin.math.sin(dLon / 2)
        return 2 * earthRadius * kotlin.math.atan2(sqrt(a), sqrt(1 - a))
    }

    // ------------------------------------------------------------------
    // Raster helpers
    // ------------------------------------------------------------------

    private fun normalizeStroke(stroke: BrushStroke): BrushStroke? {
        val points = stroke.points.filter { it.isValid() }
        if (points.isEmpty()) return null
        return stroke.copy(
            points = points,
            radiusMeters = stroke.radiusMeters
                .coerceIn(5.0, 20_000.0)
        )
    }

    private fun traceBoundaryRings(
        grid: ByteArray,
        width: Int,
        height: Int,
        originX: Double,
        originY: Double,
        cell: Double
    ): List<List<LocalPoint>> {
        val edges = ArrayList<GridEdge>()
        for (y in 0 until height) {
            for (x in 0 until width) {
                if (grid[y * width + x].toInt() == 0) continue
                if (y == 0 || grid[(y - 1) * width + x].toInt() == 0) {
                    edges.add(GridEdge(x, y, x + 1, y))
                }
                if (x == width - 1 || grid[y * width + x + 1].toInt() == 0) {
                    edges.add(GridEdge(x + 1, y, x + 1, y + 1))
                }
                if (y == height - 1 || grid[(y + 1) * width + x].toInt() == 0) {
                    edges.add(GridEdge(x + 1, y + 1, x, y + 1))
                }
                if (x == 0 || grid[y * width + x - 1].toInt() == 0) {
                    edges.add(GridEdge(x, y + 1, x, y))
                }
            }
        }
        if (edges.isEmpty()) return emptyList()

        val byStart = HashMap<Long, MutableList<Int>>()
        edges.forEachIndexed { index, edge ->
            byStart.getOrPut(vertexKey(edge.startX, edge.startY)) { mutableListOf() }
                .add(index)
        }

        val used = BooleanArray(edges.size)
        val rings = mutableListOf<List<LocalPoint>>()

        for (seed in edges.indices) {
            if (used[seed]) continue
            val seedEdge = edges[seed]
            val startX = seedEdge.startX
            val startY = seedEdge.startY
            val startKey = vertexKey(startX, startY)
            val ring = mutableListOf<LocalPoint>()
            var currentIndex = seed
            var guard = 0
            var closed = false

            while (guard++ <= edges.size + 2) {
                if (used[currentIndex]) break
                used[currentIndex] = true
                val edge = edges[currentIndex]
                ring.add(
                    LocalPoint(
                        x = originX + edge.startX * cell,
                        y = originY + edge.startY * cell
                    )
                )
                val endKey = vertexKey(edge.endX, edge.endY)
                if (endKey == startKey) {
                    closed = true
                    break
                }
                val candidates = byStart[endKey]
                    ?.filter { !used[it] }
                    .orEmpty()
                if (candidates.isEmpty()) break
                currentIndex = chooseNextEdge(edges, edge, candidates)
            }

            if (closed && ring.size >= 4) {
                rings.add(ring)
            }
        }
        return rings
    }

    /**
     * Right-hand rule: keep the filled cells on the right of the walking
     * direction. This separates rings that touch diagonally.
     */
    private fun chooseNextEdge(
        edges: List<GridEdge>,
        incoming: GridEdge,
        candidates: List<Int>
    ): Int {
        val inX = incoming.endX - incoming.startX
        val inY = incoming.endY - incoming.startY

        fun score(candidateIndex: Int): Int {
            val candidate = edges[candidateIndex]
            val outX = candidate.endX - candidate.startX
            val outY = candidate.endY - candidate.startY
            return when {
                outX == -inY && outY == inX -> 0 // right
                outX == inX && outY == inY -> 1 // straight
                outX == inY && outY == -inX -> 2 // left
                outX == -inX && outY == -inY -> 3 // back
                else -> 4
            }
        }

        return candidates.minWithOrNull(
            compareBy<Int> { score(it) }.thenBy { it }
        ) ?: candidates.first()
    }

    private fun vertexKey(x: Int, y: Int): Long =
        (x.toLong() shl 32) xor (y.toLong() and 0xFFFF_FFFFL)

    // ------------------------------------------------------------------
    // Polygon helpers
    // ------------------------------------------------------------------

    private fun signedArea(ring: List<LocalPoint>): Double {
        if (ring.size < 3) return 0.0
        var sum = 0.0
        var previous = ring.last()
        for (point in ring) {
            sum += previous.x * point.y - point.x * previous.y
            previous = point
        }
        return sum / 2.0
    }

    private fun pointInRing(point: LatLng, ring: List<LatLng>): Boolean {
        if (ring.size < 3) return false
        var inside = false
        var j = ring.size - 1
        for (i in ring.indices) {
            val xi = ring[i].longitude
            val yi = ring[i].latitude
            val xj = ring[j].longitude
            val yj = ring[j].latitude
            val intersects = (yi > point.latitude) != (yj > point.latitude) &&
                point.longitude <
                (xj - xi) * (point.latitude - yi) / ((yj - yi).takeUnless { it == 0.0 } ?: 1e-12) + xi
            if (intersects) inside = !inside
            j = i
        }
        return inside
    }

    private fun pointInRing(point: LocalPoint, ring: List<LocalPoint>): Boolean {
        if (ring.size < 3) return false
        var inside = false
        var j = ring.size - 1
        for (i in ring.indices) {
            val xi = ring[i].x
            val yi = ring[i].y
            val xj = ring[j].x
            val yj = ring[j].y
            val intersects = (yi > point.y) != (yj > point.y) &&
                point.x <
                (xj - xi) * (point.y - yi) / ((yj - yi).takeUnless { it == 0.0 } ?: 1e-12) + xi
            if (intersects) inside = !inside
            j = i
        }
        return inside
    }

    private fun simplifyRing(ring: List<LocalPoint>, tolerance: Double): List<LocalPoint> {
        if (ring.size <= 3) return ring
        val closed = ArrayList<LocalPoint>(ring.size + 1)
        closed.addAll(ring)
        closed.add(ring.first())
        val simplified = ramerDouglasPeucker(closed, tolerance)
        val result = simplified.dropLast(1)
        return if (result.size >= 3) result else ring
    }

    private fun ramerDouglasPeucker(
        points: List<LocalPoint>,
        tolerance: Double
    ): List<LocalPoint> {
        if (points.size <= 2) return points
        val keep = BooleanArray(points.size)
        keep[0] = true
        keep[points.size - 1] = true
        val stack = ArrayDeque<Pair<Int, Int>>()
        stack.addLast(0 to points.size - 1)

        while (stack.isNotEmpty()) {
            val (start, end) = stack.removeLast()
            if (end <= start + 1) continue
            var furthestIndex = -1
            var furthestDistance = 0.0
            for (index in start + 1 until end) {
                val distance = perpendicularDistance(points[index], points[start], points[end])
                if (distance > furthestDistance) {
                    furthestDistance = distance
                    furthestIndex = index
                }
            }
            if (furthestIndex != -1 && furthestDistance > tolerance) {
                keep[furthestIndex] = true
                stack.addLast(start to furthestIndex)
                stack.addLast(furthestIndex to end)
            }
        }

        return points.filterIndexed { index, _ -> keep[index] }
    }

    private fun perpendicularDistance(
        point: LocalPoint,
        lineStart: LocalPoint,
        lineEnd: LocalPoint
    ): Double {
        val dx = lineEnd.x - lineStart.x
        val dy = lineEnd.y - lineStart.y
        if (dx == 0.0 && dy == 0.0) {
            return hypot(point.x - lineStart.x, point.y - lineStart.y)
        }
        val lengthSquared = dx * dx + dy * dy
        val t = ((point.x - lineStart.x) * dx + (point.y - lineStart.y) * dy) /
            lengthSquared
        val projectedX = lineStart.x + t * dx
        val projectedY = lineStart.y + t * dy
        return hypot(point.x - projectedX, point.y - projectedY)
    }
}
