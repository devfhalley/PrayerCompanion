package com.prayeralarm;

import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.prayeralarm.api.RaspberryPiApi;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MurattalPlayerActivity extends AppCompatActivity {

    private static final String TAG = "MurattalPlayerActivity";
    private static final int FILE_SELECT_CODE = 101;

    private RaspberryPiApi raspberryPiApi;
    private ListView murattalListView;
    private List<String> murattalNames = new ArrayList<>();
    private Map<String, String> murattalPaths = new HashMap<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_murattal_player);

        raspberryPiApi = new RaspberryPiApi(this);

        murattalListView = findViewById(R.id.murattal_list);
        findViewById(R.id.upload_button).setOnClickListener(v -> selectFile());
        findViewById(R.id.stop_button).setOnClickListener(v -> stopAudio());
        findViewById(R.id.back_button).setOnClickListener(v -> finish());

        loadMurattalFiles();

        // Setup list click listener
        murattalListView.setOnItemClickListener((parent, view, position, id) -> {
            String name = murattalNames.get(position);
            String path = murattalPaths.get(name);
            playMurattal(path);
        });
    }

    private void loadMurattalFiles() {
        new LoadMurattalFilesTask().execute();
    }

    private void playMurattal(String filePath) {
        new PlayMurattalTask().execute(filePath);
    }

    private void uploadMurattal(Uri fileUri) {
        try {
            // Get the file path from the URI
            String filePath = FileUtils.getPath(this, fileUri);
            if (filePath == null) {
                Toast.makeText(this, "Unable to get file path", Toast.LENGTH_SHORT).show();
                return;
            }

            // Make sure it's an MP3 file
            if (!filePath.toLowerCase().endsWith(".mp3")) {
                Toast.makeText(this, "Please select an MP3 file", Toast.LENGTH_SHORT).show();
                return;
            }

            new UploadMurattalTask().execute(filePath);
        } catch (Exception e) {
            Log.e(TAG, "Error uploading file: " + e.getMessage());
            Toast.makeText(this, "Error uploading file", Toast.LENGTH_SHORT).show();
        }
    }

    private void stopAudio() {
        new StopAudioTask().execute();
    }

    private void selectFile() {
        Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
        intent.setType("audio/mpeg");
        intent.addCategory(Intent.CATEGORY_OPENABLE);

        try {
            startActivityForResult(Intent.createChooser(intent, "Select a Murattal MP3 File"), FILE_SELECT_CODE);
        } catch (android.content.ActivityNotFoundException ex) {
            Toast.makeText(this, "Please install a File Manager.", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == FILE_SELECT_CODE && resultCode == RESULT_OK) {
            Uri selectedFileUri = data.getData();
            if (selectedFileUri != null) {
                uploadMurattal(selectedFileUri);
            }
        }
    }

    private class LoadMurattalFilesTask extends AsyncTask<Void, Void, List<String>> {
        @Override
        protected List<String> doInBackground(Void... voids) {
            List<String> names = new ArrayList<>();
            try {
                JSONArray filesArray = raspberryPiApi.getMurattalFiles();
                for (int i = 0; i < filesArray.length(); i++) {
                    JSONObject file = filesArray.getJSONObject(i);
                    String name = file.getString("name");
                    String path = file.getString("path");
                    names.add(name);
                    murattalPaths.put(name, path);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error loading murattal files: " + e.getMessage());
            }
            return names;
        }

        @Override
        protected void onPostExecute(List<String> result) {
            murattalNames.clear();
            murattalNames.addAll(result);
            
            if (murattalNames.isEmpty()) {
                murattalNames.add("No Murattal files available");
            }
            
            ArrayAdapter<String> adapter = new ArrayAdapter<>(
                    MurattalPlayerActivity.this,
                    android.R.layout.simple_list_item_1,
                    murattalNames);
            murattalListView.setAdapter(adapter);
        }
    }

    private class PlayMurattalTask extends AsyncTask<String, Void, Boolean> {
        @Override
        protected Boolean doInBackground(String... paths) {
            if (paths.length == 0) return false;
            return raspberryPiApi.playMurattal(paths[0]);
        }

        @Override
        protected void onPostExecute(Boolean success) {
            if (success) {
                Toast.makeText(MurattalPlayerActivity.this, "Murattal playing", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(MurattalPlayerActivity.this, "Failed to play Murattal", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private class UploadMurattalTask extends AsyncTask<String, Void, Boolean> {
        @Override
        protected Boolean doInBackground(String... paths) {
            if (paths.length == 0) return false;
            return raspberryPiApi.uploadMurattal(paths[0]);
        }

        @Override
        protected void onPostExecute(Boolean success) {
            if (success) {
                Toast.makeText(MurattalPlayerActivity.this, "Murattal uploaded successfully", Toast.LENGTH_SHORT).show();
                loadMurattalFiles(); // Refresh list
            } else {
                Toast.makeText(MurattalPlayerActivity.this, "Failed to upload Murattal", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private class StopAudioTask extends AsyncTask<Void, Void, Boolean> {
        @Override
        protected Boolean doInBackground(Void... voids) {
            return raspberryPiApi.stopAudio();
        }

        @Override
        protected void onPostExecute(Boolean success) {
            if (success) {
                Toast.makeText(MurattalPlayerActivity.this, "Audio stopped", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(MurattalPlayerActivity.this, "Failed to stop audio", Toast.LENGTH_SHORT).show();
            }
        }
    }

    // Helper class for file path resolution from Uri
    // You would typically implement this in a separate file
    public static class FileUtils {
        public static String getPath(final MurattalPlayerActivity context, final Uri uri) {
            if (uri == null) return null;
            
            // Try to get the file path directly
            try {
                String path = uri.getPath();
                if (path != null) {
                    return path;
                }
            } catch (Exception e) {
                Log.e(TAG, "Error getting file path: " + e.getMessage());
            }
            
            // If that fails, try to get the real path
            try {
                InputStream inputStream = context.getContentResolver().openInputStream(uri);
                byte[] buffer = new byte[inputStream.available()];
                inputStream.read(buffer);
                inputStream.close();
                
                // Create a temporary file
                java.io.File tempFile = java.io.File.createTempFile("murattal", ".mp3", context.getCacheDir());
                java.io.FileOutputStream fos = new java.io.FileOutputStream(tempFile);
                fos.write(buffer);
                fos.close();
                
                return tempFile.getAbsolutePath();
            } catch (Exception e) {
                Log.e(TAG, "Error creating temp file: " + e.getMessage());
                return null;
            }
        }
    }
}
