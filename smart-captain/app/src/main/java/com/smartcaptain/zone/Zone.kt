package com.smartcaptain.zone

/**
 * A geographic zone with a center point, radius, and type.
 * Zones are persisted to SharedPreferences and survive app restart.
 */
data class Zone(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val radiusMeters: Double,
    val type: ZoneType,
    val color: Int = 0xFF315FE8.toInt(),
    val createdAt: Long = System.currentTimeMillis()
) {

    /** Returns true if this zone's data is valid (non-empty name, valid coordinates, positive radius). */
    fun isValid(): Boolean {
        return name.isNotBlank() &&
            latitude in -90.0..90.0 &&
            longitude in -180.0..180.0 &&
            radiusMeters > 0.0
    }
}

/** Zone type for classification and visual styling. */
enum class ZoneType {
    DANGER, FAVORITE, NEUTRAL
}

/** Serializes/deserializes zones to/from a pipe-delimited string for SharedPreferences storage. */
object ZoneSerializer {
    private val SEPARATOR = "|"

    fun serialize(zone: Zone): String {
        return listOf(
            zone.id,
            zone.name,
            zone.latitude.toString(),
            zone.longitude.toString(),
            zone.radiusMeters.toString(),
            zone.type.name,
            zone.color.toString(),
            zone.createdAt.toString()
        ).joinToString(SEPARATOR)
    }

    fun deserialize(data: String): Zone? {
        val parts = data.split(SEPARATOR)
        if (parts.size != 8) return null
        return try {
            Zone(
                id = parts[0],
                name = parts[1],
                latitude = parts[2].toDouble(),
                longitude = parts[3].toDouble(),
                radiusMeters = parts[4].toDouble(),
                type = ZoneType.valueOf(parts[5]),
                color = parts[6].toInt(),
                createdAt = parts[7].toLong()
            )
        } catch (e: Exception) {
            null
        }
    }
}

/**
 * Persists zones to SharedPreferences.
 * Zones survive app restart and navigation away from the map screen.
 */
class ZoneStore(private val context: android.content.Context) {

    private val PREFS_NAME = "smart_captain_zones"
    private val KEY_ZONE_PREFIX = "zone_"

    private val prefs = context.getSharedPreferences(PREFS_NAME, android.content.Context.MODE_PRIVATE)

    /** Returns all saved zones. */
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
