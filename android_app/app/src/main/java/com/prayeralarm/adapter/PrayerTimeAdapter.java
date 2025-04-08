package com.prayeralarm.adapter;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.prayeralarm.R;
import com.prayeralarm.model.PrayerTime;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class PrayerTimeAdapter extends RecyclerView.Adapter<PrayerTimeAdapter.PrayerTimeViewHolder> {

    private List<PrayerTime> prayerTimes;

    public void setPrayerTimes(List<PrayerTime> prayerTimes) {
        this.prayerTimes = prayerTimes;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public PrayerTimeViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_prayer_time, parent, false);
        return new PrayerTimeViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull PrayerTimeViewHolder holder, int position) {
        if (prayerTimes != null && position < prayerTimes.size()) {
            holder.bind(prayerTimes.get(position));
        }
    }

    @Override
    public int getItemCount() {
        return prayerTimes != null ? prayerTimes.size() : 0;
    }

    static class PrayerTimeViewHolder extends RecyclerView.ViewHolder {
        private final TextView nameText;
        private final TextView timeText;
        private final View statusIndicator;

        public PrayerTimeViewHolder(@NonNull View itemView) {
            super(itemView);
            nameText = itemView.findViewById(R.id.prayerNameText);
            timeText = itemView.findViewById(R.id.prayerTimeText);
            statusIndicator = itemView.findViewById(R.id.statusIndicator);
        }

        public void bind(PrayerTime prayerTime) {
            nameText.setText(formatPrayerName(prayerTime.getName()));
            
            SimpleDateFormat sdf = new SimpleDateFormat("hh:mm a", Locale.getDefault());
            timeText.setText(sdf.format(prayerTime.getTime()));
            
            // Show current/next indicator
            Date now = new Date();
            if (isPrayerCurrent(prayerTime, now)) {
                statusIndicator.setVisibility(View.VISIBLE);
                statusIndicator.setBackgroundResource(R.drawable.current_prayer_indicator);
            } else if (isPrayerNext(prayerTime, now)) {
                statusIndicator.setVisibility(View.VISIBLE);
                statusIndicator.setBackgroundResource(R.drawable.next_prayer_indicator);
            } else {
                statusIndicator.setVisibility(View.INVISIBLE);
            }
        }

        private boolean isPrayerCurrent(PrayerTime prayerTime, Date now) {
            // Check if this prayer time is the most recent in the past
            if (prayerTime.getTime().after(now)) {
                return false;
            }
            
            // Check if this is the most recent prayer
            if (prayerTimes != null) {
                Date mostRecentTime = new Date(0); // Jan 1, 1970
                
                for (PrayerTime pt : prayerTimes) {
                    if (pt.getTime().before(now) && pt.getTime().after(mostRecentTime)) {
                        mostRecentTime = pt.getTime();
                    }
                }
                
                return prayerTime.getTime().equals(mostRecentTime);
            }
            
            return false;
        }

        private boolean isPrayerNext(PrayerTime prayerTime, Date now) {
            // Check if this prayer time is the next one in the future
            if (prayerTime.getTime().before(now)) {
                return false;
            }
            
            // Check if this is the next upcoming prayer
            if (prayerTimes != null) {
                Date nextTime = null;
                
                for (PrayerTime pt : prayerTimes) {
                    if (pt.getTime().after(now)) {
                        if (nextTime == null || pt.getTime().before(nextTime)) {
                            nextTime = pt.getTime();
                        }
                    }
                }
                
                return prayerTime.getTime().equals(nextTime);
            }
            
            return false;
        }

        private String formatPrayerName(String name) {
            // Capitalize the prayer name and make it more readable
            if (name == null || name.isEmpty()) {
                return "";
            }
            
            // Common prayer names
            switch (name.toLowerCase()) {
                case "fajr":
                    return "Fajr";
                case "dhuhr":
                    return "Dhuhr";
                case "asr":
                    return "Asr";
                case "maghrib":
                    return "Maghrib";
                case "isha":
                    return "Isha";
                case "sunrise":
                    return "Sunrise";
                case "sunset":
                    return "Sunset";
                case "imsak":
                    return "Imsak";
                case "midnight":
                    return "Midnight";
                default:
                    // Capitalize first letter
                    return name.substring(0, 1).toUpperCase() + name.substring(1);
            }
        }
    }
}
