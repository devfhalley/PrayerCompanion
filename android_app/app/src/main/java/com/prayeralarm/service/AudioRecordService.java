package com.prayeralarm.service;

import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class AudioRecordService {

    private static final String TAG = "AudioRecordService";
    private static final int SAMPLE_RATE = 16000;
    private static final int CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO;
    private static final int AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT;
    private static final int BUFFER_SIZE = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT) * 2;

    private AudioRecord audioRecord;
    private boolean isRecording = false;
    private ExecutorService executorService;
    private OnAudioDataAvailableListener listener;

    public interface OnAudioDataAvailableListener {
        void onAudioDataAvailable(byte[] audioData, int length);
    }

    public AudioRecordService() {
        executorService = Executors.newSingleThreadExecutor();
    }

    public boolean initialize() {
        try {
            audioRecord = new AudioRecord(
                    MediaRecorder.AudioSource.MIC,
                    SAMPLE_RATE,
                    CHANNEL_CONFIG,
                    AUDIO_FORMAT,
                    BUFFER_SIZE);
            
            return audioRecord.getState() == AudioRecord.STATE_INITIALIZED;
        } catch (Exception e) {
            Log.e(TAG, "Error initializing AudioRecord: " + e.getMessage());
            return false;
        }
    }

    public void setOnAudioDataAvailableListener(OnAudioDataAvailableListener listener) {
        this.listener = listener;
    }

    public boolean startRecording() {
        if (audioRecord == null || audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
            Log.e(TAG, "AudioRecord not initialized or in error state");
            return false;
        }
        
        try {
            audioRecord.startRecording();
            isRecording = true;
            
            executorService.execute(this::readAudioData);
            return true;
        } catch (Exception e) {
            Log.e(TAG, "Error starting recording: " + e.getMessage());
            return false;
        }
    }

    private void readAudioData() {
        byte[] buffer = new byte[BUFFER_SIZE / 2];
        
        while (isRecording) {
            int bytesRead = audioRecord.read(buffer, 0, buffer.length);
            
            if (bytesRead > 0 && listener != null) {
                listener.onAudioDataAvailable(buffer, bytesRead);
            }
        }
    }

    public void stopRecording() {
        isRecording = false;
        
        if (audioRecord != null) {
            try {
                if (audioRecord.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                    audioRecord.stop();
                }
            } catch (Exception e) {
                Log.e(TAG, "Error stopping recording: " + e.getMessage());
            }
        }
    }

    public void release() {
        stopRecording();
        
        if (audioRecord != null) {
            audioRecord.release();
            audioRecord = null;
        }
        
        executorService.shutdown();
    }

    public boolean isRecording() {
        return isRecording;
    }
}
