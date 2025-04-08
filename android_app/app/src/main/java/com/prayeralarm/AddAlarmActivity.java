package com.prayeralarm;

import android.app.Activity;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.ToggleButton;

import androidx.appcompat.app.AppCompatActivity;

import com.google.android.material.timepicker.MaterialTimePicker;
import com.google.android.material.timepicker.TimeFormat;
import com.prayeralarm.api.RaspberryPiApi;
import com.prayeralarm.database.AppDatabase;
import com.prayeralarm.model.Alarm;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.Calendar;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class AddAlarmActivity extends AppCompatActivity {

    private static final int PICK_AUDIO_FILE = 1;

    private TextView timeText;
    private ToggleButton[] dayButtons;
    private RadioGroup alarmTypeGroup;
    private RadioButton soundFileRadio;
    private RadioButton ttsRadio;
    private Button selectFileButton;
    private TextView selectedFileText;
    private EditText ttsMessageInput;
    private Button saveButton;
    private Button cancelButton;
    private CheckBox repeatCheckBox;

    private Calendar alarmTime;
    private String soundFilePath = null;
    private boolean isEditMode = false;
    private long editAlarmId = -1;
    
    private ExecutorService executorService;
    private AppDatabase database;
    private RaspberryPiApi raspberryPiApi;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_add_alarm);

        // Initialize components
        timeText = findViewById(R.id.timeText);
        dayButtons = new ToggleButton[]{
                findViewById(R.id.sundayButton),
                findViewById(R.id.mondayButton),
                findViewById(R.id.tuesdayButton),
                findViewById(R.id.wednesdayButton),
                findViewById(R.id.thursdayButton),
                findViewById(R.id.fridayButton),
                findViewById(R.id.saturdayButton)
        };
        alarmTypeGroup = findViewById(R.id.alarmTypeRadioGroup);
        soundFileRadio = findViewById(R.id.soundFileRadio);
        ttsRadio = findViewById(R.id.ttsRadio);
        selectFileButton = findViewById(R.id.selectFileButton);
        selectedFileText = findViewById(R.id.selectedFileText);
        ttsMessageInput = findViewById(R.id.ttsMessageInput);
        saveButton = findViewById(R.id.saveButton);
        cancelButton = findViewById(R.id.cancelButton);
        repeatCheckBox = findViewById(R.id.repeatCheckBox);
        
        executorService = Executors.newSingleThreadExecutor();
        database = AppDatabase.getInstance(getApplicationContext());
        raspberryPiApi = new RaspberryPiApi(this);

        // Initialize alarm time to current time
        alarmTime = Calendar.getInstance();
        alarmTime.set(Calendar.SECOND, 0);
        updateTimeText();

        // Set up click listeners
        setupClickListeners();
        
        // Check if editing an existing alarm
        if (getIntent().hasExtra("ALARM_ID")) {
            isEditMode = true;
            editAlarmId = getIntent().getLongExtra("ALARM_ID", -1);
            loadAlarmData(editAlarmId);
        }
        
        // Set up radio button listeners to show/hide appropriate views
        alarmTypeGroup.setOnCheckedChangeListener((group, checkedId) -> {
            if (checkedId == R.id.soundFileRadio) {
                selectFileButton.setVisibility(View.VISIBLE);
                selectedFileText.setVisibility(View.VISIBLE);
                ttsMessageInput.setVisibility(View.GONE);
            } else {
                selectFileButton.setVisibility(View.GONE);
                selectedFileText.setVisibility(View.GONE);
                ttsMessageInput.setVisibility(View.VISIBLE);
            }
        });
        
        // Set up repeat checkbox listener
        repeatCheckBox.setOnCheckedChangeListener((buttonView, isChecked) -> {
            for (ToggleButton dayButton : dayButtons) {
                dayButton.setEnabled(isChecked);
                if (!isChecked) {
                    dayButton.setChecked(false);
                }
            }
        });
    }

    private void loadAlarmData(long alarmId) {
        executorService.execute(() -> {
            Alarm alarm = database.alarmDao().getById(alarmId);
            if (alarm != null) {
                runOnUiThread(() -> {
                    // Set time
                    alarmTime.setTimeInMillis(alarm.getTimeInMillis());
                    updateTimeText();
                    
                    // Set repeat
                    repeatCheckBox.setChecked(alarm.isRepeating());
                    
                    // Set days
                    if (alarm.isRepeating()) {
                        boolean[] days = alarm.getDays();
                        for (int i = 0; i < 7; i++) {
                            dayButtons[i].setChecked(days[i]);
                        }
                    }
                    
                    // Set alarm type
                    if (alarm.isTts()) {
                        ttsRadio.setChecked(true);
                        ttsMessageInput.setText(alarm.getMessage());
                    } else {
                        soundFileRadio.setChecked(true);
                        soundFilePath = alarm.getSoundPath();
                        selectedFileText.setText(getSoundFileName(soundFilePath));
                    }
                });
            }
        });
    }

    private void setupClickListeners() {
        // Time picker
        timeText.setOnClickListener(v -> showTimePicker());
        
        // Select sound file
        selectFileButton.setOnClickListener(v -> {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("audio/*");
            startActivityForResult(intent, PICK_AUDIO_FILE);
        });
        
        // Save button
        saveButton.setOnClickListener(v -> saveAlarm());
        
        // Cancel button
        cancelButton.setOnClickListener(v -> finish());
    }

    private void showTimePicker() {
        MaterialTimePicker picker = new MaterialTimePicker.Builder()
                .setTimeFormat(TimeFormat.CLOCK_12H)
                .setHour(alarmTime.get(Calendar.HOUR_OF_DAY))
                .setMinute(alarmTime.get(Calendar.MINUTE))
                .setTitleText("Select Alarm Time")
                .build();

        picker.addOnPositiveButtonClickListener(dialog -> {
            alarmTime.set(Calendar.HOUR_OF_DAY, picker.getHour());
            alarmTime.set(Calendar.MINUTE, picker.getMinute());
            updateTimeText();
        });

        picker.show(getSupportFragmentManager(), "TIME_PICKER");
    }

    private void updateTimeText() {
        int hour = alarmTime.get(Calendar.HOUR_OF_DAY);
        int minute = alarmTime.get(Calendar.MINUTE);
        
        String amPm = hour >= 12 ? "PM" : "AM";
        int hour12 = hour % 12;
        if (hour12 == 0) hour12 = 12;
        
        String timeString = String.format("%d:%02d %s", hour12, minute, amPm);
        timeText.setText(timeString);
    }

    private void saveAlarm() {
        // Validate input
        if (soundFileRadio.isChecked() && soundFilePath == null) {
            Toast.makeText(this, "Please select a sound file", Toast.LENGTH_SHORT).show();
            return;
        }
        
        if (ttsRadio.isChecked() && ttsMessageInput.getText().toString().trim().isEmpty()) {
            Toast.makeText(this, "Please enter a message for text-to-speech", Toast.LENGTH_SHORT).show();
            return;
        }
        
        if (repeatCheckBox.isChecked()) {
            boolean anyDaySelected = false;
            for (ToggleButton dayButton : dayButtons) {
                if (dayButton.isChecked()) {
                    anyDaySelected = true;
                    break;
                }
            }
            
            if (!anyDaySelected) {
                Toast.makeText(this, "Please select at least one day for repeating alarm", Toast.LENGTH_SHORT).show();
                return;
            }
        }
        
        // Create alarm object
        final Alarm alarm = new Alarm();
        if (isEditMode) {
            alarm.setId(editAlarmId);
        }
        
        alarm.setTimeInMillis(alarmTime.getTimeInMillis());
        alarm.setEnabled(true);
        alarm.setRepeating(repeatCheckBox.isChecked());
        
        if (repeatCheckBox.isChecked()) {
            boolean[] days = new boolean[7];
            for (int i = 0; i < 7; i++) {
                days[i] = dayButtons[i].isChecked();
            }
            alarm.setDays(days);
        }
        
        alarm.setTts(ttsRadio.isChecked());
        if (ttsRadio.isChecked()) {
            alarm.setMessage(ttsMessageInput.getText().toString().trim());
        } else {
            alarm.setSoundPath(soundFilePath);
        }
        
        // Save to database and sync with Raspberry Pi
        executorService.execute(() -> {
            if (isEditMode) {
                database.alarmDao().update(alarm);
            } else {
                database.alarmDao().insert(alarm);
            }
            
            // Sync with Raspberry Pi
            raspberryPiApi.addOrUpdateAlarm(alarm);
            
            runOnUiThread(() -> {
                Toast.makeText(AddAlarmActivity.this, 
                        isEditMode ? "Alarm updated" : "Alarm added", 
                        Toast.LENGTH_SHORT).show();
                finish();
            });
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        
        if (requestCode == PICK_AUDIO_FILE && resultCode == Activity.RESULT_OK) {
            if (data != null && data.getData() != null) {
                Uri uri = data.getData();
                
                // Copy file to app's storage
                soundFilePath = copyAudioFileToAppStorage(uri);
                if (soundFilePath != null) {
                    selectedFileText.setText(getSoundFileName(soundFilePath));
                } else {
                    Toast.makeText(this, "Failed to copy audio file", Toast.LENGTH_SHORT).show();
                }
            }
        }
    }

    private String copyAudioFileToAppStorage(Uri sourceUri) {
        try {
            String fileName = getFileNameFromUri(sourceUri);
            if (fileName == null) {
                fileName = "alarm_" + UUID.randomUUID().toString() + ".mp3";
            }
            
            File destDir = new File(getFilesDir(), "alarms");
            if (!destDir.exists()) {
                destDir.mkdirs();
            }
            
            File destFile = new File(destDir, fileName);
            
            InputStream is = getContentResolver().openInputStream(sourceUri);
            FileOutputStream fos = new FileOutputStream(destFile);
            
            byte[] buffer = new byte[1024];
            int length;
            while ((length = is.read(buffer)) > 0) {
                fos.write(buffer, 0, length);
            }
            
            fos.close();
            is.close();
            
            return destFile.getAbsolutePath();
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    private String getFileNameFromUri(Uri uri) {
        String result = null;
        if (uri.getScheme().equals("content")) {
            try (Cursor cursor = getContentResolver().query(uri, null, null, null, null)) {
                if (cursor != null && cursor.moveToFirst()) {
                    int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                    if (nameIndex >= 0) {
                        result = cursor.getString(nameIndex);
                    }
                }
            }
        }
        
        if (result == null) {
            result = uri.getPath();
            int cut = result.lastIndexOf('/');
            if (cut != -1) {
                result = result.substring(cut + 1);
            }
        }
        
        return result;
    }

    private String getSoundFileName(String path) {
        if (path == null) return "No file selected";
        
        int lastSlash = path.lastIndexOf('/');
        if (lastSlash != -1 && lastSlash < path.length() - 1) {
            return path.substring(lastSlash + 1);
        }
        
        return path;
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executorService.shutdown();
    }
}
