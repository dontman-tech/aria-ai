package com.dontmantech.aria

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class AriaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)

            // Foreground service channel (persistent notification for bridge service)
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

            // Notification channel for ARIA messages
            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_NOTIFY,
                    "ARIA Messages",
                    NotificationManager.IMPORTANCE_DEFAULT
                ).apply {
                    description = "Notifications from ARIA"
                }
            )

            // High priority for wake word alerts
            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ALERT,
                    "ARIA Alerts",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "High-priority ARIA alerts"
                }
            )
        }
    }

    companion object {
        const val CHANNEL_SERVICE = "aria_service"
        const val CHANNEL_NOTIFY = "aria_notify"
        const val CHANNEL_ALERT = "aria_alert"
        const val BRIDGE_PORT = 8420
        const val NOTIFICATION_ID = 8420
    }
}
