package com.dontmantech.aria

import android.app.Notification
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.PowerManager
import android.provider.AlarmClock
import android.provider.MediaStore
import android.provider.Settings
import android.util.Log
import androidx.core.app.NotificationCompat
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Controls all device hardware and system services.
 * Each method returns a JSON response for the HTTP bridge.
 */
class DeviceController(private val context: Context) {

    private val TAG = "ARIA-Device"
    private val audioManager: AudioManager? = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
    private val wifiManager: WifiManager? = context.getSystemService(Context.WIFI_SERVICE) as? WifiManager
    private val powerManager: PowerManager? = context.getSystemService(Context.POWER_SERVICE) as? PowerManager
    private var cameraManager: CameraManager? = null
    private var cameraId: String? = null
    private var flashOn = false

    init {
        try {
            cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as? CameraManager
            cameraId = cameraManager?.cameraIdList?.firstOrNull { id ->
                cameraManager?.getCameraCharacteristics(id)
                    ?.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            }
        } catch (e: Exception) {
            Log.e(TAG, "Camera init failed", e)
        }
    }

    fun status(): String = json {
        put("status", "online")
        put("app", "aria-companion")
        put("version", "1.0")
        put("model", android.os.Build.MODEL)
        put("android_version", android.os.Build.VERSION.RELEASE)
    }

    fun deviceInfo(): String = json {
        put("model", android.os.Build.MODEL)
        put("manufacturer", android.os.Build.MANUFACTURER)
        put("brand", android.os.Build.BRAND)
        put("android_version", android.os.Build.VERSION.RELEASE)
        put("sdk", android.os.Build.VERSION.SDK_INT)
        val pm = context.packageManager
        put("app_version", pm.getPackageInfo(context.packageName, 0)?.versionName ?: "unknown")
    }

    fun toggleWifi(state: String): String {
        return try {
            val on = state == "on"
            val mgr = wifiManager
            if (mgr == null) return jsonError("wifi_toggle", "WifiManager unavailable")
            @Suppress("DEPRECATION")
            mgr.isWifiEnabled = on
            json { put("wifi", if (on) "on" else "off"); put("success", true) }
        } catch (e: SecurityException) {
            jsonError("wifi_toggle", "Permission denied. Enable WRITE_SETTINGS or use Android settings.")
        } catch (e: Exception) {
            jsonError("wifi_toggle", e.message ?: "failed")
        }
    }

    fun toggleBluetooth(state: String): String {
        return try {
            val on = state == "on"
            val adapter = android.bluetooth.BluetoothAdapter.getDefaultAdapter()
            if (adapter == null) return jsonError("bluetooth", "No Bluetooth adapter")
            if (on) adapter.enable() else adapter.disable()
            json { put("bluetooth", if (on) "on" else "off"); put("success", true) }
        } catch (e: SecurityException) {
            jsonError("bluetooth_toggle", "Permission denied")
        } catch (e: Exception) {
            jsonError("bluetooth_toggle", e.message ?: "failed")
        }
    }

    fun toggleAirplaneMode(state: String): String {
        return try {
            val on = state == "on"
            // Toggle global airplane_mode setting (requires WRITE_SETTINGS)
            Settings.Global.putInt(
                context.contentResolver,
                Settings.Global.AIRPLANE_MODE_ON,
                if (on) 1 else 0
            )
            // Broadcast the change
            val intent = Intent(Intent.ACTION_AIRPLANE_MODE_CHANGED)
                .putExtra("state", on)
            context.sendBroadcast(intent)
            json { put("airplane_mode", if (on) "on" else "off"); put("success", true) }
        } catch (e: SecurityException) {
            jsonError("airplane_mode", "Permission denied. Requires WRITE_SETTINGS.")
        } catch (e: Exception) {
            jsonError("airplane_mode", e.message ?: "failed")
        }
    }

    fun toggleFlashlight(state: String): String {
        return try {
            val on = state == "on"
            val camId = cameraId ?: return jsonError("flashlight", "No flash available")
            cameraManager?.setTorchMode(camId, on)
            flashOn = on
            json { put("flashlight", if (on) "on" else "off"); put("success", true) }
        } catch (e: Exception) {
            jsonError("flashlight", e.message ?: "failed")
        }
    }

