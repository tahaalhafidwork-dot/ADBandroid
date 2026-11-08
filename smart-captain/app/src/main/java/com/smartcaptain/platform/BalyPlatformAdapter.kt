package com.smartcaptain.platform

import android.view.accessibility.AccessibilityEvent
import com.smartcaptain.domain.ExtractionSource
import com.smartcaptain.domain.TripOffer

/**
 * Baly Captain platform adapter.
 *
 * Detects when Baly is in the foreground, recognizes incoming trip-offer screens,
 * and extracts available trip information into the existing TripOffer model.
 *
 * ## Real-device verification results
 *
 * Package name verified on connected device: `app.baly.driver`
 * MainActivity: `app.driver.MainActivity`
 * Version: 3.8.1 (targetSdk=36)
 *
 * Package `com.baly.captain` was UNVERIFIED and incorrect — all references now use
 * `app.baly.driver`.
 *
 * ## Extraction status
 *
 * Fare/distance/duration extraction patterns below are based on the screenshot
 * reference fixture (3,250 IQD fare, 1 km pickup, 7 km trip, 5 min pickup ETA,
 * 15 min trip duration, Super category). These patterns must be confirmed against
 * an actual Baly trip-offer screen via Accessibility before production use.
 *
 * No trip-offer screen was observed on the device (driver was offline during
 * validation), so these patterns remain UNVERIFIED against live Accessibility data.
 */
object BalyPlatformAdapter : RidePlatformAdapter {

    /** Verified Baly Captain driver package name. */
    const val BALY_PACKAGE_NAME = "app.baly.driver"

    override val platformId: String = "baly"

    override val displayName: String = "باليCaptain"

    override fun isSupportedPackage(packageName: String): Boolean {
        return BALY_PACKAGE_NAME.equals(packageName, true)
    }

    override fun extractTripOffer(event: AccessibilityEvent): TripOffer? {
        if (event.packageName == null || !isSupportedPackage(event.packageName.toString())) {
            return null
        }
        if (event.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            return null
        }
        val text = event.text?.joinToString("\n") ?: return null
        return extractTripOfferFromText(text)
    }

    override fun extractTripOfferFromText(text: String): TripOffer? {
        if (text.isBlank()) return null
        val normalized = normalizeArabicIndicNumerals(text)

        val fare = extractFare(normalized)
        val pickupDistance = extractPickupDistance(normalized)
        val pickupTime = extractPickupTime(normalized)
        val tripDistance = extractTripDistance(normalized)
        val tripDuration = extractTripDuration(normalized)
        val pickupLocation = extractPickupLocation(normalized)
        val destinationLocation = extractDestinationLocation(normalized)
        val serviceCategory = extractServiceCategory(normalized)

        // Required fields per TripEvaluator: fare, pickupDistance, tripDistance.
        // Missing or ambiguous values remain unknown — never substitute with zero.
        if (fare == null || pickupDistance == null || tripDistance == null) {
            return null
        }

        return TripOffer(
            id = extractIdFromText(normalized),
            platformId = "baly",
            fareIqd = fare,
            pickupDistanceKm = pickupDistance,
            pickupDurationMinutes = pickupTime,
            tripDistanceKm = tripDistance,
            tripDurationMinutes = tripDuration,
            pickupAddress = pickupLocation,
            destinationAddress = destinationLocation,
            rideCategory = serviceCategory,
            source = ExtractionSource.ACCESSIBILITY
        )
    }

    // ========================================================================
    // Number normalization and parsing
    // ========================================================================

    /**
     * Convert Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩) to Western (0123456789).
     */
    internal fun normalizeArabicIndicNumerals(text: String): String {
        val arabicToWestern = mapOf(
            '٠' to '0', '١' to '1', '٢' to '2', '٣' to '3', '٤' to '4',
            '٥' to '5', '٦' to '6', '٧' to '7', '٨' to '8', '٩' to '9'
        )
        var result = text
        arabicToWestern.entries.forEach { (arabic, western) ->
            result = result.replace(arabic, western)
        }
        return result
    }

    /**
     * Parse a numeric string that may use Arabic or Western separators.
     *
     * Rules:
     * - Arabic comma (،) → Western comma (,)
     * - Arabic decimal point (٫) → Western dot (.)
     * - Comma followed by exactly 3 digits is a thousands separator (removed)
     * - Remaining commas are decimal separators (converted to dot)
     *
     * Examples:
     *   "3,250" → 3250.0
     *   "1.5" → 1.5
     *   "١,٢٥٠" → 1250.0
     */
    internal fun parseNumber(raw: String): Double? {
        val cleaned = raw.trim()
        if (cleaned.isEmpty()) return null

        var normalized = cleaned
            .replace('،', ',')  // Arabic comma → Western comma
            .replace('٫', '.')  // Arabic decimal point → Western dot

        // Remove thousands separators: comma followed by exactly 3 digits
        val thousandsRegex = Regex("""(\d+),(\d{3})(?=\D|$)""")
        normalized = thousandsRegex.replace(normalized) { match ->
            "${match.groupValues[1]}${match.groupValues[2]}"
        }

        // Remaining commas are decimal separators
        normalized = normalized.replace(',', '.')

        return normalized.toDoubleOrNull()
    }

    /**
     * Extract all number+unit pairs from text with surrounding context.
     *
     * Each result includes the parsed value, unit, and text before/after the match
     * for contextual classification (pickup vs destination).
     */
    internal data class NumberContext(
        val value: Double,
        val unit: String,
        val beforeText: String,
        val afterText: String
    )

