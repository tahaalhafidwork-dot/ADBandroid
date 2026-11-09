package com.smartcaptain.zone

/**
 * A geographic coordinate (latitude, longitude).
 * Platform-independent for use in both data model and tests.
 */
data class LatLng(val latitude: Double, val longitude: Double) {
    fun isValid(): Boolean =
        latitude in -90.0..90.0 && longitude in -180.0..180.0
}

/**
 * One freehand-brush action.
 *
 * [points] is the finger path, [radiusMeters] is the real-world brush radius at
 * the time of drawing, and [erase] marks an eraser pass instead of paint.
 * Keeping the path (rather than only the final polygon) allows the zone to be
 * re-opened and edited later, and lets the geometry layer rebuild the union.
 */
data class BrushStroke(
    val points: List<LatLng>,
    val radiusMeters: Double,
    val erase: Boolean = false
)

/**
 * One closed polygon plus its holes. Brush zones can produce several disjoint
 * polygons (for example when the user paints two separate streets), so the
 * data model keeps a primary polygon for backward compatibility and any
 * additional parts in [Zone.extraPolygons].
 */
data class ZonePolygon(
    val exterior: List<LatLng>,
    val holes: List<List<LatLng>> = emptyList()
)

/** The shape of a zone: circle (center + radius) or polygon (boundary points). */
enum class ZoneShape { CIRCLE, POLYGON }

/** Zone type for classification and visual styling. */
enum class ZoneType { DANGER, FAVORITE }

/**
 * A geographic zone with a center point, radius, and optional polygon boundary.
 *
 * Zones can be either:
 * - CIRCLE: defined by center (latitude, longitude) + radiusMeters
 * - POLYGON: defined by [polygonPoints] (3+ boundary points)
 *
 * Zones are persisted to SharedPreferences and survive app restart.
 */
data class Zone(
    val id: String,
    val name: String,
    val zoneShape: ZoneShape = ZoneShape.CIRCLE,
    val centerLatitude: Double = 0.0,
    val centerLongitude: Double = 0.0,
    val radiusMeters: Double = 0.0,
    val polygonPoints: List<LatLng> = emptyList(),
    val type: ZoneType = ZoneType.FAVORITE,
    val color: Int = 0xFF315FE8.toInt(),
    val createdAt: Long = System.currentTimeMillis(),
    /** Holes of [polygonPoints] (produced by the brush eraser). */
    val polygonHoles: List<List<LatLng>> = emptyList(),
    /** Additional disjoint polygon parts (freehand brush only). */
    val extraPolygons: List<ZonePolygon> = emptyList(),
    /**
     * The raw freehand strokes that produced this zone. Keeping them lets the
     * brush editor re-open the drawing exactly as it was painted.
     */
    val brushStrokes: List<BrushStroke> = emptyList(),
    /** Whether the zone actively blocks the area. */
    val isActive: Boolean = true
) {

    /** Returns true if this zone's data is valid. */
    fun isValid(): Boolean {
        if (name.isBlank()) return false

        return when (zoneShape) {
            ZoneShape.CIRCLE -> {
                centerLatitude in -90.0..90.0 &&
                    centerLongitude in -180.0..180.0 &&
                    radiusMeters > 0.0
            }
            ZoneShape.POLYGON -> {
                // Polygon needs at least 3 distinct valid points
                if (polygonPoints.size < 3) return false
                if (!polygonPoints.all { it.isValid() }) return false
                polygonPoints.distinct().size >= 3
            }
        }
    }

    /** True when this polygon was produced by the freehand brush. */
    fun isBrushZone(): Boolean = brushStrokes.isNotEmpty()

    /**
     * All polygon parts, primary first. The primary exterior is kept in
     * [polygonPoints] so existing code and stored data remain compatible.
     */
    fun polygons(): List<ZonePolygon> {
        if (zoneShape != ZoneShape.POLYGON) return emptyList()
        val result = mutableListOf<ZonePolygon>()
        if (polygonPoints.isNotEmpty()) {
            result.add(ZonePolygon(polygonPoints, polygonHoles))
        }
        result.addAll(extraPolygons)
        return result
    }

    /** Returns the representative center point (for circles: center; for polygons: centroid). */
    fun centerPoint(): LatLng {
        return when (zoneShape) {
            ZoneShape.CIRCLE -> LatLng(centerLatitude, centerLongitude)
            ZoneShape.POLYGON -> {
                if (polygonPoints.isEmpty()) LatLng(0.0, 0.0)
                else {
                    val avgLat = polygonPoints.sumOf { it.latitude } / polygonPoints.size
                    val avgLon = polygonPoints.sumOf { it.longitude } / polygonPoints.size
                    LatLng(avgLat, avgLon)
                }
            }
        }
    }

    /** Returns a display label combining name and type. */
    fun typeLabel(): String = when (type) {
        ZoneType.DANGER -> "منطقة خطرة"
        ZoneType.FAVORITE -> "منطقة مفضلة"
    }
}

