@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.smartcaptain.map

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Looper
import android.preference.PreferenceManager
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.AddCircle
import androidx.compose.material.icons.outlined.Architecture
import androidx.compose.material.icons.outlined.Brush
import androidx.compose.material.icons.outlined.DeleteSweep
import androidx.compose.material.icons.outlined.Gesture
import androidx.compose.material.icons.outlined.Layers
import androidx.compose.material.icons.outlined.MyLocation
import androidx.compose.material.icons.outlined.Polyline
import androidx.compose.material.icons.outlined.Redo
import androidx.compose.material.icons.outlined.SquareFoot
import androidx.compose.material.icons.outlined.Undo
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.smartcaptain.zone.BrushStroke
import com.smartcaptain.zone.LatLng
import com.smartcaptain.zone.Zone
import com.smartcaptain.zone.ZonePolygon
import com.smartcaptain.zone.ZoneShape
import com.smartcaptain.zone.ZoneStore
import com.smartcaptain.zone.ZoneType
import java.util.UUID
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.log2
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlinx.coroutines.launch
import org.osmdroid.config.Configuration
import org.osmdroid.events.MapEventsReceiver
import org.osmdroid.util.BoundingBox
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.MapEventsOverlay
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Overlay
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline

/**
 * Zones screen: a full-bleed OpenStreetMap with a draggable three-state sheet.
 *
 * Two drawing modes are supported:
 *  - polygon: tap vertices, undo/clear/save (existing behaviour),
 *  - freehand brush: real-metre brush, paint/erase/undo/redo/clear/save.
 *
 * Both modes save through [ZoneStore], so circle zones remain fully backwards
 * compatible.
 */
