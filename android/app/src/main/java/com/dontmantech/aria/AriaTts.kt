package com.dontmantech.aria

import android.content.Context
import android.speech.tts.TextToSpeech
import android.util.Log
import java.util.Locale

/**
 * TTS for the ARIA companion: speaks ARIA's responses aloud so the assistant
 * is actually a voice assistant on the phone, not just notifications.
 *
 * Initialized lazily and asynchronously; speak() is a no-op until the engine
 * is ready. Calls queue per utterance ID so we can pause wake-word listening
 * while ARIA talks (avoids the mic hearing its own voice).
 */
class AriaTts(context: Context, private val onSpeakingChanged: (speaking: Boolean) -> Unit) {

    private val TAG = "ARIA-TTS"
    private var tts: TextToSpeech? = null
    private var ready = false
    private var pending: String? = null
    private val queue = ArrayDeque<String>()

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            ready = status == TextToSpeech.SUCCESS
            if (ready) {
                tts?.language = Locale.getDefault()
                Log.i(TAG, "TTS ready")
                // Speak anything queued while the engine was warming up.
                pending?.let { speak(it) }
                pending = null
            } else {
                Log.w(TAG, "TTS init failed (status=$status); responses stay text-only")
            }
        }
    }

    val isSpeaking: Boolean
        get() = ready && (tts?.isSpeaking == true)

    /** Speak [text]. Falls back silently if TTS is unavailable (graceful degradation). */
    fun speak(text: String) {
        val clean = text.replace(Regex("[*_`#>]"), "").trim()
        if (clean.isEmpty()) return
        if (!ready) {
            pending = clean
            return
        }
        if (queue.size > 2) queue.clear() // don't pile up stale replies
        queue.addLast(clean)
        flushQueue()
    }

    private fun flushQueue() {
        if (!ready || queue.isEmpty() || tts?.isSpeaking == true) return
        val utterance = queue.removeFirst()
        onSpeakingChanged(true)
        tts?.setOnUtteranceProgressListener(object : android.speech.tts.UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) {
                if (queue.isEmpty()) onSpeakingChanged(false)
                else flushQueue()
            }
            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) {
                onSpeakingChanged(false)
            }
        })
        tts?.speak(utterance, TextToSpeech.QUEUE_ADD, null, "aria_${System.currentTimeMillis()}")
    }

    /** Stop playback immediately (e.g. wake word heard while ARIA is talking). */
    fun stop() {
        queue.clear()
        pending = null
        tts?.stop()
        onSpeakingChanged(false)
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ready = false
    }
}
