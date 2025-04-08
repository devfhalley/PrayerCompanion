package com.prayeralarm.model;

import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.Ignore;
import androidx.room.PrimaryKey;

import java.util.Calendar;

@Entity(tableName = "alarms")
public class Alarm {

    @PrimaryKey(autoGenerate = true)
    private long id;

    @ColumnInfo(name = "timeInMillis")
    private long timeInMillis;

    @ColumnInfo(name = "enabled")
    private boolean enabled;

    @ColumnInfo(name = "repeating")
    private boolean repeating;

    @ColumnInfo(name = "days")
    private boolean[] days; // Sunday=0, Saturday=6

    @ColumnInfo(name = "isTts")
    private boolean isTts; // true for Text-to-speech, false for sound file

    @ColumnInfo(name = "message")
    private String message; // Message for TTS

    @ColumnInfo(name = "soundPath")
    private String soundPath; // Path to sound file

    // Default constructor for Room
    public Alarm() {
        this.days = new boolean[7];
    }

    // Constructor for one-time alarm
    @Ignore
    public Alarm(long timeInMillis, boolean isTts, String messageOrSoundPath) {
        this.timeInMillis = timeInMillis;
        this.enabled = true;
        this.repeating = false;
        this.days = new boolean[7];
        this.isTts = isTts;
        
        if (isTts) {
            this.message = messageOrSoundPath;
        } else {
            this.soundPath = messageOrSoundPath;
        }
    }

    // Constructor for repeating alarm
    @Ignore
    public Alarm(long timeInMillis, boolean[] days, boolean isTts, String messageOrSoundPath) {
        this.timeInMillis = timeInMillis;
        this.enabled = true;
        this.repeating = true;
        this.days = days;
        this.isTts = isTts;
        
        if (isTts) {
            this.message = messageOrSoundPath;
        } else {
            this.soundPath = messageOrSoundPath;
        }
    }

    // Check if the alarm should ring today
    public boolean shouldRingToday() {
        if (!enabled) {
            return false;
        }
        
        if (!repeating) {
            // One-time alarm: check if it's in the future
            return timeInMillis > System.currentTimeMillis();
        }
        
        // Repeating alarm: check if today is selected
        Calendar now = Calendar.getInstance();
        int today = now.get(Calendar.DAY_OF_WEEK) - 1; // 0=Sunday, 6=Saturday
        
        return days[today];
    }

    // Check if the alarm should ring at a specific time
    public boolean shouldRingAt(long timeMillis) {
        if (!enabled) {
            return false;
        }
        
        // Get hour and minute from alarm time
        Calendar alarmCal = Calendar.getInstance();
        alarmCal.setTimeInMillis(timeInMillis);
        int alarmHour = alarmCal.get(Calendar.HOUR_OF_DAY);
        int alarmMinute = alarmCal.get(Calendar.MINUTE);
        
        // Get hour and minute from this alarm's time
        Calendar thisCal = Calendar.getInstance();
        thisCal.setTimeInMillis(this.timeInMillis);
        int thisHour = thisCal.get(Calendar.HOUR_OF_DAY);
        int thisMinute = thisCal.get(Calendar.MINUTE);
        
        // Check if times match
        if (alarmHour != thisHour || alarmMinute != thisMinute) {
            return false;
        }
        
        if (!repeating) {
            // For one-time alarms, check if the day matches
            return alarmCal.get(Calendar.YEAR) == thisCal.get(Calendar.YEAR) &&
                   alarmCal.get(Calendar.DAY_OF_YEAR) == thisCal.get(Calendar.DAY_OF_YEAR);
        }
        
        // For repeating alarms, check if the day of week is enabled
        int dayOfWeek = alarmCal.get(Calendar.DAY_OF_WEEK) - 1; // 0=Sunday, 6=Saturday
        return days[dayOfWeek];
    }

    // Getters and Setters
    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    public long getTimeInMillis() {
        return timeInMillis;
    }

    public void setTimeInMillis(long timeInMillis) {
        this.timeInMillis = timeInMillis;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isRepeating() {
        return repeating;
    }

    public void setRepeating(boolean repeating) {
        this.repeating = repeating;
    }

    public boolean[] getDays() {
        return days;
    }

    public void setDays(boolean[] days) {
        this.days = days;
    }

    public boolean isTts() {
        return isTts;
    }

    public void setTts(boolean tts) {
        isTts = tts;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getSoundPath() {
        return soundPath;
    }

    public void setSoundPath(String soundPath) {
        this.soundPath = soundPath;
    }
}