/** Serializes/deserializes zones to/from JSON for SharedPreferences storage.
 *
 * Format: JSON with version field for forward/backward compatibility.
 * Falls back to the legacy pipe-delimited format (8 parts) for zones saved
 * by earlier versions of the app.
 *
 * Names containing special characters are safely handled via JSON escaping.
 */
object ZoneSerializer {
    private const val FORMAT_VERSION = 2

    private fun escapeJson(s: String): String {
        val sb = StringBuilder()
        for (ch in s) {
            when (ch) {
                '"' -> sb.append("\\\"")
                '\\' -> sb.append("\\\\")
                '\n' -> sb.append("\\n")
                '\r' -> sb.append("\\r")
                '\t' -> sb.append("\\t")
                else -> {
                    if (ch.code <= 0x1F) {
                        sb.append("\\u%04x".format(ch.code.toInt()))
                    } else {
                        sb.append(ch)
                    }
                }
            }
        }
        return sb.toString()
    }

    private fun unescapeJson(s: String): String {
        return s.replace("\\\"", "\"")
            .replace("\\\\", "\\")
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\\t", "\t")
    }

    // ---------------------------------------------------------------------
    // Compact encoding for the optional brush geometry fields.
    //
    // The project deliberately avoids a JSON dependency, so the extra fields
    // are stored as simple delimited strings:
    //   point  = "lat,lon"
    //   ring   = "point;point;..."
    //   rings  = "ring|ring|..."
    //   part   = "exterior~hole~hole"
    //   stroke = "radius,erase:point;point;..."
    // ---------------------------------------------------------------------

    private fun encodeRing(ring: List<LatLng>): String =
        ring.joinToString(";") { "${it.latitude},${it.longitude}" }

    private fun decodeRing(data: String): List<LatLng> {
        if (data.isBlank()) return emptyList()
        return data.split(";").mapNotNull { token ->
            val parts = token.split(",")
            if (parts.size != 2) return@mapNotNull null
            val lat = parts[0].toDoubleOrNull() ?: return@mapNotNull null
            val lon = parts[1].toDoubleOrNull() ?: return@mapNotNull null
            LatLng(lat, lon).takeIf { it.isValid() }
        }
    }

    private fun encodeRings(rings: List<List<LatLng>>): String =
        rings.filter { it.size >= 3 }.joinToString("|") { encodeRing(it) }

    private fun decodeRings(data: String?): List<List<LatLng>> {
        if (data.isNullOrBlank()) return emptyList()
        return data.split("|").map { decodeRing(it) }.filter { it.size >= 3 }
    }

    private fun encodeParts(parts: List<ZonePolygon>): String =
        parts.filter { it.exterior.size >= 3 }.joinToString("|") { part ->
            buildString {
                append(encodeRing(part.exterior))
                part.holes.filter { it.size >= 3 }.forEach { hole ->
                    append("~")
                    append(encodeRing(hole))
                }
            }
        }

    private fun decodeParts(data: String?): List<ZonePolygon> {
        if (data.isNullOrBlank()) return emptyList()
        return data.split("|").mapNotNull { encoded ->
            val rings = encoded.split("~").map { decodeRing(it) }
            val exterior = rings.firstOrNull() ?: return@mapNotNull null
            if (exterior.size < 3) return@mapNotNull null
            ZonePolygon(exterior, rings.drop(1).filter { it.size >= 3 })
        }
    }

