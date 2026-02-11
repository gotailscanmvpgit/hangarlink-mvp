# 🗺️ Google Maps API Integration Guide

## ✅ Integration Complete!

Google Maps has been successfully integrated into HangarLink with premium dark mode styling.

---

## 📋 What Was Added

### **1. Google Maps JavaScript API Script**
- Added to `base.html` in the `<head>` section
- Includes callback function for initialization
- Premium dark mode styling for maps

### **2. Map Features**
✅ **Interactive Google Map** on homepage  
✅ **Premium dark mode styling** (navy/platinum theme)  
✅ **Test marker** at Hamilton (CYHM)  
✅ **Info windows** with clickable markers  
✅ **Responsive design** with rounded corners  
✅ **Fallback message** if API fails to load  
✅ **Map legend** showing marker types  
✅ **Quick stats** below map  

### **3. Map Location**
The map appears on the homepage in a new section:
- **Section**: "Explore Nearby Opportunities"
- **Position**: Between "Why Pilots Choose HangarLink" and final CTA
- **Height**: 500px
- **Styling**: Premium card with shadow and border

---

## 🔑 Setup Instructions - GET YOUR API KEY

### **Step 1: Get Google Maps API Key**

1. **Visit Google Cloud Console:**
   ```
   https://console.cloud.google.com/apis/credentials
   ```

