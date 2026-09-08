package `in`.gov.railos.field_app

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.PluginRegistry
import java.io.File

/**
 * Bridges the Flutter capture screen to the system camera and GPS.
 *
 * ponytail: uses the system camera app (ACTION_IMAGE_CAPTURE) rather than an
 * embedded preview — no camera plugin, no surface lifecycle to manage. Move to
 * CameraX only if an in-app viewfinder overlay becomes a requirement.
 */
class CaptureBridge :
    PluginRegistry.ActivityResultListener,
    PluginRegistry.RequestPermissionsResultListener {

    private var activity: Activity? = null
    private var pendingResult: MethodChannel.Result? = null
    private var pendingFileName: String? = null
    private var pendingOutputPath: String? = null
    private var pendingAction: String? = null
    private var pendingMaxSeconds: Int = 90

    fun attach(activity: Activity) {
        this.activity = activity
    }

    fun detach() {
        this.activity = null
    }

    // --- Camera ---------------------------------------------------------

    /**
     * action: "photo" or "video". Replies with the written path, or null if cancelled.
     * The native side owns the location: FileProvider can only share roots declared
     * in file_paths.xml, so cacheDir/evidence is the one place both sides agree on.
     */
    fun capture(action: String, fileName: String, maxSeconds: Int, result: MethodChannel.Result) {
        val act = activity
        if (act == null) {
            result.error("NO_ACTIVITY", "Capture requires a foreground activity", null)
            return
        }
        if (pendingResult != null) {
            result.error("BUSY", "A capture is already in progress", null)
            return
        }
        pendingResult = result
        pendingFileName = fileName
        pendingAction = action
        pendingMaxSeconds = maxSeconds

        val missing = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(act, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            act.requestPermissions(missing.toTypedArray(), REQ_PERMISSIONS)
            return
        }
        launchCamera(act)
    }

    private fun launchCamera(act: Activity) {
        val dir = File(act.cacheDir, "evidence").apply { mkdirs() }
        val outFile = File(dir, pendingFileName!!)
        pendingOutputPath = outFile.absolutePath
        val uri = FileProvider.getUriForFile(act, act.packageName + ".fileprovider", outFile)

        val intent = if (pendingAction == "video") {
            Intent(MediaStore.ACTION_VIDEO_CAPTURE)
                .putExtra(MediaStore.EXTRA_DURATION_LIMIT, pendingMaxSeconds)
                .putExtra(MediaStore.EXTRA_VIDEO_QUALITY, 1)
        } else {
            Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        }
        intent.putExtra(MediaStore.EXTRA_OUTPUT, uri)
        intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)

        if (intent.resolveActivity(act.packageManager) == null) {
            fail("NO_CAMERA_APP", "No camera application available on this device")
            return
        }
        act.startActivityForResult(intent, REQ_CAPTURE)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != REQ_CAPTURE) return false
        if (resultCode != Activity.RESULT_OK) {
            succeed(null) // user cancelled
            return true
        }
        val file = pendingOutputPath?.let { File(it) }
        if (file == null || !file.exists() || file.length() == 0L) {
            fail("CAPTURE_EMPTY", "Camera returned no media")
            return true
        }
        succeed(mapOf("path" to file.absolutePath, "sizeBytes" to file.length()))
        return true
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ): Boolean {
        if (requestCode != REQ_PERMISSIONS) return false
        val act = activity
        val cameraIndex = permissions.indexOf(Manifest.permission.CAMERA)
        val cameraDenied = cameraIndex >= 0 &&
            grantResults.getOrNull(cameraIndex) != PackageManager.PERMISSION_GRANTED
        if (act == null || cameraDenied) {
            fail("PERMISSION_DENIED", "Camera permission is required to capture evidence")
            return true
        }
        // Location may be denied — capture still proceeds and the GPS block degrades.
        launchCamera(act)
        return true
    }

    private fun succeed(value: Any?) {
        val result = pendingResult
        clearPending()
        result?.success(value)
    }

    private fun fail(code: String, message: String) {
        val result = pendingResult
        clearPending()
        result?.error(code, message, null)
    }

    private fun clearPending() {
        pendingResult = null
        pendingFileName = null
        pendingOutputPath = null
        pendingAction = null
    }

    // --- Location -------------------------------------------------------

    /**
     * Replies with a single fix, or null when unavailable or denied.
     * ponytail: one-shot listener with a last-known fallback; no continuous track.
     */
    fun currentLocation(timeoutMs: Long, result: MethodChannel.Result) {
        val act = activity
        if (act == null) {
            result.success(null)
            return
        }
        val granted =
            ContextCompat.checkSelfPermission(act, Manifest.permission.ACCESS_FINE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED ||
                ContextCompat.checkSelfPermission(act, Manifest.permission.ACCESS_COARSE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED
        if (!granted) {
            result.success(null)
            return
        }

        val lm = act.getSystemService(Activity.LOCATION_SERVICE) as LocationManager
        val provider = when {
            lm.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            else -> null
        }
        if (provider == null) {
            result.success(null)
            return
        }

        var replied = false
        var listener: LocationListener? = null

        fun reply(loc: Location?) {
            if (replied) return
            replied = true
            listener?.let {
                try {
                    lm.removeUpdates(it)
                } catch (e: SecurityException) {
                    // permission revoked mid-flight; nothing to remove
                }
            }
            result.success(loc?.let { toMap(it) })
        }

        listener = object : LocationListener {
            override fun onLocationChanged(location: Location) = reply(location)
            override fun onProviderEnabled(provider: String) {}
            override fun onProviderDisabled(provider: String) = reply(lastKnown(lm))
            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
        }

        try {
            lm.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper())
        } catch (e: SecurityException) {
            result.success(null)
            return
        }
        Handler(Looper.getMainLooper()).postDelayed({ reply(lastKnown(lm)) }, timeoutMs)
    }

    private fun lastKnown(lm: LocationManager): Location? = try {
        listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
            .mapNotNull { lm.getLastKnownLocation(it) }
            .maxByOrNull { it.time }
    } catch (e: SecurityException) {
        null
    }

    private fun toMap(loc: Location): Map<String, Any> = mapOf(
        "latitude" to loc.latitude,
        "longitude" to loc.longitude,
        "altitude" to loc.altitude,
        "accuracyMeters" to loc.accuracy.toDouble(),
        "fixAgeSeconds" to ((System.currentTimeMillis() - loc.time) / 1000L).coerceAtLeast(0L)
    )

    companion object {
        private const val REQ_CAPTURE = 7301
        private const val REQ_PERMISSIONS = 7302
        private val REQUIRED_PERMISSIONS = listOf(
            Manifest.permission.CAMERA,
            Manifest.permission.ACCESS_FINE_LOCATION
        )
    }
}
