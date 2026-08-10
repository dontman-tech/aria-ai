package com.dontmantech.aria

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import android.util.Log

class AriaApp : Application() {

    override fun onCreate() {
        // Install a crash handler BEFORE anything else can fail.
        // We persist the stack trace to SharedPreferences so the next launch
        // can surface it to the user (and to us for debugging).
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            try {
                val trace = Log.getStackTraceString(throwable)
                getSharedPreferences("aria_crash", Context.MODE_PRIVATE)
                    .edit()
                    .putString("last_crash", trace)
                    .putLong("last_crash_time", System.currentTimeMillis())
                    .apply()
            } catch (_: Exception) {
            }
            // Defer to the default handler so Android still shows the "app stopped" dialog.
            defaultHandler?.uncaughtException(thread, throwable)
        }

        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                val nm = getSystemService(NotificationManager::class.java)

                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_SERVICE,
                        "ARIA Service",
                        NotificationManager.IMPORTANCE_LOW
                    ).apply {
                        description = "Keeps ARIA bridge running for voice and device control"
                        setShowBadge(false)
                    }
                )

                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_NOTIFY,
                        "ARIA Messages",
                        NotificationManager.IMPORTANCE_DEFAULT
                    ).apply {
                        description = "Notifications from ARIA"
                    }
                )

                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ALERT,
                        "ARIA Alerts",
                        NotificationManager.IMPORTANCE_HIGH
                    ).apply {
                        description = "High-priority ARIA alerts"
                    }
                )
            } catch (e: Exception) {
                Log.e(TAG, "Failed to create notification channels", e)
            }
        }
    }

    companion object {
        private const val TAG = "ARIA-App"
        private val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()

        const val CHANNEL_SERVICE = "aria_service"
        const val CHANNEL_NOTIFY = "aria_notify"
        const val CHANNEL_ALERT = "aria_alert"
        const val BRIDGE_PORT = 8420
        const val NOTIFICATION_ID = 8420
    }
}
