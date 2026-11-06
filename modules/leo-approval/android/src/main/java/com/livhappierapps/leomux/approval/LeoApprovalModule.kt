package com.livhappierapps.leomux.approval

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.Build
import android.os.SystemClock
import android.security.keystore.KeyProperties
import android.security.keystore.KeyProtection
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import expo.modules.kotlin.AppContext
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import expo.modules.kotlin.viewevent.EventDispatcher
import expo.modules.kotlin.views.ExpoView
import org.json.JSONObject
import java.security.KeyStore
import java.security.MessageDigest
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

private const val ALIAS = "leomux-approval-v1"
private fun hex(bytes: ByteArray) = bytes.joinToString("") { "%02x".format(it.toInt() and 255) }
private fun store() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

class LeoApprovalModule : Module() {
  private fun protectWindow() {
    val activity = appContext.currentActivity ?: return
    activity.runOnUiThread {
      activity.window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
      if (Build.VERSION.SDK_INT >= 31) activity.window.setHideOverlayWindows(true)
    }
  }
  override fun definition() = ModuleDefinition {
    Name("LeoApproval")
    // Pairing only. There is deliberately NO sign()/approve() JS method.
    AsyncFunction("installKey") { value: String ->
      require(value.matches(Regex("[0-9a-f]{64}"))) { "Expected the 64-character local approval key" }
      val bytes = value.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
      try {
        store().setEntry(ALIAS, KeyStore.SecretKeyEntry(SecretKeySpec(bytes, "HmacSHA256")),
          KeyProtection.Builder(KeyProperties.PURPOSE_SIGN)
            .setDigests(KeyProperties.DIGEST_SHA256).build())
      } finally { bytes.fill(0) }
    }
    AsyncFunction("isPaired") { store().containsAlias(ALIAS) }
    OnCreate { protectWindow() }
    OnActivityEntersForeground { protectWindow() }
    View(LeoApprovalView::class) {
      Events("onApproved", "onBlocked")
      // Atomic snapshot: changing any proposal prop cancels an in-flight gesture.
      Prop("proposal") { view: LeoApprovalView, value: String -> view.setProposal(value) }
    }
  }
}

class LeoApprovalView(context: Context, appContext: AppContext) : ExpoView(context, appContext) {
  override val shouldUseAndroidLayout = true
  val onApproved by EventDispatcher()
  val onBlocked by EventDispatcher()
  private var snapshot = ""
  private var data: JSONObject? = null
  private var used = false
  private val text = TextView(context).apply {
    setTextColor(Color.WHITE); textSize = 13f; setPadding(12, 8, 12, 8)
    typeface = android.graphics.Typeface.MONOSPACE
  }
  private val slider = Swipe(context) { approve() }
  private val column = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }

  init {
    filterTouchesWhenObscured = true
    val scroll = ScrollView(context).apply { addView(text) }
    column.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
    column.addView(slider, LinearLayout.LayoutParams(-1, (72 * resources.displayMetrics.density).toInt()))
    addView(column, LayoutParams(-1, -1))
  }

  fun setProposal(value: String) {
    if (snapshot == value) return
    snapshot = value; slider.reset(); used = false
    data = try { JSONObject(value) } catch (_: Exception) { null }
    val p = data
    text.text = if (p == null) "Invalid proposal; approval disabled" else
      "${p.optString("risk").uppercase()} · ${p.optString("reason")}\n\n${p.optString("cmd")}"
  }

  override fun dispatchTouchEvent(event: MotionEvent): Boolean {
    val obscured = (event.flags and MotionEvent.FLAG_WINDOW_IS_OBSCURED) != 0 ||
      (Build.VERSION.SDK_INT >= 29 && (event.flags and MotionEvent.FLAG_WINDOW_IS_PARTIALLY_OBSCURED) != 0)
    if (obscured || !hasWindowFocus() || !isShown) {
      slider.reset(); onBlocked(mapOf("message" to "Obscured or unfocused approval rejected")); return false
    }
    return super.dispatchTouchEvent(event)
  }

  private fun approve() {
    try {
      check(!used && isShown && hasWindowFocus())
      val p = data ?: error("No proposal")
      val session = p.getString("session_id")
      val id = p.getString("id")
      val nonce = p.getString("nonce")
      val hash = p.getString("cmd_hash")
      check(session.matches(Regex("[0-9a-f]{32}")) && id.matches(Regex("[A-Za-z0-9_-]{1,32}")))
      check(nonce.matches(Regex("[0-9a-f]{64}")) && hash.matches(Regex("[0-9a-f]{64}")))
      check(System.currentTimeMillis() / 1000.0 < p.getDouble("deadline"))
      check(hex(MessageDigest.getInstance("SHA-256").digest(p.getString("cmd").toByteArray(Charsets.UTF_8))) == hash)
      val payload = listOf("leomux.approve.v1", session, id, nonce, hash, "approve").joinToString("\n")
      val key = store().getKey(ALIAS, null) ?: error("Pair this installation first")
      val mac = Mac.getInstance("HmacSHA256").apply { init(key) }
      val signature = hex(mac.doFinal(payload.toByteArray(Charsets.UTF_8)))
      used = true
      onApproved(mapOf("id" to id, "nonce" to nonce, "session_id" to session, "signature" to signature))
    } catch (_: Exception) {
      onBlocked(mapOf("message" to "Approval failed or expired; verify pairing and request a fresh proposal"))
    }
    slider.reset()
  }

  override fun onWindowFocusChanged(hasFocus: Boolean) { super.onWindowFocusChanged(hasFocus); if (!hasFocus) slider.reset() }
  override fun onDetachedFromWindow() { slider.reset(); super.onDetachedFromWindow() }
}