@Composable
fun MapScreen(
    zoneStore: ZoneStore,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val scope = rememberCoroutineScope()

    var zones by remember { mutableStateOf(zoneStore.getAllZones()) }
    var mapView by remember { mutableStateOf<MapView?>(null) }
    var mode by remember { mutableStateOf(MapMode.IDLE) }
    var selectedZoneId by remember { mutableStateOf<String?>(null) }
    var infoZoneId by remember { mutableStateOf<String?>(null) }
    var focusZoneId by remember { mutableStateOf<String?>(null) }
    var focusNonce by remember { mutableStateOf(0L) }
    var showAddMenu by remember { mutableStateOf(false) }
    var showCircleDialog by remember { mutableStateOf(false) }
    var editZoneId by remember { mutableStateOf<String?>(null) }
    var deleteTarget by remember { mutableStateOf<Zone?>(null) }
    var pendingSave by remember { mutableStateOf<PendingSave?>(null) }

    // Polygon drawing / vertex editing.
    var drawingPoints by remember { mutableStateOf<List<LatLng>>(emptyList()) }
    var geometryZoneId by remember { mutableStateOf<String?>(null) }
    var geometryPoints by remember { mutableStateOf<List<LatLng>>(emptyList()) }
    var selectedVertexIndex by remember { mutableStateOf<Int?>(null) }
    var geometryError by remember { mutableStateOf<String?>(null) }

    // Brush drawing.
    val brush = remember { BrushSession() }
    val brushPreview = remember { BrushPreviewOverlay(brush) }
    var brushEditingZoneId by remember { mutableStateOf<String?>(null) }
    var brushError by remember { mutableStateOf<String?>(null) }

    val editing = mode != MapMode.IDLE
    val brushResult = remember(brush.strokes, mode) {
        if (mode == MapMode.BRUSH) BrushGeometry.build(brush.strokes)
        else BrushBuildResult.EMPTY
    }

    fun refresh() {
        zones = zoneStore.getAllZones()
    }

    fun focus(zone: Zone) {
        selectedZoneId = zone.id
        infoZoneId = zone.id
        focusZoneId = zone.id
        focusNonce += 1
    }

    fun resetDrawingState() {
        drawingPoints = emptyList()
        geometryZoneId = null
        geometryPoints = emptyList()
        selectedVertexIndex = null
        geometryError = null
        brushEditingZoneId = null
        brushError = null
        brush.cancel()
    }

    fun finishModes() {
        mode = MapMode.IDLE
        resetDrawingState()
    }

    fun startPolygonDrawing() {
        resetDrawingState()
        mode = MapMode.POLYGON
        showAddMenu = false
        selectedZoneId = null
        infoZoneId = null
    }

    fun startBrushDrawing(existing: Zone? = null) {
        resetDrawingState()
        mode = MapMode.BRUSH
        showAddMenu = false
        infoZoneId = null
        if (existing != null) {
            selectedZoneId = existing.id
            brushEditingZoneId = existing.id
            if (existing.brushStrokes.isNotEmpty()) {
                brush.load(existing.brushStrokes, existing.brushStrokes.last().radiusMeters)
            } else {
                brush.reset()
            }
        } else {
            selectedZoneId = null
            brush.reset()
        }
    }

    fun startGeometryEditing(zone: Zone) {
        resetDrawingState()
        mode = MapMode.GEOMETRY
        geometryZoneId = zone.id
        geometryPoints = zone.polygonPoints
        selectedZoneId = zone.id
        infoZoneId = null
        editZoneId = null
    }

    fun savePending(pending: PendingSave, name: String, type: ZoneType) {
        val primary = pending.polygons.firstOrNull() ?: return
        val existing = pending.existingZone
        val color = if (existing != null && existing.type == type) {
            existing.color
        } else {
            ZoneDesign.colorFor(type).toArgb()
        }
        val zone = Zone(
            id = existing?.id ?: UUID.randomUUID().toString(),
            name = name.trim(),
            zoneShape = ZoneShape.POLYGON,
            centerLatitude = primary.exterior.sumOf { it.latitude } / primary.exterior.size,
            centerLongitude = primary.exterior.sumOf { it.longitude } / primary.exterior.size,
            polygonPoints = primary.exterior,
            type = type,
            color = color,
            createdAt = existing?.createdAt ?: System.currentTimeMillis(),
            polygonHoles = primary.holes,
            extraPolygons = pending.polygons.drop(1),
            brushStrokes = pending.strokes,
            isActive = existing?.isActive ?: true
        )
        zoneStore.saveZone(zone)
        pendingSave = null
        finishModes()
        refresh()
        focus(zone)
    }

    fun toggleZone(zone: Zone, active: Boolean) {
        zoneStore.saveZone(zone.copy(isActive = active))
        refresh()
    }

    fun deleteZone(zone: Zone) {
        zoneStore.deleteZone(zone.id)
        deleteTarget = null
        if (selectedZoneId == zone.id) selectedZoneId = null
        if (infoZoneId == zone.id) infoZoneId = null
        if (editZoneId == zone.id) editZoneId = null
        refresh()
    }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            locateNow(context, mapView)
        } else {
            Toast.makeText(context, "لم يتم منح إذن الموقع", Toast.LENGTH_SHORT).show()
        }
    }

    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        BoxWithConstraints(modifier = modifier.fillMaxSize()) {
            val heightPx = constraints.maxHeight.toFloat().coerceAtLeast(1f)
            val sheetHeightPx = heightPx * 0.94f
            val collapsedOffset = heightPx * 0.56f
            val halfOffset = heightPx * 0.39f
            val fullOffset = heightPx * 0.02f
            val hiddenOffset = sheetHeightPx
            val anchors = remember(heightPx) {
                listOf(collapsedOffset, halfOffset, fullOffset)
            }
            val sheetOffset = remember { Animatable(collapsedOffset) }
            val sheetHeightDp = with(density) { sheetHeightPx.toDp() }
            val sheetExpanded by remember {
                derivedStateOf { sheetOffset.value < halfOffset }
            }
            val sheetMostlyVisible by remember {
                derivedStateOf {
                    (sheetHeightPx - sheetOffset.value) < heightPx * 0.6f
                }
            }
            val fabVisible by remember {
                derivedStateOf {
                    (sheetHeightPx - sheetOffset.value) < heightPx * 0.7f
                }
            }
            val safeGapPx = with(density) { 16.dp.toPx() }

            LaunchedEffect(editing) {
                sheetOffset.animateTo(
                    targetValue = if (editing) hiddenOffset else collapsedOffset,
                    animationSpec = tween(durationMillis = 260)
                )
            }

            fun snapSheet() {
                val target = anchors.minByOrNull { abs(it - sheetOffset.value) }
                    ?: collapsedOffset
                scope.launch {
                    sheetOffset.animateTo(target, animationSpec = tween(260))
                }
            }

            fun toggleSheet() {
                val target = if (sheetOffset.value > collapsedOffset + 24f) {
                    collapsedOffset
                } else {
                    halfOffset
                }
                scope.launch {
                    sheetOffset.animateTo(target, animationSpec = tween(260))
                }
            }

            fun requestLocation() {
                val fineGranted = context.checkSelfPermission(
                    Manifest.permission.ACCESS_FINE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED
                if (fineGranted) {
                    locateNow(context, mapView)
                } else {
                    locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                }
            }

            val focusZone = zones.firstOrNull { it.id == focusZoneId }
            val infoZone = zones.firstOrNull { it.id == infoZoneId }
            val selectedZone = zones.firstOrNull { it.id == selectedZoneId }

            OsmMapView(
                zones = zones,
                selectedZoneId = selectedZoneId,
                hiddenZoneId = when (mode) {
                    MapMode.GEOMETRY -> geometryZoneId
                    MapMode.BRUSH -> brushEditingZoneId
                    else -> null
                },
                drawingPoints = drawingPoints,
                showPolygonPreview = mode == MapMode.POLYGON,
                geometryEditPoints = geometryPoints,
                showGeometryPreview = mode == MapMode.GEOMETRY,
                selectedVertexIndex = selectedVertexIndex,
                brushResult = brushResult.takeIf { mode == MapMode.BRUSH },
                previewOverlay = brushPreview,
                focusZone = focusZone,
                focusNonce = focusNonce,
                onMapReady = { mapView = it },
                onMapTap = { point ->
                    when (mode) {
                        MapMode.POLYGON -> {
                            if (point.isValid()) drawingPoints = drawingPoints + point
                        }

                        MapMode.GEOMETRY -> {
                            val vertex = PolygonDrawing.findVertexIndex(geometryPoints, point)
                            if (vertex != null) {
                                selectedVertexIndex = vertex
                                geometryError = null
                            } else {
                                val selected = selectedVertexIndex
                                if (selected != null && selected in geometryPoints.indices) {
                                    geometryPoints = PolygonDrawing.moveVertex(
                                        geometryPoints,
                                        selected,
                                        point
                                    )
                                    geometryError = null
                                }
                            }
                        }

                        MapMode.IDLE -> {
                            val tapped = zones.asReversed().firstOrNull { zone ->
                                BrushGeometry.contains(zone, point)
                            }
                            infoZoneId = tapped?.id
                            selectedZoneId = tapped?.id
                        }

                        MapMode.BRUSH -> Unit
                    }
                },
                modifier = Modifier.fillMaxSize()
            )

            if (mode == MapMode.BRUSH) {
                BrushCaptureLayer(
                    mapView = mapView,
                    session = brush,
                    modifier = Modifier.fillMaxSize()
                )
            }

            ZonesTopBar(
                zoneCount = zones.size,
                activeCount = zones.count { it.isActive },
                modifier = Modifier.align(Alignment.TopCenter)
            )

            if (infoZone != null && !editing && sheetMostlyVisible) {
                ZoneInfoCard(
                    zone = infoZone,
                    modifier = Modifier
                        // In RTL, TopEnd is the physical left; the info card
                        // lives opposite the map controls.
                        .align(Alignment.TopEnd)
                        .padding(top = 88.dp, start = 16.dp)
                        .widthIn(max = 330.dp),
                    onClose = { infoZoneId = null },
                    onLocate = { focus(infoZone) },
                    onEdit = { editZoneId = infoZone.id },
                    onDelete = { deleteTarget = infoZone }
                )
            }

            if (!editing) {
                MapControls(
                    modifier = Modifier
                        // In RTL, TopStart is the physical right edge, matching
                        // the familiar map-control placement.
                        .align(Alignment.TopStart)
                        .padding(top = 88.dp, end = 12.dp),
                    onZoomIn = {
                        mapView?.let { view ->
                            view.controller.setZoom(
                                (view.zoomLevelDouble + 1.0).coerceAtMost(20.0)
                            )
                        }
                    },
                    onZoomOut = {
                        mapView?.let { view ->
                            view.controller.setZoom(
                                (view.zoomLevelDouble - 1.0).coerceAtLeast(3.0)
                            )
                        }
                    },
                    onMyLocation = ::requestLocation
                )
            }

            if (infoZone == null && !editing && zones.isNotEmpty()) {
                // A subtle hint that zones are tappable, replacing the old
                // empty tooltip bubble that used to float above polygons.
                AssistChip(
                    onClick = { selectedZone?.let(::focus) },
                    label = { Text("اضغط على منطقة لعرض تفاصيلها", fontSize = 11.sp) },
                    leadingIcon = {
                        Icon(
                            Icons.Outlined.Layers,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    },
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .offset {
                            IntOffset(
                                safeGapPx.roundToInt(),
                                -(sheetHeightPx - sheetOffset.value + safeGapPx).roundToInt()
                            )
                        }
                )
            }

            Surface(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .height(sheetHeightDp)
                    .offset { IntOffset(0, sheetOffset.value.roundToInt()) },
                shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
                color = ZoneDesign.Surface,
                shadowElevation = 18.dp
            ) {
                Column(modifier = Modifier.fillMaxSize()) {
                    SheetHeader(
                        zoneCount = zones.size,
                        activeCount = zones.count { it.isActive },
                        expanded = sheetExpanded,
                        onToggle = ::toggleSheet,
                        onDrag = { delta ->
                            scope.launch {
                                sheetOffset.snapTo(
                                    (sheetOffset.value + delta)
                                        .coerceIn(0f, hiddenOffset)
                                )
                            }
                        },
                        onDragEnd = ::snapSheet
                    )
                    HorizontalDivider(color = ZoneDesign.Outline)
                    if (zones.isEmpty()) {
                        EmptyZones(
                            onAdd = {
                                showAddMenu = true
                                scope.launch {
                                    sheetOffset.animateTo(
                                        collapsedOffset,
                                        animationSpec = tween(260)
                                    )
                                }
                            }
                        )
                    } else {
                        LazyColumn(
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(
                                start = 16.dp,
                                end = 16.dp,
                                top = 12.dp,
                                bottom = 28.dp
                            ),
                            verticalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            items(zones, key = { it.id }) { zone ->
                                ZoneCard(
                                    zone = zone,
                                    selected = zone.id == selectedZoneId,
                                    onOpen = {
                                        focus(zone)
                                        if (sheetMostlyVisible) {
                                            scope.launch {
                                                sheetOffset.animateTo(
                                                    collapsedOffset,
                                                    animationSpec = tween(260)
                                                )
                                            }
                                        }
                                    },
                                    onToggle = { active -> toggleZone(zone, active) },
                                    onEdit = { editZoneId = zone.id },
                                    onLocate = { focus(zone) },
                                    onDelete = { deleteTarget = zone }
                                )
                            }
                        }
                    }
                }
            }

            if (!editing && fabVisible) {
                AddZoneFab(
                    expanded = showAddMenu,
                    onToggle = { showAddMenu = !showAddMenu },
                    onPolygon = ::startPolygonDrawing,
                    onBrush = { startBrushDrawing() },
                    onCircle = {
                        showAddMenu = false
                        showCircleDialog = true
                    },
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .offset {
                            IntOffset(
                                -safeGapPx.roundToInt(),
                                -(sheetHeightPx - sheetOffset.value + safeGapPx).roundToInt()
                            )
                        }
                )
            }

            when (mode) {
                MapMode.POLYGON -> PolygonToolbar(
                    points = drawingPoints,
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth()
                        .padding(16.dp),
                    onUndo = {
                        drawingPoints = PolygonDrawing.undoLastPoint(drawingPoints)
                    },
                    onClear = { drawingPoints = emptyList() },
                    onCancel = { finishModes() },
                    onSave = {
                        if (PolygonDrawing.canSavePolygon(drawingPoints)) {
                            pendingSave = PendingSave(
                                existingZone = null,
                                polygons = listOf(ZonePolygon(drawingPoints)),
                                strokes = emptyList(),
                                areaSqMeters = BrushGeometry.ringAreaSqMeters(drawingPoints),
                                pointCount = drawingPoints.size,
                                defaultType = ZoneType.DANGER
                            )
                        }
                    }
                )

                MapMode.GEOMETRY -> GeometryToolbar(
                    points = geometryPoints,
                    selectedVertexIndex = selectedVertexIndex,
                    error = geometryError,
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth()
                        .padding(16.dp),
                    onDeleteVertex = {
                        val selected = selectedVertexIndex
                        if (selected != null) {
                            val updated = PolygonDrawing.deleteVertex(geometryPoints, selected)
                            geometryPoints = updated
                            selectedVertexIndex = null
                            geometryError = if (PolygonDrawing.canSavePolygon(updated)) {
                                null
                            } else {
                                "يجب أن يبقى 3 رؤوس صالحة على الأقل للحفظ"
                            }
                        }
                    },
                    onSave = {
                        val zone = zones.firstOrNull { it.id == geometryZoneId }
                        if (zone == null) {
                            finishModes()
                        } else if (!PolygonDrawing.canSavePolygon(geometryPoints)) {
                            geometryError = "يجب تحديد 3 رؤوس صالحة على الأقل قبل الحفظ"
                        } else {
                            zoneStore.saveZone(zone.copy(polygonPoints = geometryPoints))
                            finishModes()
                            refresh()
                            focus(zone)
                        }
                    },
                    onCancel = { finishModes() }
                )

                MapMode.BRUSH -> BrushToolbar(
                    session = brush,
                    result = brushResult,
                    error = brushError,
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth()
                        .padding(16.dp),
                    onDone = {
                        if (brushResult.isEmpty()) {
                            brushError = "لا توجد مساحة مرسومة بعد"
                        } else {
                            brushError = null
                            val existing = zones.firstOrNull { it.id == brushEditingZoneId }
                            pendingSave = PendingSave(
                                existingZone = existing,
                                polygons = brushResult.polygons,
                                strokes = brush.strokes,
                                areaSqMeters = brushResult.areaSqMeters,
                                pointCount = brushResult.pointCount,
                                defaultType = existing?.type ?: ZoneType.DANGER
                            )
                        }
                    },
                    onCancel = { finishModes() }
                )

                MapMode.IDLE -> Unit
            }
        }
    }

    pendingSave?.let { pending ->
        SaveZoneSheet(
            pending = pending,
            zones = zones,
            onDismiss = { pendingSave = null },
            onSave = { name, type -> savePending(pending, name, type) }
        )
    }

    editZoneId?.let { id ->
        val zone = zones.firstOrNull { it.id == id }
        if (zone != null) {
            EditZoneSheet(
                zone = zone,
                zones = zones,
                onDismiss = { editZoneId = null },
                onSave = { name, type ->
                    val color = if (type == zone.type) {
                        zone.color
                    } else {
                        ZoneDesign.colorFor(type).toArgb()
                    }
                    zoneStore.saveZone(zone.copy(name = name.trim(), type = type, color = color))
                    editZoneId = null
                    refresh()
                },
                onEditShape = {
                    editZoneId = null
                    if (zone.isBrushZone()) startBrushDrawing(zone)
                    else startGeometryEditing(zone)
                },
                onDelete = {
                    editZoneId = null
                    deleteTarget = zone
                }
            )
        } else {
            editZoneId = null
        }
    }

    if (showCircleDialog) {
        AddCircleDialog(
            zones = zones,
            initialLatitude = mapView?.mapCenter?.latitude,
            initialLongitude = mapView?.mapCenter?.longitude,
            onDismiss = { showCircleDialog = false },
            onSave = { zone ->
                zoneStore.saveZone(zone)
                showCircleDialog = false
                refresh()
                focus(zone)
            }
        )
    }

    deleteTarget?.let { zone ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text("حذف المنطقة") },
            text = { Text("هل أنت متأكد من حذف \"${zone.name}\"؟ لا يمكن التراجع عن هذا الإجراء.") },
            confirmButton = {
                TextButton(onClick = { deleteZone(zone) }) {
                    Text("نعم، احذف", color = ZoneDesign.Danger)
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteTarget = null }) {
                    Text("إلغاء")
                }
            }
        )
    }
}

