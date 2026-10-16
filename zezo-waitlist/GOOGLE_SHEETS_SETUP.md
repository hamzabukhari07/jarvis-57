# 📊 100% Free Google Sheets Waitlist Backend Setup (2 Minutes)

This setup allows your **ZEZO Waitlist** to save every user signup directly into your own private Google Sheet with **$0 cost forever**, **no credit card required**, and **no server maintenance**.

---

## ⚡ Step 1: Create Your Google Sheet

1. Open [Google Sheets](https://sheets.new) in your browser.
2. Name the spreadsheet: **`ZEZO Waitlist Signups`**.
3. In row 1, set up the column headers:
   - **A1**: `Timestamp`
   - **B1**: `Email`
   - **C1**: `Referrer`
   - **D1**: `User Agent`

---

## ⚡ Step 2: Add the Google Apps Script

1. In your Google Sheet menu bar, click:  
   **Extensions** ➔ **Apps Script**
2. Delete any default code in the editor, and paste the following script:

```javascript
function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.tryLock(10000);

  try {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = doc.getActiveSheet();

    // Parse incoming payload
    var data;
    try {
      data = JSON.parse(e.postData.contents);
    } catch (err) {
      data = e.parameter;
    }

    var email = (data.email || "").toString().trim().toLowerCase();
    var timestamp = data.timestamp || new Date().toISOString();
    var referrer = data.referrer || "direct";

    if (!email) {
      return ContentService
        .createTextOutput(JSON.stringify({ status: "error", message: "No email provided" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Optional: Avoid duplicate entries in Column B
    var existingEmails = sheet.getRange(2, 2, Math.max(sheet.getLastRow() - 1, 1), 1).getValues().flat();
    if (existingEmails.indexOf(email) === -1) {
      // Append new row
      sheet.appendRow([timestamp, email, referrer]);
    }

    return ContentService
      .createTextOutput(JSON.stringify({ status: "success", message: "Added to waitlist" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", error: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}
```

3. Click the **Save** icon (disk icon or `Ctrl+S`).

---

## ⚡ Step 3: Deploy as Web App

1. Click the blue **Deploy** button (top right) ➔ select **New deployment**.
2. Click the gear icon ⚙️ next to *Select type* ➔ choose **Web app**.
3. Fill in the settings:
   - **Description**: `ZEZO Waitlist API`
   - **Execute as**: `Me (your_email@gmail.com)`
   - **Who has access**: **`Anyone`**  *(Crucial: allows the website to send signups without login)*
4. Click **Deploy**.
5. Google may prompt: *"Authorization Required"* ➔ Click **Authorize Access** ➔ choose your Google account ➔ click **Advanced** ➔ click **Go to Untitled project (unsafe)** ➔ click **Allow**.
6. Copy the **Web App URL** generated. It will look like:  
   `https://script.google.com/macros/s/AKfycbx.../exec`

---

## ⚡ Step 4: Paste into Your Website Config

Open `zezo-waitlist/src/config.ts` and paste your URL:

```typescript
export const CONFIG = {
  GOOGLE_SCRIPT_URL: "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec",
  INITIAL_WAITLIST_COUNT: 284,
  CREATOR_NAME: "Hamza Bukhari",
  // ...
};
```

That's it! Every time someone enters their email on the site, it will instantly appear in your Google Sheet in real time.

---

## 🚀 Free Hosting Deployment (Vercel / Cloudflare Pages)

### Option A: Free Vercel (1 Click)
1. Push this folder to a GitHub repository.
2. Go to [vercel.com](https://vercel.com) (free hobby tier).
3. Click **Add New Project** ➔ Import repository.
4. Set root directory to `zezo-waitlist` (if in monorepo) or repository root.
5. Click **Deploy**. Done!

### Option B: Cloudflare Pages (Free Unlimited Bandwidth)
1. In Cloudflare Dashboard ➔ **Workers & Pages** ➔ **Create Application** ➔ **Pages**.
2. Connect GitHub repo ➔ Build command: `npm run build` ➔ Output directory: `dist`.
3. Click **Save and Deploy**.

