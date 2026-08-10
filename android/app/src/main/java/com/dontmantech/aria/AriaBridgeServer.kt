package com.dontmantech.aria

import android.content.Context
import android.util.Log
import fi.iki.elonen.NanoHTTPD
import org.json.JSONObject

/**
 * HTTP bridge server that runs on port 8420 inside the companion app.
 * The ARIA phone_control skill connects to http://127.0.0.1:8420/aria/<action>
 * to control the phone.
 */
class AriaBridgeServer(
    private val context: Context,
    port: Int = AriaApp.BRIDGE_PORT
) : NanoHTTPD(port) {

    private val TAG = "ARIA-Bridge"
    private val controller = DeviceController(context)

    override fun serve(session: IHTTPSession): Response {
        val uri = session.uri.trimStart('/')
        val params = session.parameters

        return try {
            when {
                uri.startsWith("aria/status") -> jsonResponse(controller.status())
                uri.startsWith("aria/device_info") -> jsonResponse(controller.deviceInfo().toString())
                uri.startsWith("aria/toggle_wifi") -> {
                    val state = params["state"]?.firstOrNull() ?: "on"
                    jsonResponse(controller.toggleWifi(state))
                }
                uri.startsWith("aria/toggle_bluetooth") -> {
                    val state = params["state"]?.firstOrNull() ?: "on"
                    jsonResponse(controller.toggleBluetooth(state))
                }
                uri.startsWith("aria/toggle_airplane_mode") -> {
                    val state = params["state"]?.firstOrNull() ?: "on"
                    jsonResponse(controller.toggleAirplaneMode(state))
                }
                uri.startsWith("aria/toggle_flashlight") -> {
                    val state = params["state"]?.firstOrNull() ?: "on"
                    jsonResponse(controller.toggleFlashlight(state))
                }
                uri.startsWith("aria/toggle_dnd") -> {
                    val state = params["state"]?.firstOrNull() ?: "on"
                    jsonResponse(controller.toggleDnd(state))
                }
                uri.startsWith("aria/set_brightness") -> {
                    val level = params["level"]?.firstOrNull()?.toIntOrNull() ?: 50
                    jsonResponse(controller.setBrightness(level))
                }
                uri.startsWith("aria/set_volume") -> {
                    val level = params["level"]?.firstOrNull()?.toIntOrNull() ?: 50
                    jsonResponse(controller.setVolume(level))
                }
                uri.startsWith("aria/battery") -> jsonResponse(controller.battery())
                uri.startsWith("aria/notify") -> {
                    val title = params["title"]?.firstOrNull() ?: "ARIA"
                    val body = params["body"]?.firstOrNull() ?: ""
                    jsonResponse(controller.notify(title, body))
                }
                uri.startsWith("aria/screenshot") -> jsonResponse(controller.screenshot())
                uri.startsWith("aria/set_alarm") -> {
                    val time = params["time"]?.firstOrNull() ?: "07:00"
                    jsonResponse(controller.setAlarm(time))
                }
                uri.startsWith("aria/open_app") -> {
                    val pkg = params["package"]?.firstOrNull() ?: ""
                    jsonResponse(controller.openApp(pkg))
                }
                uri.startsWith("aria/open_url") -> {
                    val url = params["url"]?.firstOrNull() ?: ""
                    jsonResponse(controller.openUrl(url))
                }

                // File operations
                uri.startsWith("aria/file_list") -> {
                    val path = params["path"]?.firstOrNull() ?: "/"
                    jsonResponse(controller.fileList(path))
                }
                uri.startsWith("aria/file_read") -> {
                    val path = params["path"]?.firstOrNull() ?: ""
                    jsonResponse(controller.fileRead(path))
                }
                uri.startsWith("aria/file_write") -> {
                    val path = params["path"]?.firstOrNull() ?: ""
                    val content = params["content"]?.firstOrNull() ?: ""
                    jsonResponse(controller.fileWrite(path, content))
                }
                uri.startsWith("aria/file_move") -> {
                    val src = params["src"]?.firstOrNull() ?: ""
                    val dest = params["dest"]?.firstOrNull() ?: ""
                    jsonResponse(controller.fileMove(src, dest))
                }
                uri.startsWith("aria/file_copy") -> {
                    val src = params["src"]?.firstOrNull() ?: ""
                    val dest = params["dest"]?.firstOrNull() ?: ""
                    jsonResponse(controller.fileCopy(src, dest))
                }
                uri.startsWith("aria/file_delete") -> {
                    val path = params["path"]?.firstOrNull() ?: ""
                    jsonResponse(controller.fileDelete(path))
                }
                uri.startsWith("aria/file_search") -> {
                    val dir = params["dir"]?.firstOrNull() ?: "/"
                    val query = params["query"]?.firstOrNull() ?: ""
                    jsonResponse(controller.fileSearch(dir, query))
                }
                uri.startsWith("aria/file_mkdir") -> {
                    val path = params["path"]?.firstOrNull() ?: ""
                    jsonResponse(controller.fileMkdir(path))
                }

                // Voice command passthrough to ARIA server (optional)
                uri.startsWith("aria/voice_command") -> {
                    val command = params["command"]?.firstOrNull() ?: ""
                    // This will be handled by the voice service forwarding to ARIA
                    val result = (context.applicationContext as? AriaApp)
                        ?.let { VoiceController.sendToAria(it, command) }
                        ?: "Voice controller not available"
                    jsonResponse(result)
                }

                uri.isEmpty() || uri == "favicon.ico" -> {
                    jsonResponse("""{"status":"online","app":"aria-companion","version":"1.0"}""")
                }
                else -> {
                    Log.w(TAG, "Unknown endpoint: $uri")
                    jsonResponse("""{"success":false,"error":"Unknown endpoint: $uri"}""")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error handling $uri", e)
            jsonResponse("""{"success":false,"error":"${e.message}"}""")
        }
    }

    private fun jsonResponse(text: String): Response {
        val r = newFixedLengthResponse(Response.Status.OK, "application/json", text)
        r.addHeader("Access-Control-Allow-Origin", "*")
        r.addHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        r.addHeader("Access-Control-Allow-Headers", "*")
        return r
    }

    fun startBridge() {
        try {
            start(SOCKET_READ_TIMEOUT, false)
            Log.i(TAG, "ARIA bridge started on port ${AriaApp.BRIDGE_PORT}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start bridge", e)
        }
    }

    fun stopBridge() {
        stop()
        Log.i(TAG, "ARIA bridge stopped")
    }
}
