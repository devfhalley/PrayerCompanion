package com.prayeralarm.api;

import android.util.Log;

import com.prayeralarm.model.PrayerTime;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class PrayerTimeApi {

    private static final String TAG = "PrayerTimeApi";
    private static final String API_BASE_URL = "http://api.aladhan.com/v1/timingsByCity";

    public List<PrayerTime> getPrayerTimes(String city, String date) {
        try {
            String urlStr = API_BASE_URL + 
                    "?city=" + city + 
                    "&country=Indonesia" + 
                    "&method=11"; // Method 11 is for Indonesian Ministry of Religious Affairs
            
            if (date != null && !date.isEmpty()) {
                urlStr += "&date=" + date;
            }
            
            URL url = new URL(urlStr);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            
            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                reader.close();
                
                return parsePrayerTimesJson(response.toString(), date);
            } else {
                Log.e(TAG, "HTTP error: " + responseCode);
                return null;
            }
        } catch (Exception e) {
            Log.e(TAG, "Error fetching prayer times: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }

    public List<PrayerTime> getTodayPrayerTimes(String city) {
        return getPrayerTimes(city, null);
    }

    private List<PrayerTime> parsePrayerTimesJson(String json, String dateStr) {
        try {
            JSONObject jsonObject = new JSONObject(json);
            
            // Check if request was successful
            if (!jsonObject.getBoolean("status")) {
                Log.e(TAG, "API returned error status");
                return null;
            }
            
            JSONObject data = jsonObject.getJSONObject("data");
            JSONObject timings = data.getJSONObject("timings");
            
            // Parse date
            Date date;
            if (dateStr != null && !dateStr.isEmpty()) {
                SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());
                date = sdf.parse(dateStr);
            } else {
                // Use date from response
                JSONObject dateObject = data.getJSONObject("date");
                String gregorianDate = dateObject.getJSONObject("gregorian").getString("date");
                SimpleDateFormat sdf = new SimpleDateFormat("dd-MM-yyyy", Locale.getDefault());
                date = sdf.parse(gregorianDate);
            }
            
            if (date == null) {
                date = new Date(); // Fallback to today
            }
            
            Calendar calendar = Calendar.getInstance();
            calendar.setTime(date);
            
            List<PrayerTime> prayerTimes = new ArrayList<>();
            
            // Extract prayer times
            String[] prayerNames = {"Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"};
            
            SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm", Locale.getDefault());
            
            for (String prayerName : prayerNames) {
                String timeStr = timings.getString(prayerName);
                
                // Parse time
                Date timeDate = timeFormat.parse(timeStr);
                if (timeDate != null) {
                    // Set the time part in the calendar
                    Calendar timeCal = Calendar.getInstance();
                    timeCal.setTime(timeDate);
                    
                    calendar.set(Calendar.HOUR_OF_DAY, timeCal.get(Calendar.HOUR_OF_DAY));
                    calendar.set(Calendar.MINUTE, timeCal.get(Calendar.MINUTE));
                    calendar.set(Calendar.SECOND, 0);
                    calendar.set(Calendar.MILLISECOND, 0);
                    
                    // Create prayer time object
                    PrayerTime prayerTime = new PrayerTime(prayerName, calendar.getTime());
                    prayerTimes.add(prayerTime);
                }
            }
            
            return prayerTimes;
        } catch (Exception e) {
            Log.e(TAG, "Error parsing prayer times: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }
}
