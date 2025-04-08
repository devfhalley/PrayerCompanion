package com.prayeralarm;

import android.Manifest;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Bundle;
import android.util.Log;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.prayeralarm.api.RaspberryPiApi;
import com.prayeralarm.service.WebSocketService;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class PushToTalkActivity extends AppCompatActivity {

    private static final String TAG = "PushToTalkActivity";
    private static final int REQUEST_RECORD_AUDIO_PERMISSION = 200;
    private static final int SAMPLE_RATE = 16000;
    private static final int CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO;
    private static final int AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT;
    private static final int BUFFER_SIZE = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT) * 2;

    private ImageButton pushToTalkButton;
    private TextView statusText;
    private Button backButton;
    
    private AudioRecord audioRecord;
    private boolean isRecording = false;
    private ExecutorService executorService;
    private WebSocketService webSocketService;
    private RaspberryPiApi raspberryPiApi;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_push_to_talk);

        // Initialize components
        pushToTalkButton = findViewById(R.id.pushToTalkButton);
        statusText = findViewById(R.id.statusText);
        backButton = findViewById(R.id.backButton);
        
        executorService = Executors.newSingleThreadExecutor();
        raspberryPiApi = new RaspberryPiApi(this);
        
        // Check and request microphone permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO},
                    REQUEST_RECORD_AUDIO_PERMISSION);
        } else {
            initializeAudio();
        }
        
        // Initialize WebSocket
        initWebSocket();
        
        // Setup button listeners
        setupButtonListeners();
    }

    private void initWebSocket() {
        webSocketService = new WebSocketService(raspberryPiApi.getWebSocketUrl());
        webSocketService.connect(
            // onConnected
            () -> runOnUiThread(() -> {
                statusText.setText("Connected and ready");
                pushToTalkButton.setEnabled(true);
            }),
            // onDisconnected
            () -> runOnUiThread(() -> {
                statusText.setText("Disconnected");
                pushToTalkButton.setEnabled(false);
            }),
            // onError
            (error) -> runOnUiThread(() -> {
                statusText.setText("Error: " + error);
                pushToTalkButton.setEnabled(false);
            })
        );
    }

    private void initializeAudio() {
        try {
            audioRecord = new AudioRecord(
                    MediaRecorder.AudioSource.MIC,
                    SAMPLE_RATE,
                    CHANNEL_CONFIG,
                    AUDIO_FORMAT,
                    BUFFER_SIZE);
        } catch (Exception e) {
            Log.e(TAG, "Failed to initialize AudioRecord: " + e.getMessage());
            Toast.makeText(this, "Failed to initialize audio recorder", Toast.LENGTH_SHORT).show();
        }
    }

    private void setupButtonListeners() {
        pushToTalkButton.setOnTouchListener((v, event) -> {
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    // Start recording
                    if (!isRecording && webSocketService.isConnected()) {
                        startRecording();
                    }
                    break;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    // Stop recording
                    if (isRecording) {
                        stopRecording();
                    }
                    break;
            }
            return false;
        });
        
        backButton.setOnClickListener(v -> finish());
    }

    private void startRecording() {
        if (audioRecord == null) {
            return;
        }
        
        try {
            audioRecord.startRecording();
            isRecording = true;
            statusText.setText("Recording... (Keep button pressed)");
            
            // Send start message to Raspberry Pi
            try {
                JSONObject message = new JSONObject();
                message.put("type", "ptt_start");
                webSocketService.send(message.toString());
            } catch (Exception e) {
                Log.e(TAG, "Error sending ptt_start message: " + e.getMessage());
            }
            
            // Start streaming audio in a background thread
            executorService.execute(this::streamAudio);
        } catch (Exception e) {
            Log.e(TAG, "Error starting recording: " + e.getMessage());
            Toast.makeText(this, "Failed to start recording", Toast.LENGTH_SHORT).show();
        }
    }

    private void streamAudio() {
        byte[] buffer = new byte[BUFFER_SIZE / 2];
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        
        while (isRecording && webSocketService.isConnected()) {
            int bytesRead = audioRecord.read(buffer, 0, buffer.length);
            
            if (bytesRead > 0) {
                try {
                    // Create a JSON message with audio data and format information
                    JSONObject message = new JSONObject();
                    message.put("type", "ptt_audio");
                    message.put("data", android.util.Base64.encodeToString(buffer, 0, bytesRead, android.util.Base64.DEFAULT));
                    message.put("format", "pcm_16bit"); // PCM 16-bit audio format from AudioRecord
                    message.put("sample_rate", SAMPLE_RATE);
                    message.put("channels", 1); // Mono
                    
                    // Send through WebSocket
                    webSocketService.send(message.toString());
                } catch (Exception e) {
                    Log.e(TAG, "Error sending audio data: " + e.getMessage());
                }
            }
        }
    }

    private void stopRecording() {
        if (audioRecord != null) {
            try {
                audioRecord.stop();
                
                // Send stop message to Raspberry Pi
                try {
                    JSONObject message = new JSONObject();
                    message.put("type", "ptt_stop");
                    webSocketService.send(message.toString());
                } catch (Exception e) {
                    Log.e(TAG, "Error sending ptt_stop message: " + e.getMessage());
                }
                
            } catch (Exception e) {
                Log.e(TAG, "Error stopping recording: " + e.getMessage());
            }
        }
        
        isRecording = false;
        statusText.setText("Connected and ready");
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_RECORD_AUDIO_PERMISSION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                initializeAudio();
            } else {
                Toast.makeText(this, "Microphone permission is required for Push-to-Talk", 
                        Toast.LENGTH_LONG).show();
                finish();
            }
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        
        // Clean up resources
        if (audioRecord != null) {
            audioRecord.release();
            audioRecord = null;
        }
        
        if (webSocketService != null) {
            webSocketService.disconnect();
        }
        
        executorService.shutdown();
    }
}