// =====================================================================
// State models
// =====================================================================

private enum class MapMode { IDLE, POLYGON, BRUSH, GEOMETRY }

private data class PendingSave(
    val existingZone: Zone?,
    val polygons: List<ZonePolygon>,
    val strokes: List<BrushStroke>,
    val areaSqMeters: Double,
    val pointCount: Int,
    val defaultType: ZoneType
)

/**
 * Mutable brush state. The active path is intentionally not a Compose state:
 * it changes on every touch move and is drawn directly by [BrushPreviewOverlay],
 * while committed strokes (which trigger geometry rebuilds) are observable.
 */
private class BrushSession {
    var strokes by mutableStateOf<List<BrushStroke>>(emptyList())
    var redo by mutableStateOf<List<BrushStroke>>(emptyList())
    var radiusMeters by mutableStateOf(BrushGeometry.DEFAULT_RADIUS_METERS.toFloat())
    var tool by mutableStateOf(BrushTool.BRUSH)

    val activePoints = mutableListOf<LatLng>()
    var activeErase = false
    var cursor: LatLng? = null

    fun begin(point: LatLng, erase: Boolean) {
        activePoints.clear()
        activePoints.add(point)
        activeErase = erase
        cursor = point
    }

    fun append(point: LatLng) {
        activePoints.add(point)
        cursor = point
    }

    fun finish() {
        if (activePoints.isEmpty()) return
        strokes = strokes + BrushStroke(
            points = activePoints.toList(),
            radiusMeters = radiusMeters.toDouble(),
            erase = activeErase
        )
        redo = emptyList()
        activePoints.clear()
    }

    fun cancel() {
        activePoints.clear()
        cursor = null
    }

    fun undoLast() {
        if (strokes.isEmpty()) return
        redo = redo + strokes.last()
        strokes = strokes.dropLast(1)
    }

    fun redoLast() {
        if (redo.isEmpty()) return
        strokes = strokes + redo.last()
        redo = redo.dropLast(1)
    }

    fun clearAll() {
        strokes = emptyList()
        redo = emptyList()
        activePoints.clear()
        cursor = null
    }

    fun reset() {
        clearAll()
        radiusMeters = BrushGeometry.DEFAULT_RADIUS_METERS.toFloat()
        tool = BrushTool.BRUSH
    }

    fun load(loaded: List<BrushStroke>, radiusMeters: Double) {
        strokes = loaded
        redo = emptyList()
        activePoints.clear()
        cursor = null
        tool = BrushTool.BRUSH
        this.radiusMeters = radiusMeters.toFloat()
            .coerceIn(
                BrushGeometry.MIN_RADIUS_METERS.toFloat(),
                BrushGeometry.MAX_RADIUS_METERS.toFloat()
            )
    }
}

// =====================================================================
// Map
// =====================================================================

@Composable
private fun OsmMapView(
    zones: List<Zone>,
    selectedZoneId: String?,
    hiddenZoneId: String?,
    drawingPoints: List<LatLng>,
    showPolygonPreview: Boolean,
    geometryEditPoints: List<LatLng>,
    showGeometryPreview: Boolean,
    selectedVertexIndex: Int?,
    brushResult: BrushBuildResult?,
    previewOverlay: BrushPreviewOverlay,
    focusZone: Zone?,
    focusNonce: Long,
    onMapReady: (MapView) -> Unit,
    onMapTap: (LatLng) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val mapView = remember { MapView(context) }
    var ready by remember { mutableStateOf(false) }
    val latestFocusZone by rememberUpdatedState(focusZone)

    LaunchedEffect(Unit) {
        Configuration.getInstance().load(
            context,
            PreferenceManager.getDefaultSharedPreferences(context)
        )
        Configuration.getInstance().userAgentValue = context.packageName
    }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            mapView.onDetach()
        }
    }

    LaunchedEffect(focusNonce, ready) {
        if (!ready) return@LaunchedEffect
        val zone = latestFocusZone ?: return@LaunchedEffect
        mapView.zoomToBoundingBox(zoneBounds(zone), true, 160)
    }

    AndroidView(
        modifier = modifier,
        factory = {
            mapView.setMultiTouchControls(true)
            mapView.setTilesScaledToDpi(true)
            mapView.minZoomLevel = 3.0
            mapView.maxZoomLevel = 20.0
            mapView.controller.setZoom(14.0)
            mapView.controller.setCenter(GeoPoint(24.7136, 46.6753))
            mapView.setTileSource(
                org.osmdroid.tileprovider.tilesource.TileSourceFactory.MAPNIK
            )

            val eventsReceiver = object : MapEventsReceiver {
                override fun singleTapConfirmedHelper(p: GeoPoint?): Boolean {
                    p?.let { onMapTap(LatLng(it.latitude, it.longitude)) }
                    return true
                }

                override fun longPressHelper(p: GeoPoint?): Boolean = false
            }
            mapView.overlays.add(MapEventsOverlay(eventsReceiver))
            mapView.overlays.add(previewOverlay)
            onMapReady(mapView)
            ready = true
            mapView
        },
        update = { view ->
            view.overlays.removeAll { overlay ->
                overlay !== previewOverlay && overlay !is MapEventsOverlay
            }

            val density = context.resources.displayMetrics.density
            val normalDotPx = (14 * density).toInt()
            val selectedDotPx = (20 * density).toInt()

            for (zone in zones) {
                if (zone.id == hiddenZoneId) continue
                addZoneOverlays(
                    mapView = view,
                    zone = zone,
                    selected = zone.id == selectedZoneId,
                    density = density
                )
            }

            if (showGeometryPreview && geometryEditPoints.isNotEmpty()) {
                val orange = android.graphics.Color.parseColor("#B45309")
                val geoPoints = geometryEditPoints.map { GeoPoint(it.latitude, it.longitude) }
                if (geometryEditPoints.size >= 3) {
                    val preview = Polygon(view)
                    preview.points = geoPoints
                    preview.fillPaint.color = android.graphics.Color.argb(
                        55,
                        android.graphics.Color.red(orange),
                        android.graphics.Color.green(orange),
                        android.graphics.Color.blue(orange)
                    )
                    preview.outlinePaint.color = orange
                    preview.outlinePaint.strokeWidth = 4f
                    view.overlays.add(preview)
                } else if (geoPoints.size >= 2) {
                    val line = Polyline(view)
                    line.setPoints(geoPoints)
                    line.outlinePaint.color = orange
                    line.outlinePaint.strokeWidth = 4f
                    view.overlays.add(line)
                }
                addVertexMarkers(
                    view = view,
                    points = geometryEditPoints,
                    selected = selectedVertexIndex,
                    normalSizePx = normalDotPx,
                    selectedSizePx = selectedDotPx,
                    normalColor = orange
                )
            }

            if (showPolygonPreview && drawingPoints.isNotEmpty()) {
                val blue = android.graphics.Color.parseColor("#315FE8")
                val geoPoints = drawingPoints.map { GeoPoint(it.latitude, it.longitude) }
                if (geoPoints.size >= 2) {
                    val line = Polyline(view)
                    line.setPoints(geoPoints)
                    line.outlinePaint.color = blue
                    line.outlinePaint.strokeWidth = 4f
                    view.overlays.add(line)
                }
                addVertexMarkers(
                    view = view,
                    points = drawingPoints,
                    selected = null,
                    normalSizePx = normalDotPx,
                    selectedSizePx = selectedDotPx,
                    normalColor = blue
                )
            }

            if (brushResult != null) {
                val red = android.graphics.Color.parseColor("#DC2626")
                for (part in brushResult.polygons) {
                    if (part.exterior.size < 3) continue
                    val polygon = Polygon(view)
                    polygon.points = part.exterior.map { GeoPoint(it.latitude, it.longitude) }
                    if (part.holes.isNotEmpty()) {
                        polygon.setHoles(
                            part.holes.map { hole ->
                                hole.map { GeoPoint(it.latitude, it.longitude) }
                            }
                        )
                    }
                    polygon.fillPaint.color = android.graphics.Color.argb(70, 220, 38, 38)
                    polygon.outlinePaint.color = red
                    polygon.outlinePaint.strokeWidth = 3f
                    view.overlays.add(polygon)
                }
            }

            // osmdroid dispatches taps from the top overlay down. Some
            // overlays (notably Polygon) consume a single tap to show their
            // own info bubble, which used to stop taps from reaching the
            // polygon-drawing handler whenever the user tapped on top of an
            // existing zone. Keeping the events overlay last means it always
            // receives the tap first; the preview overlay is drawn above the
            // zones so the brush cursor stays visible.
            val tapOverlays = view.overlays.filterIsInstance<MapEventsOverlay>()
            view.overlays.removeAll(tapOverlays)
            view.overlays.remove(previewOverlay)
            view.overlays.add(previewOverlay)
            view.overlays.addAll(tapOverlays)

            view.invalidate()
        }
    )
}

