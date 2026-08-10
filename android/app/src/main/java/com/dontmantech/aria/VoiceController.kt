package com.dontmantech.aria

import android.content.Context
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

/**
 * Voice controller: background wake word detection using Android SpeechRecognizer.
 * Listens for "ARIA" wake word, then captures a command and forwards it to the
 * ARIA web server running on the phone.
 *
 * The ARIA server URL is configurable; default is http://127.0.0.1:5000
 */
class VoiceController(private val context: Context) {

    private val TAG = "ARIA-Voice"
    private var speechRecognizer: SpeechRecognizer? = null
    private var listening = false
    private var ariaServerUrl = "http://127.0.0.1:5000"

    fun startListening() {
        if (listening) return
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            Log.w(TAG, "Speech recognition not available on this device")
            return
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context)
        speechRecognizer?.setRecognitionListener(AriaRecognitionListener())
        listening = true
        startRecognition()
        Log.i(TAG, "Voice wake word listening started")
    }

    fun stopListening() {
        listening = false
        speechRecognizer?.stopListening()
        speechRecognizer?.destroy()
        speechRecognizer = null
        Log.i(TAG, "Voice wake word listening stopped")
    }

    private fun startRecognition() {
        if (!listening) return
        val intent = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        }
        try {
            speechRecognizer?.startListening(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start recognition", e)
            // Retry after delay
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                if (listening) startRecognition()
            }, 2000)
        }
    }

    private inner class AriaRecognitionListener : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}
        override fun onError(error: Int) {
            // Restart listening after a brief delay
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                if (listening) startRecognition()
            }, 500)
        }

        override fun onResults(results: Bundle?) {
            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            val text = matches?.firstOrNull()?.lowercase() ?: ""
            Log.d(TAG, "Heard: $text")

            if (text.contains("aria")) {
                // Wake word detected! Extract the command after "aria"
                val command = text.substringAfter("aria").trim()
                if (command.isNotEmpty()) {
                    Log.i(TAG, "Wake word detected, command: $command")
                    CoroutineScope(Dispatchers.IO).launch {
                        sendToAria(context, command)
                    }
                } else {
                    Log.i(TAG, "Wake word detected, waiting for command...")
                    // Start a new recognition for the command
                    startRecognition()
                }
            }
            // Continue listening
            if (listening) startRecognition()
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val partial = partialResults
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                ?.lowercase() ?: ""
            // Quick check for wake word in partial results
            if (partial.contains("aria") && !listening) {
                onResults(partialResults)
            }
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    companion object {
        private const val TAG = "ARIA-Voice"

        /**
         * Send a voice command to the ARIA web server.
         * The ARIA server processes it through skills + LLM brain.
         */
        fun sendToAria(context: Context, command: String): String {
            return try {
                val url = URL("http://127.0.0.1:5000/api/chat")
                val conn = (url.openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    setRequestProperty("Content-Type", "application/json")
                    connectTimeout = 10000
                    readTimeout = 30000
                    doOutput = true
                }
                val body = JSONObject().put("message", command).toString()
                conn.outputStream.use { it.write(body.toByteArray()) }

                val responseCode = conn.responseCode
                if (responseCode == 200) {
                    val response = conn.inputStream.bufferedReader().use { it.readText() }
                    val json = JSONObject(response)
                    val ariaResponse = json.optString("response", "No response")
                    val success = json.optBoolean("success", false)

                    // Show ARIA's response as a notification
                    if (success) {
                        showAriaResponseNotification(context, ariaResponse)
                    }
                    response
                } else {
                    """{"success":false,"error":"ARIA server returned $responseCode"}"""
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send command to ARIA server", e)
                """{"success":false,"error":"ARIA server not reachable. Is the web server running?"}"""
            }
        }

        private fun showAriaResponseNotification(context: Context, response: String) {
            try {
                val notification = androidx.core.app.NotificationCompat.Builder(
                    context, AriaApp.CHANNEL_NOTIFY
                )
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle("ARIA")
                    .setContentText(response.take(100))
                    .setStyle(
                        androidx.core.app.NotificationCompat.BigTextStyle()
                            .bigText(response)
                    )
                    .setPriority(androidx.core.app.NotificationCompat.PRIORITY_DEFAULT)
                    .setAutoCancel(true)
                    .build()

                val nm = context.getSystemService(Context.NOTIFICATION_SERVICE)
                        as android.app.NotificationManager
                val notifId = (System.currentTimeMillis() % Int.MAX_VALUE).toInt()
                nm.notify(notifId, notification)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to show response notification", e)
            }
        }
    }
}
