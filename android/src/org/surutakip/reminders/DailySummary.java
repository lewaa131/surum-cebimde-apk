package org.surutakip.reminders;

import java.text.SimpleDateFormat;
import java.util.*;

/** Android-independent daily batching and local-time scheduling. */
public final class DailySummary {
    public static final class Event {
        public final String key, kind, day, until, time;
        public Event(String key, String kind, String day, String until, String time) {
            this.key=key; this.kind=kind; this.day=day; this.until=until; this.time=time;
        }
        boolean active(String onDay) { return until.isEmpty() || onDay.compareTo(until)<0; }
    }
    public static String day(long now) {
        return new SimpleDateFormat("yyyy-MM-dd",Locale.US).format(new Date(now));
    }
    private static long at(String day,String time) throws Exception {
        SimpleDateFormat format=new SimpleDateFormat("yyyy-MM-dd HH:mm",Locale.US);
        format.setLenient(false);
        return format.parse(day+" "+time).getTime();
    }
    public static List<Event> due(List<Event> events,long now) throws Exception {
        List<Event> result=new ArrayList<>();
        Set<String> seen=new HashSet<>();
        String today=day(now);
        for(Event e:events) {
            String onDay=e.day.compareTo(today)>0?e.day:today;
            if(e.active(today) && at(onDay,e.time)<=now && seen.add(e.key)) result.add(e);
        }
        return result;
    }
    public static long next(List<Event> events,long now,String sentDay) throws Exception {
        String earliest=day(now);
        if(earliest.equals(sentDay)) {
            Calendar calendar=Calendar.getInstance(); calendar.setTimeInMillis(now);
            calendar.add(Calendar.DATE,1); earliest=day(calendar.getTimeInMillis());
        }
        long next=Long.MAX_VALUE;
        for(Event e:events) {
            String onDay=e.day.compareTo(earliest)>0?e.day:earliest;
            if(e.active(onDay)) next=Math.min(next,Math.max(now+1000,at(onDay,e.time)));
        }
        return next;
    }
    public static String body(List<Event> events) {
        Map<String,Integer> counts=new LinkedHashMap<>();
        for(Event e:events) {
            String label;
            switch(e.kind) {
                case "weaning": label="buzağı için sütten kesme değerlendirmesi"; break;
                case "fresh": label="yeni doğuran kontrolü"; break;
                case "dry": label="kuruya ayırma"; break;
                case "birth": label="doğum takibi"; break;
                case "heat": label="kızgınlık dönüş kontrolü"; break;
                case "pregnancy": label="gebelik kontrolü"; break;
                case "breed": label="tohumlama değerlendirmesi"; break;
                default: label="kontrol";
            }
            counts.put(label,counts.containsKey(label)?counts.get(label)+1:1);
        }
        StringBuilder body=new StringBuilder();
        for(Map.Entry<String,Integer> entry:counts.entrySet()) {
            if(body.length()>0) body.append('\n');
            body.append(entry.getValue()).append(" ").append(entry.getKey());
        }
        return body.append("\nAyrıntılar için Bugün ekranını aç.").toString();
    }
}
