package de.listingturbo.mobile;

import android.content.ContentResolver;
import android.content.Context;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.database.Cursor;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

final class ListingProject {
    String category = "Sonstiges";
    String productType = "Artikel";
    String brand = "";
    String model = "";
    String size = "";
    String color = "";
    String storage = "";
    String condition = "Gut";
    String desiredPrice = "";
    String originalPrice = "";
    String accessories = "";
    String defects = "";
    String notes = "";
    String location = "";
    String shipping = "Abholung oder Versand";
    String household = "Keine Angabe";
    final List<Uri> imageUris = new ArrayList<>();

    JSONObject toSyncJson(Context context) throws Exception {
        JSONObject product = new JSONObject();
        product.put("category", valueOr(category, "Sonstiges"));
        product.put("product_type", valueOr(productType, "Artikel"));
        product.put("brand", brand.trim());
        product.put("model", model.trim());
        product.put("size", size.trim());
        product.put("color", color.trim());
        product.put("storage", storage.trim());
        product.put("condition", valueOr(condition, "Gut"));
        product.put("shipping", valueOr(shipping, "Abholung oder Versand"));
        product.put("household", valueOr(household, "Keine Angabe"));
        product.put("quantity", 1);
        putNumber(product, "desired_price", desiredPrice);
        putNumber(product, "original_price", originalPrice);
        product.put("accessories", accessories.trim());
        product.put("defects", defects.trim());
        product.put("notes", notes.trim());
        product.put("location_hint", location.trim());

        JSONArray images = new JSONArray();
        for (int index = 0; index < imageUris.size(); index++) {
            Uri uri = imageUris.get(index);
            byte[] data = readBytes(context.getContentResolver(), uri, 20 * 1024 * 1024);
            JSONObject image = new JSONObject();
            image.put("filename", displayName(context.getContentResolver(), uri, index + 1));
            image.put("mime_type", valueOr(context.getContentResolver().getType(uri), "image/jpeg"));
            image.put("base64", Base64.encodeToString(data, Base64.NO_WRAP));
            images.put(image);
        }

        JSONObject root = new JSONObject();
        root.put("schema_version", 2);
        root.put("source", "ListingTurboAndroid");
        root.put("device_name", android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL);
        root.put("created", Instant.now().toString());
        root.put("product", product);
        root.put("images", images);
        return root;
    }

    String previewText() {
        StringBuilder title = new StringBuilder();
        append(title, brand);
        append(title, model);
        append(title, productType);
        append(title, storage);
        append(title, color);
        String titleText = title.length() == 0 ? "Artikel verkaufen" : title.toString();
        return "Titelvorschau:\n" + titleText + "\n\n" +
            "Kurzbeschreibung:\n" +
            "Zum Verkauf steht " + titleText + ".\n" +
            "Zustand: " + valueOr(condition, "Gut") + "\n" +
            "Mängel/Hinweise: " + valueOr(defects, "keine besonderen Mängel angegeben") + "\n" +
            "Zubehör: " + valueOr(accessories, "siehe Fotos") + "\n" +
            "Ort: " + valueOr(location, "nach Absprache") + "\n" +
            "Fotos: " + imageUris.size();
    }

    private static void append(StringBuilder target, String value) {
        String clean = value == null ? "" : value.trim();
        if (clean.isEmpty()) return;
        if (target.length() > 0) target.append(' ');
        target.append(clean);
    }

    private static String valueOr(String value, String fallback) {
        if (value == null || value.trim().isEmpty()) return fallback;
        return value.trim();
    }

    private static void putNumber(JSONObject object, String key, String value) throws Exception {
        if (value == null || value.trim().isEmpty()) return;
        String normalized = value.trim().replace(',', '.');
        object.put(key, Double.parseDouble(normalized));
    }

    private static byte[] readBytes(ContentResolver resolver, Uri uri, int maxBytes) throws Exception {
        try (InputStream input = resolver.openInputStream(uri); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            if (input == null) throw new IllegalArgumentException("Bild konnte nicht gelesen werden: " + uri);
            byte[] buffer = new byte[64 * 1024];
            int total = 0;
            int read;
            while ((read = input.read(buffer)) >= 0) {
                total += read;
                if (total > maxBytes) throw new IllegalArgumentException("Bild ist größer als 20 MB: " + uri);
                output.write(buffer, 0, read);
            }
            return output.toByteArray();
        }
    }

    private static String displayName(ContentResolver resolver, Uri uri, int index) {
        String result = null;
        try (Cursor cursor = resolver.query(uri, null, null, null, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                int nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (nameIndex >= 0) result = cursor.getString(nameIndex);
            }
        } catch (Exception ignored) {
            result = null;
        }
        if (result == null || result.trim().isEmpty()) result = "android_photo_" + index + ".jpg";
        return result;
    }
}
