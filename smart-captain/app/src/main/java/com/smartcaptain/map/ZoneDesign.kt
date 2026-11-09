package com.smartcaptain.map

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.smartcaptain.zone.ZoneType

/**
 * Shared visual tokens for the zones experience: colours, spacing and radii.
 *
 * Keeping these in one place prevents the "random orange/blue buttons" look
 * that the screen previously had. The app is light-theme only today, so the
 * tokens are intentionally light-surface based.
 */
object ZoneDesign {
    val Navy = Color(0xFF101B32)
    val Blue = Color(0xFF315FE8)
    val BlueSoft = Color(0xFFEAF0FF)
    val Danger = Color(0xFFDC2626)
    val DangerSoft = Color(0xFFFEE7E7)
    val Success = Color(0xFF16845B)
    val SuccessSoft = Color(0xFFE1F5EC)
    val Warning = Color(0xFFB45309)
    val WarningSoft = Color(0xFFFFF2DD)
    val Canvas = Color(0xFFF4F6FA)
    val Surface = Color.White
    val Text = Navy
    val Muted = Color(0xFF6B7280)
    val Outline = Color(0xFFE4E8F1)
    val MapScrim = Color(0xE6FFFFFF)

    val Space4 = 4.dp
    val Space8 = 8.dp
    val Space12 = 12.dp
    val Space16 = 16.dp
    val Space20 = 20.dp
    val Space24 = 24.dp
    val Radius12 = 12.dp
    val Radius16 = 16.dp
    val Radius20 = 20.dp
    val Radius24 = 24.dp

    fun colorFor(type: ZoneType): Color = when (type) {
        ZoneType.DANGER -> Danger
        ZoneType.FAVORITE -> Success
    }

    fun softColorFor(type: ZoneType): Color = when (type) {
        ZoneType.DANGER -> DangerSoft
        ZoneType.FAVORITE -> SuccessSoft
    }

    fun labelFor(type: ZoneType): String = when (type) {
        ZoneType.DANGER -> "منطقة خطرة"
        ZoneType.FAVORITE -> "منطقة مفضلة"
    }
}