/** One finger: start in left 20%, swipe right 85%, dwell 600ms, RELEASE.
 * A tap, fling, multi-touch, obscured event, focus loss, prop change or cancel resets.
 * No performClick/accessibility action is allowed to synthesize approval.
 */
private class Swipe(context: Context, val confirmed: () -> Unit) : View(context) {
  private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
  private var active = false
  private var startY = 0f
  private var progress = 0f
  private var dwell = 0L
  init { filterTouchesWhenObscured = true; contentDescription = "Swipe right, hold, then release to approve" }
  fun reset() { active = false; progress = 0f; dwell = 0; invalidate() }
  override fun onTouchEvent(e: MotionEvent): Boolean {
    if ((e.flags and MotionEvent.FLAG_WINDOW_IS_OBSCURED) != 0 ||
        (Build.VERSION.SDK_INT >= 29 && (e.flags and MotionEvent.FLAG_WINDOW_IS_PARTIALLY_OBSCURED) != 0) ||
        e.pointerCount != 1 || !hasWindowFocus()) { reset(); return false }
    when(e.actionMasked) {
      MotionEvent.ACTION_DOWN -> {
        reset(); active = e.x <= width * .2f && e.x >= 0; startY = e.y
        if (active) parent.requestDisallowInterceptTouchEvent(true)
      }
      MotionEvent.ACTION_MOVE -> {
        if (!active) return false
        if (kotlin.math.abs(e.y - startY) > height * .6f || e.x < 0 || e.x > width || e.y < 0 || e.y > height) { reset(); return false }
        progress = (e.x / width).coerceIn(0f, 1f)
        if (progress >= .85f) { if (dwell == 0L) dwell = SystemClock.elapsedRealtime() }
        else dwell = 0
        invalidate()
      }
      MotionEvent.ACTION_UP -> {
        val ok = active && progress >= .85f && e.x >= width * .85f && e.x <= width &&
          e.y >= 0 && e.y <= height && dwell > 0 && SystemClock.elapsedRealtime() - dwell >= 600
        reset(); parent.requestDisallowInterceptTouchEvent(false)
        if (ok) confirmed()
      }
      MotionEvent.ACTION_CANCEL, MotionEvent.ACTION_POINTER_DOWN -> reset()
    }
    return active || e.actionMasked == MotionEvent.ACTION_UP
  }
  override fun onDraw(c: Canvas) {
    super.onDraw(c)
    paint.color = Color.rgb(50, 30, 43); c.drawRoundRect(0f, 0f, width.toFloat(), height.toFloat(), 20f, 20f, paint)
    paint.color = Color.rgb(150, 45, 85); c.drawRoundRect(0f, 0f, width * progress, height.toFloat(), 20f, 20f, paint)
    paint.color = Color.WHITE; paint.textSize = 14 * resources.displayMetrics.scaledDensity; paint.textAlign = Paint.Align.CENTER
    c.drawText(if (progress >= .85f) "Hold, then release" else "Start here → Swipe to approve", width / 2f, height / 2f + paint.textSize / 3, paint)
  }
}
