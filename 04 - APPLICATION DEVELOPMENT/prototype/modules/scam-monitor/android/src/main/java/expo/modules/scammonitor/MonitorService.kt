package expo.modules.scammonitor

import android.app.*
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.*
import android.os.*
import android.os.Process
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.io.File
import java.io.RandomAccessFile
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.math.min

/** Native audio/network loop survives activity backgrounding; JS only renders UI. */
class MonitorService : Service() {
  companion object {
    @Volatile var active = false
    @Volatile var stopping = false
    @Volatile private var owner: MonitorService? = null
    @Volatile var paused = false
    @Volatile var held = false
    @Volatile var visible = true
    @Volatile var notificationOrigin: String? = null
    @Volatile var saveRequested = false
    @Volatile var retryRequested = false
    private var current = "{}"
    val archives = ConcurrentHashMap<String, String>()
    @Synchronized fun snapshot(): String = JSONObject(current).put("native_active", active || stopping).toString()
    @Synchronized fun publish(value: JSONObject) { current = value.toString() }
    @Synchronized fun clearDisplay() { if (!active) current = "{}" }
    fun requestEvidenceSave() { owner?.markEvidenceSave(); saveRequested = true }
  }
  private val executor = Executors.newSingleThreadScheduledExecutor()
  private val watchdog = Executors.newSingleThreadScheduledExecutor()
  private var player: MediaPlayer? = null
  private var source: RandomAccessFile? = null
  private var recordingFile: File? = null
  private var wake: PowerManager.WakeLock? = null
  @Volatile private var saveIntended = false
  @Volatile private var playbackError: String? = null
  private var endpoint = ""
  private var session = ""
  private var mode = ""
  private var config = JSONObject()
  private var options = JSONObject()
  @Volatile private var state = JSONObject()
  @Volatile private var sentSamples = 0L
  private var sequence = 0
  private var totalSamples = 0L
  private var dataOffset = 0L
  @Volatile private var completedInput = false
  private var finishingSent = false
  private var warningPosted = false
  private var connectionError: String? = null
  @Volatile private var automaticPause = false
  @Volatile private var watchdogPaused = false
  private var startedAt = 0L
  private var lastPoll = 0L
  private var staged = false
  private var ending = false
  private var pendingAudio: ByteArray? = null
  private var pendingAvailableMs = 0.0
  private var pendingAvailableClock = 0L
  private var lastResource = 0L
  private var delayShown = false
  private var observedUserPause = false

  override fun onCreate() {
    super.onCreate()
    owner = this
  }

  private fun markEvidenceSave() {
    saveIntended = true
  }
  private fun ownsState() = owner === this
  private fun publish(value: JSONObject) { if (ownsState()) Companion.publish(value) }

