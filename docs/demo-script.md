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

4. Visit a normal HTTPS page and open the popup. Confirm a low or moderate score.

5. Visit a local or test URL with suspicious terms such as `http://login-secure.example.test/account-update` if resolvable in a controlled environment, or inspect the backend directly with:

   ```bash
   curl -X POST http://localhost:8000/analyze ^
     -H "Content-Type: application/json" ^
     -d "{\"url\":\"http://login-secure.example.test/account-update\",\"dom_features\":{\"has_password_field\":true,\"num_forms\":1,\"external_form_action\":true,\"num_iframes\":0,\"external_links_ratio\":0.2,\"has_hidden_inputs\":true}}"
   ```

6. Explain the displayed reasons and privacy boundary.
