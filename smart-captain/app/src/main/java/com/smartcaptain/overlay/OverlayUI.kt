package com.smartcaptain.overlay

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.*
import com.smartcaptain.domain.TripDecision
import com.smartcaptain.domain.TripEvaluation

/**
 * Composable UI for the Smart Captain floating overlay.
 *
 * Provides two states:
 * 1. Bubble — compact circular floating button, draggable across the screen
 * 2. Panel — expanded analysis panel showing trip data
 *
 * The overlay is rendered inside a WindowManager view (MATCH_PARENT) so the
 * bubble can be positioned anywhere on screen via offset.
 */
@Composable
fun SmartCaptainOverlay(
    onClose: () -> Unit,
    onCollapse: () -> Unit,
    onExpand: () -> Unit,
    isExpanded: Boolean,
    evaluation: TripEvaluation?,
    isProcessing: Boolean,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .fillMaxHeight()
            .clipToBounds()
    ) {
        if (isExpanded) {
            AnalysisPanel(
                onClose = onClose,
                onCollapse = onCollapse,
                evaluation = evaluation,
                isProcessing = isProcessing,
                modifier = Modifier.fillMaxWidth()
            )
        } else {
            FloatingBubble(
                onClose = onClose,
                onExpand = onExpand,
                modifier = Modifier.fillMaxSize()
            )
        }
    }
}

/**
 * Compact circular floating bubble that stays on top of other apps.
 * Draggable via touch gestures, clamped to screen boundaries.
 */
@Composable
private fun FloatingBubble(
    onClose: () -> Unit,
    onExpand: () -> Unit,
    modifier: Modifier = Modifier
) {
    val density = LocalDensity.current
    val config = LocalConfiguration.current
    val screenWidthPx = with(density) { config.screenWidthDp.dp.toPx() }
    val screenHeightPx = with(density) { config.screenHeightDp.dp.toPx() }
    val bubbleDiameterPx = with(density) { 56f.dp.toPx() }

    var offset by remember { mutableStateOf(Offset(50f, 200f)) }

    Box(
        modifier = modifier
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    offset = Offset(
                        (offset.x + dragAmount.x).coerceIn(
                            0f,
                            (screenWidthPx - bubbleDiameterPx).coerceAtLeast(0f)
                        ),
                        (offset.y + dragAmount.y).coerceIn(
                            0f,
                            (screenHeightPx - bubbleDiameterPx).coerceAtLeast(0f)
                        )
                    )
                }
            }
    ) {
        // Bubble
        Box(
            modifier = Modifier
                .offset {
                    IntOffset(offset.x.toInt(), offset.y.toInt())
                }
                .size(56.dp)
                .background(OverlayTheme.BubbleBackground, CircleShape)
                .clip(CircleShape)
                .clickable { onExpand() }
                .padding(4.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "S",
                color = OverlayTheme.BubbleIcon,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold
            )
        }

        // Close button positioned just below-right of the bubble
        Box(
            modifier = Modifier
                .offset {
                    IntOffset(
                        (offset.x + bubbleDiameterPx / 2f).toInt(),
                        (offset.y + bubbleDiameterPx + 4f).toInt()
                    )
                }
        ) {
            Button(
                onClick = onClose,
                modifier = Modifier.padding(horizontal = 4.dp)
            ) {
                Text(
                    text = "✕",
                    color = OverlayTheme.TextMuted,
                    fontSize = 14.sp
                )
            }
        }
    }
}

/**
 * Expanded analysis panel showing trip details and evaluation.
 */
