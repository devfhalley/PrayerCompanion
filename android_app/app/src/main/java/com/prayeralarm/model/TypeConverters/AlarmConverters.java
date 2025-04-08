package com.prayeralarm.model.TypeConverters;

import androidx.room.TypeConverter;

public class AlarmConverters {

    @TypeConverter
    public static String fromBooleanArray(boolean[] value) {
        if (value == null) {
            return null;
        }
        
        StringBuilder sb = new StringBuilder();
        for (boolean b : value) {
            sb.append(b ? '1' : '0');
        }
        return sb.toString();
    }

    @TypeConverter
    public static boolean[] toBooleanArray(String value) {
        if (value == null) {
            return new boolean[7]; // Return default empty array
        }
        
        boolean[] result = new boolean[value.length()];
        for (int i = 0; i < value.length(); i++) {
            result[i] = value.charAt(i) == '1';
        }
        return result;
    }
}
