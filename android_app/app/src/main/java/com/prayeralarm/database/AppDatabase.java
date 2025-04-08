package com.prayeralarm.database;

import android.content.Context;

import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;
import androidx.room.TypeConverters;

import com.prayeralarm.model.Alarm;
import com.prayeralarm.model.PrayerTime;
import com.prayeralarm.model.TypeConverters.AlarmConverters;
import com.prayeralarm.model.TypeConverters.DateConverter;

@Database(entities = {Alarm.class, PrayerTime.class}, version = 1, exportSchema = false)
@TypeConverters({DateConverter.class, AlarmConverters.class})
public abstract class AppDatabase extends RoomDatabase {

    private static final String DATABASE_NAME = "prayer_alarm_db";
    private static AppDatabase instance;

    public abstract AlarmDao alarmDao();
    public abstract PrayerTimeDao prayerTimeDao();

    public static synchronized AppDatabase getInstance(Context context) {
        if (instance == null) {
            instance = Room.databaseBuilder(
                    context.getApplicationContext(),
                    AppDatabase.class,
                    DATABASE_NAME)
                    .fallbackToDestructiveMigration()
                    .build();
        }
        return instance;
    }
}
