package com.prayeralarm.database;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;

import com.prayeralarm.model.PrayerTime;

import java.util.Date;
import java.util.List;

@Dao
public interface PrayerTimeDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    void insertAll(PrayerTime... prayerTimes);

    @Query("SELECT * FROM prayer_times WHERE date(time / 1000, 'unixepoch', 'localtime') = date(:date / 1000, 'unixepoch', 'localtime') ORDER BY time ASC")
    List<PrayerTime> getByDate(Date date);

    @Query("SELECT * FROM prayer_times WHERE date(time / 1000, 'unixepoch', 'localtime') = date('now', 'localtime') ORDER BY time ASC")
    List<PrayerTime> getToday();

    @Query("SELECT * FROM prayer_times WHERE time >= :startTime ORDER BY time ASC LIMIT 1")
    PrayerTime getNextPrayer(long startTime);

    @Query("DELETE FROM prayer_times WHERE date(time / 1000, 'unixepoch', 'localtime') = date(:date / 1000, 'unixepoch', 'localtime')")
    void deleteByDate(Date date);

    @Query("DELETE FROM prayer_times")
    void deleteAll();
}
