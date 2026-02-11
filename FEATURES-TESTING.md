# 🚀 Quick Setup & Test Guide

## Step 1: Install WeasyPrint

```powershell
pip install WeasyPrint==60.1
```

**If you get errors on Windows:**
1. WeasyPrint requires GTK+ libraries
2. Download from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
3. Install GTK+
4. Restart terminal
5. Try `pip install WeasyPrint` again

**Alternative (if WeasyPrint fails)**:
```powershell
pip install reportlab
```
Then modify the PDF generation route to use reportlab instead.

---

## Step 2: Recreate Database

The new features require additional database fields. Run this:

```powershell
cd d:\HangarLink-MVP-2025\code
python
```

```python
from app import app, db
with app.app_context():
    # WARNING: This deletes all existing data!
    db.drop_all()
    db.create_all()
    print("✅ Database recreated with new fields!")
exit()
```

---

## Step 3: Restart Server

```powershell
python app.py
```

---

## Step 4: Test Features

### **Test 1: Profile & Smart Alerts** ⏰

1. Register as `renter@test.com`
2. Visit: `http://localhost:5000/profile`
3. Enable "Smart Alerts"
4. Set:
   - Airport: `KJFK`
   - Max Price: `1000`
   - Min Size: `2000`
   - Covered Only: ✓
5. Click "Save Alert Preferences"
6. You should see: "Alert preferences saved!"

7. Logout, register as `owner@test.com`
8. Post a listing:
   - Airport: `KJFK`
   - Size: `2500`
   - Covered: ✓
   - Price: `850`
9. Submit listing
10. Check terminal console → Should see:
    ```
    ✨ ALERT: User renter@test.com matches listing 1 at KJFK
    ```

**✅ Success!** The alert system is working!

---

### **Test 2: Price Intelligence** 💰

1. Create 2-3 listings at KJFK:
   - Listing 1: $800/mo
   - Listing 2: $900/mo
   - Listing 3: $1000/mo

2. Visit: `http://localhost:5000/post-listing?airport=KJFK`

3. **Add this code to `post_listing.html`** (after the airport field, around line 30):

```html
{% if price_intel %}
<div class="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-700 rounded-xl p-6 mb-6 animate-fade-in">
    <div class="flex items-start">
        <div class="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mr-4 flex-shrink-0">
            <i class="fas fa-chart-line text-white text-xl"></i>
        </div>
        <div class="flex-1">
            <h4 class="text-lg font-bold text-gray-900 dark:text-platinum-100 mb-2">
                💡 Price Intelligence
            </h4>
            <p class="text-gray-700 dark:text-platinum-200 mb-2">
                Similar spaces at <strong class="text-blue-600">{{ airport }}</strong> rent for:
            </p>
            <div class="flex items-center gap-4 mb-2">
                <div class="bg-white dark:bg-dark-900 rounded-lg px-4 py-2 border border-blue-200 dark:border-blue-700">
                    <div class="text-xs text-gray-500 dark:text-platinum-400">Low</div>
                    <div class="text-xl font-bold text-blue-600">${{ price_intel.min|int }}</div>
                </div>
                <div class="text-gray-400">→</div>
                <div class="bg-white dark:bg-dark-900 rounded-lg px-4 py-2 border border-blue-200 dark:border-blue-700">
                    <div class="text-xs text-gray-500 dark:text-platinum-400">Average</div>
                    <div class="text-xl font-bold text-green-600">${{ price_intel.avg|int }}</div>
                </div>
                <div class="text-gray-400">→</div>
                <div class="bg-white dark:bg-dark-900 rounded-lg px-4 py-2 border border-blue-200 dark:border-blue-700">
                    <div class="text-xs text-gray-500 dark:text-platinum-400">High</div>
                    <div class="text-xl font-bold text-purple-600">${{ price_intel.max|int }}</div>
                </div>
            </div>
            <p class="text-sm text-gray-600 dark:text-platinum-300">
                Based on {{ price_intel.count }} active listing{{ 's' if price_intel.count != 1 else '' }}
            </p>
        </div>
    </div>
</div>
{% endif %}
```

4. Refresh page → See price intelligence box!

**✅ Success!** Price intelligence is showing!

---

### **Test 3: Photo Gallery** 📸

1. Post a listing with 3-4 photos
2. View the listing detail page
3. **Add this code to `listing_detail.html`** (replace the single photo section):

