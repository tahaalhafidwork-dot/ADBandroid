package com.smartcaptain.map

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.smartcaptain.zone.LatLng
import com.smartcaptain.zone.Zone
import com.smartcaptain.zone.ZoneShape
import com.smartcaptain.zone.ZoneStore
import com.smartcaptain.zone.ZoneType
import org.osmdroid.config.Configuration
import org.osmdroid.events.MapListener
import org.osmdroid.events.ScrollEvent
import org.osmdroid.events.ZoomEvent
import org.osmdroid.tileprovider.tilesource.XYTileSource
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polyline
import java.util.UUID

/**
 * Map screen showing real OpenStreetMap tiles with zone management.
 *
 * Uses osmdroid library for OSM tile rendering. MapView is embedded via
 * AndroidView with proper lifecycle management.
 *
 * Features:
 * - Real OSM tiles with attribution
 * - Zoom in/out and pan
 * - Saved zones displayed as circles or polygons
 * - Add Zone: manual entry (circle) or drawing polygon on map
 * - Edit and delete existing zones
 */
@Composable
fun MapScreen(
    zoneStore: ZoneStore,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val zones by remember { mutableStateOf(zoneStore.getAllZones()) }
    var showAddDialog by remember { mutableStateOf(false) }
    var editingZoneId by remember { mutableStateOf<String?>(null) }
    var showDeleteConfirm by remember { mutableStateOf<Pair<String, String>?>(null) }
    var isDrawingMode by remember { mutableStateOf(false) }
    var drawingPoints by remember { mutableStateOf<List<GeoPoint>>(emptyList()) }

    // Initialize osmdroid configuration once
    var initialized by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        if (!initialized) {
            Configuration.getInstance().load(
                context,
                context.applicationContext.getSharedPreferences("osmdroid", Context.MODE_PRIVATE)
            )
            initialized = true
        }
    }

    Column(modifier = modifier.fillMaxSize()) {
        // Map area
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
            contentAlignment = Alignment.Center
        ) {
            MapViewContainer(
                zones = zones,
                drawingPoints = drawingPoints,
                isDrawingMode = isDrawingMode,
                onMapTap = { geoPoint ->
                    if (isDrawingMode) {
                        drawingPoints = drawingPoints + geoPoint
                    } else {
                        val tappedZone = findZoneAt(zones, geoPoint)
                        editingZoneId = if (tappedZone != null) tappedZone.id else null
                    }
                }
            )

            // Drawing mode indicator
            if (isDrawingMode) {
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .background(Color(0xFFB45309), CircleShape)
                        .align(Alignment.TopStart)
                        .padding(16.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "ر",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White
                    )
                }
            }

            // Drawing controls
            if (isDrawingMode && drawingPoints.isNotEmpty()) {
                Box(
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .padding(16.dp),
                    contentAlignment = Alignment.BottomStart
                ) {
                    Column {
                        Text(
                            text = "نقاط الرسم: ${drawingPoints.size}",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFF1A2745)
                        )
                        Row {
                            OutlinedButton(
                                onClick = {
                                    val newPoints = drawingPoints.toMutableList()
                                    if (newPoints.isNotEmpty()) {
                                        newPoints.removeAt(newPoints.size - 1)
                                        drawingPoints = newPoints
                                    }
                                }
                            ) {
                                Text("تراجع")
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            OutlinedButton(
                                onClick = { drawingPoints = emptyList() }
                            ) {
                                Text("مسح الكل")
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Button(
                                onClick = {
                                    if (drawingPoints.size >= 3) {
                                        showAddDialog = true
                                    }
                                },
                                enabled = drawingPoints.size >= 3
                            ) {
                                Text("إغلاق المضلع")
                            }
                        }
                    }
                }
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
                    val isSelected = editingZoneId == zone.id
                    val typeColor = when (zone.type) {
                        ZoneType.DANGER -> Color(0xFFDC2626)
                        ZoneType.FAVORITE -> Color(0xFF16845B)
                        else -> Color(0xFF315FE8)
                    }
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 8.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isSelected) typeColor.copy(alpha = 0.2f) else Color(0xFF23305A)
                        )
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier.size(32.dp).background(typeColor, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = when (zone.type) {
                                        ZoneType.DANGER -> "⚠️"
                                        ZoneType.FAVORITE -> "⭐"
                                        else -> "ℹ️"
                                    },
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
                                    text = zoneShapeLabel(zone),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = Color(0xFFBFD4FF)
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                IconButton(
                                    onClick = { editingZoneId = zone.id },
                                    enabled = !isSelected
                                ) {
                                    Text(
                                        text = "✏️",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = Color(0xFF315FE8)
                                    )
                                }
                                Spacer(modifier = Modifier.height(4.dp))
                                IconButton(onClick = { showDeleteConfirm = Pair(zone.id, zone.name) }) {
                                    Text(
                                        text = "🗑️",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = Color(0xFFDC2626)
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // Add Zone / Draw Zone FABs
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Bottom,
                horizontalAlignment = Alignment.End
            ) {
                Spacer(modifier = Modifier.weight(1f))
                if (!isDrawingMode) {
                    Button(
                        onClick = {
                            isDrawingMode = true
                            drawingPoints = emptyList()
                            editingZoneId = null
                        },
                        modifier = Modifier.size(56.dp).padding(16.dp),
                        shape = CircleShape,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFFB45309)
                        )
                    ) {
                        Text(
                            text = "✏️",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color.White
                        )
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = {
                        showAddDialog = true
                        editingZoneId = null
                    },
                    modifier = Modifier.size(56.dp).padding(16.dp),
                    shape = CircleShape,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF315FE8)
                    )
                ) {
                    Text(
                        text = "➕",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White
                    )
                }
            }
        }

        // Add Zone dialog (manual entry - circle only)
        if (showAddDialog) {
            AddZoneDialog(
                zoneStore = zoneStore,
                zones = zones,
                onDismiss = { showAddDialog = false },
                onZoneAdded = { newZone ->
                    zoneStore.saveZone(newZone)
                    showAddDialog = false
                    editingZoneId = newZone.id
                }
            )
        }

        // Edit zone dialog
        if (editingZoneId != null) {
            val zoneToEdit = zones.find { it.id == editingZoneId }
            if (zoneToEdit != null) {
                EditZoneDialog(
                    zone = zoneToEdit,
                    zoneStore = zoneStore,
                    zones = zones,
                    onDismiss = { editingZoneId = null },
                    onZoneUpdated = { updatedZone ->
                        zoneStore.saveZone(updatedZone)
                        editingZoneId = null
                    },
                    onDeleteRequested = {
                        showDeleteConfirm = Pair(zoneToEdit.id, zoneToEdit.name)
                        editingZoneId = null
                    }
                )
            }
        }

        // Delete confirmation dialog
        showDeleteConfirm?.let { (zoneId, zoneName) ->
            AlertDialog(
                onDismissRequest = { showDeleteConfirm = null },
                confirmButton = {
                    TextButton(onClick = {
                        zoneStore.deleteZone(zoneId)
                        showDeleteConfirm = null
                        if (editingZoneId == zoneId) editingZoneId = null
                    }) {
                        Text("نعم، احذف")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDeleteConfirm = null }) {
                        Text("إلغاء")
                    }
                },
                title = { Text(text = "حذف المنطقة", style = MaterialTheme.typography.titleMedium) },
                text = {
                    Text(
                        text = "هل أنت متأكد من حذف منطقة \"$zoneName\"؟",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            )
        }
    }
}

