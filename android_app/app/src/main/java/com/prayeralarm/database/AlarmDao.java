package com.prayeralarm.database;

import androidx.room.Dao;
import androidx.room.Delete;
import androidx.room.Insert;
import androidx.room.OnConflictStrategy;
import androidx.room.Query;
import androidx.room.Update;

import com.prayeralarm.model.Alarm;

import java.util.List;

@Dao
public interface AlarmDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    long insert(Alarm alarm);

    @Update
    void update(Alarm alarm);

    @Delete
    void delete(Alarm alarm);

    @Query("SELECT * FROM alarms ORDER BY timeInMillis ASC")
    List<Alarm> getAll();

    @Query("SELECT * FROM alarms WHERE id = :id")
    Alarm getById(long id);

    @Query("SELECT * FROM alarms WHERE enabled = 1 ORDER BY timeInMillis ASC")
    List<Alarm> getEnabled();

    @Query("SELECT * FROM alarms WHERE enabled = 1 AND repeating = 0 AND timeInMillis >= :startTime AND timeInMillis <= :endTime ORDER BY timeInMillis ASC")
    List<Alarm> getEnabledOneTimeInRange(long startTime, long endTime);

    @Query("SELECT * FROM alarms WHERE enabled = 1 AND repeating = 1")
    List<Alarm> getEnabledRepeating();
}
