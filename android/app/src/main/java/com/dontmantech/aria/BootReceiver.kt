package com.dontmantech.aria

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            // Start the bridge service on boot
            AriaBridgeService.start(context, voiceEnabled = false)
        }
    }
}