    private fun encodeStrokes(strokes: List<BrushStroke>): String =
        strokes.filter { it.points.isNotEmpty() }.joinToString("|") { stroke ->
            "${stroke.radiusMeters},${if (stroke.erase) 1 else 0}:${encodeRing(stroke.points)}"
        }

    private fun decodeStrokes(data: String?): List<BrushStroke> {
        if (data.isNullOrBlank()) return emptyList()
        return data.split("|").mapNotNull { encoded ->
            val separator = encoded.indexOf(':')
            if (separator <= 0) return@mapNotNull null
            val header = encoded.substring(0, separator).split(",")
            if (header.size != 2) return@mapNotNull null
            val radius = header[0].toDoubleOrNull() ?: return@mapNotNull null
            val erase = header[1] == "1"
            val points = decodeRing(encoded.substring(separator + 1))
            if (points.isEmpty() || radius <= 0.0) return@mapNotNull null
            BrushStroke(points, radius, erase)
        }
    }

    fun serialize(zone: Zone): String {
        val sb = StringBuilder()
        sb.append("{")
        sb.append("\"v\":$FORMAT_VERSION,")
        sb.append("\"id\":\"${escapeJson(zone.id)}\",")
        sb.append("\"n\":\"${escapeJson(zone.name)}\",")
        sb.append("\"s\":${zone.zoneShape.ordinal},")
        sb.append("\"clat\":${zone.centerLatitude},")
        sb.append("\"clon\":${zone.centerLongitude},")
        sb.append("\"rad\":${zone.radiusMeters},")
        sb.append("\"t\":${zone.type.ordinal},")
        sb.append("\"c\":${zone.color},")
        sb.append("\"ct\":${zone.createdAt},")
        sb.append("\"pts\":[")
        sb.append(zone.polygonPoints.map { p -> "[${p.latitude},${p.longitude}]" }.joinToString(","))
        sb.append("]")
        sb.append(",\"act\":${if (zone.isActive) 1 else 0}")
        sb.append(",\"holes\":\"${encodeRings(zone.polygonHoles)}\"")
        sb.append(",\"parts\":\"${encodeParts(zone.extraPolygons)}\"")
        sb.append(",\"strk\":\"${encodeStrokes(zone.brushStrokes)}\"")
        sb.append("}")
        return sb.toString()
    }

    /** Parses a JSON array of [lat, lon] pairs. Returns empty list on failure. */
    private fun parsePolygonPoints(data: String): List<LatLng> {
        val points = mutableListOf<LatLng>()
        // Very lightweight parse: find all [lat,lon] patterns
        val regex = Regex("\\[\\s*(-?\\d+(?:\\.\\d+)?)\\s*,\\s*(-?\\d+(?:\\.\\d+)?)\\s*\\]")
        regex.findAll(data).forEach { match ->
            val lat = match.groupValues[1].toDoubleOrNull()
            val lon = match.groupValues[2].toDoubleOrNull()
            if (lat != null && lon != null) {
                points.add(LatLng(lat, lon))
            }
        }
        return points
    }

    /** Deserialize from JSON format (version 2). Returns null if not valid JSON v2. */
    private fun deserializeJson(data: String): Zone? {
        val trimmed = data.trim()
        if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) return null

