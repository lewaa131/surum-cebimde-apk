import org.surutakip.reminders.DailySummary;
import org.surutakip.reminders.DailySummary.Event;
import java.util.*;
import java.text.SimpleDateFormat;

public class DailySummaryTest {
    static long time(String value) throws Exception {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm",Locale.US).parse(value).getTime();
    }
    static void check(boolean condition,String message) {
        if(!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        TimeZone.setDefault(TimeZone.getTimeZone("Europe/Istanbul"));
        List<Event> events=new ArrayList<>();
        for(int i=0;i<15;i++) events.add(new Event("cow"+i,
            i<5?"pregnancy":i<8?"dry":"weaning","2026-09-12","","09:00"));
        long now=time("2026-09-12 09:00");
        List<Event> due=DailySummary.due(events,now);
        check(due.size()==15,"All 15 tasks in one batch");
        String body=DailySummary.body(due);
        check(body.contains("5 gebelik kontrolü") && body.contains("3 kuruya ayırma") &&
            body.contains("7 buzağı için sütten kesme"),"Category counts including weaning");
        check(DailySummary.due(events,time("2026-09-12 08:59")).isEmpty(),"Not before selected hour");
        check(DailySummary.next(events,time("2026-09-12 08:00"),"")==now,"Today's selected hour");
        check(DailySummary.next(events,now,"2026-09-12")==time("2026-09-13 09:00"),"No second summary after sync or reboot");
        check(DailySummary.next(events,time("2026-09-13 08:00"),"2026-09-12")==time("2026-09-13 09:00"),"Overdue tasks wait until selected hour tomorrow");
        check(DailySummary.due(events,time("2026-09-13 08:00")).isEmpty(),"Boot before selected hour must not send overdue tasks early");
        check(DailySummary.due(events,time("2026-09-13 09:00")).size()==15,"Unfinished tasks recur in next daily summary");
        check(DailySummary.next(events,now,"")==now+1000,"Catch up missed alarm");
        events.add(events.get(0));
        events.add(new Event("future","birth","2026-09-14","","09:00"));
        events.add(new Event("expired","heat","2026-09-01","2026-09-12","09:00"));
        check(DailySummary.due(events,now).size()==15,"Exclude duplicates, future and expired tasks");
        events.clear();
        check(DailySummary.next(events,now,"")==Long.MAX_VALUE,"No empty summary alarm");
        events.add(new Event("expires","heat","2026-09-12","2026-09-13","09:00"));
        check(DailySummary.next(events,now,"2026-09-12")==Long.MAX_VALUE,"Do not schedule expired tomorrow");
        events.clear();
        events.add(new Event("future","breed","2026-09-14","","10:30"));
        check(DailySummary.next(events,now,"")==time("2026-09-14 10:30"),"Future task and changed hour");
        System.out.println("PASS: daily batching, 15 tasks, weaning, time, deduplication, next day, expiry, empty plan");
    }
}