private fun addZoneOverlays(
    mapView: MapView,
    zone: Zone,
    selected: Boolean,
    density: Float
) {
    val active = zone.isActive
    val fillAlpha = when {
        !active -> 18
        selected -> 115
        else -> 60
    }
    val outlineWidth = if (selected) 6f else 3f

    when (zone.zoneShape) {
        ZoneShape.CIRCLE -> {
            val polygon = Polygon(mapView)
            polygon.points = circlePoints(zone)
            val color = if (active) zone.color else android.graphics.Color.GRAY
            polygon.fillPaint.color = android.graphics.Color.argb(
                fillAlpha,
                android.graphics.Color.red(color),
                android.graphics.Color.green(color),
                android.graphics.Color.blue(color)
            )
            polygon.outlinePaint.color = color
            polygon.outlinePaint.strokeWidth = outlineWidth
            mapView.overlays.add(polygon)
        }

        ZoneShape.POLYGON -> {
            for (part in zone.polygons()) {
                if (part.exterior.size < 3) continue
                val polygon = Polygon(mapView)
                polygon.points = part.exterior.map { GeoPoint(it.latitude, it.longitude) }
                if (part.holes.isNotEmpty()) {
                    polygon.setHoles(
                        part.holes.map { hole ->
                            hole.map { GeoPoint(it.latitude, it.longitude) }
                        }
                    )
                }
                val color = if (active) zone.color else android.graphics.Color.GRAY
                polygon.fillPaint.color = android.graphics.Color.argb(
                    fillAlpha,
                    android.graphics.Color.red(color),
                    android.graphics.Color.green(color),
                    android.graphics.Color.blue(color)
                )
                polygon.outlinePaint.color = color
                polygon.outlinePaint.strokeWidth = outlineWidth
                mapView.overlays.add(polygon)
            }
        }
    }
}

private fun addVertexMarkers(
    view: MapView,
    points: List<LatLng>,
    selected: Int?,
    normalSizePx: Int,
    selectedSizePx: Int,
    normalColor: Int
) {
    val density = view.resources.displayMetrics.density
    fun dotIcon(color: Int, sizePx: Int): android.graphics.drawable.Drawable =
        android.graphics.drawable.GradientDrawable().apply {
            shape = android.graphics.drawable.GradientDrawable.OVAL
            setColor(color)
            setStroke((2 * density).toInt(), android.graphics.Color.WHITE)
            setSize(sizePx, sizePx)
        }

    points.forEachIndexed { index, point ->
        val marker = Marker(view)
        marker.position = GeoPoint(point.latitude, point.longitude)
        marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
        marker.icon = if (selected == index) {
            dotIcon(android.graphics.Color.parseColor("#DC2626"), selectedSizePx)
        } else {
            dotIcon(normalColor, normalSizePx)
        }
        marker.setOnMarkerClickListener { _, _ -> false }
        view.overlays.add(marker)
    }
}

private fun circlePoints(zone: Zone): List<GeoPoint> {
    val points = ArrayList<GeoPoint>(73)
    val latScale = cos(Math.toRadians(zone.centerLatitude)).coerceAtLeast(0.01)
    for (i in 0..72) {
        val angle = Math.toRadians(i * 5.0)
        val latitude = zone.centerLatitude +
            (zone.radiusMeters / 111_320.0) * cos(angle)
        val longitude = zone.centerLongitude +
            (zone.radiusMeters / (111_320.0 * latScale)) * sin(angle)
        points.add(GeoPoint(latitude, longitude))
    }
    return points
}

private fun zoneBounds(zone: Zone): BoundingBox {
    var north = -90.0
    var south = 90.0
    var east = -180.0
    var west = 180.0

    fun include(point: LatLng) {
        north = maxOf(north, point.latitude)
        south = minOf(south, point.latitude)
        east = maxOf(east, point.longitude)
        west = minOf(west, point.longitude)
    }

    when (zone.zoneShape) {
        ZoneShape.CIRCLE -> {
            val latDelta = zone.radiusMeters / 111_320.0
            val lonDelta = zone.radiusMeters /
                (111_320.0 * cos(Math.toRadians(zone.centerLatitude)).coerceAtLeast(0.01))
            include(LatLng(zone.centerLatitude + latDelta, zone.centerLongitude + lonDelta))
            include(LatLng(zone.centerLatitude - latDelta, zone.centerLongitude - lonDelta))
        }

        ZoneShape.POLYGON -> zone.polygons().forEach { part ->
            part.exterior.forEach(::include)
        }
    }

    if (north < south || east < west) {
        return BoundingBox(24.72, 46.69, 24.70, 46.66)
    }
    return BoundingBox(north, east, south, west)
}

// =====================================================================
// Brush touch capture + preview
// =====================================================================

@Composable
private fun BrushCaptureLayer(
    mapView: MapView?,
    session: BrushSession,
    modifier: Modifier = Modifier
) {
    val currentMap by rememberUpdatedState(mapView)
    val currentSession by rememberUpdatedState(session)
    val radius by rememberUpdatedState(session.radiusMeters)
    val tool by rememberUpdatedState(session.tool)

    Box(
        modifier = modifier.pointerInput(currentMap, radius, tool) {
            val map = currentMap ?: return@pointerInput
            awaitEachGesture {
                val down = awaitFirstDown(requireUnconsumed = false)
                val start = map.geoAt(down.position) ?: return@awaitEachGesture
                down.consume()
                val localSession = currentSession
                localSession.begin(start, tool == BrushTool.ERASER)
                map.invalidate()

                var pinching = false
                var previousCentroid: Offset? = null
                var previousDistance = 0f
                var lastPoint = start

                while (true) {
                    val event = awaitPointerEvent()
                    val pressed = event.changes.filter { it.pressed }
                    if (pressed.isEmpty()) break

                    if (pressed.size >= 2) {
                        if (!pinching) {
                            localSession.cancel()
                            pinching = true
                            previousCentroid = null
                            previousDistance = 0f
                        }
                        val first = pressed[0].position
                        val second = pressed[1].position
                        val centroid = (first + second) / 2f
                        val distance = (second - first).getDistance()
                        if (previousDistance > 0f && distance > 0f) {
                            val delta = log2((distance / previousDistance).toDouble())
                            map.controller.setZoom(
                                (map.zoomLevelDouble + delta).coerceIn(3.0, 20.0)
                            )
                        }
                        previousCentroid?.let { previous ->
                            val dx = centroid.x - previous.x
                            val dy = centroid.y - previous.y
                            val projection = map.projection
                            val newCenter = projection.fromPixels(
                                (map.width / 2f - dx).roundToInt(),
                                (map.height / 2f - dy).roundToInt()
                            )
                            if (newCenter != null) {
                                map.controller.setCenter(newCenter)
                            }
                        }
                        previousCentroid = centroid
                        previousDistance = distance
                        event.changes.forEach { it.consume() }
                        map.invalidate()
                        continue
                    }

                    if (!pinching && pressed.size == 1) {
                        val change = pressed.first()
                        val point = map.geoAt(change.position)
                        if (
                            point != null &&
                            localSession.activePoints.size < 6_000 &&
                            BrushGeometry.shouldAppendPoint(
                                lastPoint,
                                point,
                                localSession.radiusMeters.toDouble()
                            )
                        ) {
                            localSession.append(point)
                            lastPoint = point
                            map.invalidate()
                        }
                        change.consume()
                    }
                }

                if (!pinching) {
                    localSession.finish()
                } else {
                    localSession.cancel()
                }
                map.invalidate()
            }
        }
    )
}