  override fun onBind(intent: Intent?) = null
  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    if (intent?.action == "end") {
      ending = true
      player?.let { runCatching { it.pause() } }
      // Session cancellation stops host capture and clears unsaved in-memory audio.
      state.put("native_state", "stopping"); publish(state)
      Thread({ closeSession(true) }, "ScamMonitorStop").apply { isDaemon = true; start() }
      return START_NOT_STICKY
    }
    if (active || intent?.action != "start") return START_NOT_STICKY
    options = JSONObject(intent.getStringExtra("options") ?: "{}")
    mode = options.getString("mode")
    endpoint = options.getString("endpoint").trimEnd('/')
    if (URL(endpoint).host !in setOf("10.0.2.2", "localhost", "127.0.0.1")) {
      state = JSONObject().put("native_state", "failed").put("connection_error", "Only the approved local computer endpoint is supported")
      publish(state); stopSelf(); return START_NOT_STICKY
    }
    active = true
    paused = false
    staged = options.optBoolean("staged_background", false)
    held = staged
    saveRequested = false
    retryRequested = false
    saveIntended = options.optBoolean("save", false)
    startedAt = SystemClock.elapsedRealtime()
    state = JSONObject().put("native_state", "starting").put("mode", mode)
    publish(state)
    channels()
    val end = PendingIntent.getService(this, 0, Intent(this, MonitorService::class.java).setAction("end"),
      PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    val notification = NotificationCompat.Builder(this, "monitoring").setSmallIcon(android.R.drawable.ic_btn_speak_now)
      .setContentTitle("Scam Call Alert monitoring").setContentText("Conversation analysis is active")
      .setOngoing(true).addAction(android.R.drawable.ic_media_pause, "Stop", end).build()
    val kind = if (mode == "microphone") ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC else ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
    startForeground(1, notification, kind)
    wake = (getSystemService(POWER_SERVICE) as PowerManager).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ScamCallAlert:monitoring")
    wake?.acquire(60 * 60 * 1000L)
    executor.execute {
      try {
        config = request("GET", "/health").getJSONObject("configuration")
        val data = JSONObject().put("mode", mode).put("approach", options.optString("approach", "accumulated"))
          .put("save", options.optBoolean("save", false))
        if (mode == "recorded") data.put("recording_id", options.getString("recording_id"))
        state = request("POST", "/sessions", data.toString().toByteArray())
        session = state.getString("session_id")
        if (ending) { closeSession(true); return@execute }
        watchdog.scheduleWithFixedDelay({
          if (active && !ending && mode == "recorded") {
            runCatching {
              val backlog = maxOf(0.0, ((player?.currentPosition ?: 0) * 16 - sentSamples) / 16000.0)
              if (!automaticPause && backlog + state.optDouble("queued_seconds", 0.0) >= config.optDouble("max_queued_audio_seconds", 20.0) - 2) {
                player?.pause()
                automaticPause = true; watchdogPaused = true
              }
            }
          }
        }, 0, 250, TimeUnit.MILLISECONDS)
        if (mode == "recorded") preparePlayback() else prepareCapture()
        emit("native_session_ready")
        executor.scheduleWithFixedDelay({ tickSafely() }, 0, 250, TimeUnit.MILLISECONDS)
      } catch (error: Exception) {
        // Startup has not accepted speech; preserve the native failure cause.
        android.util.Log.e("ScamMonitor", "Monitoring startup failed", error)
        fail("Unable to start monitoring: ${error.javaClass.simpleName}")
      }
    }
    return START_NOT_STICKY
  }

  private fun request(method: String, path: String, body: ByteArray? = null, binary: Boolean = false): JSONObject {
    val conn = URL(endpoint + path).openConnection() as HttpURLConnection
    val timeout = config.optInt("request_timeout_seconds", 30) * 1000
    conn.connectTimeout = timeout; conn.readTimeout = timeout; conn.requestMethod = method
    try {
      if (method == "POST") {
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", if (binary) "application/octet-stream" else "application/json")
        conn.outputStream.use { it.write(body ?: "{}".toByteArray()) }
      }
      val status = conn.responseCode
      val text = (if (status < 400) conn.inputStream else conn.errorStream).bufferedReader().use { it.readText() }
      if (status >= 400) throw IllegalStateException(JSONObject(text).optJSONObject("error")?.optString("message") ?: "HTTP $status")
      val result = JSONObject(text)
      if (session.isNotEmpty() && path.startsWith("/sessions/$session") && result.optString("session_id") != session)
        throw IllegalStateException("Obsolete or mismatched session response")
      return result
    } finally { conn.disconnect() }
  }

