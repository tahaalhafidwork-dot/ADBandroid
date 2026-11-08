package com.smartcaptain.map

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.smartcaptain.zone.Zone
import com.smartcaptain.zone.ZoneStore
import com.smartcaptain.zone.ZoneType

/**
 * Map screen showing saved zones with Add Zone capability.
 *
 * Displays map area with zone list. Zone data is persisted via [ZoneStore]
 * and survives app restart. OpenStreetMap tile integration can be added
 * by replacing the map area with osmdroid MapView or similar library.
 */
@Composable
fun MapScreen(
    zoneStore: ZoneStore,
    onZoneAdded: (Zone) -> Unit = {},
    onZoneDeleted: (String) -> Unit = {},
    modifier: Modifier = Modifier
) {
    val zones by remember { mutableStateOf(zoneStore.getAllZones()) }
    var showAddDialog by remember { mutableStateOf(false) }

    Column(modifier = modifier.fillMaxSize()) {
        // Map area
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(300.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    modifier = Modifier.size(48.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "🗺️",
                        style = MaterialTheme.typography.displaySmall,
                        color = Color.White
                    )
                }
                Text(
                    text = "الخريطة",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color(0xFF1A2745)
                )
                Text(
                    text = "OpenStreetMap - الخريطة",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFF7F8FA3)
                )
            }
        }

        // Zone list header
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "المناطق المحفوظة (${zones.size})",
                style = MaterialTheme.typography.titleMedium,
                color = Color(0xFF1A2745)
            )
        }

        // Zone list
        if (zones.isEmpty()) {
            Text(
                text = "لا توجد مناطق محفوظة بعد. استخدم الزر أدناه لإضافة منطقة.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF7F8FA3),
                modifier = Modifier.padding(16.dp).align(Alignment.CenterHorizontally)
            )
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp)
            ) {
                items(zones, key = { it.id }) { zone ->
                    val typeColor = when (zone.type) {
                        ZoneType.DANGER -> Color(0xFFDC2626)
                        ZoneType.FAVORITE -> Color(0xFF16845B)
                        else -> Color(0xFF315FE8)
                    }
                    val typeIcon = when (zone.type) {
                        ZoneType.DANGER -> "⚠️"
                        ZoneType.FAVORITE -> "⭐"
                        else -> "ℹ️"
                    }
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF23305A))
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier.size(32.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = typeIcon,
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = Color.White
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = zone.name,
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = Color.White
                                )
                                Text(
                                    text = "${zone.latitude.toString().take(6)}, ${zone.longitude.toString().take(6)} • ${zone.radiusMeters.toInt()}م",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = Color(0xFFBFD4FF)
                                )
                            }
                            IconButton(onClick = { zoneStore.deleteZone(zone.id) }) {
                                Box(
                                    modifier = Modifier.size(24.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = "🗑️",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = Color.White
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // Add Zone FAB
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Bottom,
                horizontalAlignment = Alignment.End
            ) {
                Spacer(modifier = Modifier.weight(1f))
                FloatingActionButton(
                    onClick = { showAddDialog = true },
                    modifier = Modifier.padding(16.dp)
                ) {
                    Box(
                        modifier = Modifier.size(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "➕",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color.White
                        )
                    }
                }
            }
        }

        // Add Zone dialog
        if (showAddDialog) {
            AddZoneDialog(
                zoneStore = zoneStore,
                onDismiss = { showAddDialog = false },
                onZoneAdded = { newZone ->
                    zoneStore.saveZone(newZone)
                    onZoneAdded(newZone)
                    showAddDialog = false
                }
            )
        }
    }
}

/**
 * Dialog for creating a new zone.
 */
@Composable
private fun AddZoneDialog(
    zoneStore: ZoneStore,
    onDismiss: () -> Unit,
    onZoneAdded: (Zone) -> Unit,
    modifier: Modifier = Modifier
) {
    var name by remember { mutableStateOf("") }
    var latitude by remember { mutableStateOf("") }
    var longitude by remember { mutableStateOf("") }
    var radius by remember { mutableStateOf("500") }
    var selectedType by remember { mutableStateOf(ZoneType.NEUTRAL) }
    var error by remember { mutableStateOf<String?>(null) }

    val zones = zoneStore.getAllZones()
    val existingNames = zones.map { it.name }.toSet()

    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = {
                if (name.isBlank()) {
                    error = "الرجاء إدخال اسم المنطقة"
                    return@TextButton
                }
                if (existingNames.contains(name)) {
                    error = "هذه المنطقة موجودة مسبقاً"
                    return@TextButton
                }
                val lat = latitude.toDoubleOrNull() ?: run {
                    error = "خطأ في خط العرض"
                    return@TextButton
                }
                val lon = longitude.toDoubleOrNull() ?: run {
                    error = "خطأ في خط الطول"
                    return@TextButton
                }
                val rad = radius.toDoubleOrNull() ?: run {
                    error = "خطأ في نصف القطر"
                    return@TextButton
                }
                if (lat !in -90.0..90.0) {
                    error = "خط العرض يجب أن يكون بين -90 و 90"
                    return@TextButton
                }
                if (lon !in -180.0..180.0) {
                    error = "خط الطول يجب أن يكون بين -180 و 180"
                    return@TextButton
                }
                if (rad <= 0.0) {
                    error = "نصف القطر يجب أن يكون أكبر من صفر"
                    return@TextButton
                }

                val newZone = Zone(
                    id = java.util.UUID.randomUUID().toString(),
                    name = name.trim(),
                    latitude = lat,
                    longitude = lon,
                    radiusMeters = rad,
                    type = selectedType
                )
                onZoneAdded(newZone)
            }) {
                Text("حفظ")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("إلغاء")
            }
        },
        title = {
            Text(text = "إضافة منطقة جديدة", style = MaterialTheme.typography.titleMedium)
        },
        text = {
            Column(modifier = Modifier.wrapContentSize()) {
                error?.let {
                    Text(text = it, color = Color.Red, style = MaterialTheme.typography.bodySmall)
                }

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("اسم المنطقة") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))

                Row(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.weight(1f)) {
                        OutlinedTextField(
                            value = latitude,
                            onValueChange = { latitude = it },
                            label = { Text("خط العرض") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        OutlinedTextField(
                            value = longitude,
                            onValueChange = { longitude = it },
                            label = { Text("خط الطول") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = radius,
                    onValueChange = { radius = it },
                    label = { Text("نصف القطر (أمتار)") },
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))

                Text(text = "نوع المنطقة:", style = MaterialTheme.typography.labelSmall)
                Row(modifier = Modifier.fillMaxWidth()) {
                    Row(modifier = Modifier.weight(1f)) {
                        RadioButton(
                            selected = selectedType == ZoneType.DANGER,
                            onClick = { selectedType = ZoneType.DANGER }
                        )
                        Text("خطر")
                    }
                    Row(modifier = Modifier.weight(1f)) {
                        RadioButton(
                            selected = selectedType == ZoneType.FAVORITE,
                            onClick = { selectedType = ZoneType.FAVORITE }
                        )
                        Text("مفضلة")
                    }
                    Row(modifier = Modifier.weight(1f)) {
                        RadioButton(
                            selected = selectedType == ZoneType.NEUTRAL,
                            onClick = { selectedType = ZoneType.NEUTRAL }
                        )
                        Text("محايد")
                    }
                }
            }
        },
        modifier = modifier
    )
}
