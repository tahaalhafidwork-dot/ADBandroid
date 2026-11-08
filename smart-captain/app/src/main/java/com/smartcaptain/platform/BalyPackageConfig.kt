package com.smartcaptain.platform

/**
 * Baly Captain package configuration.
 *
 * ## Verification status
 *
 * Package name verified on real device: `app.baly.driver`
 * MainActivity: `app.driver.MainActivity`
 * Version: 3.8.1 (targetSdk=36)
 *
 * The previous placeholder `com.baly.captain` was UNVERIFIED and incorrect.
 * All references now use the verified `app.baly.driver`.
 */
object BalyPackageConfig {
    /** Verified Baly Captain driver package name. */
    const val VERIFIED_PACKAGE_NAME = "app.baly.driver"

    /**
     * Candidate package names for Baly Captain.
     *
     * Only the verified entry is trusted. Unverified entries are rejected.
     */
    val candidatePackages = listOf(
        PackageEntry(
            packageName = "app.baly.driver",
            verified = true,
            note = "Verified on real device via `adb shell pm list packages`. MainActivity: app.driver.MainActivity, v3.8.1"
        )
    )

    /** A single candidate package entry. */
    data class PackageEntry(
        val packageName: String,
        val verified: Boolean,
        val note: String
    )

    /** Returns true if [packageName] matches any candidate, regardless of verification. */
    fun isCandidate(packageName: String): Boolean =
        candidatePackages.any { it.packageName == packageName }

    /** Returns true only if [packageName] matches a verified candidate. */
    fun isVerified(packageName: String): Boolean =
        candidatePackages.any { it.verified && it.packageName == packageName }

    /** The verified package name, or null if none exist. */
    val preferredPackage: String?
        get() = candidatePackages.firstOrNull { it.verified }?.packageName
}