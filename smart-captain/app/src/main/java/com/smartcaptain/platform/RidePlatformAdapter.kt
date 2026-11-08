package com.smartcaptain.platform

import android.view.accessibility.AccessibilityEvent
import com.smartcaptain.domain.TripOffer

interface RidePlatformAdapter {
    val platformId: String
    val displayName: String
    fun isSupportedPackage(packageName: String): Boolean
    fun extractTripOffer(event: AccessibilityEvent): TripOffer?
    fun extractTripOfferFromText(text: String): TripOffer?
}
