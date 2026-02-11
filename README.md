# HangarLink

**Modern marketplace for hangar, tie-down, and ramp parking spaces**

## Overview

HangarLink is a premium web application that connects aircraft owners who have unused parking spaces with pilots who need parking at airports. The platform focuses exclusively on parking space coordination — no flight coordination, no regulatory complexity.

## Status

**MVP in Progress** - v1.0.0

Current features:
- ✅ User authentication (email/password)
- ✅ Listing creation for owners
- ✅ Search and browse functionality
- ✅ Individual listing detail pages
- ✅ Responsive, mobile-first UI with Tailwind CSS + Flowbite
- ✅ Dark mode support
- ✅ Legal disclaimer framework

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (MVP), PostgreSQL (production-ready)
- **Frontend**: Tailwind CSS + Flowbite
- **Authentication**: Flask-Login
- **ORM**: SQLAlchemy

## Project Structure

```
HangarLink-MVP-2025/
├── prompts/                  # All input prompts (numbered)
├── code/                     # Active code files
│   ├── app.py               # Main Flask application
│   ├── models.py            # Database models
│   ├── routes.py            # Route handlers
│   ├── config.py            # Configuration
│   └── requirements.txt     # Python dependencies
├── backups/                  # Old versions
├── templates/                # Jinja HTML templates
├── static/                   # CSS, JS, images, uploads
│   ├── css/
│   ├── js/
│   ├── images/
│   └── uploads/
├── planning/                 # Notes, roadmap, legal
│   └── legal-disclaimers.txt
└── README.md                 # This file
```

## Installation

1. **Install dependencies:**
   ```bash
   cd code
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Visit in browser:**
   ```
   http://localhost:5000
   ```

## Legal Note

**Non-flight coordination only — no FAA/CARs risk**

HangarLink is a parking space coordination tool only. We do not verify ownership, lease status, or suitability of spaces. Users are solely responsible for vetting partners, negotiating terms, ensuring compliance with local laws, and maintaining safety.

The platform does NOT:
- Coordinate flights
- Arrange pilot services
- Facilitate commercial aviation activities
- Verify aircraft airworthiness

This approach eliminates regulatory complexity and liability associated with flight coordination platforms.

## Roadmap

### Phase 1 (Current - MVP)
- [x] Basic authentication
- [x] Listing CRUD
- [x] Search functionality
- [x] Legal framework

### Phase 2 (Next)
- [ ] Photo uploads
- [ ] Direct messaging
- [ ] User profiles
- [ ] Email notifications
- [ ] Advanced search filters

### Phase 3 (Future)
- [ ] Premium subscriptions
- [ ] Analytics dashboard
- [ ] Mobile app
- [ ] Payment processing (optional)

## Contributing

This is a private MVP project. For questions or suggestions, contact the development team.

## License

Proprietary - All rights reserved

---

**Version**: v1.0.0  
**Last Updated**: February 2026
