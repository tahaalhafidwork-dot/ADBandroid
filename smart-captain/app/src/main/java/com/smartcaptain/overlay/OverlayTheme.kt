package com.smartcaptain.overlay

import androidx.compose.ui.graphics.Color

/**
 * Dark professional theme for the Smart Captain floating overlay.
 *
 * Colors:
 * - Navy background (#101B32) — deep dark surface
 * - Blue primary accent (#315FE8) — interactive elements
 * - Green (#16845B) — positive results (EXCELLENT, GOOD)
 * - Orange (#D97706) — warnings (MARGINAL)
 * - Red (#DC2626) — rejection (REJECT)
 * - White / light gray — text on dark surfaces
 */
object OverlayTheme {

    // Background surfaces
    val BackgroundDark = Color(0xFF101B32)
    val SurfaceElevated = Color(0xFF1A2745)
    val SurfaceCard = Color(0xFF23305A)

    // Accent
    val PrimaryBlue = Color(0xFF315FE8)
    val PrimaryBlueDim = Color(0xFF2A4BB3)

    // Status colors
    val SuccessGreen = Color(0xFF16845B)
    val WarningOrange = Color(0xFFD97706)
    val ErrorRed = Color(0xFFDC2626)

    // Text
    val TextOnDark = Color(0xFFFFFFFF)
    val TextMuted = Color(0xFFBFD4FF)
    val TextDim = Color(0xFF7F8FA3)

    // Bubble
    val BubbleBackground = Color(0xFF315FE8)
    val BubbleIcon = Color(0xFFFFFFFF)

    // Panel
    val PanelBorder = Color(0xFF3A4E84)
}