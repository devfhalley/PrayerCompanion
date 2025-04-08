package com.prayeralarm.adapter;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.Switch;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.prayeralarm.R;
import com.prayeralarm.model.Alarm;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;

public class AlarmAdapter extends RecyclerView.Adapter<AlarmAdapter.AlarmViewHolder> {

    private List<Alarm> alarms;
    private final AlarmClickListener listener;

    public interface AlarmClickListener {
        void onAlarmClick(Alarm alarm);
        void onAlarmToggle(Alarm alarm, boolean isEnabled);
        void onAlarmDelete(Alarm alarm);
    }

    public AlarmAdapter(AlarmClickListener listener) {
        this.listener = listener;
    }

    public void setAlarms(List<Alarm> alarms) {
        this.alarms = alarms;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public AlarmViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_alarm, parent, false);
        return new AlarmViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull AlarmViewHolder holder, int position) {
        if (alarms != null && position < alarms.size()) {
            holder.bind(alarms.get(position));
        }
    }

    @Override
    public int getItemCount() {
        return alarms != null ? alarms.size() : 0;
    }

    class AlarmViewHolder extends RecyclerView.ViewHolder {
        private final TextView timeText;
        private final TextView daysText;
        private final TextView typeText;
        private final Switch enabledSwitch;
        private final ImageButton deleteButton;

        public AlarmViewHolder(@NonNull View itemView) {
            super(itemView);
            timeText = itemView.findViewById(R.id.alarmTimeText);
            daysText = itemView.findViewById(R.id.alarmDaysText);
            typeText = itemView.findViewById(R.id.alarmTypeText);
            enabledSwitch = itemView.findViewById(R.id.alarmEnabledSwitch);
            deleteButton = itemView.findViewById(R.id.alarmDeleteButton);
        }

        public void bind(final Alarm alarm) {
            // Format time
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(alarm.getTimeInMillis());
            SimpleDateFormat sdf = new SimpleDateFormat("hh:mm a", Locale.getDefault());
            timeText.setText(sdf.format(cal.getTime()));

            // Set days text
            daysText.setText(getDaysText(alarm));

            // Set type text
            if (alarm.isTts()) {
                typeText.setText("TTS: " + truncate(alarm.getMessage(), 20));
            } else {
                typeText.setText("Sound: " + getFileName(alarm.getSoundPath()));
            }

            // Set switch state
            enabledSwitch.setChecked(alarm.isEnabled());
            enabledSwitch.setOnCheckedChangeListener((buttonView, isChecked) -> 
                listener.onAlarmToggle(alarm, isChecked));

            // Set click listeners
            itemView.setOnClickListener(v -> listener.onAlarmClick(alarm));
            deleteButton.setOnClickListener(v -> listener.onAlarmDelete(alarm));
        }

        private String getDaysText(Alarm alarm) {
            if (!alarm.isRepeating()) {
                // Format date for one-time alarm
                Calendar cal = Calendar.getInstance();
                cal.setTimeInMillis(alarm.getTimeInMillis());
                
                // Check if it's today, tomorrow, or another day
                Calendar today = Calendar.getInstance();
                Calendar tomorrow = Calendar.getInstance();
                tomorrow.add(Calendar.DAY_OF_YEAR, 1);
                
                if (cal.get(Calendar.YEAR) == today.get(Calendar.YEAR) && 
                    cal.get(Calendar.DAY_OF_YEAR) == today.get(Calendar.DAY_OF_YEAR)) {
                    return "Today";
                } else if (cal.get(Calendar.YEAR) == tomorrow.get(Calendar.YEAR) && 
                           cal.get(Calendar.DAY_OF_YEAR) == tomorrow.get(Calendar.DAY_OF_YEAR)) {
                    return "Tomorrow";
                } else {
                    SimpleDateFormat sdf = new SimpleDateFormat("MMM d, yyyy", Locale.getDefault());
                    return sdf.format(cal.getTime());
                }
            }
            
            // Repeating alarm
            boolean[] days = alarm.getDays();
            StringBuilder sb = new StringBuilder();
            String[] dayAbbr = {"Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"};
            
            boolean allDays = true;
            boolean noDays = true;
            
            for (boolean day : days) {
                if (!day) allDays = false;
                if (day) noDays = false;
            }
            
            if (allDays) {
                return "Every day";
            } else if (noDays) {
                return "Never";
            }
            
            // Check for weekdays
            boolean allWeekdays = true;
            for (int i = 1; i <= 5; i++) { // Monday to Friday
                if (!days[i]) {
                    allWeekdays = false;
                    break;
                }
            }
            
            if (allWeekdays && !days[0] && !days[6]) {
                return "Weekdays";
            }
            
            // Check for weekends
            if (days[0] && days[6] && !days[1] && !days[2] && !days[3] && !days[4] && !days[5]) {
                return "Weekends";
            }
            
            // List specific days
            for (int i = 0; i < days.length; i++) {
                if (days[i]) {
                    if (sb.length() > 0) sb.append(", ");
                    sb.append(dayAbbr[i]);
                }
            }
            
            return sb.toString();
        }

        private String getFileName(String path) {
            if (path == null) return "Default sound";
            
            int lastSlash = path.lastIndexOf('/');
            if (lastSlash != -1 && lastSlash < path.length() - 1) {
                return path.substring(lastSlash + 1);
            }
            
            return path;
        }

        private String truncate(String text, int maxLength) {
            if (text == null) return "";
            if (text.length() <= maxLength) return text;
            return text.substring(0, maxLength - 3) + "...";
        }
    }
}