@Composable
private fun AnalysisPanel(
    onClose: () -> Unit,
    onCollapse: () -> Unit,
    evaluation: TripEvaluation?,
    isProcessing: Boolean,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .padding(16.dp)
            .background(OverlayTheme.SurfaceCard)
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, OverlayTheme.PanelBorder, RoundedCornerShape(16.dp))
    ) {
        // Header row: title + collapse + close
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Smart Captain",
                style = MaterialTheme.typography.titleMedium,
                color = OverlayTheme.TextOnDark,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Button(
                onClick = onCollapse,
                modifier = Modifier.padding(horizontal = 4.dp)
            ) {
                Text(text = "˄", color = OverlayTheme.PrimaryBlue, fontSize = 14.sp)
            }
            Button(
                onClick = onClose,
                modifier = Modifier.padding(horizontal = 4.dp)
            ) {
                Text(text = "✕", color = OverlayTheme.TextMuted, fontSize = 14.sp)
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Evaluation result badge (prominent)
        if (evaluation != null) {
            EvaluationBadge(
                decision = evaluation.decision,
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(12.dp))
        }

        // Processing state
        if (isProcessing) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                CircularProgressIndicator(
                    color = OverlayTheme.PrimaryBlue,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "جاري التحليل...",
                    style = MaterialTheme.typography.bodySmall,
                    color = OverlayTheme.TextMuted
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
        }

        // Trip details section
        Text(
            text = "تفاصيل الرحلة",
            style = MaterialTheme.typography.labelMedium,
            color = OverlayTheme.TextMuted,
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(8.dp))

        val fare = evaluation?.estimatedNetIqd?.let { "%.0f د.ع".format(it) } ?: "— د.ع"
        val totalDistance = evaluation?.totalDistanceKm?.let { "%.1f كم".format(it) } ?: "— كم"
        val totalDuration = evaluation?.totalDurationMinutes?.let { "%.0f دقيقة".format(it) } ?: "— دقيقة"
        val fuelCost = evaluation?.fuelCostIqd?.let { "%.0f د.ع".format(it) } ?: "— د.ع"
        val netProfit = evaluation?.estimatedNetIqd?.let { "%.0f د.ع".format(it) } ?: "— د.ع"
        val netPerKm = evaluation?.netPerKmIqd?.let { "%.0f د.ع/كم".format(it) } ?: "— د.ع/كم"
        val netPerHour = evaluation?.netPerHourIqd?.let { "%.0f د.ع/س".format(it) } ?: "— د.ع/س"

        DetailRow(title = "الأجرة", value = fare, modifier = Modifier.fillMaxWidth())
        DetailRow(title = "المسافة الإجمالية", value = totalDistance, modifier = Modifier.fillMaxWidth())
        DetailRow(title = "المدة الإجمالية", value = totalDuration, modifier = Modifier.fillMaxWidth())
        DetailRow(title = "تكلفة الوقود", value = fuelCost, modifier = Modifier.fillMaxWidth())
        DetailRow(title = "صافي الربح", value = netProfit, modifier = Modifier.fillMaxWidth())
        DetailRow(title = "الربح لكل كم", value = netPerKm, modifier = Modifier.fillMaxWidth())
        DetailRow(title = "الربح لكل ساعة", value = netPerHour, modifier = Modifier.fillMaxWidth())

        Spacer(modifier = Modifier.height(12.dp))

        // Reasons (if any)
        val reasons = evaluation?.reasons?.filter { it.isNotEmpty() }
        if (reasons?.isNotEmpty() == true) {
            Text(
                text = "ملاحظات:",
                style = MaterialTheme.typography.labelSmall,
                color = OverlayTheme.TextDim,
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(modifier = Modifier.height(4.dp))
            reasons.forEach { reason ->
                Text(
                    text = "• $reason",
                    style = MaterialTheme.typography.bodySmall,
                    color = OverlayTheme.TextMuted,
                    modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
        }

        // Missing data notice
        if (evaluation?.decision == TripDecision.INCOMPLETE) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp)
                    .background(OverlayTheme.WarningOrange.copy(alpha = 0.15f))
                    .clip(RoundedCornerShape(8.dp))
            ) {
                Text(
                    text = "بيانات ناقصة — لا يمكن تقييم الرحلة",
                    style = MaterialTheme.typography.bodySmall,
                    color = OverlayTheme.WarningOrange
                )
            }
        }
    }
}

/**
 * Prominent evaluation decision badge.
 */
@Composable
private fun EvaluationBadge(
    decision: TripDecision,
    modifier: Modifier = Modifier
) {
    val (badgeColor, label) = when (decision) {
        TripDecision.EXCELLENT -> OverlayTheme.SuccessGreen to "ممتاز"
        TripDecision.GOOD -> OverlayTheme.SuccessGreen to "مقبول"
        TripDecision.MARGINAL -> OverlayTheme.WarningOrange to "يُحتاج مراجعة"
        TripDecision.REJECT -> OverlayTheme.ErrorRed to "مرفوض"
        TripDecision.INCOMPLETE -> OverlayTheme.WarningOrange to "ناقص البيانات"
    }

    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .padding(horizontal = 12.dp, vertical = 6.dp)
                .background(badgeColor.copy(alpha = 0.15f))
                .clip(CircleShape)
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.bodyMedium,
                color = badgeColor,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

/**
 * A single detail row with title and value.
 */
@Composable
private fun DetailRow(
    title: String,
    value: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.bodyMedium,
            color = OverlayTheme.TextMuted,
            modifier = Modifier.weight(1f)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = OverlayTheme.TextOnDark,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.wrapContentWidth()
        )
    }
}