private fun MapView.geoAt(offset: Offset): LatLng? = try {
    val point = projection.fromPixels(offset.x.roundToInt(), offset.y.roundToInt())
    if (point == null) {
        null
    } else {
        LatLng(point.latitude, point.longitude).takeIf { it.isValid() }
    }
} catch (_: Exception) {
    null
}

private class BrushPreviewOverlay(
    private val session: BrushSession
) : Overlay() {

    private val pathPaint = android.graphics.Paint().apply {
        isAntiAlias = true
        style = android.graphics.Paint.Style.STROKE
        strokeCap = android.graphics.Paint.Cap.ROUND
        strokeJoin = android.graphics.Paint.Join.ROUND
    }

    private val cursorFill = android.graphics.Paint().apply {
        isAntiAlias = true
        style = android.graphics.Paint.Style.FILL
    }

    private val cursorStroke = android.graphics.Paint().apply {
        isAntiAlias = true
        style = android.graphics.Paint.Style.STROKE
        strokeWidth = 3f
        color = android.graphics.Color.WHITE
    }

    override fun draw(
        canvas: android.graphics.Canvas,
        mapView: MapView,
        shadow: Boolean
    ) {
        val cursor = session.cursor ?: return
        val radiusPx = radiusPixels(mapView, cursor, session.radiusMeters.toDouble())
        if (radiusPx <= 0f) return

        if (session.activePoints.isNotEmpty()) {
            pathPaint.strokeWidth = (radiusPx * 2f).coerceAtLeast(2f)
            pathPaint.color = if (session.activeErase) {
                android.graphics.Color.argb(150, 255, 255, 255)
            } else {
                android.graphics.Color.argb(115, 220, 38, 38)
            }
            if (session.activePoints.size == 1) {
                val point = mapView.projection.toPixels(
                    GeoPoint(
                        session.activePoints.first().latitude,
                        session.activePoints.first().longitude
                    ),
                    null
                )
                pathPaint.style = android.graphics.Paint.Style.FILL
                canvas.drawCircle(point.x.toFloat(), point.y.toFloat(), radiusPx, pathPaint)
                pathPaint.style = android.graphics.Paint.Style.STROKE
            } else {
                val path = android.graphics.Path()
                var first = true
                for (point in session.activePoints) {
                    val pixel = mapView.projection.toPixels(
                        GeoPoint(point.latitude, point.longitude),
                        null
                    )
                    if (first) {
                        path.moveTo(pixel.x.toFloat(), pixel.y.toFloat())
                        first = false
                    } else {
                        path.lineTo(pixel.x.toFloat(), pixel.y.toFloat())
                    }
                }
                canvas.drawPath(path, pathPaint)
            }
        }

        val center = mapView.projection.toPixels(
            GeoPoint(cursor.latitude, cursor.longitude),
            null
        )
        cursorFill.color = if (session.tool == BrushTool.ERASER) {
            android.graphics.Color.argb(40, 107, 114, 128)
        } else {
            android.graphics.Color.argb(45, 220, 38, 38)
        }
        canvas.drawCircle(center.x.toFloat(), center.y.toFloat(), radiusPx, cursorFill)
        cursorStroke.color = if (session.tool == BrushTool.ERASER) {
            android.graphics.Color.rgb(107, 114, 128)
        } else {
            android.graphics.Color.rgb(220, 38, 38)
        }
        canvas.drawCircle(center.x.toFloat(), center.y.toFloat(), radiusPx, cursorStroke)
    }
}

private fun radiusPixels(mapView: MapView, center: LatLng, radiusMeters: Double): Float {
    val projection = mapView.projection ?: return 0f
    val a = projection.toPixels(GeoPoint(center.latitude, center.longitude), null)
    val b = projection.toPixels(
        GeoPoint(center.latitude + radiusMeters / 111_320.0, center.longitude),
        null
    )
    return hypot((a.x - b.x).toFloat(), (a.y - b.y).toFloat()).coerceAtLeast(1f)
}

// =====================================================================
// Chrome / sheet / cards
// =====================================================================

@Composable
private fun ZonesTopBar(
    zoneCount: Int,
    activeCount: Int,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = ZoneDesign.MapScrim,
        shape = RoundedCornerShape(bottomStart = 20.dp, bottomEnd = 20.dp),
        shadowElevation = 1.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "المناطق",
                    color = ZoneDesign.Navy,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "$activeCount نشطة • $zoneCount منطقة",
                    color = ZoneDesign.Muted,
                    fontSize = 12.sp
                )
            }
            Surface(
                color = ZoneDesign.BlueSoft,
                shape = CircleShape
            ) {
                Text(
                    text = zoneCount.toString(),
                    color = ZoneDesign.Blue,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp)
                )
            }
        }
    }
}

@Composable
private fun MapControls(
    modifier: Modifier = Modifier,
    onZoomIn: () -> Unit,
    onZoomOut: () -> Unit,
    onMyLocation: () -> Unit
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        color = ZoneDesign.Surface,
        shadowElevation = 6.dp
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            IconButton(onClick = onZoomIn, modifier = Modifier.size(48.dp)) {
                Icon(
                    Icons.Default.Add,
                    contentDescription = "تكبير",
                    tint = ZoneDesign.Navy
                )
            }
            HorizontalDivider(
                modifier = Modifier.width(28.dp),
                color = ZoneDesign.Outline
            )
            IconButton(onClick = onZoomOut, modifier = Modifier.size(48.dp)) {
                Icon(
                    Icons.Default.Remove,
                    contentDescription = "تصغير",
                    tint = ZoneDesign.Navy
                )
            }
            HorizontalDivider(
                modifier = Modifier.width(28.dp),
                color = ZoneDesign.Outline
            )
            IconButton(onClick = onMyLocation, modifier = Modifier.size(48.dp)) {
                Icon(
                    Icons.Outlined.MyLocation,
                    contentDescription = "موقعي",
                    tint = ZoneDesign.Blue,
                    modifier = Modifier.size(22.dp)
                )
            }
        }
    }
}

@Composable
private fun SheetHeader(
    zoneCount: Int,
    activeCount: Int,
    expanded: Boolean,
    onToggle: () -> Unit,
    onDrag: (Float) -> Unit,
    onDragEnd: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .pointerInput(Unit) {
                detectVerticalDragGestures(
                    onVerticalDrag = { change, dragAmount ->
                        change.consume()
                        onDrag(dragAmount)
                    },
                    onDragEnd = { onDragEnd() },
                    onDragCancel = { onDragEnd() }
                )
            }
            .padding(top = 8.dp, bottom = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(width = 44.dp, height = 4.dp)
                .background(ZoneDesign.Outline, RoundedCornerShape(2.dp))
        )
        Spacer(Modifier.height(8.dp))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "المناطق المحفوظة",
                    color = ZoneDesign.Navy,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "$activeCount نشطة من $zoneCount",
                    color = ZoneDesign.Muted,
                    fontSize = 12.sp
                )
            }
            IconButton(onClick = onToggle, modifier = Modifier.size(48.dp)) {
                Icon(
                    imageVector = if (expanded) {
                        Icons.Default.KeyboardArrowDown
                    } else {
                        Icons.Default.KeyboardArrowUp
                    },
                    contentDescription = if (expanded) "تصغير القائمة" else "توسيع القائمة",
                    tint = ZoneDesign.Muted
                )
            }
        }
    }
}

