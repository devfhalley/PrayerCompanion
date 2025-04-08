package com.prayeralarm;

import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.prayeralarm.api.RaspberryPiApi;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SettingsActivity extends AppCompatActivity {

    private EditText serverIpInput;
    private EditText serverPortInput;
    private Button testConnectionButton;
    private Button saveButton;
    private Button backButton;
    
    private ExecutorService executorService;
    private SharedPreferences preferences;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        // Initialize components
        serverIpInput = findViewById(R.id.serverIpInput);
        serverPortInput = findViewById(R.id.serverPortInput);
        testConnectionButton = findViewById(R.id.testConnectionButton);
        saveButton = findViewById(R.id.saveButton);
        backButton = findViewById(R.id.backButton);
        
        executorService = Executors.newSingleThreadExecutor();
        preferences = getSharedPreferences("PrayerAlarmPrefs", MODE_PRIVATE);

        // Load saved settings
        loadSettings();
        
        // Setup button listeners
        setupButtonListeners();
    }

    private void loadSettings() {
        String serverIp = preferences.getString("server_ip", "192.168.1.100");
        int serverPort = preferences.getInt("server_port", 8000);
        
        serverIpInput.setText(serverIp);
        serverPortInput.setText(String.valueOf(serverPort));
    }

    private void setupButtonListeners() {
        testConnectionButton.setOnClickListener(v -> testConnection());
        
        saveButton.setOnClickListener(v -> saveSettings());
        
        backButton.setOnClickListener(v -> finish());
    }

    private void testConnection() {
        String serverIp = serverIpInput.getText().toString().trim();
        String serverPortStr = serverPortInput.getText().toString().trim();
        
        if (serverIp.isEmpty() || serverPortStr.isEmpty()) {
            Toast.makeText(this, "Please enter server IP and port", Toast.LENGTH_SHORT).show();
            return;
        }
        
        int serverPort;
        try {
            serverPort = Integer.parseInt(serverPortStr);
        } catch (NumberFormatException e) {
            Toast.makeText(this, "Please enter a valid port number", Toast.LENGTH_SHORT).show();
            return;
        }
        
        testConnectionButton.setEnabled(false);
        testConnectionButton.setText("Testing...");
        
        executorService.execute(() -> {
            RaspberryPiApi api = new RaspberryPiApi(serverIp, serverPort);
            boolean isConnected = api.checkConnection();
            
            runOnUiThread(() -> {
                testConnectionButton.setEnabled(true);
                testConnectionButton.setText("Test Connection");
                
                if (isConnected) {
                    Toast.makeText(SettingsActivity.this, 
                            "Connection successful!", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(SettingsActivity.this, 
                            "Connection failed. Check IP and port.", Toast.LENGTH_SHORT).show();
                }
            });
        });
    }

    private void saveSettings() {
        String serverIp = serverIpInput.getText().toString().trim();
        String serverPortStr = serverPortInput.getText().toString().trim();
        
        if (serverIp.isEmpty() || serverPortStr.isEmpty()) {
            Toast.makeText(this, "Please enter server IP and port", Toast.LENGTH_SHORT).show();
            return;
        }
        
        int serverPort;
        try {
            serverPort = Integer.parseInt(serverPortStr);
        } catch (NumberFormatException e) {
            Toast.makeText(this, "Please enter a valid port number", Toast.LENGTH_SHORT).show();
            return;
        }
        
        // Save to preferences
        SharedPreferences.Editor editor = preferences.edit();
        editor.putString("server_ip", serverIp);
        editor.putInt("server_port", serverPort);
        editor.apply();
        
        Toast.makeText(this, "Settings saved", Toast.LENGTH_SHORT).show();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executorService.shutdown();
    }
}
