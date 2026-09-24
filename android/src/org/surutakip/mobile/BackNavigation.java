package org.surutakip.mobile;

import android.app.Activity;
import android.os.Build;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

/** Android 13+ back gestures and navigation buttons enter the same Kivy stack. */
public final class BackNavigation {
    private static OnBackInvokedCallback callback;
    public static void install(final Activity activity, final Runnable action) {
        if (Build.VERSION.SDK_INT < 33) return;
        activity.runOnUiThread(new Runnable() {
            @Override public void run() {
                if (callback != null) activity.getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(callback);
                callback = new OnBackInvokedCallback() {
                    @Override public void onBackInvoked() { action.run(); }
                };
                activity.getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, callback);
            }
        });
    }
    public static void background(final Activity activity) {
        activity.runOnUiThread(new Runnable() {
            @Override public void run() { activity.moveTaskToBack(true); }
        });
    }
}