@Composable
private fun EmptyZones(onAdd: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Box(
            modifier = Modifier
                .size(88.dp)
                .background(ZoneDesign.BlueSoft, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                Icons.Outlined.Layers,
                contentDescription = null,
                tint = ZoneDesign.Blue,
                modifier = Modifier.size(40.dp)
            )
        }
        Spacer(Modifier.height(16.dp))
        Text(
            text = "لا توجد مناطق محفوظة",
            color = ZoneDesign.Navy,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(6.dp))
        Text(
            text = "ارسم منطقة محظورة على الخريطة لتظهر هنا. يمكنك الرسم بالنقاط أو بالفرشاة الحرة.",
            color = ZoneDesign.Muted,
            fontSize = 13.sp,
            lineHeight = 21.sp
        )
        Spacer(Modifier.height(18.dp))
        Button(
            onClick = onAdd,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(containerColor = ZoneDesign.Blue)
        ) {
            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("إضافة منطقة")
        }
    }
}

@Composable
private fun ZoneCard(
    zone: Zone,
    selected: Boolean,
    onOpen: () -> Unit,
    onToggle: (Boolean) -> Unit,
    onEdit: () -> Unit,
    onLocate: () -> Unit,
    onDelete: () -> Unit
) {
    var menuExpanded by remember { mutableStateOf(false) }
    val typeColor = if (zone.isActive) ZoneDesign.colorFor(zone.type) else ZoneDesign.Muted
    val softColor = ZoneDesign.softColorFor(zone.type)
    val shape = RoundedCornerShape(16.dp)

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 64.dp)
            .clickable(onClick = onOpen),
        shape = shape,
        color = if (selected) ZoneDesign.BlueSoft.copy(alpha = 0.55f) else ZoneDesign.Surface,
        border = BorderStroke(
            1.dp,
            if (selected) ZoneDesign.Blue.copy(alpha = 0.55f) else ZoneDesign.Outline
        ),
        shadowElevation = if (selected) 2.dp else 0.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .background(softColor, RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = when (zone.type) {
                        ZoneType.DANGER -> Icons.Default.Warning
                        ZoneType.FAVORITE -> Icons.Default.Star
                        ZoneType.NEUTRAL -> Icons.Default.Place
                    },
                    contentDescription = null,
                    tint = typeColor,
                    modifier = Modifier.size(22.dp)
                )
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = zone.name,
                    color = if (zone.isActive) ZoneDesign.Navy else ZoneDesign.Muted,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = zoneDetailLine(zone),
                    color = ZoneDesign.Muted,
                    fontSize = 11.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            Switch(
                checked = zone.isActive,
                onCheckedChange = onToggle,
                modifier = Modifier.heightIn(min = 48.dp)
            )
            Box {
                IconButton(
                    onClick = { menuExpanded = true },
                    modifier = Modifier.size(48.dp)
                ) {
                    Icon(
                        Icons.Default.MoreVert,
                        contentDescription = "خيارات المنطقة",
                        tint = ZoneDesign.Muted
                    )
                }
                DropdownMenu(
                    expanded = menuExpanded,
                    onDismissRequest = { menuExpanded = false }
                ) {
                    DropdownMenuItem(
                        text = { Text("تعديل") },
                        leadingIcon = {
                            Icon(Icons.Default.Edit, contentDescription = null)
                        },
                        onClick = {
                            menuExpanded = false
                            onEdit()
                        }
                    )
                    DropdownMenuItem(
                        text = { Text("تحديد على الخريطة") },
                        leadingIcon = {
                            Icon(Icons.Outlined.MyLocation, contentDescription = null)
                        },
                        onClick = {
                            menuExpanded = false
                            onLocate()
                        }
                    )
                    DropdownMenuItem(
                        text = { Text("حذف", color = ZoneDesign.Danger) },
                        leadingIcon = {
                            Icon(
                                Icons.Default.Delete,
                                contentDescription = null,
                                tint = ZoneDesign.Danger
                            )
                        },
                        onClick = {
                            menuExpanded = false
                            onDelete()
                        }
                    )
                }
            }
        }
    }
}

private fun zoneDetailLine(zone: Zone): String {
    val kind = when {
        zone.zoneShape == ZoneShape.CIRCLE -> "دائرة"
        zone.isBrushZone() -> "رسم حر"
        else -> "مضلع"
    }
    val area = BrushGeometry.formatArea(BrushGeometry.areaSqMeters(zone))
    val points = if (zone.zoneShape == ZoneShape.CIRCLE) {
        "نصف قطر ${BrushGeometry.formatRadius(zone.radiusMeters)}"
    } else {
        val count = zone.polygons().sumOf { part ->
            part.exterior.size + part.holes.sumOf { it.size }
        }
        "$count نقطة"
    }
    return "$kind • $points • $area"
}

@Composable
private fun ZoneInfoCard(
    zone: Zone,
    modifier: Modifier = Modifier,
    onClose: () -> Unit,
    onLocate: () -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        color = ZoneDesign.Surface,
        shadowElevation = 10.dp
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .background(
                            ZoneDesign.softColorFor(zone.type),
                            RoundedCornerShape(10.dp)
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = when (zone.type) {
                            ZoneType.DANGER -> Icons.Default.Warning
                            ZoneType.FAVORITE -> Icons.Default.Star
                            ZoneType.NEUTRAL -> Icons.Default.Place
                        },
                        contentDescription = null,
                        tint = ZoneDesign.colorFor(zone.type),
                        modifier = Modifier.size(20.dp)
                    )
                }
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = zone.name,
                        color = ZoneDesign.Navy,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        text = "${ZoneDesign.labelFor(zone.type)} • ${zoneDetailLine(zone)}",
                        color = ZoneDesign.Muted,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                IconButton(onClick = onClose, modifier = Modifier.size(40.dp)) {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "إغلاق",
                        tint = ZoneDesign.Muted
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = onLocate) {
                    Icon(
                        Icons.Outlined.MyLocation,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(4.dp))
                    Text("عرض")
                }
                TextButton(onClick = onEdit) {
                    Icon(
                        Icons.Default.Edit,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(4.dp))
                    Text("تعديل")
                }
                TextButton(onClick = onDelete) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = null,
                        tint = ZoneDesign.Danger,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(Modifier.width(4.dp))
                    Text("حذف", color = ZoneDesign.Danger)
                }
            }
        }
    }
}

@Composable
private fun AddZoneFab(
    expanded: Boolean,
    onToggle: () -> Unit,
    onPolygon: () -> Unit,
    onBrush: () -> Unit,
    onCircle: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.End
    ) {
        AnimatedVisibility(
            visible = expanded,
            enter = fadeIn() + expandVertically(),
            exit = fadeOut() + shrinkVertically()
        ) {
            Surface(
                shape = RoundedCornerShape(18.dp),
                color = ZoneDesign.Surface,
                shadowElevation = 10.dp
            ) {
                Column(modifier = Modifier.padding(6.dp)) {
                    AddZoneOption(
                        icon = Icons.Outlined.Polyline,
                        title = "رسم مضلع بالنقاط",
                        subtitle = "أضف رؤوساً على الخريطة",
                        onClick = onPolygon
                    )
                    AddZoneOption(
                        icon = Icons.Outlined.Brush,
                        title = "رسم حر بالفرشاة",
                        subtitle = "لوّن المنطقة بإصبعك",
                        onClick = onBrush
                    )
                    AddZoneOption(
                        icon = Icons.Outlined.AddCircle,
                        title = "دائرة بنصف قطر",
                        subtitle = "إدخال إحداثيات ونصف قطر",
                        onClick = onCircle
                    )
                }
            }
            Spacer(Modifier.height(10.dp))
        }
        FloatingActionButton(
            onClick = onToggle,
            containerColor = ZoneDesign.Blue,
            contentColor = Color.White,
            shape = CircleShape
        ) {
            Icon(
                imageVector = if (expanded) Icons.Default.Close else Icons.Default.Add,
                contentDescription = if (expanded) "إغلاق قائمة الإضافة" else "إضافة منطقة"
            )
        }
    }
}

@Composable
private fun AddZoneOption(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp)
            .heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(ZoneDesign.BlueSoft, RoundedCornerShape(10.dp)),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = ZoneDesign.Blue)
        }
        Spacer(Modifier.width(10.dp))
        Column {
            Text(title, color = ZoneDesign.Navy, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            Text(subtitle, color = ZoneDesign.Muted, fontSize = 11.sp)
        }
    }
}

// =====================================================================
// Editing toolbars
// =====================================================================