```html
{% if listing.photos %}
    {% set photo_list = listing.photos.split(',') %}
    
    <!-- Photo Gallery -->
    <div class="mb-8">
        <!-- Main Photo -->
        <div class="mb-4">
            <img id="main-photo" 
                 src="{{ url_for('static', filename='uploads/listings/' + photo_list[0]) }}" 
                 alt="Main photo" 
                 class="w-full h-96 object-cover rounded-2xl shadow-2xl cursor-pointer transition-transform hover:scale-[1.02]"
                 onclick="openLightbox(0)">
        </div>
        
        <!-- Thumbnail Gallery -->
        {% if photo_list|length > 1 %}
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            {% for photo in photo_list %}
            <img src="{{ url_for('static', filename='uploads/listings/' + photo) }}" 
                 alt="Photo {{ loop.index }}" 
                 class="w-full h-24 object-cover rounded-xl shadow-lg cursor-pointer hover:opacity-75 hover:scale-105 transition-all border-2 border-transparent hover:border-blue-500"
                 onclick="changeMainPhoto('{{ photo }}'); openLightbox({{ loop.index0 }})">
            {% endfor %}
        </div>
        {% endif %}
    </div>
    
    <!-- Lightbox -->
    <div id="lightbox" class="fixed inset-0 bg-black/95 z-50 hidden items-center justify-center p-4" onclick="closeLightbox()">
        <button class="absolute top-4 right-4 text-white text-5xl hover:text-blue-400 transition-colors" onclick="closeLightbox()">&times;</button>
        <button class="absolute left-4 top-1/2 -translate-y-1/2 text-white text-4xl hover:text-blue-400 transition-colors" onclick="event.stopPropagation(); prevPhoto()">‹</button>
        <button class="absolute right-4 top-1/2 -translate-y-1/2 text-white text-4xl hover:text-blue-400 transition-colors" onclick="event.stopPropagation(); nextPhoto()">›</button>
        <img id="lightbox-img" src="" class="max-w-5xl max-h-screen rounded-xl shadow-2xl">
    </div>
    
    <script>
        const photos = {{ photo_list|tojson }};
        let currentPhotoIndex = 0;
        
        function changeMainPhoto(photoFilename) {
            document.getElementById('main-photo').src = `/static/uploads/listings/${photoFilename}`;
        }
        
        function openLightbox(index) {
            currentPhotoIndex = index;
            document.getElementById('lightbox').classList.remove('hidden');
            document.getElementById('lightbox').classList.add('flex');
            document.getElementById('lightbox-img').src = `/static/uploads/listings/${photos[index]}`;
        }
        
        function closeLightbox() {
            document.getElementById('lightbox').classList.add('hidden');
            document.getElementById('lightbox').classList.remove('flex');
        }
        
        function nextPhoto() {
            currentPhotoIndex = (currentPhotoIndex + 1) % photos.length;
            document.getElementById('lightbox-img').src = `/static/uploads/listings/${photos[currentPhotoIndex]}`;
        }
        
        function prevPhoto() {
            currentPhotoIndex = (currentPhotoIndex - 1 + photos.length) % photos.length;
            document.getElementById('lightbox-img').src = `/static/uploads/listings/${photos[currentPhotoIndex]}`;
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!document.getElementById('lightbox').classList.contains('hidden')) {
                if (e.key === 'ArrowRight') nextPhoto();
                if (e.key === 'ArrowLeft') prevPhoto();
                if (e.key === 'Escape') closeLightbox();
            }
        });
    </script>
{% endif %}
```

4. Refresh → See photo gallery with lightbox!
5. Click thumbnails → Main photo changes
6. Click main photo → Lightbox opens
7. Use arrow keys or buttons to navigate

**✅ Success!** Photo gallery is working!

---

### **Test 4: Rental Agreement PDF** 📄

1. User A (renter) messages User B (owner) about a listing
2. **Add this code to `message_user.html`** (after the chat header, before messages):

```html
{% if listing %}
<div class="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 rounded-2xl p-6 border-2 border-purple-200 dark:border-purple-700 mb-6">
    <div class="flex items-start">
        <div class="w-12 h-12 bg-purple-600 rounded-xl flex items-center justify-center mr-4 flex-shrink-0">
            <i class="fas fa-file-contract text-white text-xl"></i>
        </div>
        <div class="flex-1">
            <h4 class="text-lg font-bold text-gray-900 dark:text-platinum-100 mb-2">
                Rental Agreement
                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 ml-2">
                    <i class="fas fa-crown mr-1"></i>Premium
                </span>
            </h4>
            <p class="text-sm text-gray-700 dark:text-platinum-200 mb-4">
                Generate a professional rental agreement for <strong>{{ listing.airport_icao }}</strong> parking space
            </p>
            <a href="{{ url_for('generate_agreement', listing_id=listing.id, renter_id=partner.id) }}" 
               class="inline-flex items-center bg-purple-600 hover:bg-purple-700 text-white font-bold px-6 py-3 rounded-xl shadow-lg hover:shadow-2xl transition-all hover-lift">
                <i class="fas fa-file-pdf mr-2"></i>Generate Agreement PDF
            </a>
        </div>
    </div>
</div>
{% endif %}
```

3. Click "Generate Agreement PDF"
4. PDF should download automatically
5. Open PDF → See professional rental agreement with all details!

**✅ Success!** PDF generation is working!

---

## Step 5: Add Profile Link to Navbar

**Edit `base.html`** (around line 120, in the authenticated user section):

```html
{% if current_user.is_authenticated %}
<div class="flex items-center space-x-3">
    <a href="{{ url_for('profile') }}"
        class="text-gray-700 dark:text-platinum-200 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors">
        <i class="fas fa-user-circle mr-1"></i>Profile
    </a>
    <a href="{{ url_for('messages') }}"
        class="text-gray-700 dark:text-platinum-200 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors">
        <i class="fas fa-envelope mr-1"></i>Messages
    </a>
    <a href="{{ url_for('my_listings') }}"
        class="text-gray-700 dark:text-platinum-200 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition-colors">
        My Listings
    </a>
    <a href="{{ url_for('logout') }}"
        class="bg-gray-600 hover:bg-gray-700 text-white font-semibold px-5 py-2.5 rounded-lg transition-all hover-lift">
        Logout
    </a>
</div>
{% endif %}
```

---

## ✅ All Features Working!

You now have:
1. ✅ **Smart Alerts** - Users get notified of matching listings
2. ✅ **Price Intelligence** - Owners see competitive pricing
3. ✅ **Photo Gallery** - Beautiful lightbox with navigation
4. ✅ **Rental Agreements** - Professional PDF generation

**Your HangarLink MVP is now feature-complete!** 🎉✈️
