package de.listingturbo.mobile;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

public final class MainActivity extends Activity {
    private static final int REQ_PICK_IMAGES = 1001;
    private static final int REQ_CAMERA = 1002;

    private final ListingProject project = new ListingProject();
    private EditText desktopUrl;
    private EditText pin;
    private EditText category;
    private EditText productType;
    private EditText brand;
    private EditText model;
    private EditText storage;
    private EditText color;
    private EditText condition;
    private EditText desiredPrice;
    private EditText originalPrice;
    private EditText accessories;
    private EditText defects;
    private EditText notes;
    private EditText location;
    private TextView status;
    private TextView preview;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildUi());
    }

    private int dp(float value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private GradientDrawable roundedDrawable(int bgColor, int cornerRadiusDp, int strokeColor, int strokeWidthDp) {
        GradientDrawable gd = new GradientDrawable();
        gd.setColor(bgColor);
        gd.setCornerRadius(dp(cornerRadiusDp));
        if (strokeWidthDp > 0) {
            gd.setStroke(dp(strokeWidthDp), strokeColor);
        }
        return gd;
    }

    private LinearLayout createCard(LinearLayout parent, String titleText) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(16), dp(16), dp(16));
        card.setBackground(roundedDrawable(0xFF1E293B, 12, 0xFF334155, 1)); // Slate-blue card with border
        
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, dp(16));
        card.setLayoutParams(params);
        
        if (titleText != null && !titleText.isEmpty()) {
            TextView header = new TextView(this);
            header.setText(titleText.toUpperCase());
            header.setTextSize(12);
            header.setTextColor(0xFF3B82F6); // Accent blue
            header.setTypeface(Typeface.create("sans-serif-medium", Typeface.BOLD));
            header.setPadding(0, 0, 0, dp(12));
            card.addView(header);
        }
        
        parent.addView(card);
        return card;
    }

    private EditText input(LinearLayout card, String label, String initial) {
        return input(card, label, initial, "");
    }

    private EditText input(LinearLayout card, String label, String initial, String hint) {
        TextView text = new TextView(this);
        text.setText(label);
        text.setTextSize(13);
        text.setTextColor(0xFF9CA3AF); // slate gray label
        text.setPadding(0, dp(4), 0, dp(4));
        card.addView(text);
        
        EditText edit = new EditText(this);
        edit.setSingleLine(false);
        edit.setMinLines(1);
        edit.setText(initial);
        edit.setHint(hint);
        edit.setTextColor(0xFFFFFFFF);
        edit.setTextSize(15);
        edit.setHintTextColor(0xFF4B5563);
        edit.setBackground(roundedDrawable(0xFF0B0F19, 8, 0xFF334155, 1)); // Dark input field background
        edit.setPadding(dp(12), dp(10), dp(12), dp(10));
        
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, dp(12));
        edit.setLayoutParams(params);
        
        card.addView(edit);
        return edit;
    }

    private Button styledButton(String text, int bgColor, int textColor) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextColor(textColor);
        button.setTextSize(13);
        button.setTypeface(Typeface.create("sans-serif-medium", Typeface.BOLD));
        button.setAllCaps(true);
        button.setBackground(roundedDrawable(bgColor, 8, 0, 0));
        button.setPadding(dp(16), dp(12), dp(16), dp(12));
        return button;
    }

    private LinearLayout.LayoutParams weightParams(float weight, int rightMarginDp) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                weight
        );
        params.setMargins(0, 0, dp(rightMarginDp), 0);
        return params;
    }

    private void setFullWidthParams(View view, int topMarginDp, int bottomMarginDp) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, dp(topMarginDp), 0, dp(bottomMarginDp));
        view.setLayoutParams(params);
    }

    private View buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(0xFF0F172A); // Dark Slate background
        
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(20), dp(16), dp(20));
        scroll.addView(root);

        // Header Card
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setPadding(dp(20), dp(20), dp(20), dp(20));
        GradientDrawable headerBg = new GradientDrawable(
            GradientDrawable.Orientation.TL_BR,
            new int[] { 0xFF1E1B4B, 0xFF0F172A } // Indigo to dark slate gradient
        );
        headerBg.setCornerRadius(dp(16));
        headerBg.setStroke(dp(1), 0xFF312E81);
        header.setBackground(headerBg);
        
        LinearLayout.LayoutParams headerParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        );
        headerParams.setMargins(0, 0, 0, dp(16));
        header.setLayoutParams(headerParams);
        
        TextView title = new TextView(this);
        title.setText("ListingTurbo");
        title.setTextSize(24);
        title.setTextColor(0xFFFFFFFF);
        title.setTypeface(Typeface.create("sans-serif-condensed", Typeface.BOLD));
        header.addView(title);
        
        TextView badge = new TextView(this);
        badge.setText("ENTERPRISE MOBILE");
        badge.setTextSize(10);
        badge.setTextColor(0xFF60A5FA); // Sky blue accent
        badge.setPadding(0, dp(2), 0, dp(8));
        badge.setTypeface(Typeface.create("sans-serif", Typeface.BOLD));
        header.addView(badge);
        
        TextView subtitle = new TextView(this);
        subtitle.setText("Lokale Erfassung von Artikeldaten & Fotos. Senden an den Desktop-Sync-Server.");
        subtitle.setTextColor(0xFF9CA3AF);
        subtitle.setTextSize(13);
        header.addView(subtitle);
        
        root.addView(header);

        // Cards for Inputs
        LinearLayout cardVerbindung = createCard(root, "Verbindung & Server");
        TextView lanWarning = new TextView(this);
        lanWarning.setText("Nur im vertrauenswürdigen lokalen WLAN nutzen. Die PIN ist kurzlebig und steht im Desktop-Lizenz-Tab.");
        lanWarning.setTextColor(0xFFF59E0B);
        lanWarning.setTextSize(13);
        lanWarning.setPadding(0, 0, 0, dp(12));
        cardVerbindung.addView(lanWarning);
        desktopUrl = input(cardVerbindung, "Desktop-URL", "", "http://192.168.x.x:53317");
        pin = input(cardVerbindung, "Transfer-PIN", "", "6-stellige PIN aus der Desktop-App");

        LinearLayout cardKlassifizierung = createCard(root, "Kategorie & Typ");
        category = input(cardKlassifizierung, "Kategorie", "Elektronik");
        productType = input(cardKlassifizierung, "Artikeltyp", "Smartphone");

        LinearLayout cardDetails = createCard(root, "Produkt-Details");
        brand = input(cardDetails, "Marke", "Samsung");
        model = input(cardDetails, "Modell / Variante", "Galaxy S22");
        storage = input(cardDetails, "Speicher / Größe", "128 GB");
        color = input(cardDetails, "Farbe", "Schwarz");

        LinearLayout cardZustand = createCard(root, "Zustand & Preise");
        condition = input(cardZustand, "Zustand", "Gut");
        desiredPrice = input(cardZustand, "Wunschpreis €", "");
        originalPrice = input(cardZustand, "Neupreis €", "");
        location = input(cardZustand, "Ort / Abholung", "");

        LinearLayout cardBeschreibungen = createCard(root, "Beschreibungen & Mängel");
        accessories = input(cardBeschreibungen, "Zubehör / Lieferumfang", "");
        defects = input(cardBeschreibungen, "Mängel / Hinweise", "");
        notes = input(cardBeschreibungen, "Zusatzinfo", "");

        // Media Card
        LinearLayout mediaCard = createCard(root, "Medien erfassen");
        status = new TextView(this);
        status.setText("Bereit. Fotos: 0");
        status.setTextColor(0xFFF59E0B); // Amber warning indicator
        status.setTextSize(14);
        status.setTypeface(Typeface.create("sans-serif-medium", Typeface.BOLD));
        status.setPadding(0, 0, 0, dp(12));
        mediaCard.addView(status);
        
        LinearLayout mediaRow = new LinearLayout(this);
        mediaRow.setOrientation(LinearLayout.HORIZONTAL);
        Button pick = styledButton("Fotos auswählen", 0xFF2563EB, 0xFFFFFFFF); // Royal blue
        pick.setOnClickListener(v -> pickImages());
        mediaRow.addView(pick, weightParams(1.0f, 8));
        Button camera = styledButton("Kamera", 0xFF4F46E5, 0xFFFFFFFF); // Indigo
        camera.setOnClickListener(v -> captureThumbnail());
        mediaRow.addView(camera, weightParams(1.0f, 0));
        mediaCard.addView(mediaRow);

        // Preview Card
        LinearLayout previewCard = createCard(root, "Vorschau & Zusammenfassung");
        preview = new TextView(this);
        preview.setText(project.previewText());
        preview.setTextIsSelectable(true);
        preview.setTextColor(0xFFE2E8F0);
        preview.setTextSize(13);
        preview.setTypeface(Typeface.create("monospace", Typeface.NORMAL));
        preview.setPadding(dp(12), dp(12), dp(12), dp(12));
        preview.setBackground(roundedDrawable(0xFF0B0F19, 8, 0xFF334155, 1));
        previewCard.addView(preview);

        // Actions Card
        LinearLayout actionsCard = createCard(root, "Server-Synchronisation");
        LinearLayout actionRow = new LinearLayout(this);
        actionRow.setOrientation(LinearLayout.HORIZONTAL);
        Button makePreview = styledButton("Vorschau", 0xFF4B5563, 0xFFFFFFFF);
        makePreview.setOnClickListener(v -> updateProjectFromFormAndPreview());
        actionRow.addView(makePreview, weightParams(1.0f, 8));
        Button saveJson = styledButton("JSON speichern", 0xFF4B5563, 0xFFFFFFFF);
        saveJson.setOnClickListener(v -> saveJsonToAppFolder());
        actionRow.addView(saveJson, weightParams(1.0f, 0));
        actionsCard.addView(actionRow);
        
        Button send = styledButton("An Desktop senden", 0xFF10B981, 0xFFFFFFFF); // Emerald green
        send.setOnClickListener(v -> sendToDesktop());
        setFullWidthParams(send, 12, 0);
        actionsCard.addView(send);

        return scroll;
    }

    private void pickImages() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.setType("image/*");
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(intent, REQ_PICK_IMAGES);
    }

    private void captureThumbnail() {
        Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        try {
            startActivityForResult(intent, REQ_CAMERA);
        } catch (Exception e) {
            toast("Keine Kamera-App gefunden: " + e.getMessage());
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null) return;
        if (requestCode == REQ_PICK_IMAGES) {
            if (data.getClipData() != null) {
                for (int i = 0; i < data.getClipData().getItemCount(); i++) addImageUri(data.getClipData().getItemAt(i).getUri(), data);
            } else if (data.getData() != null) {
                addImageUri(data.getData(), data);
            }
        } else if (requestCode == REQ_CAMERA) {
            Object bitmap = data.getExtras() == null ? null : data.getExtras().get("data");
            if (bitmap instanceof Bitmap) saveCameraBitmap((Bitmap) bitmap);
        }
        status.setText("Fotos: " + project.imageUris.size());
        updateProjectFromFormAndPreview();
    }

    private void addImageUri(Uri uri, Intent sourceIntent) {
        try {
            int flags = sourceIntent.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION;
            getContentResolver().takePersistableUriPermission(uri, flags);
        } catch (Exception ignored) {
            // Einige Provider erlauben keine persistente Berechtigung; für die laufende Session reicht die temporäre Grant-Berechtigung.
        }
        project.imageUris.add(uri);
    }

    private void saveCameraBitmap(Bitmap bitmap) {
        try {
            File dir = new File(getExternalFilesDir(null), "camera");
            if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Kameraordner konnte nicht erstellt werden.");
            File file = new File(dir, "camera_" + System.currentTimeMillis() + ".jpg");
            try (FileOutputStream output = new FileOutputStream(file)) {
                bitmap.compress(Bitmap.CompressFormat.JPEG, 92, output);
            }
            project.imageUris.add(Uri.fromFile(file));
        } catch (Exception exc) {
            toast("Kamerabild konnte nicht gespeichert werden: " + exc.getMessage());
        }
    }

    private void updateProjectFromFormAndPreview() {
        updateProjectFromForm();
        preview.setText(project.previewText());
        status.setText("Vorschau aktualisiert. Fotos: " + project.imageUris.size());
    }

    private void updateProjectFromForm() {
        project.category = text(category);
        project.productType = text(productType);
        project.brand = text(brand);
        project.model = text(model);
        project.storage = text(storage);
        project.color = text(color);
        project.condition = text(condition);
        project.desiredPrice = text(desiredPrice);
        project.originalPrice = text(originalPrice);
        project.accessories = text(accessories);
        project.defects = text(defects);
        project.notes = text(notes);
        project.location = text(location);
    }

    private String text(EditText editText) {
        return editText.getText().toString().trim();
    }

    private void sendToDesktop() {
        updateProjectFromForm();
        if (text(desktopUrl).isEmpty() || text(pin).isEmpty()) {
            status.setText("Desktop-URL und Transfer-PIN eintragen.");
            toast("Desktop-URL und Transfer-PIN eintragen.");
            return;
        }
        status.setText("Sende an Desktop ...");
        new Thread(() -> {
            try {
                JSONObject payload = project.toSyncJson(this);
                String response = LocalSyncClient.postProject(text(desktopUrl), text(pin), payload);
                runOnUiThread(() -> {
                    status.setText("Desktop-Sync erfolgreich: " + response);
                    toast("Sync erfolgreich.");
                });
            } catch (Exception exc) {
                runOnUiThread(() -> {
                    status.setText("Sync fehlgeschlagen: " + exc.getMessage());
                    toast("Sync fehlgeschlagen.");
                });
            }
        }, "ListingTurboSync").start();
    }

    private void saveJsonToAppFolder() {
        updateProjectFromForm();
        try {
            File dir = new File(getExternalFilesDir(null), "exports");
            if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Exportordner konnte nicht erstellt werden.");
            File file = new File(dir, "listingturbo_mobile_" + System.currentTimeMillis() + ".json");
            byte[] data = project.toSyncJson(this).toString(2).getBytes(StandardCharsets.UTF_8);
            try (FileOutputStream output = new FileOutputStream(file)) {
                output.write(data);
            }
            status.setText("JSON gespeichert: " + file.getAbsolutePath());
            toast("JSON gespeichert.");
        } catch (Exception exc) {
            status.setText("JSON-Export fehlgeschlagen: " + exc.getMessage());
            toast("JSON-Export fehlgeschlagen.");
        }
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
}