  private fun preparePlayback() {
    recordingFile = File(cacheDir, "session-$session.wav")
    val conn = URL("$endpoint/recordings/${options.getString("recording_id")}").openConnection() as HttpURLConnection
    conn.connectTimeout = 30000; conn.readTimeout = 30000
    try { conn.inputStream.use { input -> recordingFile!!.outputStream().use { input.copyTo(it) } } }
    finally { conn.disconnect() }
    source = RandomAccessFile(recordingFile, "r")
    val wav = source!!
    if (wav.readInt() != 0x52494646) throw IllegalArgumentException("Expected RIFF WAV")
    wav.skipBytes(4)
    if (wav.readInt() != 0x57415645) throw IllegalArgumentException("Expected WAVE")
    var validFormat = false
    while (wav.filePointer + 8 <= wav.length()) {
      val type = wav.readInt()
      val size = Integer.reverseBytes(wav.readInt()).toLong() and 0xffffffffL
      val body = wav.filePointer
      if (type == 0x666d7420) {
        val encoding = java.lang.Short.reverseBytes(wav.readShort()).toInt()
        val channels = java.lang.Short.reverseBytes(wav.readShort()).toInt()
        val rate = Integer.reverseBytes(wav.readInt())
        wav.skipBytes(6)
        val bits = java.lang.Short.reverseBytes(wav.readShort()).toInt()
        validFormat = encoding == 1 && channels == 1 && rate == 16000 && bits == 16
      } else if (type == 0x64617461) {
        if (!validFormat || size % 2 != 0L) throw IllegalArgumentException("Recording must be PCM16 mono 16kHz")
        dataOffset = body; totalSamples = size / 2; break
      }
      wav.seek(body + size + size % 2)
    }
    if (totalSamples <= 0) throw IllegalArgumentException("Empty recording")
    player = MediaPlayer().apply {
      setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
      setDataSource(recordingFile!!.absolutePath)
      setOnCompletionListener { completedInput = true }
      setOnErrorListener { mp, what, extra ->
        playbackError = "Playback failed ($what/$extra); remaining audio was not delivered"
        runCatching { mp.pause() }; true
      }
      prepare()
    }
    if (!held) {
      startedAt = SystemClock.elapsedRealtime()
      player!!.start()
      emit("playback_started")
    }
  }

  private fun prepareCapture() {
    require(config.getInt("audio_sample_rate_hz") == 16000) { "Host microphone must supply 16 kHz PCM" }
    startedAt = SystemClock.elapsedRealtime()
    if (ending) return
    emit("capture_started")
  }

  private fun tickSafely() {
    if (ending || !active || !ownsState()) return
    try { tick() } catch (error: Exception) {
      if (!ownsState() || ending) return
      if (mode == "recorded") {
        paused = true; player?.pause()
        connectionError = "Connection or processing failed. Retry explicitly."
        publishState()
      } else fail("Connection or processing failed; microphone session interrupted")
    }
  }

