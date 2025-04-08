package com.prayeralarm.api;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;

import com.prayeralarm.model.Alarm;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Base64;
import java.util.Calendar;
import java.util.Locale;

public class RaspberryPiApi {

    private static final String TAG = "RaspberryPiApi";
    private String serverIp;
    private int serverPort;
    private Context context;

    public RaspberryPiApi(Context context) {
        this.context = context;
        SharedPreferences prefs = context.getSharedPreferences("PrayerAlarmPrefs", Context.MODE_PRIVATE);
        this.serverIp = prefs.getString("server_ip", "192.168.1.100");
        this.serverPort = prefs.getInt("server_port", 5000);
    }

    public RaspberryPiApi(String serverIp, int serverPort) {
        this.serverIp = serverIp;
        this.serverPort = serverPort;
    }

    public String getBaseUrl() {
        return "http://" + serverIp + ":" + serverPort;
    }

    public String getWebSocketUrl() {
        return "ws://" + serverIp + ":" + serverPort + "/ws";
    }

    public boolean checkConnection() {
        try {
            URL url = new URL(getBaseUrl() + "/status");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(5000);
            
            int responseCode = connection.getResponseCode();
            return responseCode == HttpURLConnection.HTTP_OK;
        } catch (Exception e) {
            Log.e(TAG, "Error checking connection: " + e.getMessage());
            return false;
        }
    }

    public boolean addOrUpdateAlarm(Alarm alarm) {
        try {
            URL url = new URL(getBaseUrl() + "/alarms");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setDoOutput(true);
            
            // Prepare alarm JSON
            JSONObject alarmJson = new JSONObject();
            alarmJson.put("id", alarm.getId());
            alarmJson.put("time", new SimpleDateFormat("HH:mm", Locale.getDefault())
                    .format(new java.util.Date(alarm.getTimeInMillis())));
            
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(alarm.getTimeInMillis());
            alarmJson.put("hour", cal.get(Calendar.HOUR_OF_DAY));
            alarmJson.put("minute", cal.get(Calendar.MINUTE));
            
            alarmJson.put("enabled", alarm.isEnabled());
            alarmJson.put("repeating", alarm.isRepeating());
            
            if (alarm.isRepeating()) {
                JSONArray daysArray = new JSONArray();
                for (boolean day : alarm.getDays()) {
                    daysArray.put(day);
                }
                alarmJson.put("days", daysArray);
            } else {
                // For one-time alarms, include the full date
                alarmJson.put("date", new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                        .format(new java.util.Date(alarm.getTimeInMillis())));
            }
            
            alarmJson.put("is_tts", alarm.isTts());
            
            if (alarm.isTts()) {
                alarmJson.put("message", alarm.getMessage());
            } else {
                // For sound files, we need to send the file content as well
                String soundPath = alarm.getSoundPath();
                if (soundPath != null && !soundPath.isEmpty()) {
                    alarmJson.put("sound_file_name", getFileName(soundPath));
                    
                    // For API simplicity, we embed the file content directly in the JSON
                    // In a production app, you'd want to use multipart form data for larger files
                    File soundFile = new File(soundPath);
                    if (soundFile.exists()) {
                        byte[] fileBytes = new byte[(int) soundFile.length()];
                        FileInputStream fis = new FileInputStream(soundFile);
                        fis.read(fileBytes);
                        fis.close();
                        
                        // Base64 encode the file content
                        String fileContent = android.util.Base64.encodeToString(fileBytes, android.util.Base64.DEFAULT);
                        alarmJson.put("sound_file_content", fileContent);
                    }
                }
            }
            
            // Send the request
            OutputStream os = connection.getOutputStream();
            os.write(alarmJson.toString().getBytes());
            os.flush();
            os.close();
            
            int responseCode = connection.getResponseCode();
            return responseCode == HttpURLConnection.HTTP_OK || responseCode == HttpURLConnection.HTTP_CREATED;
        } catch (Exception e) {
            Log.e(TAG, "Error adding/updating alarm: " + e.getMessage());
            e.printStackTrace();
            return false;
        }
    }

    public boolean disableAlarm(long alarmId) {
        try {
            URL url = new URL(getBaseUrl() + "/alarms/" + alarmId + "/disable");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            
            int responseCode = connection.getResponseCode();
            return responseCode == HttpURLConnection.HTTP_OK;
        } catch (Exception e) {
            Log.e(TAG, "Error disabling alarm: " + e.getMessage());
            return false;
        }
    }

    public boolean deleteAlarm(long alarmId) {
        try {
            URL url = new URL(getBaseUrl() + "/alarms/" + alarmId);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("DELETE");
            
            int responseCode = connection.getResponseCode();
            return responseCode == HttpURLConnection.HTTP_OK || responseCode == HttpURLConnection.HTTP_NO_CONTENT;
        } catch (Exception e) {
            Log.e(TAG, "Error deleting alarm: " + e.getMessage());
            return false;
        }
    }

    private String getFileName(String path) {
        if (path == null) return null;
        
        int lastSlash = path.lastIndexOf('/');
        if (lastSlash != -1 && lastSlash < path.length() - 1) {
            return path.substring(lastSlash + 1);
        }
        
        return path;
    }
}
