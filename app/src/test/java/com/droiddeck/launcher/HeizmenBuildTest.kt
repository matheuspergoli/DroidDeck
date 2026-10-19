package com.droiddeck.launcher

import android.app.Activity
import android.os.Handler
import android.os.Looper
import com.droiddeck.launcher.update.AppUpdates
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment

@RunWith(RobolectricTestRunner::class)
class HeizmenBuildTest {
    @Test fun personalPackageAndLauncherLabelAreDistinct() {
        assumeTrue(BuildConfig.HEIZMEN_BUILD)
        val app = RuntimeEnvironment.getApplication()
        assertEquals("com.droiddeck.launcher.heizmen", app.packageName)
        assertEquals("DroidDeck Heizmen", app.packageManager.getApplicationLabel(app.applicationInfo).toString())
    }

    @Test fun personalMenuDoesNotStartOfficialCatalogRequests() {
        assumeTrue(BuildConfig.HEIZMEN_BUILD)
        val activity = Robolectric.buildActivity(Activity::class.java).setup()
        try {
            val menu = UpdatesMenu(activity.get(), Handler(Looper.getMainLooper()))
            menu.start()
            menu.check(force = true)
            assertFalse(menu.checking)
            assertNull(menu.catalog)
            assertFalse(menu.hasUpdate)
        } finally {
            activity.pause().stop().destroy()
        }
    }

    @Test fun personalBuildIsNotMarkedAsOfficiallyUpdatable() {
        assumeTrue(BuildConfig.HEIZMEN_BUILD)
        AppUpdates.init(RuntimeEnvironment.getApplication())
        assertFalse(AppUpdates.installed().updatable)
    }
}