  private fun tick() {
    if (retryRequested) {
      retryRequested = false
      state = request("GET", "/sessions/$session")
      if (state.optString("state") in setOf("cancelled", "failed", "complete")) {
        connectionError = "This host session has ended. Stop and start a fresh session."
        paused = true
        player?.pause()
        publishState()
        return
      }
      if (state.optJSONObject("error") != null) request("POST", "/sessions/$session/retry")
      connectionError = null
      emit("explicit_retry")
    }
    if (saveRequested) { saveRequested = false; state = request("POST", "/sessions/$session/save") }
    if (connectionError != null) return
    if (playbackError != null) { fail(playbackError!!); return }
    if (watchdogPaused) { watchdogPaused = false; emit("automatic_queue_pause", "native_backlog_watchdog") }
    if (staged && held && !visible) {
      held = false
      startedAt = SystemClock.elapsedRealtime()
      emit("background_playback_released", "background")
      player!!.start()
      emit("playback_started", "background")
    }
    if (mode == "recorded" && !completedInput) {
      val play = player!!
      if (paused || held || automaticPause) { if (play.isPlaying) play.pause() }
      else if (!play.isPlaying) play.start()
      if (paused != observedUserPause) {
        observedUserPause = paused
        emit(if (paused) "playback_paused" else "playback_resumed", "user_control")
      }
    }
    val now = SystemClock.elapsedRealtime()
    if (now - lastPoll >= 500) {
      state = request("GET", "/sessions/$session")
      lastPoll = now
      if (state.optString("state") == "cancelled") {
        connectionError = "This host session has ended. Stop and start a fresh session."
        paused = true
        player?.pause()
        if (mode == "microphone") {
          state.put("native_state", "cancelled").put("connection_error", connectionError)
          publish(state)
          closeSession(false)
        } else publishState()
        return
      }
      if (state.optString("state") == "failed") {
        if (mode == "recorded") {
          paused = true; player?.pause()
          connectionError = state.optJSONObject("error")?.optString("message") ?: "Analysis interrupted. End and start a fresh session."
          publishState(); return
        }
        fail(state.optJSONObject("error")?.optString("message") ?: "Analysis failed"); return
      }
      val queued = state.optDouble("queued_seconds", 0.0)
      val pendingSeconds = if (mode == "recorded") maxOf(0.0, (player!!.currentPosition * 16 - sentSamples) / 16000.0) else 0.0
      val limit = config.optDouble("max_queued_audio_seconds", 20.0)
      if (queued + pendingSeconds >= limit - 2) {
        if (mode == "microphone") { fail("Analysis cannot keep up"); return }
        if (!automaticPause) { automaticPause = true; player?.pause(); emit("automatic_queue_pause") }
      } else if (automaticPause && queued + pendingSeconds < limit / 2) { automaticPause = false; emit("automatic_queue_resume") }
      maybeWarn()
    }
    var pcm = ByteArray(0)
    var availableMs = 0.0
    if (!finishingSent && mode == "recorded" && (!paused || automaticPause || completedInput) && !held) {
      val available = if (completedInput) totalSamples else min(totalSamples, player!!.currentPosition.toLong() * 16)
      val count = min(32000L, available - sentSamples).toInt()
      if (count >= 16000 || (completedInput && count > 0)) {
        pcm = ByteArray(count * 2)
        source!!.seek(dataOffset + sentSamples * 2); source!!.readFully(pcm)
        availableMs = available / 16.0
      }
    }
    if (pcm.isNotEmpty() && state.optDouble("queued_seconds", 0.0) <= config.optDouble("max_queued_audio_seconds", 20.0) - pcm.size / 32000.0) {
      if (pendingAudio == null) { pendingAudio = pcm; pendingAvailableMs = availableMs; pendingAvailableClock = SystemClock.elapsedRealtime() }
      pcm = pendingAudio!!; availableMs = pendingAvailableMs
      val end = sentSamples + pcm.size / 2
      state = request("POST", "/sessions/$session/audio?seq=$sequence&start=$sentSamples&end=$end&available_ms=$availableMs&available_monotonic_ms=$pendingAvailableClock", pcm, true)
      sentSamples = end; sequence++
      pendingAudio = null
      maybeWarn()
    }
    if (mode == "recorded" && completedInput && sentSamples == totalSamples && !finishingSent) {
      state = request("POST", "/sessions/$session/finish"); finishingSent = true
      emit("recording_input_complete")
    }
    publishState()
    if (now - lastResource >= 1000) {
      lastResource = now
      val event = JSONObject().put("kind", "native_resource_sample")
        .put("client_monotonic_ms", now).put("timing_origin_ms", startedAt)
        .put("process_pss_bytes", Debug.getPss() * 1024L)
        .put("process_cpu_time_ms", Process.getElapsedCpuTime())
      request("POST", "/sessions/$session/events", event.toString().toByteArray())
    }
    if (state.optString("state") == "complete") closeSession(false)
  }

  private fun publishState() {
    if (ending || !ownsState()) return
    val pendingSeconds = if (mode == "microphone") 0.0
      else maxOf(0.0, (player?.currentPosition ?: 0) / 1000.0 - sentSamples / 16000.0)
    val backlogSeconds = pendingSeconds + state.optDouble("queued_seconds", 0.0)
    val delayed = backlogSeconds >= config.optDouble("delay_indicator_seconds", 8.0)
    if (delayed != delayShown) {
      delayShown = delayed
      emit(if (delayed) "analysis_delay_shown" else "analysis_delay_cleared")
    }
    state.put("analysis_delayed", delayed).put("analysis_backlog_seconds", backlogSeconds)
    state.put("native_state", when {
      connectionError != null -> "error"
      state.optString("state") == "complete" -> "complete"
      finishingSent -> "finishing"
      held -> "held"
      automaticPause -> "catching_up"
      paused -> "paused"
      else -> "active"
    })
    state.put("connection_error", connectionError)
    val hostMicrophoneSamples = state.optLong("audio_samples", 0L)
    state.put("audio_position_ms", if (mode == "recorded") player?.currentPosition ?: 0 else hostMicrophoneSamples / 16)
    state.put("duration_ms", if (mode == "recorded") totalSamples / 16 else hostMicrophoneSamples / 16)
    state.put("client_elapsed_ms", SystemClock.elapsedRealtime() - startedAt)
    state.put("foreground", visible)
    publish(state)
  }