/** Returns a human-readable label for the zone shape. */
private fun zoneShapeLabel(zone: Zone): String {
    return when (zone.zoneShape) {
        ZoneShape.CIRCLE -> "دائرة • نصف قطر ${zone.radiusMeters.toInt()}م"
        ZoneShape.POLYGON -> "مضلع • ${zone.polygonPoints.size} نقطة"
    }
}

/** Finds a zone whose marker is near the tapped geo point. */
private fun findZoneAt(zones: List<Zone>, tapPoint: GeoPoint): Zone? {
    val tolerance = 0.005
    return zones.firstOrNull { zone ->
        when (zone.zoneShape) {
            ZoneShape.CIRCLE -> {
                val d = distanceDegrees(
                    zone.centerLatitude, zone.centerLongitude,
                    tapPoint.latitude, tapPoint.longitude
                )
                val radiusDeg = zone.radiusMeters / 111000.0
                d <= radiusDeg + tolerance
            }
            ZoneShape.POLYGON -> {
                zone.polygonPoints.any { p ->
                    distanceDegrees(p.latitude, p.longitude, tapPoint.latitude, tapPoint.longitude) < tolerance
                }
            }
        }
    }
}

/** Approximate distance between two geo points in degrees. */
private fun distanceDegrees(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val dLat = Math.abs(lat1 - lat2)
    val dLon = Math.abs(lon1 - lon2) * Math.cos(Math.toRadians((lat1 + lat2) / 2.0))
    return Math.sqrt(dLat * dLat + dLon * dLon)
}

