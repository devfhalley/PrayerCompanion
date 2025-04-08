package com.prayeralarm;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.prayeralarm.adapter.AlarmAdapter;
import com.prayeralarm.api.RaspberryPiApi;
import com.prayeralarm.database.AppDatabase;
import com.prayeralarm.model.Alarm;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class AlarmListActivity extends AppCompatActivity implements AlarmAdapter.AlarmClickListener {

    private RecyclerView recyclerView;
    private AlarmAdapter alarmAdapter;
    private FloatingActionButton addAlarmFab;
    private TextView emptyView;
    private Button backButton;
    
    private ExecutorService executorService;
    private AppDatabase database;
    private RaspberryPiApi raspberryPiApi;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_alarm_list);

        // Initialize components
        recyclerView = findViewById(R.id.alarmsRecyclerView);
        addAlarmFab = findViewById(R.id.addAlarmFab);
        emptyView = findViewById(R.id.emptyAlarmsView);
        backButton = findViewById(R.id.backButton);
        
        executorService = Executors.newSingleThreadExecutor();
        database = AppDatabase.getInstance(getApplicationContext());
        raspberryPiApi = new RaspberryPiApi(this);

        // Set up RecyclerView
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        alarmAdapter = new AlarmAdapter(this);
        recyclerView.setAdapter(alarmAdapter);

        // Set up click listeners
        addAlarmFab.setOnClickListener(v -> {
            Intent intent = new Intent(AlarmListActivity.this, AddAlarmActivity.class);
            startActivity(intent);
        });
        
        backButton.setOnClickListener(v -> finish());

        // Load alarms
        loadAlarms();
    }

    private void loadAlarms() {
        executorService.execute(() -> {
            List<Alarm> alarms = database.alarmDao().getAll();
            runOnUiThread(() -> {
                alarmAdapter.setAlarms(alarms);
                
                // Show empty view if no alarms
                if (alarms == null || alarms.isEmpty()) {
                    emptyView.setVisibility(View.VISIBLE);
                    recyclerView.setVisibility(View.GONE);
                } else {
                    emptyView.setVisibility(View.GONE);
                    recyclerView.setVisibility(View.VISIBLE);
                }
            });
        });
    }

    @Override
    public void onAlarmClick(Alarm alarm) {
        // Open edit alarm activity
        Intent intent = new Intent(AlarmListActivity.this, AddAlarmActivity.class);
        intent.putExtra("ALARM_ID", alarm.getId());
        startActivity(intent);
    }

    @Override
    public void onAlarmToggle(Alarm alarm, boolean isEnabled) {
        // Update alarm enabled status
        executorService.execute(() -> {
            alarm.setEnabled(isEnabled);
            database.alarmDao().update(alarm);
            
            // Sync with Raspberry Pi
            if (isEnabled) {
                raspberryPiApi.addOrUpdateAlarm(alarm);
            } else {
                raspberryPiApi.disableAlarm(alarm.getId());
            }
        });
    }

    @Override
    public void onAlarmDelete(Alarm alarm) {
        // Delete alarm
        executorService.execute(() -> {
            database.alarmDao().delete(alarm);
            
            // Sync with Raspberry Pi
            raspberryPiApi.deleteAlarm(alarm.getId());
            
            // Refresh UI
            List<Alarm> alarms = database.alarmDao().getAll();
            runOnUiThread(() -> {
                alarmAdapter.setAlarms(alarms);
                
                // Show empty view if no alarms
                if (alarms == null || alarms.isEmpty()) {
                    emptyView.setVisibility(View.VISIBLE);
                    recyclerView.setVisibility(View.GONE);
                }
            });
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        // Refresh alarms when returning to activity
        loadAlarms();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executorService.shutdown();
    }
}
