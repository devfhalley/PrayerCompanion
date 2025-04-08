package com.prayeralarm.model;

import androidx.room.ColumnInfo;
import androidx.room.Entity;
import androidx.room.PrimaryKey;

import java.util.Date;

@Entity(tableName = "prayer_times")
public class PrayerTime {

    @PrimaryKey(autoGenerate = true)
    private long id;

    @ColumnInfo(name = "name")
    private String name;

    @ColumnInfo(name = "time")
    private Date time;

    @ColumnInfo(name = "enabled")
    private boolean enabled;

    @ColumnInfo(name = "custom_sound")
    private String customSound;

    public PrayerTime() {
        this.enabled = true;
    }

    public PrayerTime(String name, Date time) {
        this.name = name;
        this.time = time;
        this.enabled = true;
    }

    // Getters and Setters
    public long getId() {
        return id;
    }

    public void setId(long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Date getTime() {
        return time;
    }

    public void setTime(Date time) {
        this.time = time;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getCustomSound() {
        return customSound;
    }

    public void setCustomSound(String customSound) {
        this.customSound = customSound;
    }
}
