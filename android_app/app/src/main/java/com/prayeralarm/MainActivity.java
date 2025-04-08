package com.prayeralarm;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.prayeralarm.api.PrayerTimeApi;
import com.prayeralarm.api.RaspberryPiApi;
import com.prayeralarm.database.AppDatabase;
import com.prayeralarm.model.PrayerTime;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {

    private TextView dateTimeText;
    private TextView nextPrayerText;
    private Button alarmsButton;
    private Button prayerTimesButton;
    private Button pushToTalkButton;
    private Button settingsButton;
    
    private ExecutorService executorService;
    private RaspberryPiApi raspberryPiApi;
    private PrayerTimeApi prayerTimeApi;
    private AppDatabase database;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Initialize components
        dateTimeText = findViewById(R.id.dateTimeText);
        nextPrayerText = findViewById(R.id.nextPrayerText);
        alarmsButton = findViewById(R.id.alarmsButton);
        prayerTimesButton = findViewById(R.id.prayerTimesButton);
        pushToTalkButton = findViewById(R.id.pushToTalkButton);
        settingsButton = findViewById(R.id.settingsButton);
        
        executorService = Executors.newFixedThreadPool(4);
        raspberryPiApi = new RaspberryPiApi(this);
        prayerTimeApi = new PrayerTimeApi();
        database = AppDatabase.getInstance(getApplicationContext());

        // Set current date and time
        updateDateTime();

        // Check Raspberry Pi connection
        checkRaspberryPiConnection();

        // Set up button click listeners
        setupButtonListeners();
        
        // Update next prayer time
        updateNextPrayerTime();
    }

    private void updateDateTime() {
        SimpleDateFormat sdf = new SimpleDateFormat("EEEE, MMMM d, yyyy\nhh:mm a", Locale.getDefault());
        String currentDateTimeText = sdf.format(new Date());
        dateTimeText.setText(currentDateTimeText);
    }

    private void checkRaspberryPiConnection() {
        executorService.execute(() -> {
            boolean isConnected = raspberryPiApi.checkConnection();
            runOnUiThread(() -> {
                if (!isConnected) {
                    Toast.makeText(MainActivity.this, 
                            "Cannot connect to Raspberry Pi. Check settings.", 
                            Toast.LENGTH_LONG).show();
                }
            });
        });
    }

    private void updateNextPrayerTime() {
        executorService.execute(() -> {
            // Try to get from local database first
            List<PrayerTime> prayerTimes = database.prayerTimeDao().getToday();
            
            if (prayerTimes == null || prayerTimes.isEmpty()) {
                // If no data in database, fetch from API
                prayerTimes = prayerTimeApi.getTodayPrayerTimes("Jakarta");
                if (prayerTimes != null && !prayerTimes.isEmpty()) {
                    // Save to database
                    database.prayerTimeDao().insertAll(prayerTimes.toArray(new PrayerTime[0]));
                }
            }
            
            final String nextPrayer = getNextPrayerText(prayerTimes);
            runOnUiThread(() -> nextPrayerText.setText(nextPrayer));
        });
    }

    private String getNextPrayerText(List<PrayerTime> prayerTimes) {
        if (prayerTimes == null || prayerTimes.isEmpty()) {
            return "Prayer times not available";
        }
        
        Date now = new Date();
        
        for (PrayerTime prayer : prayerTimes) {
            if (prayer.getTime().after(now)) {
                SimpleDateFormat sdf = new SimpleDateFormat("hh:mm a", Locale.getDefault());
                return "Next Prayer: " + prayer.getName() + " at " + sdf.format(prayer.getTime());
            }
        }
        
        // If all prayers for today have passed
        return "All prayers for today have passed";
    }

    private void setupButtonListeners() {
        alarmsButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, AlarmListActivity.class);
            startActivity(intent);
        });

        prayerTimesButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, PrayerTimesActivity.class);
            startActivity(intent);
        });

        pushToTalkButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, PushToTalkActivity.class);
            startActivity(intent);
        });

        settingsButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, SettingsActivity.class);
            startActivity(intent);
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        // Refresh data when returning to activity
        updateDateTime();
        updateNextPrayerTime();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executorService.shutdown();
    }
}
