package expo.modules.scammonitor

import android.content.Intent
import androidx.core.content.ContextCompat
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class ScamMonitorModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("ScamMonitor")
    OnActivityEntersForeground { MonitorService.visible = true }
    OnActivityEntersBackground { MonitorService.visible = false }
    OnNewIntent { intent -> MonitorService.notificationOrigin = intent.getStringExtra("session_id") }
    AsyncFunction("start") { options: String ->
      val context = appContext.reactContext ?: throw IllegalStateException("Application unavailable")
      if (MonitorService.active || MonitorService.stopping) throw IllegalStateException("Wait for the current session to end")
      ContextCompat.startForegroundService(context, Intent(context, MonitorService::class.java)
        .putExtra("options", options).setAction("start"))
      Unit
    }
    AsyncFunction("pause") { paused: Boolean -> MonitorService.paused = paused }
    AsyncFunction("releasePlayback") { MonitorService.held = false }
    AsyncFunction("end") {
      appContext.reactContext?.startService(Intent(appContext.reactContext, MonitorService::class.java).setAction("end"))
      Unit
    }
    AsyncFunction("state") { MonitorService.snapshot() }
    AsyncFunction("clearDisplay") { MonitorService.clearDisplay() }
    AsyncFunction("save") { MonitorService.requestEvidenceSave() }
    AsyncFunction("retry") { MonitorService.retryRequested = true }
    AsyncFunction("notificationSession") {
      MonitorService.notificationOrigin ?: appContext.currentActivity?.intent?.getStringExtra("session_id")
    }
    AsyncFunction("clearNotificationSession") {
      MonitorService.notificationOrigin = null
      appContext.currentActivity?.intent?.removeExtra("session_id")
    }
    AsyncFunction("sessionSnapshot") { id: String -> MonitorService.archives[id] ?: "{}" }
  }
}
