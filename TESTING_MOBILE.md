# Mobile Responsiveness Testing Checklist

## 1. Navigation Bar
- [x] **Hamburger Menu**: Verify the hamburger menu icon appears on screens narrower than 768px (MD breakpoint).
- [x] **Menu Expansion**: Click the hamburger icon and ensure the menu expands smoothly, showing all links (Home, AI Match, Feed, etc.).
- [x] **Menu Collapse**: Click the hamburger icon again to close the menu.
- [x] **Desktop View**: Resize window to > 768px and verify the hamburger menu disappears and full navigation links reappear.
- [x] **User Dropdown**: Verify the user profile dropdown works correctly on mobile.

## 2. Homepage (Hero & Layout)
- [x] **Hero Section Height**: Ensure the hero section takes up appropriate vertical space (`min-h-[80vh]`) without overflowing content on small screens.
- [ ] **Hero Text Scaling**: Verify main headlines scale down (`text-4xl`) to fit narrow screens without horizontal scrolling.
- [ ] **Search Form**: Check that the search form inputs stack vertically on mobile (1 column) and expand to 2 columns on tablets.
- [ ] **Forecast Widget**: Ensure the Forecast Widget stacks vertically (Icon/Title top, details below) on mobile.

## 3. Listings & Search Results
- [ ] **Grid Layout**: distinct listings should stack in a single column on mobile, 2 columns on tablet, 3 on desktop.
- [ ] **Card Sizing**: Verification that listing cards do not overflow the screen width.
- [ ] **Images**: Listing thumbnails should maintain aspect ratio and fit within the card width.

## 4. Listing Detail Page
- [x] **Main Photo**: Verify the main listing photo height is reduced (`h-64`) on mobile to save vertical space, and expands (`h-96`) on desktop.
- [ ] **Photo Grid**: thumbnails should wrap or hide gracefully.
- [ ] **Sidebar Stacking**: The "Contact Owner" and "Availability" sidebars should stack *below* the main content on mobile.
- [ ] **Concierge Button**: The Floating Action Button (FAB) for AI Concierge should be visible and clickable without blocking essential content.

## 5. Forms & Inputs
- [ ] **Input Size**: All text inputs and dropdowns should span 100% width on mobile for easy tapping.
- [ ] **Touch Targets**: Buttons and links should have sufficient padding (min 44px height) for touch interaction.
- [ ] **Post Listing Form**: Verify the multi-step or long form on "Post Listing" is scrollable and usable on mobile.

## 6. General
- [ ] **Horizontal Scroll**: Ensure there is NO unwanted horizontal scrolling on any page (overflow-x: hidden).
- [ ] **Dark Mode**: Toggle dark mode on mobile and ensure all text/background contrasts are correct.
