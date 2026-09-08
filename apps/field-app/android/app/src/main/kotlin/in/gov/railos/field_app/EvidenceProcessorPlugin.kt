package `in`.gov.railos.field_app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import androidx.exifinterface.media.ExifInterface
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.embedding.engine.plugins.activity.ActivityAware
import io.flutter.embedding.engine.plugins.activity.ActivityPluginBinding
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import kotlin.math.abs

class EvidenceProcessorPlugin : FlutterPlugin, ActivityAware, MethodChannel.MethodCallHandler {
    private lateinit var channel: MethodChannel
    private val capture = CaptureBridge()
    private var activityBinding: ActivityPluginBinding? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel = MethodChannel(binding.binaryMessenger, "in.gov.railos.field_app/evidence_processor")
        channel.setMethodCallHandler(this)
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
    }

    override fun onAttachedToActivity(binding: ActivityPluginBinding) {
        activityBinding = binding
        binding.addActivityResultListener(capture)
        binding.addRequestPermissionsResultListener(capture)
        capture.attach(binding.activity)
    }

    override fun onReattachedToActivityForConfigChanges(binding: ActivityPluginBinding) =
        onAttachedToActivity(binding)

    override fun onDetachedFromActivityForConfigChanges() = onDetachedFromActivity()

    override fun onDetachedFromActivity() {
        activityBinding?.removeActivityResultListener(capture)
        activityBinding?.removeRequestPermissionsResultListener(capture)
        activityBinding = null
        capture.detach()
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "burnPhotoOverlay" -> {
                val sourcePath = call.argument<String>("sourcePath") ?: ""
                val outputPath = call.argument<String>("outputPath") ?: ""
                val evidenceId = call.argument<String>("evidenceId") ?: ""
                val taskId = call.argument<String>("taskId") ?: ""
                val stepId = call.argument<String>("stepId") ?: ""
                val supervisorId = call.argument<String>("supervisorId") ?: ""
                val timestampUtc = call.argument<String>("timestampUtc") ?: ""
                val latitude = call.argument<Double>("latitude") ?: 0.0
                val longitude = call.argument<Double>("longitude") ?: 0.0
                val altitude = call.argument<Double>("altitude") ?: 0.0
                val accuracyMeters = call.argument<Double>("accuracyMeters") ?: 0.0
                val geoVerdict = call.argument<String>("geoVerdict") ?: "WITHIN_RADIUS"
                val distanceMeters = call.argument<Double>("distanceMeters") ?: 0.0

                try {
                    val res = processPhotoProof(
                        sourcePath, outputPath, evidenceId, taskId, stepId,
                        supervisorId, timestampUtc, latitude, longitude,
                        altitude, accuracyMeters, geoVerdict, distanceMeters
                    )
                    result.success(res)
                } catch (e: Exception) {
                    result.error("PROCESSING_FAILED", e.localizedMessage, null)
                }
            }
            "computeSha256" -> {
                val filePath = call.argument<String>("filePath") ?: ""
                try {
                    val file = File(filePath)
                    if (!file.exists()) {
                        result.error("FILE_NOT_FOUND", "File does not exist: $filePath", null)
                        return
                    }
                    val hash = calculateSha256(file)
                    result.success(mapOf("sha256" to hash, "sizeBytes" to file.length()))
                } catch (e: Exception) {
                    result.error("HASH_FAILED", e.localizedMessage, null)
                }
            }
            "capturePhoto", "captureVideo" -> {
                val fileName = call.argument<String>("fileName") ?: "capture.jpg"
                val maxSeconds = call.argument<Int>("maxSeconds") ?: 90
                val action = if (call.method == "captureVideo") "video" else "photo"
                capture.capture(action, fileName, maxSeconds, result)
            }
            "currentLocation" -> {
                val timeoutMs = (call.argument<Int>("timeoutMs") ?: 8000).toLong()
                capture.currentLocation(timeoutMs, result)
            }
            else -> result.notImplemented()
        }
    }

    private fun processPhotoProof(
        sourcePath: String,
        outputPath: String,
        evidenceId: String,
        taskId: String,
        stepId: String,
        supervisorId: String,
        timestampUtc: String,
        latitude: Double,
        longitude: Double,
        altitude: Double,
        accuracyMeters: Double,
        geoVerdict: String,
        distanceMeters: Double
    ): Map<String, Any> {
        val srcFile = File(sourcePath)
        val origSha256 = calculateSha256(srcFile)
        val originalBitmap = BitmapFactory.decodeFile(sourcePath)
            ?: throw IllegalStateException("Cannot decode source image")

        val mutableBitmap = originalBitmap.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(mutableBitmap)
        val width = mutableBitmap.width.toFloat()
        val height = mutableBitmap.height.toFloat()

        // Evidence strip banner configuration (bottom 12% of image, min 160px)
        val bannerHeight = (height * 0.12f).coerceAtLeast(160f)
        val bannerTop = height - bannerHeight

        // Graphite evidence strip from RailOS DESIGN.md (not the legacy
        // blue/navy palette). The baked proof must agree with the Flutter UI.
        val bgPaint = Paint().apply {
            color = Color.argb(224, 10, 7, 3) // #0A0703 / graphite overlay
            style = Paint.Style.FILL
        }
        canvas.drawRect(0f, bannerTop, width, height, bgPaint)

        // Accent top border line
        val borderPaint = Paint().apply {
            color = if (geoVerdict == "WITHIN_RADIUS") Color.rgb(232, 163, 23) else Color.rgb(217, 120, 100)
            strokeWidth = 6f
            style = Paint.Style.STROKE
        }
        canvas.drawLine(0f, bannerTop, width, bannerTop, borderPaint)

        // Text typography
        val fontSize = (bannerHeight * 0.18f).coerceIn(24f, 44f)
        val textPaint = Paint().apply {
            color = Color.WHITE
            textSize = fontSize
            typeface = Typeface.MONOSPACE
            isAntiAlias = true
        }

        val accentPaint = Paint().apply {
            color = Color.rgb(232, 163, 23)
            textSize = fontSize
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            isAntiAlias = true
        }

        val linePadding = fontSize * 1.35f
        var currentY = bannerTop + (bannerHeight * 0.28f)
        val leftX = 32f

        // Line 1: Header mark & IDs
        canvas.drawText("RAILOS EVIDENCE PROOF // ", leftX, currentY, accentPaint)
        val markWidth = accentPaint.measureText("RAILOS EVIDENCE PROOF // ")
        canvas.drawText("EVID: ${evidenceId.take(12)}... | TASK: $taskId | STEP: $stepId", leftX + markWidth, currentY, textPaint)

        // Line 2: Supervisor and Timestamp
        currentY += linePadding
        canvas.drawText("SUP: $supervisorId | UTC: $timestampUtc", leftX, currentY, textPaint)

        // Line 3: Location and Verdict
        currentY += linePadding
        val verdictColor = if (geoVerdict == "WITHIN_RADIUS") Color.rgb(143, 179, 139) else Color.rgb(217, 120, 100)
        val verdictPaint = Paint().apply {
            color = verdictColor
            textSize = fontSize
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            isAntiAlias = true
        }
        val locStr = String.format("LOC: %.5f, %.5f (±%.1fm) | DIST: %.1fm | ", latitude, longitude, accuracyMeters, distanceMeters)
        canvas.drawText(locStr, leftX, currentY, textPaint)
        val locWidth = textPaint.measureText(locStr)
        canvas.drawText(geoVerdict, leftX + locWidth, currentY, verdictPaint)

        // Save proof derivative
        val outFile = File(outputPath)
        outFile.parentFile?.mkdirs()
        FileOutputStream(outFile).use { out ->
            mutableBitmap.compress(Bitmap.CompressFormat.JPEG, 85, out)
        }

        // Embed EXIF GPS metadata into the proof derivative
        try {
            val exif = ExifInterface(outputPath)
            setExifGps(exif, latitude, longitude, altitude)
            exif.setAttribute(ExifInterface.TAG_SOFTWARE, "RailOS Geotagged Field-Evidence Mobile 1.0")
            exif.setAttribute(ExifInterface.TAG_IMAGE_DESCRIPTION, "evidenceId=$evidenceId,taskId=$taskId,stepId=$stepId")
            exif.saveAttributes()
        } catch (e: Exception) {
            // Non-fatal if EXIF write fails on derivative
        }

        val proofSha256 = calculateSha256(outFile)

        return mapOf(
            "originalSha256" to origSha256,
            "proofSha256" to proofSha256,
            "proofPath" to outputPath,
            "proofSizeBytes" to outFile.length(),
            "originalSizeBytes" to srcFile.length()
        )
    }

    private fun setExifGps(exif: ExifInterface, latitude: Double, longitude: Double, altitude: Double) {
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE, decimalToDms(latitude))
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE_REF, if (latitude >= 0) "N" else "S")
        exif.setAttribute(ExifInterface.TAG_GPS_LONGITUDE, decimalToDms(longitude))
        exif.setAttribute(ExifInterface.TAG_GPS_LONGITUDE_REF, if (longitude >= 0) "E" else "W")
        exif.setAttribute(ExifInterface.TAG_GPS_ALTITUDE, abs(altitude).toString())
        exif.setAttribute(ExifInterface.TAG_GPS_ALTITUDE_REF, if (altitude >= 0) "0" else "1")
    }

    private fun decimalToDms(coord: Double): String {
        val absCoord = abs(coord)
        val degrees = absCoord.toInt()
        val minutes = ((absCoord - degrees) * 60).toInt()
        val seconds = (absCoord - degrees - minutes / 60.0) * 3600.0 * 1000.0
        return "$degrees/1,$minutes/1,${seconds.toInt()}/1000"
    }

    private fun calculateSha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { fis ->
            val buffer = ByteArray(65536)
            var bytesRead: Int
            while (fis.read(buffer).also { bytesRead = it } != -1) {
                digest.update(buffer, 0, bytesRead)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
