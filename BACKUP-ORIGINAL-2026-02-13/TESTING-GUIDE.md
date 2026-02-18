# 🚀 HangarLink MVP - Quick Testing Guide

## ✅ Server Status: RUNNING

**URL**: http://localhost:5000

---

## 📋 Complete Testing Flow

### **Step 1: Create Owner Account**

1. Visit `http://localhost:5000`
2. Click **"Sign Up"** (top-right)
3. Fill in:
   - Email: `owner@test.com`
   - Password: `password123`
   - Select: **"Rent out my parking space"**
4. Click **"Create Account"**
5. You'll be logged in automatically

### **Step 2: Post a Listing**

1. Click **"List Space"** in navbar
2. Fill out the form:
   - **Airport ICAO**: `KJFK`
   - **Size**: `2500`
   - **Covered**: ✓ (check the box)
   - **Monthly Price**: `850`
   - **Description**: 
     ```
     Premium covered hangar space at JFK International. 
     Features include:
     - 24/7 access with security code
     - Climate controlled
     - Security cameras
     - Electricity and water hookups
     - Perfect for single-engine aircraft
     ```
   - **Photos**: Upload 1-3 images (optional - you can skip for testing)
3. Click **"Create Listing"**
4. You should see your listing detail page!

### **Step 3: View Your Listing**

1. Click **"My Listings"** in navbar
2. You should see your KJFK listing with:
   - Green "Active" badge
   - $850/mo price
   - "View" and "Edit" buttons

### **Step 4: Create Renter Account**

1. Click **"Logout"** (top-right)
2. Click **"Sign Up"**
3. Fill in:
   - Email: `renter@test.com`
   - Password: `password123`
   - Select: **"Find parking for my aircraft"**
4. Click **"Create Account"**

### **Step 5: Search for Listings**

1. Click **"Find Parking"** in navbar
2. In the search form:
   - **Airport ICAO**: `KJFK`
   - **Covered**: Any
   - Leave price fields empty
3. Click **"Search Listings"**
4. You should see the listing you created!

### **Step 6: View Listing Details**

1. Click on the KJFK listing card
2. You should see:
   - Full description
   - Price and features
   - "Message Owner" button in sidebar

### **Step 7: Message the Owner**

1. Click **"Message Owner"** button
2. Type a message:
   ```
   Hi! I'm interested in renting this space for my Cessna 172. 
   Is it available starting next month?
   ```
3. Click the send button (paper plane icon)
4. Your message appears in a blue bubble!

### **Step 8: Owner Responds**

1. Click **"Logout"**
2. Click **"Login"**
3. Login as `owner@test.com` / `password123`
4. Click **"Messages"** in navbar
   - You should see a conversation with renter
   - Unread count badge (1)
5. Click on the conversation
6. You'll see the renter's message
7. Reply:
   ```
   Yes, it's available! The space is perfect for a 172. 
   Would you like to schedule a viewing?
   ```
8. Click send
9. Your reply appears in blue!

### **Step 9: Edit Listing**

1. Click **"My Listings"**
2. Click **"Edit"** on your KJFK listing
3. Change:
   - **Status**: Select "Rented"
   - **Price**: Change to `900`
4. Click **"Save Changes"**
5. Listing now shows "Rented" status

### **Step 10: Test Search Filters**

1. Logout and login as `renter@test.com`
2. Click **"Find Parking"**
3. Try different filters:
   - **Covered**: Yes
   - **Min Price**: 500
   - **Max Price**: 1000
4. Click **"Search Listings"**
5. Your listing should still appear (it's covered and $900)

---

## 🎯 Features to Test

### ✅ **Authentication**
- [x] Register new account
- [x] Login
- [x] Logout
- [x] Role selection (owner/renter)

### ✅ **Listings**
- [x] Create listing
- [x] View listing details
- [x] Edit listing
- [x] Change status
- [x] Upload photos (optional)
- [x] View own listings

### ✅ **Search**
- [x] Search by airport
- [x] Filter by covered status
- [x] Filter by price range
- [x] View search results
- [x] No results state

### ✅ **Messaging**
- [x] Send message to owner
- [x] View messages inbox
- [x] Unread count badges
- [x] Reply to messages
- [x] Message history

### ✅ **UI/UX**
- [x] Dark mode toggle
- [x] Responsive design
- [x] Hover animations
- [x] Status badges
- [x] Premium styling
- [x] Flash messages

---

## 🐛 Common Issues & Solutions

### **Issue**: Can't see images on listing cards
**Solution**: Images are optional. Listings without photos show a blue gradient placeholder with a plane icon.

### **Issue**: "Template not found" error
**Solution**: Make sure you're in the `code/` directory when running the server.

### **Issue**: Can't upload photos
**Solution**: The upload folder was created at `static/uploads/listings/`. Photos are optional for testing.

### **Issue**: Flash messages not showing
**Solution**: Flash messages appear at the top of the page after actions (login, create listing, etc.)

---

## 📊 Test Data Summary

### **Accounts Created**
- `owner@test.com` / `password123` (Owner role)
- `renter@test.com` / `password123` (Renter role)

### **Listing Created**
- Airport: KJFK
- Size: 2,500 sq ft
- Covered: Yes
- Price: $850/mo (later changed to $900)
- Status: Active (later changed to Rented)

### **Messages Sent**
- Renter → Owner: Inquiry about availability
- Owner → Renter: Confirmation and viewing offer

---

## 🎉 Success Criteria

You've successfully tested the MVP if you can:

✅ Create two different user accounts  
✅ Post a listing as an owner  
✅ Search and find that listing as a renter  
✅ Send a message to the owner  
✅ Receive and reply to the message  
✅ Edit the listing and change its status  
✅ See all features working with premium UI  

---

## 🚀 Next Steps

After testing, you can:

1. **Add more listings** - Create listings for different airports
2. **Test edge cases** - Try searching for non-existent airports
3. **Test mobile view** - Resize browser to mobile width
4. **Test dark mode** - Toggle between light/dark themes
5. **Add real photos** - Upload actual hangar/aircraft photos

---

**Your HangarLink MVP is fully functional!** 🎊✈️

Visit: http://localhost:5000