@Composable
private fun PolygonToolbar(
    points: List<LatLng>,
    modifier: Modifier = Modifier,
    onUndo: () -> Unit,
    onClear: () -> Unit,
    onCancel: () -> Unit,
    onSave: () -> Unit
) {
    val distinct = PolygonDrawing.distinctPointCount(points)
    val canSave = PolygonDrawing.canSavePolygon(points)
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        color = ZoneDesign.Surface,
        shadowElevation = 12.dp
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Polyline, contentDescription = null, tint = ZoneDesign.Blue)
                Spacer(Modifier.width(8.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text("رسم مضلع بالنقاط", color = ZoneDesign.Navy, fontWeight = FontWeight.Bold)
                    Text(
                        "اضغط على الخريطة لإضافة رأس. اسحب بإصبعين للتنقل.",
                        color = ZoneDesign.Muted,
                        fontSize = 11.sp
                    )
                }
                AssistChip(
                    onClick = {},
                    label = { Text("$distinct رأس", fontSize = 11.sp) }
                )
            }
            Spacer(Modifier.height(10.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                FilledTonalIconButton(
                    onClick = onUndo,
                    enabled = points.isNotEmpty()
                ) {
                    Icon(Icons.Outlined.Undo, contentDescription = "تراجع")
                }
                FilledTonalIconButton(
                    onClick = onClear,
                    enabled = points.isNotEmpty()
                ) {
                    Icon(Icons.Outlined.DeleteSweep, contentDescription = "مسح الكل")
                }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = onCancel) { Text("إلغاء") }
                Button(
                    onClick = onSave,
                    enabled = canSave,
                    colors = ButtonDefaults.buttonColors(containerColor = ZoneDesign.Blue)
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("حفظ")
                }
            }
            if (!canSave) {
                Text(
                    text = "أضف 3 رؤوس مختلفة على الأقل للحفظ",
                    color = ZoneDesign.Muted,
                    fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
private fun GeometryToolbar(
    points: List<LatLng>,
    selectedVertexIndex: Int?,
    error: String?,
    modifier: Modifier = Modifier,
    onDeleteVertex: () -> Unit,
    onSave: () -> Unit,
    onCancel: () -> Unit
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        color = ZoneDesign.Surface,
        shadowElevation = 12.dp
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Architecture, contentDescription = null, tint = ZoneDesign.Warning)
                Spacer(Modifier.width(8.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text("تعديل شكل المضلع", color = ZoneDesign.Navy, fontWeight = FontWeight.Bold)
                    Text(
                        if (selectedVertexIndex != null) {
                            "الرأس المحدد: ${selectedVertexIndex + 1}. اضغط على الخريطة لنقله."
                        } else {
                            "اضغط على رأس لتحديده، ثم اضغط على الخريطة لنقله."
                        },
                        color = ZoneDesign.Muted,
                        fontSize = 11.sp
                    )
                }
                AssistChip(
                    onClick = {},
                    label = { Text("${points.size} رأس", fontSize = 11.sp) }
                )
            }
            error?.let {
                Spacer(Modifier.height(6.dp))
                Text(it, color = ZoneDesign.Danger, fontSize = 11.sp)
            }
            Spacer(Modifier.height(10.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                FilledTonalIconButton(
                    onClick = onDeleteVertex,
                    enabled = selectedVertexIndex != null
                ) {
                    Icon(Icons.Default.Delete, contentDescription = "حذف الرأس")
                }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = onCancel) { Text("إلغاء") }
                Button(
                    onClick = onSave,
                    enabled = PolygonDrawing.canSavePolygon(points),
                    colors = ButtonDefaults.buttonColors(containerColor = ZoneDesign.Warning)
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("حفظ الشكل")
                }
            }
        }
    }
}

