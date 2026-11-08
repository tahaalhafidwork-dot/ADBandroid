package com.smartcaptain

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartcaptain.accessibility.AccessibilityConnectionManager
import com.smartcaptain.integration.IntegrationStatus
import com.smartcaptain.integration.TripPipeline
import com.smartcaptain.map.MapScreen
import com.smartcaptain.overlay.OverlayManager
import com.smartcaptain.overlay.OverlayManagerInstance
import com.smartcaptain.zone.ZoneStore
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.LaunchedEffect
import kotlinx.coroutines.launch

private val Navy = Color(0xFF101B32)
private val Blue = Color(0xFF315FE8)
private val Canvas = Color(0xFFF4F6FA)
private val Green = Color(0xFF16845B)
private val Muted = Color(0xFF6B7280)

class MainActivity : ComponentActivity() {

    private lateinit var overlayManager: OverlayManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize overlay manager once and register it for state sync
        overlayManager = OverlayManager(applicationContext)
        OverlayManagerInstance.set(overlayManager)

        setContent { SmartCaptainApp(overlayManager) }
    }
}

@Composable
private fun SmartCaptainApp(overlayManager: OverlayManager) {
    val context = LocalContext.current

    var automatic by remember { mutableStateOf(false) }
    var tab by remember { mutableStateOf(0) }
    var overlayPermissionGranted by remember { mutableStateOf(overlayManager.hasOverlayPermission()) }
    var showOverlayPermissionDialog by remember { mutableStateOf(false) }

    val zoneStore = remember(context) { ZoneStore(context) }

    // Observe accessibility connection state as Compose state
    val isAccessibilityConnected by AccessibilityConnectionManager.isConnected
        .collectAsState(initial = false)

    // Observe accessibility enabled state from system settings
    val isAccessibilityEnabled by AccessibilityConnectionManager.isEnabled
        .collectAsState(initial = false)

    // Refresh enabled state from system settings when the screen is shown
    LaunchedEffect(Unit) {
        AccessibilityConnectionManager.refreshEnabledState(context)
    }

    val overlayPermissionLauncher = rememberLauncherForActivityResult(
        contract = overlayManager.overlayPermissionContract()
    ) { granted ->
        overlayPermissionGranted = granted
        showOverlayPermissionDialog = false
    }

    MaterialTheme(
        colorScheme = lightColorScheme(primary = Blue, background = Canvas, surface = Color.White)
    ) {
        Scaffold(
            containerColor = Canvas,
            bottomBar = {
                NavigationBar(containerColor = Color.White) {
                    listOf(
                        Icons.Default.Dashboard to "الرئيسية",
                        Icons.Default.Tune to "الإعدادات",
                        Icons.Default.Map to "المناطق",
                        Icons.Default.History to "السجل"
                    )
                        .forEachIndexed { index, item ->
                            NavigationBarItem(
                                selected = tab == index,
                                onClick = { tab = index },
                                icon = { Icon(item.first, contentDescription = item.second) },
                                label = { Text(item.second, fontSize = 11.sp) }
                            )
                        }
                }
            }
        ) { padding ->
            when (tab) {
                0 -> Dashboard(
                    automatic = automatic,
                    onMode = { automatic = it },
                    accessibilityEnabled = isAccessibilityEnabled,
                    accessibilityConnected = isAccessibilityConnected,
                    onOpenAccessibilitySettings = {
                        AccessibilityConnectionManager.openAccessibilitySettings(context)
                    },
                    modifier = Modifier.padding(padding)
                )
                1 -> SettingsPage(
                    overlayManager = overlayManager,
                    overlayPermissionGranted = overlayPermissionGranted,
                    onRequestPermission = {
                        showOverlayPermissionDialog = true
                        overlayPermissionLauncher.launch(Unit)
                    },
                    onToggleOverlay = { checked ->
                        if (checked) {
                            overlayManager.showOverlay()
                        } else {
                            overlayManager.hideOverlay()
                        }
                    },
                    modifier = Modifier.padding(padding)
                )
                2 -> MapScreen(
                    zoneStore = zoneStore,
                    modifier = Modifier.padding(padding)
                )
                else -> SimplePage("سجل الرحلات", "ستظهر هنا الرحلات التي تم تحليلها ونتائجها.")
            }

            // Overlay permission rationale dialog
            if (showOverlayPermissionDialog) {
                OverlayPermissionDialog(
                    onDismiss = { showOverlayPermissionDialog = false },
                    onGrant = {
                        showOverlayPermissionDialog = false
                        overlayPermissionLauncher.launch(Unit)
                    }
                )
            }
        }
    }
}