2. **Create a New Project** (if you don't have one):
   - Click "Select a project" → "New Project"
   - Name: `HangarLink-MVP`
   - Click "Create"

3. **Enable Maps JavaScript API:**
   - Go to: https://console.cloud.google.com/apis/library
   - Search for "Maps JavaScript API"
   - Click on it
   - Click "Enable"

4. **Create API Key:**
   - Go to: https://console.cloud.google.com/apis/credentials
   - Click "+ CREATE CREDENTIALS" → "API key"
   - Your API key will be generated (looks like: `AIzaSyD...`)
   - **Copy this key!**

5. **Restrict Your API Key** (Important for security):
   - Click on your newly created API key
   - Under "Application restrictions":
     - Select "HTTP referrers (web sites)"
     - Click "+ ADD AN ITEM"
     - Add these referrers:
       ```
       http://localhost:5000/*
       http://127.0.0.1:5000/*
       ```
   - Under "API restrictions":
     - Select "Restrict key"
     - Check "Maps JavaScript API"
   - Click "Save"

6. **Enable Billing** (Required even for free tier):
   - Go to: https://console.cloud.google.com/billing
   - Link a billing account
   - **Note**: Google provides $200/month free credit
   - You won't be charged unless you exceed the free tier

---

### **Step 2: Add API Key to Your Project**

1. **Open the file:**
   ```
   d:\HangarLink-MVP-2025\templates\base.html
   ```

2. **Find this line** (around line 73):
   ```html
   <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY_HERE&callback=initMap" async defer></script>
   ```

3. **Replace `YOUR_API_KEY_HERE` with your actual API key:**
   ```html
   <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyD...YOUR_ACTUAL_KEY...&callback=initMap" async defer></script>
   ```

4. **Save the file**

---

### **Step 3: Restart the Server**

```powershell
# Stop the current server (Ctrl+C in terminal)
# Then restart:
cd d:\HangarLink-MVP-2025\code
python app.py
```

---

### **Step 4: Test the Map**

1. **Visit:** `http://localhost:5000`
2. **Scroll down** to the "Explore Nearby Opportunities" section
3. **You should see:**
   - ✅ Interactive Google Map centered on Toronto (CYTZ)
   - ✅ Blue marker at Hamilton (CYHM)
   - ✅ Premium dark mode styling (if dark mode is on)
   - ✅ Map legend below the map
   - ✅ Quick stats (50+ listings, 25+ airports, 100% verified)

4. **Test interactions:**
   - Click on the blue marker → Info window appears
   - Zoom in/out using mouse wheel
   - Pan the map by dragging
   - Toggle dark mode → Map styling changes

---

## 🎨 Premium Features

### **Dark Mode Styling**
The map automatically adapts to your theme:
- **Dark Mode**: Navy/platinum color scheme matching HangarLink
- **Light Mode**: Standard Google Maps colors
- **Smooth transitions** when toggling themes

### **Custom Markers**
- **Blue circle markers** for parking locations
- **White stroke** for visibility
- **Clickable** with info windows
- **Custom icons** (can be updated later)

### **Map Controls**
- ✅ Zoom controls
- ✅ Map type selector (Map/Satellite)
- ✅ Fullscreen button
- ❌ Street View (disabled for cleaner UI)

---

## 🔧 Troubleshooting

### **Issue: Map shows "Map Loading..." message**

**Causes:**
1. API key not added or incorrect
2. Maps JavaScript API not enabled
3. Billing not set up
4. API key restrictions too strict

**Solutions:**
1. Double-check your API key in `base.html`
2. Verify Maps JavaScript API is enabled in Google Cloud Console
3. Ensure billing is enabled (even for free tier)
4. Check API key restrictions allow `localhost:5000`

---

### **Issue: "This page can't load Google Maps correctly"**

**Cause:** Billing not enabled

**Solution:**
1. Go to: https://console.cloud.google.com/billing
2. Enable billing (you won't be charged within free tier)
3. Wait 5 minutes for changes to propagate
4. Refresh the page

---

### **Issue: Map appears but is grayed out**

**Cause:** API key restrictions

**Solution:**
1. Go to your API key settings
2. Under "Application restrictions" → "HTTP referrers"
3. Make sure you have:
   - `http://localhost:5000/*`
   - `http://127.0.0.1:5000/*`
4. Save and wait 5 minutes

---

## 📊 Current Map Configuration

### **Default Center**
- **Location**: Toronto (CYTZ / Billy Bishop Airport)
- **Coordinates**: 43.6275°N, 79.3962°W
- **Zoom Level**: 11

### **Test Marker**
- **Location**: Hamilton (CYHM)
- **Coordinates**: 43.1605°N, 79.9349°W
- **Title**: "Test Hangar Location - CYHM"
- **Color**: Blue (#3B82F6)

---

## 🚀 Future Enhancements

### **Phase 1: Dynamic Markers**
Add markers from actual listings in the database:
```javascript
// In initMap() function
listings.forEach(listing => {
    new google.maps.Marker({
        position: { lat: listing.lat, lng: listing.lng },
        map: map,
        title: listing.airport_icao
    });
});
```

### **Phase 2: Clustering**
Group nearby markers for better performance:
- Use MarkerClusterer library
- Show count badges for clusters
- Expand on zoom

### **Phase 3: Search Integration**
- Click marker → Show listing details
- Filter map by search criteria
- Draw radius circle around search location

### **Phase 4: Real-time Updates**
- Update markers when new listings are posted
- Show "New" badge on recent listings
- Highlight featured listings

---

## 📝 Code Locations

### **Map Initialization**
- **File**: `d:\HangarLink-MVP-2025\templates\base.html`
- **Lines**: ~73-220
- **Function**: `initMap()`

### **Map Container**
- **File**: `d:\HangarLink-MVP-2025\templates\index.html`
- **Lines**: ~275-325
- **Element**: `<div id="map">`

### **Map Styling**
- **File**: `d:\HangarLink-MVP-2025\templates\base.html`
- **Lines**: ~66-69
- **CSS**: `#map` styles

---

## ✅ Success Checklist

After setup, you should have:

- [x] Google Maps API key obtained
- [x] API key added to `base.html`
- [x] Maps JavaScript API enabled
- [x] Billing enabled in Google Cloud
- [x] API key restrictions configured
- [x] Server restarted
- [x] Map visible on homepage
- [x] Test marker clickable
- [x] Dark mode styling working
- [x] Map legend displayed

---

## 💰 Pricing Information

### **Google Maps Free Tier**
- **Monthly Credit**: $200 USD
- **Map Loads**: ~28,000 per month (free)
- **Typical Usage**: Well within free tier for MVP

### **What Counts as Usage**
- Each page load with map = 1 map load
- Marker clicks = Free
- Info windows = Free
- Pan/zoom = Free

### **Cost Estimate**
For an MVP with ~1,000 visitors/month:
- **Cost**: $0 (within free tier)
- **Map loads**: ~1,000
- **Free tier covers**: 28,000 loads

---

**Your Google Maps integration is ready!** 🗺️✨

**Next Step**: Add your API key and test the map!