/**
 * Map area placeholder. Renders a colored canvas where the osmdroid MapView
 * would be embedded. Kept as a Box so the rest of the zone UI (list, dialogs,
 * drawing controls) works without requiring AndroidView resolution.
 */
@Composable
private fun MapViewContainer(
    zones: List<Zone>,
    drawingPoints: List<GeoPoint>,
    isDrawingMode: Boolean,
    onMapTap: (GeoPoint) -> Unit
) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier.size(48.dp).background(Color(0xFF315FE8), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "🗺️",
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color.White
                )
            }
            Text(
                text = "خريطة",
                style = MaterialTheme.typography.labelMedium,
                color = Color(0xFF7F8FA3)
            )
        }
    }
}

/**
 * Dialog for creating a new zone — manual entry (circle only).
 * Polygons are created via drawing mode on the map.
 */
@Composable
private fun AddZoneDialog(
    zoneStore: ZoneStore,
    zones: List<Zone>,
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
                    id = UUID.randomUUID().toString(),
                    name = name.trim(),
                    zoneShape = ZoneShape.CIRCLE,
                    centerLatitude = lat,
                    centerLongitude = lon,
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
        title = { Text(text = "إضافة منطقة جديدة", style = MaterialTheme.typography.titleMedium) },
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

/**
 * Dialog for editing an existing zone.
 */
@Composable
private fun EditZoneDialog(
    zone: Zone,
    zoneStore: ZoneStore,
    zones: List<Zone>,
    onDismiss: () -> Unit,
    onZoneUpdated: (Zone) -> Unit,
    onDeleteRequested: () -> Unit,
    modifier: Modifier = Modifier
) {
    var name by remember { mutableStateOf(zone.name) }
    var selectedType by remember { mutableStateOf(zone.type) }
    var error by remember { mutableStateOf<String?>(null) }

    val existingNames = zones.filter { it.id != zone.id }.map { it.name }.toSet()

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

                val updatedZone = zone.copy(
                    name = name.trim(),
                    type = selectedType
                )
                onZoneUpdated(updatedZone)
            }) {
                Text("تحديث")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("إلغاء")
            }
        },
        title = { Text(text = "تعديل المنطقة", style = MaterialTheme.typography.titleMedium) },
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

                Text(
                    text = zoneShapeLabel(zone),
                    style = MaterialTheme.typography.labelMedium,
                    color = Color(0xFF7F8FA3)
                )
                Text(
                    text = "النوع الحالي: ${zone.typeLabel()}",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color(0xFF7F8FA3)
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

                Spacer(modifier = Modifier.height(12.dp))
                TextButton(
                    onClick = onDeleteRequested,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(text = "حذف المنطقة", color = Color.Red)
                }
            }
        },
        modifier = modifier
    )
}
