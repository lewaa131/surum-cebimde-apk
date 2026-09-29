package org.surutakip.mobile;

import android.app.*;
import android.app.job.*;
import android.content.*;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.content.pm.PackageManager;
import org.json.JSONObject;
import java.net.URL;
import javax.net.ssl.HttpsURLConnection;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.concurrent.atomic.AtomicBoolean;

/** Persisted hourly network check; Android may defer it during idle or offline periods. */
public class UpdateJob extends JobService {
    private static final int JOB=7013, NOTICE=7014;
    private static final String CHANNEL="app_updates";
    private static final String REPO="https://github.com/lewaa131/surum-cebimde-apk/releases/";
    private AtomicBoolean stopped;
    private volatile HttpsURLConnection connection;
    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("surum_updates",Context.MODE_PRIVATE);
    }
    public static void schedule(Context c) {
        JobScheduler scheduler=(JobScheduler)c.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if (scheduler.getPendingJob(JOB)!=null) return;
        int result=scheduler.schedule(new JobInfo.Builder(JOB,new ComponentName(c,UpdateJob.class))
            .setPeriodic(60*60*1000L).setPersisted(true)
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).build());
        if (result!=JobScheduler.RESULT_SUCCESS) throw new IllegalStateException("Güncelleme kontrolü planlanamadı");
    }
    public static void defer(Context c,String version) {
        prefs(c).edit().putString("deferred",version).putLong("until",System.currentTimeMillis()+86400000L).remove("notified").apply();
        ((NotificationManager)c.getSystemService(Context.NOTIFICATION_SERVICE)).cancel(NOTICE);
    }
    public static boolean deferred(Context c,String version) {
        return version.equals(prefs(c).getString("deferred","")) && System.currentTimeMillis()<prefs(c).getLong("until",0);
    }
    public static class LaterReceiver extends BroadcastReceiver {
        @Override public void onReceive(Context c,Intent intent) {
            String version=intent.getStringExtra("version");
            if (version!=null) defer(c,version);
        }
    }
    @Override public boolean onStartJob(JobParameters parameters) {
        final AtomicBoolean token=new AtomicBoolean(false);
        stopped=token;
        new Thread(() -> {
            boolean retry=false;
            try {
                connection=(HttpsURLConnection)new URL(REPO+"latest/download/update.json").openConnection();
                connection.setConnectTimeout(15000); connection.setReadTimeout(15000);
                connection.setRequestProperty("User-Agent","Surum-Cebimde-Updater");
                connection.setRequestProperty("Cache-Control","no-cache");
                int response=connection.getResponseCode();
                if (response==404) return;
                if (response!=200) throw new java.io.IOException("HTTP "+response);
                ByteArrayOutputStream out=new ByteArrayOutputStream();
                try (InputStream input=connection.getInputStream()) {
                    byte[] buffer=new byte[2048]; int n;
                    while ((n=input.read(buffer))!=-1) {
                        if (token.get()) return;
                        if (out.size()+n>32768) throw new java.io.IOException("Metadata too large");
                        out.write(buffer,0,n);
                    }
                }
                JSONObject data=new JSONObject(out.toString("UTF-8"));
                String version=data.getString("version");
                if (!version.matches("\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}")) return;
                String[] parts=version.split("\\.");
                long code=100000000L+Integer.parseInt(parts[0])*1000000L+Integer.parseInt(parts[1])*1000L+Integer.parseInt(parts[2]);
                long installed=getPackageManager().getPackageInfo(getPackageName(),0).versionCode;
                if (code<=installed) {
                    ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).cancel(NOTICE); return;
                }
                if (!getPackageName().equals(data.getString("package")) || data.getLong("version_code")!=code
                    || !data.getString("url").equals(REPO+"download/v"+version+"/surum-cebimde.apk")
                    || !data.getString("sha256").matches("[a-f0-9]{64}")
                    || data.getLong("size")<=0 || data.getLong("size")>200*1024*1024L) return;
                if (!token.get()) post(version);
            } catch (Exception error) {
                retry=true;
                android.util.Log.w("SurumUpdates","Güncelleme kontrolü daha sonra denenecek",error);
            } finally {
                if (connection!=null) connection.disconnect();
                final boolean again=retry;
                new Handler(Looper.getMainLooper()).post(() -> { if (!token.get()) jobFinished(parameters,again); });
            }
        },"Surum-update-check").start();
        return true;
    }
    @Override public boolean onStopJob(JobParameters parameters) {
        if (stopped!=null) stopped.set(true);
        if (connection!=null) connection.disconnect();
        return true;
    }
    private void post(String version) {
        if (deferred(this,version) || version.equals(prefs(this).getString("notified",""))) return;
        NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT>=33 && checkSelfPermission("android.permission.POST_NOTIFICATIONS")!=PackageManager.PERMISSION_GRANTED) return;
        if (!manager.areNotificationsEnabled()) return;
        if (Build.VERSION.SDK_INT>=26) {
            manager.createNotificationChannel(new NotificationChannel(CHANNEL,"Uygulama güncellemeleri",NotificationManager.IMPORTANCE_DEFAULT));
            if (manager.getNotificationChannel(CHANNEL).getImportance()==NotificationManager.IMPORTANCE_NONE) return;
        }
        Intent launch=getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (launch==null) return;
        launch.putExtra("surum_open_update",true).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent open=PendingIntent.getActivity(this,NOTICE,launch,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Intent later=new Intent(this,LaterReceiver.class).putExtra("version",version);
        PendingIntent snooze=PendingIntent.getBroadcast(this,NOTICE,later,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder=Build.VERSION.SDK_INT>=26 ? new Notification.Builder(this,CHANNEL) : new Notification.Builder(this);
        NotificationBrand.apply(this,builder);
        builder.setContentTitle("Sürüm Cebimde · Yeni sürüm var")
            .setContentText("Sürüm "+version+" hazır. Güncellemek için dokun.")
            .setContentIntent(open).setAutoCancel(true).setOnlyAlertOnce(true)
            .addAction(new Notification.Action.Builder((android.graphics.drawable.Icon)null,"Güncelle",open).build())
            .addAction(new Notification.Action.Builder((android.graphics.drawable.Icon)null,"Daha sonra",snooze).build());
        manager.notify(NOTICE,builder.build());
        prefs(this).edit().putString("notified",version).apply();
    }
}
