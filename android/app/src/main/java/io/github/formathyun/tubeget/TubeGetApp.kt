package io.github.formathyun.tubeget

import android.app.Application

class TubeGetApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Settings.init(this)
        Notifier.ensureChannels(this)
        Engine.start(this)
        Downloads.init(this)
    }
}