  private fun channels() {
    val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
    manager.createNotificationChannel(NotificationChannel("monitoring", "Active monitoring", NotificationManager.IMPORTANCE_LOW))
    manager.createNotificationChannel(NotificationChannel("scam-warning", "Possible scam warning", NotificationManager.IMPORTANCE_HIGH))
  }

  private fun maybeWarn() {
    if (ending || !active || !ownsState() || warningPosted || !state.optBoolean("warning", false)) return
    warningPosted = true
    val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
    val permission = ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    if (!permission) { emit("notification_suppressed", "permission_denied"); return }
    val intent = packageManager.getLaunchIntentForPackage(packageName)!!.putExtra("session_id", session)
      .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
    intent.data = android.net.Uri.parse("scam-call-alert://session/$session")
    val pending = PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    manager.notify(session, 2, NotificationCompat.Builder(this, "scam-warning")
      .setSmallIcon(android.R.drawable.ic_dialog_alert).setContentTitle(config.getString("warning_title"))
      .setContentText(config.getString("warning_message"))
      .setStyle(NotificationCompat.BigTextStyle().bigText(config.getString("warning_message")))
      .setPriority(NotificationCompat.PRIORITY_HIGH).setAutoCancel(true).setContentIntent(pending).build())
    emit("notification_posted", "display_unobserved")
  }

  private fun emit(kind: String, condition: String = "") {
    if (session.isEmpty()) return
    val event = JSONObject().put("kind", kind).put("condition", condition)
      .put("client_monotonic_ms", SystemClock.elapsedRealtime()).put("timing_origin_ms", startedAt)
      .put("client_elapsed_ms", SystemClock.elapsedRealtime() - startedAt)
      .put("audio_position_ms", if (mode == "recorded") player?.currentPosition ?: 0 else sentSamples / 16)
    request("POST", "/sessions/$session/events", event.toString().toByteArray())
  }

  private fun fail(message: String) {
    state.put("native_state", "failed").put("connection_error", message)
    publish(state)
    try {
      if (session.isNotEmpty()) request("POST", "/sessions/$session/interrupt",
        JSONObject().put("code", "E_NATIVE_INTERRUPTION").put("message", message).toString().toByteArray())
    } catch (_: Exception) { }
    closeSession(false)
  }

  private fun closeSession(cancel: Boolean) {
    if (ownsState()) stopping = true
    ending = true
    if (cancel && session.isNotEmpty()) {
      try { state = request("POST", "/sessions/$session/cancel") } catch (_: Exception) {
        state.put("connection_error", "Cancellation could not reach host; late results remain rejected locally")
      }
      state.put("native_state", "cancelled"); publish(state)
      (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).cancel(session, 2)
    }
    player?.release(); player = null
    source?.close(); source = null
    recordingFile?.delete()
    if (mode == "microphone" && !saveIntended && !state.optBoolean("save_evidence", false)) {
      state.remove("transcript"); state.remove("segments"); state.remove("prediction"); state.put("warning", false)
      publish(state)
    }
    if (ownsState()) active = false
    if (session.isNotEmpty()) archives[session] = JSONObject(snapshot()).put("native_active", false).toString()
    wake?.let { if (it.isHeld) it.release() }
    executor.shutdown()
    watchdog.shutdown()
    stopForeground(STOP_FOREGROUND_REMOVE); stopSelf()
  }

  override fun onDestroy() {
    if (active && !ending && ownsState()) {
      active = false
      state.put("native_state", "failed").put("connection_error", "Android monitoring service stopped unexpectedly")
      publish(state)
    }
    ending = true
    if (mode == "microphone" && !saveIntended && !state.optBoolean("save_evidence", false)) {
      state.remove("transcript"); state.remove("segments"); state.remove("prediction"); state.put("warning", false); publish(state)
    }
    player?.release(); player = null
    source?.close(); source = null
    recordingFile?.delete()
    wake?.let { if (it.isHeld) it.release() }
    executor.shutdownNow()
    watchdog.shutdownNow()
    if (ownsState()) { active = false; stopping = false; owner = null }
    super.onDestroy()
  }

}