@Composable
private fun Dashboard(
    automatic: Boolean,
    onMode: (Boolean) -> Unit,
    accessibilityEnabled: Boolean,
    accessibilityConnected: Boolean,
    onOpenAccessibilitySettings: () -> Unit,
    modifier: Modifier = Modifier
) {
    val integrationStatus by remember {
        mutableStateOf(
            IntegrationStatus(
                balyDetected = true,
                accessibilityConnected = accessibilityConnected
            )
        )
    }

    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
        Spacer(Modifier.height(22.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("صباح الخير، كابتن", color = Muted, fontSize = 13.sp)
                Text("Smart Captain", color = Navy, fontSize = 25.sp, fontWeight = FontWeight.Bold)
            }
            Box(Modifier.size(48.dp).background(Color.White, CircleShape), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.DirectionsCar, null, tint = Blue)
            }
        }
        Spacer(Modifier.height(20.dp))
        Card(
            shape = RoundedCornerShape(26.dp),
            colors = CardDefaults.cardColors(containerColor = Navy),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("حالة المساعد", color = Color.White.copy(alpha = .75f), modifier = Modifier.weight(1f))
                    Surface(
                        color = when {
                            accessibilityConnected -> Color(0xFF16845B)
                            accessibilityEnabled -> Color(0xFFB45309)
                            else -> Color(0xFF203B60)
                        },
                        shape = RoundedCornerShape(50)
                    ) {
                        Text(
                            text = when {
                                !integrationStatus.balyDetected -> "بلي غير مكتشف"
                                !accessibilityEnabled -> "خدمة إمكانية الوصول غير مفعّلة"
                                !accessibilityConnected -> "الخدمة مفعّلة ولكن غير متصلة"
                                else -> "الخدمة متصلة"
                            },
                            color = Color.White,
                            fontSize = 11.sp,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                        )
                    }
                }
                Spacer(Modifier.height(18.dp))
                if (!accessibilityConnected) {
                    TextButton(
                        onClick = onOpenAccessibilitySettings,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "تفعيل خدمة إمكانية الوصول",
                            color = Color(0xFFBFE8D7)
                        )
                    }
                    Spacer(Modifier.height(8.dp))
                }
                Text("جاهز لتحليل الرحلات", color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text("فعّل خدمة إمكانية الوصول بعد اكتمال ربط بلي.", color = Color.White.copy(alpha = .68f), fontSize = 13.sp)
                Spacer(Modifier.height(18.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Shield, null, tint = Color(0xFF7CD7B1), modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("القبول التلقائي متوقف افتراضياً", color = Color(0xFFBFE8D7), fontSize = 12.sp)
                }
            }
        }
        Spacer(Modifier.height(18.dp))
        Text("وضع التشغيل", color = Navy, fontWeight = FontWeight.Bold, fontSize = 17.sp)
        Spacer(Modifier.height(10.dp))
        Card(shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(42.dp).background(if (automatic) Color(0xFFFFF2DD) else Color(0xFFEAF0FF), CircleShape), contentAlignment = Alignment.Center) {
                    Icon(if (automatic) Icons.Default.AutoMode else Icons.Default.TouchApp, null, tint = if (automatic) Color(0xFFB46A0A) else Blue)
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(if (automatic) "تلقائي" else "يدوي", color = Navy, fontWeight = FontWeight.SemiBold)
                    Text(if (automatic) "يتطلب تحقق جميع شروط الأمان" else "راجع القرار قبل قبول الرحلة", color = Muted, fontSize = 12.sp)
                }
                Switch(checked = automatic, onCheckedChange = onMode)
            }
        }
        Spacer(Modifier.height(22.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("ملخص اليوم", color = Navy, fontSize = 17.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            Text("تقديري", color = Muted, fontSize = 11.sp)
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("رحلات محللة", "0", Icons.Default.Route, Modifier.weight(1f))
            MetricCard("صافي تقديري", "— د.ع", Icons.Default.Payments, Modifier.weight(1f))
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("متوسط / كم", "— د.ع", Icons.Default.Speed, Modifier.weight(1f))
            MetricCard("وقود اليوم", "— د.ع", Icons.Default.LocalGasStation, Modifier.weight(1f))
        }
        Spacer(Modifier.height(20.dp))
        Card(shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Column(Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.TipsAndUpdates, null, tint = Blue)
                    Spacer(Modifier.width(8.dp))
                    Text("خطوة الإعداد التالية", fontWeight = FontWeight.Bold, color = Navy)
                }
                Spacer(Modifier.height(8.dp))
                Text("أكمل إعداد السيارة وسعر الوقود لتصبح تقديرات الربح أدق.", color = Muted, fontSize = 13.sp)
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun MetricCard(title: String, value: String, icon: androidx.compose.ui.graphics.vector.ImageVector, modifier: Modifier = Modifier) {
    Card(modifier, shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(Modifier.padding(15.dp)) {
            Icon(icon, null, tint = Blue, modifier = Modifier.size(20.dp))
            Spacer(Modifier.height(12.dp))
            Text(value, color = Navy, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text(title, color = Muted, fontSize = 11.sp)
        }
    }
}

@Composable
private fun SimplePage(title: String, description: String) {
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text(title, fontSize = 26.sp, fontWeight = FontWeight.Bold, color = Navy)
        Spacer(Modifier.height(12.dp))
        Text(description, color = Muted, fontSize = 15.sp, lineHeight = 23.sp)
    }
}

/**
 * Settings page with overlay permission controls.
 */
@Composable
private fun SettingsPage(
    overlayManager: OverlayManager,
    overlayPermissionGranted: Boolean,
    onRequestPermission: () -> Unit,
    onToggleOverlay: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    // Observe actual overlay visibility from the manager
    val isOverlayVisible by overlayManager.overlayVisible.collectAsState(initial = false)

    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Top
    ) {
        Text(
            text = "الإعدادات",
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold,
            color = Navy
        )
        Spacer(Modifier.height(12.dp))

        // Overlay permission section
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color.White)
        ) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    text = "النافذة العائمة",
                    style = MaterialTheme.typography.titleMedium,
                    color = Navy,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = "تمكين النافذة العائمة لعرض تقييم الرحلات فوق تطبيق بلي.",
                    color = Muted,
                    fontSize = 13.sp,
                    lineHeight = 20.sp
                )
                Spacer(Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "إذن العرض فوق التطبيقات",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (overlayPermissionGranted) Navy else Muted
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    if (overlayPermissionGranted) {
                        Text(
                            text = "ممنوح",
                            style = MaterialTheme.typography.bodySmall,
                            color = Green
                        )
                    } else {
                        Text(
                            text = "غير ممنوح",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFFDC2626)
                        )
                    }
                }
                Spacer(Modifier.height(12.dp))

                if (!overlayPermissionGranted) {
                    TextButton(
                        onClick = onRequestPermission,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("طلب إذن النافذة العائمة")
                    }
                }

                Spacer(Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "تشغيل النافذة العائمة",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Navy
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Switch(
                        checked = isOverlayVisible,
                        onCheckedChange = { checked -> onToggleOverlay(checked) },
                        enabled = overlayPermissionGranted
                    )
                }

                // Show overlay status text
                if (overlayPermissionGranted) {
                    Spacer(Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = if (isOverlayVisible) "النافذة نشطة" else "النافذة متوقفة",
                            style = MaterialTheme.typography.bodySmall,
                            color = if (isOverlayVisible) Green else Muted
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(16.dp))

        // Auto mode section
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color.White)
        ) {
            Column(Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "القبول التلقائي",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Navy
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "متوقف افتراضياً",
                        style = MaterialTheme.typography.bodySmall,
                        color = Muted
                    )
                }
            }
        }
    }
}

/**
 * Overlay permission rationale dialog.
 */
@Composable
fun OverlayPermissionDialog(
    onDismiss: () -> Unit,
    onGrant: () -> Unit,
    modifier: Modifier = Modifier
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = onGrant) {
                Text("منح الإذن")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("إلغاء")
            }
        },
        title = {
            Text(
                text = "إذن العرض فوق التطبيقات",
                style = MaterialTheme.typography.titleMedium,
                color = Navy
            )
        },
        text = {
            Text(
                text = "يحتاج Smart Captain إلى إذن " +
                    "الDisplay over other apps " +
                    "لعرض النافذة العائمة فوق تطبيق بلي. " +
                    "سيتم فتح إعدادات النظام لمنح الإذن.",
                style = MaterialTheme.typography.bodyMedium,
                color = Muted
            )
        },
        modifier = modifier
    )
}