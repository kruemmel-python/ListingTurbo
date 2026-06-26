package de.listingturbo.mobile;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.OutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

final class LocalSyncClient {
    static String postProject(String baseUrl, String pin, JSONObject payload) throws Exception {
        String cleanBase = baseUrl.trim();
        if (cleanBase.endsWith("/")) cleanBase = cleanBase.substring(0, cleanBase.length() - 1);
        URL url = new URL(cleanBase + "/api/v1/mobile-project");
        byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(30000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setRequestProperty("X-ListingTurbo-Pin", pin.trim());
        connection.setFixedLengthStreamingMode(body.length);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(body);
        }
        int status = connection.getResponseCode();
        BufferedReader reader = new BufferedReader(new InputStreamReader(
            status >= 200 && status < 300 ? connection.getInputStream() : connection.getErrorStream(),
            StandardCharsets.UTF_8
        ));
        StringBuilder response = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) response.append(line).append('\n');
        if (status < 200 || status >= 300) throw new IllegalStateException("HTTP " + status + ": " + response);
        return response.toString().trim();
    }
}
