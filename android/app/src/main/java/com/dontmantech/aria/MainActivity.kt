package com.dontmantech.aria

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.SwitchCompat
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var voiceSwitch: SwitchCompat
    private lateinit var startButton: Button
    private lateinit var stopButton: Button
    private lateinit var permButton: Button
    private lateinit var storagePermButton: Button
    private lateinit var settingsPermButton: Button

    private var serviceRunning = false

    private val requiredPermissions: Array<String>
        get() = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            arrayOf(
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.CAMERA,
                Manifest.permission.POST_NOTIFICATIONS,
                Manifest.permission.READ_MEDIA_AUDIO,
                Manifest.permission.READ_MEDIA_IMAGES,
                Manifest.permission.READ_MEDIA_VIDEO,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
        } else {
            arrayOf(
                Manifest.permission.RECORD_AUDIO,
                Manifest.permission.CAMERA,
                Manifest.permission.READ_EXTERNAL_STORAGE,
                Manifest.permission.WRITE_EXTERNAL_STORAGE,
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
        }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val allGranted = results.values.all { it }
        if (allGranted) {
            updateStatus("Permissions granted. Ready to start.")
            Toast.makeText(this, "Permissions granted", Toast.LENGTH_SHORT).show()
        } else {
            val denied = results.filter { !it.value }.keys
            updateStatus("Some permissions denied: ${denied.size}")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        voiceSwitch = findViewById(R.id.voiceSwitch)
        startButton = findViewById(R.id.startButton)
        stopButton = findViewById(R.id.stopButton)
        permButton = findViewById(R.id.permButton)
        storagePermButton = findViewById(R.id.storagePermButton)
        settingsPermButton = findViewById(R.id.settingsPermButton)

        // Check initial permission status
        checkPermissions()

        // If the app crashed on a previous launch, surface the stack trace so we can debug.
        val crashPrefs = getSharedPreferences("aria_crash", Context.MODE_PRIVATE)
        val lastCrash = crashPrefs.getString("last_crash", null)
        if (!lastCrash.isNullOrEmpty()) {
            val time = crashPrefs.getLong("last_crash_time", 0)
            val ago = (System.currentTimeMillis() - time) / 1000
            updateStatus("Previous crash detected (${ago}s ago):\n\n$lastCrash\n\nThis report has been saved. Clearing it now.")
            // Clear it so it only shows once.
            crashPrefs.edit().clear().apply()
        }

        // Request all permissions button
        permButton.setOnClickListener {
            requestPermissions()
        }

        // Request MANAGE_EXTERNAL_STORAGE (all files access) - Android 11+
        storagePermButton.setOnClickListener {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                        .setData(Uri.parse("package:$packageName"))
                    startActivity(intent)
                } catch (e: Exception) {
                    val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    startActivity(intent)
                }
            } else {
                requestPermissions()
            }
        }

        // Request WRITE_SETTINGS permission
        settingsPermButton.setOnClickListener {
            if (!Settings.System.canWrite(this)) {
                val intent = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS)
                    .setData(Uri.parse("package:$packageName"))
                startActivity(intent)
            } else {
                Toast.makeText(this, "Write settings already granted", Toast.LENGTH_SHORT).show()
            }
        }

        // Start service
        startButton.setOnClickListener {
            if (!hasAllPermissions()) {
                Toast.makeText(this, "Please grant permissions first", Toast.LENGTH_LONG).show()
                requestPermissions()
                return@setOnClickListener
            }
            AriaBridgeService.start(this, voiceSwitch.isChecked)
            serviceRunning = true
            updateServiceUI()
            updateStatus(
                "ARIA bridge started on port ${AriaApp.BRIDGE_PORT}\n" +
                "Voice listening: ${if (voiceSwitch.isChecked) "ON" else "OFF"}"
            )
            Toast.makeText(this, "ARIA bridge started", Toast.LENGTH_SHORT).show()
        }

        // Stop service
        stopButton.setOnClickListener {
            AriaBridgeService.stop(this)
            serviceRunning = false
            updateServiceUI()
            updateStatus("ARIA bridge stopped")
            Toast.makeText(this, "ARIA bridge stopped", Toast.LENGTH_SHORT).show()
        }

        // Auto-start on first launch if permissions are granted
        if (hasAllPermissions()) {
            startButton.performClick()
        }
    }

    override fun onResume() {
        super.onResume()
        checkPermissions()
        updateServiceUI()
    }

    private fun checkPermissions() {
        val ungranted = requiredPermissions.count {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (ungranted > 0) {
            updateStatus("$ungranted permission(s) needed. Tap 'Grant Permissions'.")
        } else if (!serviceRunning) {
            updateStatus("Permissions OK. Tap 'Start ARIA Bridge' to begin.")
        }
    }

    private fun requestPermissions() {
        val toRequest = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }.toTypedArray()
        if (toRequest.isNotEmpty()) {
            permissionLauncher.launch(toRequest)
        }
    }

    private fun hasAllPermissions(): Boolean {
        return requiredPermissions.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    private fun updateServiceUI() {
        startButton.isEnabled = !serviceRunning
        stopButton.isEnabled = serviceRunning
    }

    private fun updateStatus(msg: String) {
        statusText.text = msg
    }
}
