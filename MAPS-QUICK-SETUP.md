# 🗺️ Google Maps - Quick Setup Card

## 🔑 Get Your API Key (5 minutes)

1. **Visit**: https://console.cloud.google.com/apis/credentials
2. **Create Project** → Name: `HangarLink-MVP`
3. **Enable API**: Search "Maps JavaScript API" → Enable
4. **Create Key**: "+ CREATE CREDENTIALS" → API key
5. **Copy Key**: Looks like `AIzaSyD...`

## 🔒 Secure Your Key

1. Click on your API key
2. **HTTP referrers**:
   - Add: `http://localhost:5000/*`
   - Add: `http://127.0.0.1:5000/*`
3. **API restrictions**: Select "Maps JavaScript API"
4. **Save**

## 💳 Enable Billing (Required)

- Visit: https://console.cloud.google.com/billing
- Link billing account
- **Free**: $200/month credit (covers ~28,000 map loads)
- **Your usage**: ~1,000 loads/month = $0

## 📝 Add Key to Project

**File**: `d:\HangarLink-MVP-2025\templates\base.html`

**Find** (line ~73):
```html
<script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY_HERE&callback=initMap"
```

**Replace** `YOUR_API_KEY_HERE` with your actual key:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyD...&callback=initMap"
```

**Save** the file.

## 🚀 Restart & Test

```powershell
# Stop server (Ctrl+C)
cd d:\HangarLink-MVP-2025\code
python app.py
```

**Visit**: http://localhost:5000

**Scroll to**: "Explore Nearby Opportunities" section

**You should see**:
✅ Interactive Google Map  
✅ Blue marker at Hamilton (CYHM)  
✅ Premium dark mode styling  
✅ Clickable marker with info window  

## 🐛 Troubleshooting

**"Map Loading..." message?**
→ Check API key is correct in `base.html`

**"Can't load Google Maps correctly"?**
→ Enable billing in Google Cloud Console

**Map grayed out?**
→ Check API key restrictions allow `localhost:5000/*`

---

**Full Guide**: See `GOOGLE-MAPS-SETUP.md` for detailed instructions
