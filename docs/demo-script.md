# Demo Script

1. Start the backend:

   ```bash
   python -m uvicorn app.main:app --app-dir backend --reload
   ```

2. Build the extension:

   ```bash
   cd extension
   npm install
   npm run build
   ```

3. Load `extension/dist` in Chrome Developer mode.

4. Open PhishLens settings from the popup and confirm:

   - Backend URL: `http://localhost:8000`.
   - Timeout: `2500`.
   - Danger overlay: enabled.

5. Visit a normal HTTPS page and open the popup. Confirm a low or moderate score and the `Backend enriched` state when the API is running.

6. Stop the backend and reopen the popup. Confirm analysis still works and the UI shows `Backend unavailable`.

7. Start the backend again and inspect a suspicious case directly:

   ```bash
   curl -X POST http://localhost:8000/analyze ^
     -H "Content-Type: application/json" ^
     -d "{\"url\":\"http://login-secure.example.test/account-update\",\"dom_features\":{\"has_password_field\":true,\"num_forms\":1,\"external_form_action\":true,\"num_iframes\":0,\"external_links_ratio\":0.2,\"has_hidden_inputs\":true}}"
   ```

8. On a page whose final score is `dangerous`, confirm the dismissible warning overlay appears when enabled.

9. Use popup feedback:

   - `Mark as safe` for suspected false positives.
   - `Mark as phishing` for suspected false negatives.

10. Explain the displayed reasons, backend/local state, feedback flow, and privacy boundary.
