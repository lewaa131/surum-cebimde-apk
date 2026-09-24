package org.surutakip.mobile;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import java.io.File;
import java.util.HashSet;

public final class UpdateInstaller {
    private static HashSet<String> certificates(PackageInfo info) {
        HashSet<String> result = new HashSet<String>();
        if (info.signatures != null) for (Signature s : info.signatures) result.add(s.toCharsString());
        return result;
    }
    public static String install(final Activity activity, String path) throws Exception {
        File file = new File(path).getCanonicalFile();
        File expected = new File(activity.getCacheDir(), "updates/update.apk").getCanonicalFile();
        if (!expected.equals(file) || !file.isFile()) return "Ä°ndirilen gÃ¼ncelleme bulunamadÄ±; tekrar indir.";
        PackageManager pm = activity.getPackageManager();
        PackageInfo current = pm.getPackageInfo(activity.getPackageName(), PackageManager.GET_SIGNATURES);
        PackageInfo incoming = pm.getPackageArchiveInfo(file.getAbsolutePath(), PackageManager.GET_SIGNATURES);
        if (incoming == null || !current.packageName.equals(incoming.packageName)) return "Bu APK uygulamayla uyuÅŸmuyor.";
        if (incoming.versionCode <= current.versionCode) return "Bu sÃ¼rÃ¼m zaten yÃ¼klÃ¼ veya daha eski.";
        if (certificates(current).isEmpty() || !certificates(current).equals(certificates(incoming)))
            return "GÃ¼ncellemenin imzasÄ± uyuÅŸmuyor. UygulamayÄ± silme; geliÅŸtiriciye bildir.";
        if (Build.VERSION.SDK_INT >= 26 && !pm.canRequestPackageInstalls()) {
            activity.runOnUiThread(new Runnable() { public void run() {
                try { activity.startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + activity.getPackageName()))); }
                catch (Exception e) { android.widget.Toast.makeText(activity,"Yükleme izni ekranı açılamadı.",android.widget.Toast.LENGTH_LONG).show(); }
            }});
            return "Bu kaynaktan yÃ¼klemeye izin ver; uygulamaya dÃ¶nÃ¼p Kurulumu aÃ§ dÃ¼ÄŸmesine bas.";
        }
        final Uri uri = Uri.parse("content://" + activity.getPackageName() + ".updates/update.apk");
        activity.runOnUiThread(new Runnable() { public void run() {
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri,"application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            try { activity.startActivity(intent); }
            catch (Exception e) { android.widget.Toast.makeText(activity,"Kurulum ekranı açılamadı.",android.widget.Toast.LENGTH_LONG).show(); }
        }});
        return "Android kurulum ekranÄ±nda GÃ¼ncelle seÃ§eneÄŸini onayla. Ä°ptal ettiysen yeniden aÃ§abilirsin.";
    }
}
