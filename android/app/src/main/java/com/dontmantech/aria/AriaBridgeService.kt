package com.dontmantech.aria

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * Foreground service that keeps the ARIA bridge server running and
 * background voice wake word listening active, even when the screen is off.
 */
class AriaBridgeService : Service() {

    private val TAG = "ARIA-Service"
    private var bridgeServer: AriaBridgeServer? = null
    private var voiceController: VoiceController? = null
    private var voiceEnabled = false

    override fun onCreate() {
        super.onCreate()
        bridgeServer = AriaBridgeServer(this)
        voiceController = VoiceController(this)
        Log.i(TAG, "Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        voiceEnabled = intent?.getBooleanExtra(EXTRA_VOICE_ENABLED, false) ?: false

        startForegroundNotification()

        // Start the HTTP bridge server
        bridgeServer?.startBridge()

        // Start voice listening if enabled
        if (voiceEnabled) {
            voiceController?.startListening()
        }

        return START_STICKY
    }

    private fun startForegroundNotification() {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, AriaApp.CHANNEL_SERVICE)
            .setContentTitle("ARIA Companion Active")
            .setContentText(
                if (voiceEnabled) "Bridge + voice listening active"
                else "Bridge active (voice off)"
            )
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            val type = if (voiceEnabled)
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            else
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            startForeground(AriaApp.NOTIFICATION_ID, notification, type)
        } else {
            startForeground(AriaApp.NOTIFICATION_ID, notification)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        voiceController?.stopListening()
        bridgeServer?.stopBridge()
        Log.i(TAG, "Service destroyed")
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Restart service if task is removed (app swiped away)
        val restartIntent = Intent(applicationContext, AriaBridgeService::class.java)
            .putExtra(EXTRA_VOICE_ENABLED, voiceEnabled)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(restartIntent)
        } else {
            startService(restartIntent)
        }
        super.onTaskRemoved(rootIntent)
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val EXTRA_VOICE_ENABLED = "voice_enabled"

        fun start(context: Context, voiceEnabled: Boolean) {
            val intent = Intent(context, AriaBridgeService::class.java)
                .putExtra(EXTRA_VOICE_ENABLED, voiceEnabled)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, AriaBridgeService::class.java))
        }
    }
}
