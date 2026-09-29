package org.surutakip.mobile;

import android.app.Notification;
import android.content.Context;
import android.graphics.BitmapFactory;

public final class NotificationBrand {
    public static void apply(Context c, Notification.Builder b) {
        int small=c.getResources().getIdentifier("surum_notification","drawable",c.getPackageName());
        int large=c.getResources().getIdentifier("surum_brand","drawable",c.getPackageName());
        b.setSmallIcon(small!=0 ? small : android.R.drawable.ic_dialog_info).setColor(0xff126449);
        if (large!=0) {
            BitmapFactory.Options options=new BitmapFactory.Options();
            options.inSampleSize=4;
            b.setLargeIcon(BitmapFactory.decodeResource(c.getResources(),large,options));
        }
    }
}