    internal fun extractNumberContexts(text: String, unitRegex: Regex): List<NumberContext> {
        val normalized = normalizeArabicIndicNumerals(text)
        val contexts = mutableListOf<NumberContext>()
        val matches = unitRegex.findAll(normalized)
        for (match in matches) {
            val value = parseNumber(match.groupValues[1]) ?: continue
            val unit = match.groupValues[2]
            val start = match.range.first
            val end = match.range.last
            val beforeStart = maxOf(0, start - 60)
            val afterEnd = minOf(normalized.length, end + 1 + 60)
            val safeStart = start.coerceIn(0, normalized.length)
            val safeEnd = (end + 1).coerceIn(safeStart, normalized.length)
            val safeAfterEnd = afterEnd.coerceIn(safeEnd, normalized.length)
            contexts.add(NumberContext(
                value = value,
                unit = unit,
                beforeText = normalized.substring(beforeStart, safeStart),
                afterText = normalized.substring(safeEnd, safeAfterEnd)
            ))
        }
        return contexts
    }

    // ========================================================================
    // Fare extraction
    // ========================================================================

    /**
     * Extract fare in IQD from normalized text.
     *
     * Pattern: number followed by "دينار" (currency label).
     * Supports comma as thousands separator: "3,250 دينار" → 3250.0
     */
    internal fun extractFare(text: String): Double? {
        val normalized = normalizeArabicIndicNumerals(text)
        val fareRegex = Regex("""([\d,،]+)\s*دينار""", RegexOption.IGNORE_CASE)
        val match = fareRegex.find(normalized)
        if (match == null) {
            return null
        }
        val value = parseNumber(match.groupValues[1])
        return value
    }

    // ========================================================================
    // Distance and time extraction (context-aware)
    // ========================================================================

    private val distanceUnitRegex = Regex("""(\d+(?:[.,]\d+)?)\s*(كم|km|kilometer|kilometre|كيلومتر)""", RegexOption.IGNORE_CASE)
    private val timeUnitRegex = Regex("""(\d+(?:[.,]\d+)?)\s*(دقيقة|دقيقة|min|minute|دقيقة)""", RegexOption.IGNORE_CASE)

    /**
     * Extract pickup distance using contextual labels.
     * Returns the first distance match on screen (typically the pickup distance).
     */
    internal fun extractPickupDistance(text: String): Double? {
        val contexts = extractNumberContexts(text, distanceUnitRegex)
        return contexts.firstOrNull()?.value
    }

    /**
     * Extract trip distance using contextual labels.
     * Returns the last distance match on screen (typically the trip distance).
     */
    internal fun extractTripDistance(text: String): Double? {
        val contexts = extractNumberContexts(text, distanceUnitRegex)
        return contexts.lastOrNull()?.value
    }

    /**
     * Extract pickup ETA using contextual labels.
     * Returns the first time match on screen (typically the pickup ETA).
     */
    internal fun extractPickupTime(text: String): Double? {
        val contexts = extractNumberContexts(text, timeUnitRegex)
        return contexts.firstOrNull()?.value
    }

    /**
     * Extract trip duration using contextual labels.
     * Returns the last time match on screen (typically the trip duration).
     */
    internal fun extractTripDuration(text: String): Double? {
        val contexts = extractNumberContexts(text, timeUnitRegex)
        return contexts.lastOrNull()?.value
    }

    // ========================================================================
    // Location extraction
    // ========================================================================

    /**
     * Extract pickup location text after "نقطة الوصول" label.
     */
    internal fun extractPickupLocation(text: String): String? {
        return extractValueAfterLabel(text, "نقطة الوصول")
            ?: extractValueAfterLabel(text, "وصول")
            ?: extractValueAfterLabel(text, "pickup")
            ?: extractValueAfterLabel(text, "from")
    }

    /**
     * Extract destination location text after "الوجهة" label.
     */
    internal fun extractDestinationLocation(text: String): String? {
        return extractValueAfterLabel(text, "الوجهه")
            ?: extractValueAfterLabel(text, "الوجهة")
            ?: extractValueAfterLabel(text, "destination")
            ?: extractValueAfterLabel(text, "to")
    }

    private fun extractValueAfterLabel(text: String, label: String): String? {
        val lower = text.lowercase()
        val labelLower = label.lowercase()
        val index = lower.indexOf(labelLower)
        if (index < 0) return null
        val after = text.substring(index + labelLower.length).trim()
        if (after.isEmpty()) return null
        // Trim at common field separators (next label-like keyword)
        val boundaryRegex = Regex("""(\n|•|-|–|\|)""")
        val boundaryMatch = boundaryRegex.find(after)
        val trimmed = if (boundaryMatch != null) after.substring(0, boundaryMatch.range.first).trim() else after
        return if (trimmed.isEmpty()) null else trimmed
    }

    // ========================================================================
    // Service category extraction
    // ========================================================================

    /**
     * Extract service category (e.g., "Super", "سوبر").
     */
    internal fun extractServiceCategory(text: String): String? {
        val normalized = normalizeArabicIndicNumerals(text)
        val lower = normalized.lowercase()
        if (lower.contains("سوبر") || lower.contains("super")) {
            return "Super"
        }
        return null
    }

    // ========================================================================
    // ID extraction
    // ========================================================================

    internal fun extractIdFromText(text: String): String {
        return text.hashCode().toString()
    }
}