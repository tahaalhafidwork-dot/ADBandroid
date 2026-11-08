package com.smartcaptain

import android.app.Activity
import android.os.Bundle
import androidx.activity.compose.setContent
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Navy = Color(0xFF101B32)
private val Blue = Color(0xFF315FE8)
private val Canvas = Color(0xFFF4F6FA)
private val Green = Color(0xFF16845B)
private val Muted = Color(0xFF6B7280)

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { SmartCaptainApp() }
    }
}

@Composable
private fun SmartCaptainApp() {
    var automatic by remember { mutableStateOf(false) }
    var tab by remember { mutableStateOf(0) }
    MaterialTheme(
        colorScheme = lightColorScheme(primary = Blue, background = Canvas, surface = Color.White)
    ) {
        Scaffold(
            containerColor = Canvas,
            bottomBar = {
                NavigationBar(containerColor = Color.White) {
                    listOf(Icons.Default.Dashboard to "الرئيسية", Icons.Default.Tune to "الإعدادات", Icons.Default.Map to "المناطق", Icons.Default.History to "السجل")
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
                0 -> Dashboard(automatic, { automatic = it }, Modifier.padding(padding))
                1 -> SimplePage("الإعدادات", "اضبط الحد الأدنى للكيلومتر، الوقود، وقت الوصول، وقواعد القبول.")
                2 -> SimplePage("المناطق", "أضف مناطق محظورة أو مفضلة على الخريطة بعد إعداد مزود الخرائط.")
                else -> SimplePage("سجل الرحلات", "ستظهر هنا الرحلات التي تم تحليلها ونتائجها.")
            }
        }
    }
}

@Composable
private fun Dashboard(automatic: Boolean, onMode: (Boolean) -> Unit, modifier: Modifier = Modifier) {
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
                    Surface(color = Color(0xFF203B60), shape = RoundedCornerShape(50)) {
                        Text("غير متصل ببلي", color = Color(0xFFBFD4FF), fontSize = 11.sp, modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp))
                    }
                }
                Spacer(Modifier.height(18.dp))
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
