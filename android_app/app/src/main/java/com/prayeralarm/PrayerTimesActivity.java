package com.prayeralarm;

import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.prayeralarm.adapter.PrayerTimeAdapter;
import com.prayeralarm.api.PrayerTimeApi;
import com.prayeralarm.database.AppDatabase;
import com.prayeralarm.model.PrayerTime;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class PrayerTimesActivity extends AppCompatActivity {

    private RecyclerView recyclerView;
    private PrayerTimeAdapter adapter;
    private ProgressBar progressBar;
    private TextView dateText;
    private Button prevDayButton;
    private Button nextDayButton;
    private Button refreshButton;
    private Button backButton;
    
    private ExecutorService executorService;
    private PrayerTimeApi prayerTimeApi;
    private AppDatabase database;
    
    private Calendar currentDate;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_prayer_times);

        // Initialize components
        recyclerView = findViewById(R.id.prayerTimesRecyclerView);
        progressBar = findViewById(R.id.progressBar);
        dateText = findViewById(R.id.dateText);
        prevDayButton = findViewById(R.id.prevDayButton);
        nextDayButton = findViewById(R.id.nextDayButton);
        refreshButton = findViewById(R.id.refreshButton);
        backButton = findViewById(R.id.backButton);
        
        executorService = Executors.newSingleThreadExecutor();
        prayerTimeApi = new PrayerTimeApi();
        database = AppDatabase.getInstance(getApplicationContext());
        
        // Initialize with current date
        currentDate = Calendar.getInstance();
        
        // Setup RecyclerView
        recyclerView.setLayoutManager(new LinearLayoutManager(this));
        adapter = new PrayerTimeAdapter();
        recyclerView.setAdapter(adapter);
        
        // Load prayer times for current date
        updateDateText();
        loadPrayerTimes();
        
        // Setup button listeners
        setupButtonListeners();
    }

    private void setupButtonListeners() {
        prevDayButton.setOnClickListener(v -> {
            currentDate.add(Calendar.DAY_OF_MONTH, -1);
            updateDateText();
            loadPrayerTimes();
        });
        
        nextDayButton.setOnClickListener(v -> {
            currentDate.add(Calendar.DAY_OF_MONTH, 1);
            updateDateText();
            loadPrayerTimes();
        });
        
        refreshButton.setOnClickListener(v -> {
            // Force refresh from API
            loadPrayerTimes(true);
        });
        
        backButton.setOnClickListener(v -> finish());
    }

    private void updateDateText() {
        SimpleDateFormat sdf = new SimpleDateFormat("EEEE, MMMM d, yyyy", Locale.getDefault());
        dateText.setText(sdf.format(currentDate.getTime()));
    }

    private void loadPrayerTimes() {
        loadPrayerTimes(false);
    }

    private void loadPrayerTimes(boolean forceRefresh) {
        progressBar.setVisibility(View.VISIBLE);
        
        executorService.execute(() -> {
            Date date = currentDate.getTime();
            List<PrayerTime> prayerTimes = null;
            
            if (!forceRefresh) {
                // Try to get from database first
                prayerTimes = database.prayerTimeDao().getByDate(date);
            }
            
            if (prayerTimes == null || prayerTimes.isEmpty() || forceRefresh) {
                // If not in database or force refresh, fetch from API
                SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());
                String dateStr = sdf.format(date);
                
                prayerTimes = prayerTimeApi.getPrayerTimes("Jakarta", dateStr);
                
                if (prayerTimes != null && !prayerTimes.isEmpty()) {
                    // Save to database
                    if (forceRefresh) {
                        // Delete existing entries first
                        database.prayerTimeDao().deleteByDate(date);
                    }
                    database.prayerTimeDao().insertAll(prayerTimes.toArray(new PrayerTime[0]));
                }
            }
            
            final List<PrayerTime> finalPrayerTimes = prayerTimes;
            runOnUiThread(() -> {
                progressBar.setVisibility(View.GONE);
                
                if (finalPrayerTimes != null && !finalPrayerTimes.isEmpty()) {
                    adapter.setPrayerTimes(finalPrayerTimes);
                } else {
                    Toast.makeText(this, "Failed to load prayer times", Toast.LENGTH_SHORT).show();
                    adapter.setPrayerTimes(null);
                }
            });
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executorService.shutdown();
    }
}