    fun toggleDnd(state: String): String {
        return try {
            val on = state == "on"
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                val filter = if (on)
                    NotificationManager.INTERRUPTION_FILTER_PRIORITY
                else
                    NotificationManager.INTERRUPTION_FILTER_ALL
                nm.setInterruptionFilter(filter)
            }
            json { put("dnd", if (on) "on" else "off"); put("success", true) }
        } catch (e: Exception) {
            jsonError("dnd", e.message ?: "failed")
        }
    }

    fun setBrightness(level: Int): String {
        return try {
            // 0-255 brightness value
            val brightness = level.coerceIn(0, 255)
            if (!Settings.System.canWrite(context)) {
                return jsonError("brightness", "WRITE_SETTINGS permission required. Open ARIA settings to grant.")
            }
            // Set manual mode first
            Settings.System.putInt(
                context.contentResolver,
                Settings.System.SCREEN_BRIGHTNESS_MODE,
                Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL
            )
            Settings.System.putInt(
                context.contentResolver,
                Settings.System.SCREEN_BRIGHTNESS,
                brightness
            )
            json { put("brightness", brightness); put("success", true) }
        } catch (e: Exception) {
            jsonError("brightness", e.message ?: "failed")
        }
    }

    fun setVolume(level: Int): String {
        return try {
            val mgr = audioManager
            if (mgr == null) return jsonError("volume", "AudioManager unavailable")
            val maxVol = mgr.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            val vol = (level.toDouble() / 100.0 * maxVol).toInt().coerceIn(0, maxVol)
            mgr.setStreamVolume(
                AudioManager.STREAM_MUSIC,
                vol,
                AudioManager.FLAG_SHOW_UI
            )
            json { put("volume", vol); put("max", maxVol); put("success", true) }
        } catch (e: Exception) {
            jsonError("volume", e.message ?: "failed")
        }
    }

    fun battery(): String {
        return try {
            val intentFilter = android.content.IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            val battery = context.registerReceiver(null, intentFilter)
            val level = battery?.getIntExtra(android.os.BatteryManager.EXTRA_LEVEL, -1) ?: -1
            val scale = battery?.getIntExtra(android.os.BatteryManager.EXTRA_SCALE, -1) ?: -1
            val pct = if (level >= 0 && scale > 0) (level * 100 / scale) else -1
            val plugged = battery?.getIntExtra(android.os.BatteryManager.EXTRA_PLUGGED, 0) ?: 0
            val status = battery?.getIntExtra(android.os.BatteryManager.EXTRA_STATUS, -1) ?: -1
            val charging = status == android.os.BatteryManager.BATTERY_STATUS_CHARGING ||
                    status == android.os.BatteryManager.BATTERY_STATUS_FULL

            json {
                put("level", pct)
                put("charging", charging)
                put("plugged", plugged != 0)
                put("success", true)
            }
        } catch (e: Exception) {
            jsonError("battery", e.message ?: "failed")
        }
    }

    fun notify(title: String, body: String): String {
        return try {
            val notification = NotificationCompat.Builder(context, AriaApp.CHANNEL_NOTIFY)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(body)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .build()

            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val notifId = (System.currentTimeMillis() % Int.MAX_VALUE).toInt()
            nm.notify(notifId, notification)

            json { put("notification", "sent"); put("title", title); put("success", true) }
        } catch (e: Exception) {
            jsonError("notify", e.message ?: "failed")
        }
    }

    fun screenshot(): String {
        // Screenshot requires MediaProjection API which needs a user consent activity.
        // For now, we'll capture the current visible screen if we have the permission.
        // A full screenshot implementation would need ScreenCaptureActivity
        return jsonError("screenshot",
            "Screenshot requires MediaProjection consent. Use the ARIA dashboard screenshot instead.")
    }

    fun setAlarm(time: String): String {
        return try {
            val intent = Intent(AlarmClock.ACTION_SET_ALARM).apply {
                putExtra(AlarmClock.EXTRA_MESSAGE, "ARIA alarm")
                // Parse time like "07:30" or "14:00"
                val parts = time.trim().split(":")
                if (parts.size == 2) {
                    putExtra(AlarmClock.EXTRA_HOUR, parts[0].toIntOrNull() ?: 7)
                    putExtra(AlarmClock.EXTRA_MINUTES, parts[1].toIntOrNull() ?: 0)
                    putExtra(AlarmClock.EXTRA_SKIP_UI, false)
                }
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            json { put("alarm", time); put("success", true) }
        } catch (e: Exception) {
            jsonError("alarm", e.message ?: "failed")
        }
    }

    fun openApp(packageName: String): String {
        return try {
            val intent = context.packageManager.getLaunchIntentForPackage(packageName)
                ?: return jsonError("open_app", "App not found: $packageName")
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            json { put("app", packageName); put("success", true) }
        } catch (e: Exception) {
            jsonError("open_app", e.message ?: "failed")
        }
    }

    fun openUrl(url: String): String {
        return try {
            val fixedUrl = if (!url.startsWith("http")) "https://$url" else url
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(fixedUrl)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            json { put("url", fixedUrl); put("success", true) }
        } catch (e: Exception) {
            jsonError("open_url", e.message ?: "failed")
        }
    }

    // --- File operations ---

    fun fileList(path: String): String {
        return try {
            val dir = if (path.isEmpty() || path == "/")
                Environment.getExternalStorageDirectory()
            else File(path)

            if (!dir.exists() || !dir.isDirectory) {
                return jsonError("file_list", "Directory not found: $path")
            }

            val files = dir.listFiles() ?: emptyArray()
            val arr = org.json.JSONArray()
            for (f in files) {
                arr.put(jsonObject {
                    put("name", f.name)
                    put("path", f.absolutePath)
                    put("type", if (f.isDirectory) "dir" else "file")
                    put("size", f.length())
                    put("modified", f.lastModified())
                })
            }
            json {
                put("path", dir.absolutePath)
                put("files", arr)
                put("count", files.size)
                put("success", true)
            }
        } catch (e: Exception) {
            jsonError("file_list", e.message ?: "failed")
        }
    }

    fun fileRead(path: String): String {
        return try {
            val file = File(path)
            if (!file.exists()) return jsonError("file_read", "File not found: $path")
            val content = file.readText()
            json {
                put("path", path)
                put("content", content)
                put("size", file.length())
                put("success", true)
            }
        } catch (e: Exception) {
            jsonError("file_read", e.message ?: "failed")
        }
    }

    fun fileWrite(path: String, content: String): String {
        return try {
            val file = File(path)
            file.parentFile?.mkdirs()
            file.writeText(content)
            json { put("path", path); put("bytes", file.length()); put("success", true) }
        } catch (e: Exception) {
            jsonError("file_write", e.message ?: "failed")
        }
    }

    fun fileMove(srcPath: String, destPath: String): String {
        return try {
            val src = File(srcPath)
            val dest = File(destPath)
            if (!src.exists()) return jsonError("file_move", "Source not found: $srcPath")
            dest.parentFile?.mkdirs()
            if (src.renameTo(dest)) {
                json { put("from", srcPath); put("to", destPath); put("success", true) }
            } else {
                // Fallback: copy then delete
                src.copyTo(dest, overwrite = true)
                src.delete()
                json { put("from", srcPath); put("to", destPath); put("success", true) }
            }
        } catch (e: Exception) {
            jsonError("file_move", e.message ?: "failed")
        }
    }

    fun fileCopy(srcPath: String, destPath: String): String {
        return try {
            val src = File(srcPath)
            val dest = File(destPath)
            if (!src.exists()) return jsonError("file_copy", "Source not found: $srcPath")
            dest.parentFile?.mkdirs()
            src.copyTo(dest, overwrite = true)
            json { put("from", srcPath); put("to", destPath); put("success", true) }
        } catch (e: Exception) {
            jsonError("file_copy", e.message ?: "failed")
        }
    }

    fun fileDelete(path: String): String {
        return try {
            val file = File(path)
            if (!file.exists()) return jsonError("file_delete", "File not found: $path")
            val deleted = file.deleteRecursively()
            json { put("path", path); put("deleted", deleted); put("success", deleted) }
        } catch (e: Exception) {
            jsonError("file_delete", e.message ?: "failed")
        }
    }

    fun fileSearch(dirPath: String, query: String): String {
        return try {
            val dir = File(dirPath)
            if (!dir.exists()) return jsonError("file_search", "Directory not found")
            val results = mutableListOf<JSONObject>()
            dir.walkTopDown().forEach { f ->
                if (f.name.contains(query, ignoreCase = true)) {
                    results.add(jsonObject {
                        put("name", f.name)
                        put("path", f.absolutePath)
                        put("type", if (f.isDirectory) "dir" else "file")
                    })
                }
                if (results.size >= 50) return@forEach
            }
            val arr = org.json.JSONArray()
            results.forEach { arr.put(it) }
            json { put("query", query); put("results", arr); put("count", results.size); put("success", true) }
        } catch (e: Exception) {
            jsonError("file_search", e.message ?: "failed")
        }
    }

    fun fileMkdir(path: String): String {
        return try {
            val dir = File(path)
            val created = dir.mkdirs()
            json { put("path", path); put("created", created); put("success", true) }
        } catch (e: Exception) {
            jsonError("file_mkdir", e.message ?: "failed")
        }
    }

    // --- Helpers ---

    private inline fun jsonObject(init: JSONObject.() -> Unit): JSONObject =
        JSONObject().apply(init)

    private inline fun json(init: JSONObject.() -> Unit): String =
        JSONObject().apply(init).toString()

    private fun jsonError(action: String, message: String): String {
        return JSONObject()
            .put("success", false)
            .put("action", action)
            .put("error", message)
            .toString()
    }

    private fun JSONObject.put(key: String, value: Any?): JSONObject {
        return this.putOpt(key, value ?: JSONObject.NULL)
    }
}
