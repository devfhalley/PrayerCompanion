package com.prayeralarm.service;

import android.util.Log;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import java.net.URI;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

public class WebSocketService {

    private static final String TAG = "WebSocketService";
    private WebSocketClient webSocketClient;
    private String serverUrl;
    private OnConnectedListener onConnectedListener;
    private OnDisconnectedListener onDisconnectedListener;
    private OnErrorListener onErrorListener;
    private boolean isConnected = false;
    private int reconnectAttempts = 0;
    private static final int MAX_RECONNECT_ATTEMPTS = 5;
    private static final int RECONNECT_DELAY_MS = 3000; // 3 seconds
    private boolean useSecureConnection = false;

    public interface OnConnectedListener {
        void onConnected();
    }

    public interface OnDisconnectedListener {
        void onDisconnected();
    }

    public interface OnErrorListener {
        void onError(String message);
    }

    public WebSocketService(String serverUrl) {
        this.serverUrl = serverUrl;
        // Check if the URL starts with "wss:" for secure WebSocket
        this.useSecureConnection = serverUrl.toLowerCase().startsWith("wss:");
    }

    public void connect(OnConnectedListener onConnected, OnDisconnectedListener onDisconnected, OnErrorListener onError) {
        this.onConnectedListener = onConnected;
        this.onDisconnectedListener = onDisconnected;
        this.onErrorListener = onError;
        
        try {
            URI uri = URI.create(serverUrl);
            webSocketClient = new WebSocketClient(uri) {
                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    Log.i(TAG, "WebSocket connected");
                    isConnected = true;
                    reconnectAttempts = 0;
                    
                    if (onConnectedListener != null) {
                        onConnectedListener.onConnected();
                    }
                }

                @Override
                public void onMessage(String message) {
                    Log.d(TAG, "WebSocket message received: " + message);
                    // Process incoming messages if needed
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    Log.i(TAG, "WebSocket closed: " + reason);
                    isConnected = false;
                    
                    if (onDisconnectedListener != null) {
                        onDisconnectedListener.onDisconnected();
                    }
                    
                    // Attempt to reconnect
                    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                        reconnectAttempts++;
                        Log.i(TAG, "Attempting to reconnect... (" + reconnectAttempts + "/" + MAX_RECONNECT_ATTEMPTS + ")");
                        
                        try {
                            Thread.sleep(RECONNECT_DELAY_MS);
                            connect(onConnectedListener, onDisconnectedListener, onErrorListener);
                        } catch (InterruptedException e) {
                            Log.e(TAG, "Reconnect interrupted: " + e.getMessage());
                        }
                    }
                }

                @Override
                public void onError(Exception ex) {
                    Log.e(TAG, "WebSocket error: " + ex.getMessage());
                    
                    if (onErrorListener != null) {
                        onErrorListener.onError(ex.getMessage());
                    }
                }
            };
            
            // For secure connections (WSS), configure SSL socket factory to trust all certificates
            if (useSecureConnection) {
                SSLSocketFactory sslSocketFactory = createTrustAllSSLSocketFactory();
                if (sslSocketFactory != null) {
                    webSocketClient.setSocketFactory(sslSocketFactory);
                    Log.i(TAG, "Configured WebSocket with trust-all SSL socket factory");
                } else {
                    Log.e(TAG, "Failed to create SSL socket factory");
                }
            }
            
            webSocketClient.connect();
        } catch (Exception e) {
            Log.e(TAG, "Error creating WebSocket: " + e.getMessage());
            
            if (onErrorListener != null) {
                onErrorListener.onError("Failed to create WebSocket: " + e.getMessage());
            }
        }
    }

    public void send(String message) {
        if (webSocketClient != null && isConnected) {
            webSocketClient.send(message);
        } else {
            Log.e(TAG, "Cannot send message: WebSocket not connected");
            
            if (onErrorListener != null) {
                onErrorListener.onError("WebSocket not connected");
            }
        }
    }

    public void disconnect() {
        if (webSocketClient != null) {
            try {
                webSocketClient.close();
            } catch (Exception e) {
                Log.e(TAG, "Error closing WebSocket: " + e.getMessage());
            }
            
            webSocketClient = null;
        }
        
        isConnected = false;
    }

    public boolean isConnected() {
        return isConnected;
    }
    
    /**
     * Creates an SSL socket factory that trusts all certificates.
     * This is necessary for self-signed certificates used in development environments.
     * 
     * @return SSLSocketFactory that trusts all certificates
     */
    private SSLSocketFactory createTrustAllSSLSocketFactory() {
        try {
            // Create a trust manager that does not validate certificate chains
            TrustManager[] trustAllCerts = new TrustManager[] {
                new X509TrustManager() {
                    public X509Certificate[] getAcceptedIssuers() {
                        return new X509Certificate[0];
                    }
                    
                    public void checkClientTrusted(X509Certificate[] certs, String authType) {
                        // Trust all client certificates
                    }
                    
                    public void checkServerTrusted(X509Certificate[] certs, String authType) {
                        // Trust all server certificates
                    }
                }
            };
            
            // Install the all-trusting trust manager
            SSLContext sslContext = SSLContext.getInstance("TLS");
            sslContext.init(null, trustAllCerts, new SecureRandom());
            
            // Create an SSL socket factory with our all-trusting manager
            return sslContext.getSocketFactory();
        } catch (NoSuchAlgorithmException | KeyManagementException e) {
            Log.e(TAG, "Error creating SSL socket factory: " + e.getMessage());
            return null;
        }
    }
}