        // Extract fields using simple regex (avoids adding a JSON library dependency)
        val getStr = { key: String ->
            val regex = Regex("\"$key\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"")
            regex.find(data)?.groupValues?.get(1)?.let { unescapeJson(it) }
        }
        val getInt = { key: String ->
            val regex = Regex("\"$key\"\\s*:\\s*(-?\\d+)")
            regex.find(data)?.groupValues?.get(1)?.toIntOrNull()
        }
        val getDouble = { key: String ->
            val regex = Regex("\"$key\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)")
            regex.find(data)?.groupValues?.get(1)?.toDoubleOrNull()
        }
        val getLong = { key: String ->
            val regex = Regex("\"$key\"\\s*:\\s*(-?\\d+)")
            regex.find(data)?.groupValues?.get(1)?.toLongOrNull()
        }

        val version = getInt("v") ?: return null
        if (version != FORMAT_VERSION) return null

        val id = getStr("id") ?: return null
        val name = getStr("n") ?: return null
        val shapeOrdinal = getInt("s") ?: return null
        val centerLat = getDouble("clat") ?: return null
        val centerLon = getDouble("clon") ?: return null
        val radius = getDouble("rad") ?: return null
        val typeOrdinal = getInt("t") ?: return null
        val color = getInt("c") ?: return null
        val createdAt = getLong("ct") ?: return null

        val zoneShape = when (shapeOrdinal) {
            0 -> ZoneShape.CIRCLE
            1 -> ZoneShape.POLYGON
            else -> return null
        }
        val type = when (typeOrdinal) {
            0 -> ZoneType.DANGER
            1 -> ZoneType.FAVORITE
            // Backward compatibility: older saved zones may have ordinal 2 (NEUTRAL)
            // or ordinal 3 (NONE). Treat them as FAVORITE since those types no
            // longer exist.
            else -> ZoneType.FAVORITE
        }

        val points = parsePolygonPoints(data)

        return Zone(
            id = id,
            name = name,
            zoneShape = zoneShape,
            centerLatitude = centerLat,
            centerLongitude = centerLon,
            radiusMeters = radius,
            polygonPoints = points,
            type = type,
            color = color,
            createdAt = createdAt,
            polygonHoles = decodeRings(getStr("holes")),
            extraPolygons = decodeParts(getStr("parts")),
            brushStrokes = decodeStrokes(getStr("strk")),
            isActive = (getInt("act") ?: 1) == 1
        )
    }

    /** Deserialize from legacy pipe-delimited format (8 parts). */
    private fun deserializePipe(data: String): Zone? {
        val parts = data.split("|")
        if (parts.size != 8) return null
        return try {
            Zone(
                id = parts[0],
                name = parts[1],
                zoneShape = ZoneShape.CIRCLE,
                centerLatitude = parts[2].toDouble(),
                centerLongitude = parts[3].toDouble(),
                radiusMeters = parts[4].toDouble(),
                polygonPoints = emptyList(),
                type = ZoneType.values()[parts[5].toInt()],
                color = parts[6].toInt(),
                createdAt = parts[7].toLong()
            )
        } catch (e: Exception) {
            null
        }
    }

    fun deserialize(data: String): Zone? {
        if (data.isBlank()) return null
        return deserializeJson(data) ?: deserializePipe(data)
    }
}

/**
 * Persists zones to SharedPreferences.
 * Zones survive app restart and navigation away from the map screen.
 *
 * Uses JSON format (version 2) with backward-compatible fallback to the
 * legacy pipe-delimited format for zones saved by earlier app versions.
 * Corrupted records are silently skipped (never crash the app).
 */
class ZoneStore(private val context: android.content.Context) {

    private val PREFS_NAME = "smart_captain_zones"
    private val KEY_ZONE_PREFIX = "zone_"

    private val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)

    /** Returns all saved zones. Corrupted records are silently skipped. */
    fun getAllZones(): List<Zone> {
        val zones = mutableListOf<Zone>()
        val keys = prefs.all.keys
        for (key in keys) {
            if (key.startsWith(KEY_ZONE_PREFIX)) {
                val data = prefs.getString(key, "") ?: ""
                ZoneSerializer.deserialize(data)?.let { zones.add(it) }
            }
        }
        return zones.sortedBy { it.createdAt }
    }

    /** Saves a zone. If a zone with the same id exists, it is replaced. */
    fun saveZone(zone: Zone) {
        require(zone.isValid()) { "Zone data is invalid" }
        prefs.edit().putString(KEY_ZONE_PREFIX + zone.id, ZoneSerializer.serialize(zone)).apply()
    }

    /** Deletes a zone by id. */
    fun deleteZone(id: String) {
        prefs.edit().remove(KEY_ZONE_PREFIX + id).apply()
    }

    /** Deletes all zones. */
    fun deleteAllZones() {
        val keys = prefs.all.keys.filter { it.startsWith(KEY_ZONE_PREFIX) }
        val editor = prefs.edit()
        for (key in keys) {
            editor.remove(key)
        }
        editor.apply()
    }

    /** Returns the zone with the given id, or null if not found. */
    fun getZone(id: String): Zone? {
        val data = prefs.getString(KEY_ZONE_PREFIX + id, "") ?: ""
        return ZoneSerializer.deserialize(data)
    }
}