@Composable
private fun BrushToolbar(
    session: BrushSession,
    result: BrushBuildResult,
    error: String?,
    modifier: Modifier = Modifier,
    onDone: () -> Unit,
    onCancel: () -> Unit
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        color = ZoneDesign.Surface,
        shadowElevation = 12.dp
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Brush, contentDescription = null, tint = ZoneDesign.Danger)
                Spacer(Modifier.width(8.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text("رسم حر بالفرشاة", color = ZoneDesign.Navy, fontWeight = FontWeight.Bold)
                    Text(
                        "لمسة واحدة تختم دائرة، والسحب يرسم مساراً مستمراً.",
                        color = ZoneDesign.Muted,
                        fontSize = 11.sp
                    )
                }
                AssistChip(
                    onClick = {},
                    label = {
                        Text(
                            if (result.isEmpty()) "—" else BrushGeometry.formatArea(result.areaSqMeters),
                            fontSize = 11.sp
                        )
                    },
                    leadingIcon = {
                        Icon(
                            Icons.Outlined.SquareFoot,
                            contentDescription = null,
                            modifier = Modifier.size(15.dp)
                        )
                    }
                )
            }
            Spacer(Modifier.height(8.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = session.tool == BrushTool.BRUSH,
                    onClick = { session.tool = BrushTool.BRUSH },
                    label = { Text("فرشاة") },
                    leadingIcon = {
                        Icon(
                            Icons.Outlined.Brush,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                )
                FilterChip(
                    selected = session.tool == BrushTool.ERASER,
                    onClick = { session.tool = BrushTool.ERASER },
                    label = { Text("ممحاة") },
                    leadingIcon = {
                        Icon(
                            Icons.Outlined.DeleteSweep,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                )
                Spacer(Modifier.weight(1f))
                Text(
                    text = "الحجم: ${BrushGeometry.formatRadius(session.radiusMeters.toDouble())}",
                    color = ZoneDesign.Navy,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
            Slider(
                value = session.radiusMeters,
                onValueChange = { session.radiusMeters = it },
                valueRange = BrushGeometry.MIN_RADIUS_METERS.toFloat()..
                    BrushGeometry.MAX_RADIUS_METERS.toFloat(),
                steps = 194
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                FilledTonalIconButton(
                    onClick = { session.undoLast() },
                    enabled = session.strokes.isNotEmpty()
                ) {
                    Icon(Icons.Outlined.Undo, contentDescription = "تراجع")
                }
                FilledTonalIconButton(
                    onClick = { session.redoLast() },
                    enabled = session.redo.isNotEmpty()
                ) {
                    Icon(Icons.Outlined.Redo, contentDescription = "إعادة")
                }
                FilledTonalIconButton(
                    onClick = { session.clearAll() },
                    enabled = session.strokes.isNotEmpty()
                ) {
                    Icon(Icons.Outlined.DeleteSweep, contentDescription = "مسح الكل")
                }
                Spacer(Modifier.weight(1f))
                TextButton(onClick = onCancel) { Text("إلغاء") }
                Button(
                    onClick = onDone,
                    enabled = !result.isEmpty(),
                    colors = ButtonDefaults.buttonColors(containerColor = ZoneDesign.Danger)
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("تم")
                }
            }
            error?.let {
                Text(it, color = ZoneDesign.Danger, fontSize = 11.sp)
            }
        }
    }
}

// =====================================================================
// Save / edit sheets
// =====================================================================

@Composable
private fun SaveZoneSheet(
    pending: PendingSave,
    zones: List<Zone>,
    onDismiss: () -> Unit,
    onSave: (String, ZoneType) -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var name by remember {
        mutableStateOf(pending.existingZone?.name ?: "منطقة ${zones.size + 1}")
    }
    var type by remember { mutableStateOf(pending.defaultType) }
    var error by remember { mutableStateOf<String?>(null) }
    val existingNames = remember(zones, pending.existingZone) {
        zones.filter { it.id != pending.existingZone?.id }
            .map { it.name.trim() }
            .toSet()
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp)
                .imePadding()
        ) {
            Text(
                text = if (pending.existingZone == null) "حفظ المنطقة" else "تحديث المنطقة",
                color = ZoneDesign.Navy,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "أدخل اسماً واضحاً للمنطقة قبل الحفظ.",
                color = ZoneDesign.Muted,
                fontSize = 12.sp
            )
            Spacer(Modifier.height(14.dp))
            OutlinedTextField(
                value = name,
                onValueChange = {
                    name = it
                    error = null
                },
                label = { Text("اسم المنطقة") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            error?.let {
                Spacer(Modifier.height(6.dp))
                Text(it, color = ZoneDesign.Danger, fontSize = 11.sp)
            }
            Spacer(Modifier.height(14.dp))
            Text("نوع المنطقة", color = ZoneDesign.Navy, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ZoneType.entries.forEach { option ->
                    FilterChip(
                        selected = type == option,
                        onClick = { type = option },
                        label = { Text(ZoneDesign.labelFor(option), fontSize = 11.sp) }
                    )
                }
            }
            Spacer(Modifier.height(14.dp))
            Surface(
                shape = RoundedCornerShape(14.dp),
                color = ZoneDesign.Canvas
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("المساحة التقريبية", color = ZoneDesign.Muted, fontSize = 11.sp)
                        Text(
                            BrushGeometry.formatArea(pending.areaSqMeters),
                            color = ZoneDesign.Navy,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text("عدد النقاط", color = ZoneDesign.Muted, fontSize = 11.sp)
                        Text(
                            pending.pointCount.toString(),
                            color = ZoneDesign.Navy,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
            Spacer(Modifier.height(18.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                TextButton(
                    onClick = onDismiss,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("إلغاء")
                }
                Button(
                    onClick = {
                        val trimmed = name.trim()
                        when {
                            trimmed.isBlank() -> error = "الرجاء إدخال اسم المنطقة"
                            existingNames.contains(trimmed) -> error = "هذه المنطقة موجودة مسبقاً"
                            pending.polygons.isEmpty() -> error = "لا توجد مساحة صالحة للحفظ"
                            else -> onSave(trimmed, type)
                        }
                    },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ZoneDesign.Blue)
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("حفظ")
                }
            }
        }
    }
}

@Composable
private fun EditZoneSheet(
    zone: Zone,
    zones: List<Zone>,
    onDismiss: () -> Unit,
    onSave: (String, ZoneType) -> Unit,
    onEditShape: () -> Unit,
    onDelete: () -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var name by remember(zone.id) { mutableStateOf(zone.name) }
    var type by remember(zone.id) { mutableStateOf(zone.type) }
    var error by remember { mutableStateOf<String?>(null) }
    val existingNames = remember(zones, zone.id) {
        zones.filter { it.id != zone.id }.map { it.name.trim() }.toSet()
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp)
                .padding(bottom = 28.dp)
                .imePadding()
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .background(ZoneDesign.softColorFor(zone.type), RoundedCornerShape(12.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = when (zone.type) {
                            ZoneType.DANGER -> Icons.Default.Warning
                            ZoneType.FAVORITE -> Icons.Default.Star
                            ZoneType.NEUTRAL -> Icons.Default.Place
                        },
                        contentDescription = null,
                        tint = ZoneDesign.colorFor(zone.type)
                    )
                }
                Spacer(Modifier.width(10.dp))
                Column {
                    Text("تعديل المنطقة", color = ZoneDesign.Navy, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Text(zoneDetailLine(zone), color = ZoneDesign.Muted, fontSize = 11.sp)
                }
            }
            Spacer(Modifier.height(14.dp))
            OutlinedTextField(
                value = name,
                onValueChange = {
                    name = it
                    error = null
                },
                label = { Text("اسم المنطقة") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            error?.let {
                Spacer(Modifier.height(6.dp))
                Text(it, color = ZoneDesign.Danger, fontSize = 11.sp)
            }
            Spacer(Modifier.height(14.dp))
            Text("نوع المنطقة", color = ZoneDesign.Navy, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ZoneType.entries.forEach { option ->
                    FilterChip(
                        selected = type == option,
                        onClick = { type = option },
                        label = { Text(ZoneDesign.labelFor(option), fontSize = 11.sp) }
                    )
                }
            }
            Spacer(Modifier.height(14.dp))
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(onClick = onEditShape),
                shape = RoundedCornerShape(14.dp),
                color = ZoneDesign.Canvas
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        if (zone.isBrushZone()) Icons.Outlined.Brush else Icons.Outlined.Architecture,
                        contentDescription = null,
                        tint = ZoneDesign.Blue
                    )
                    Spacer(Modifier.width(10.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            if (zone.isBrushZone()) "تعديل الرسم الحر" else "تعديل شكل المضلع",
                            color = ZoneDesign.Navy,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            if (zone.isBrushZone()) {
                                "أعد فتح الفرشاة لإضافة أو مسح أجزاء."
                            } else {
                                "حرّك الرؤوس أو احذفها ثم احفظ الشكل."
                            },
                            color = ZoneDesign.Muted,
                            fontSize = 11.sp
                        )
                    }
                    Icon(
                        Icons.Outlined.Gesture,
                        contentDescription = null,
                        tint = ZoneDesign.Muted
                    )
                }
            }
            Spacer(Modifier.height(18.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                TextButton(
                    onClick = onDelete,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("حذف", color = ZoneDesign.Danger)
                }
                Button(
                    onClick = {
                        val trimmed = name.trim()
                        when {
                            trimmed.isBlank() -> error = "الرجاء إدخال اسم المنطقة"
                            existingNames.contains(trimmed) -> error = "هذه المنطقة موجودة مسبقاً"
                            else -> onSave(trimmed, type)
                        }
                    },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ZoneDesign.Blue)
                ) {
                    Text("حفظ التعديلات")
                }
            }
        }
    }
}

@Composable
private fun AddCircleDialog(
    zones: List<Zone>,
    initialLatitude: Double?,
    initialLongitude: Double?,
    onDismiss: () -> Unit,
    onSave: (Zone) -> Unit
) {
    var name by remember { mutableStateOf("منطقة ${zones.size + 1}") }
    var latitude by remember {
        mutableStateOf(initialLatitude?.toString() ?: "24.7136")
    }
    var longitude by remember {
        mutableStateOf(initialLongitude?.toString() ?: "46.6753")
    }
    var radius by remember { mutableStateOf("500") }
    var type by remember { mutableStateOf(ZoneType.DANGER) }
    var error by remember { mutableStateOf<String?>(null) }
    val existingNames = remember(zones) { zones.map { it.name.trim() }.toSet() }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("إضافة دائرة") },
        text = {
            Column {
                error?.let {
                    Text(it, color = ZoneDesign.Danger, fontSize = 11.sp)
                }
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("اسم المنطقة") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = latitude,
                        onValueChange = { latitude = it },
                        label = { Text("خط العرض") },
                        singleLine = true,
                        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                            keyboardType = KeyboardType.Decimal
                        ),
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = longitude,
                        onValueChange = { longitude = it },
                        label = { Text("خط الطول") },
                        singleLine = true,
                        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                            keyboardType = KeyboardType.Decimal
                        ),
                        modifier = Modifier.weight(1f)
                    )
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = radius,
                    onValueChange = { radius = it },
                    label = { Text("نصف القطر (م)") },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                        keyboardType = KeyboardType.Decimal
                    ),
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ZoneType.entries.forEach { option ->
                        FilterChip(
                            selected = type == option,
                            onClick = { type = option },
                            label = { Text(ZoneDesign.labelFor(option), fontSize = 11.sp) }
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val trimmed = name.trim()
                    val lat = latitude.toDoubleOrNull()
                    val lon = longitude.toDoubleOrNull()
                    val rad = radius.toDoubleOrNull()
                    when {
                        trimmed.isBlank() -> error = "الرجاء إدخال اسم المنطقة"
                        existingNames.contains(trimmed) -> error = "هذه المنطقة موجودة مسبقاً"
                        lat == null || lat !in -90.0..90.0 -> error = "خط عرض غير صالح"
                        lon == null || lon !in -180.0..180.0 -> error = "خط طول غير صالح"
                        rad == null || rad <= 0.0 -> error = "نصف القطر يجب أن يكون أكبر من صفر"
                        else -> onSave(
                            Zone(
                                id = UUID.randomUUID().toString(),
                                name = trimmed,
                                zoneShape = ZoneShape.CIRCLE,
                                centerLatitude = lat,
                                centerLongitude = lon,
                                radiusMeters = rad,
                                type = type,
                                color = ZoneDesign.colorFor(type).toArgb(),
                                isActive = true
                            )
                        )
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = ZoneDesign.Blue)
            ) {
                Text("حفظ")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("إلغاء") }
        }
    )
}

// =====================================================================
// Location
// =====================================================================

private fun locateNow(context: Context, mapView: MapView?) {
    val view = mapView ?: return
    if (
        context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) !=
        PackageManager.PERMISSION_GRANTED
    ) {
        return
    }
    val manager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
        ?: return
    val lastKnown = sequenceOf(
        LocationManager.GPS_PROVIDER,
        LocationManager.NETWORK_PROVIDER
    ).mapNotNull { provider ->
        try {
            manager.getLastKnownLocation(provider)
        } catch (_: SecurityException) {
            null
        }
    }.maxByOrNull { it.time }

    if (lastKnown != null) {
        view.controller.animateTo(
            GeoPoint(lastKnown.latitude, lastKnown.longitude),
            17.0,
            600L
        )
        return
    }

    val provider = when {
        manager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
        manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
        else -> null
    }
    if (provider == null) {
        Toast.makeText(context, "خدمة الموقع غير مفعّلة", Toast.LENGTH_SHORT).show()
        return
    }

    val listener = object : LocationListener {
        override fun onLocationChanged(location: Location) {
            view.controller.animateTo(
                GeoPoint(location.latitude, location.longitude),
                17.0,
                600L
            )
            try {
                manager.removeUpdates(this)
            } catch (_: SecurityException) {
                // Permission can only be revoked while the app is backgrounded.
            }
        }

        override fun onProviderEnabled(provider: String) = Unit
        override fun onProviderDisabled(provider: String) = Unit

        @Deprecated("Deprecated in Java")
        override fun onStatusChanged(provider: String?, status: Int, extras: android.os.Bundle?) = Unit
    }

    try {
        manager.requestSingleUpdate(provider, listener, Looper.getMainLooper())
        Toast.makeText(context, "جارٍ تحديد موقعك…", Toast.LENGTH_SHORT).show()
    } catch (_: SecurityException) {
        Toast.makeText(context, "تعذّر الوصول إلى الموقع", Toast.LENGTH_SHORT).show()
    }
}
