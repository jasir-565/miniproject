# Vehicle Service & Roadside Assistance Management System

A full-stack Django web application designed for managing vehicle servicing, real-time service tracking, and emergency roadside assistance dispatches.

## 🚀 Features

### 👤 Customer Features
- **Account Management**: Register and sign in with a customer profile.
- **Vehicle Fleet Management**: Register and track multiple personal vehicles with registration numbers, brand, model, and manufacturing year.
- **Service Booking**: Request repairs and servicing; assigned staff schedule the appointment.
- **Work Tracking**: View the latest `current_work` status and technician notes on page refresh.
- **Emergency Roadside Assistance**: Request immediate roadside assistance with live location integration (Google Maps link) and breakdown category.
- **Service History**: Access completed services, replacement parts, inspection reports, and total service costs.
- **Notification System**: In-app records of status changes, assignments, and dispatch updates.

### 🛠️ Staff & Admin Features
- **Staff Dashboard**: Overview of pending service bookings, active repairs, and emergency roadside dispatch queues.
- **Service Management**: Accept bookings, assign staff technicians, update current work progress, and complete service records.
- **Emergency Dispatch Tracking**: View incoming roadside assistance requests, update staff dispatch location links (`staff_location_link`), and manage technician arrival status.
- **Historical Records**: Comprehensive service log history for all serviced vehicles and emergency dispatches.

---

## 🏗️ Project Architecture

```
miniproject/
├── config/                  # Django project configuration
│   ├── settings.py          # App settings & database configuration
│   ├── urls.py              # Root URL routing
│   ├── wsgi.py / asgi.py    # WSGI/ASGI deployment scripts
├── core/                    # Main application module
│   ├── models.py            # Customer, Staff, Vehicle, Booking & Assistance models
│   ├── views.py             # Business logic & workflow controllers
│   ├── urls.py              # App-level routing
│   ├── admin.py             # Django Admin registration
│   ├── templates/core/      # Frontend HTML templates
│   ├── static/core/         # Custom CSS & static assets
│   └── migrations/          # Database schema migration history
├── local_settings.json      # Local MySQL credentials (ignored by Git)
├── manage.py                # Django CLI management entrypoint
└── README.md                # Project Documentation
```

---

## 🛢️ Database Schema Overview

- **`CustomerProfile`**: One-to-One extension of Django `User` for customer contact details.
- **`StaffProfile`**: One-to-One extension of Django `User` for service staff & designation.
- **`Vehicle`**: Belongs to `CustomerProfile`, stores registration, brand, model, year.
- **`ServiceBooking`**: Connects customer vehicle to service type, assigned staff, status, appointment date/time, and live `current_work` tracking.
- **`ServiceRecord`**: One-to-One with completed `ServiceBooking` storing inspection notes, repair details, parts replaced, and total cost.
- **`AssistanceRequest`**: Stores emergency breakdown details, customer location map links, technician dispatch links, and status.
- **`Notification`**: In-app alerts for customers regarding service and assistance status updates.

---

## 🔧 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/miniproject.git
   cd miniproject
   ```

2. **Set up a Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure MySQL and run database migrations**:
   Create a MySQL database named `autonexa_db` and an application database user with access to it. Copy `local_settings.example.json` to `local_settings.json` in the project root and enter your database credentials and a long random development secret. The local file is ignored by Git. Existing local credentials were preserved during the security fixes.

   Generate a random secret with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

   ```bash
   python manage.py migrate
   ```

5. **Create Superuser (Optional)**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Start Development Server**:
   ```bash
   python manage.py runserver
   ```
   Access the web app at `http://127.0.0.1:8000/`.

7. **Create service staff**:
   In Django admin, create a user and then a `StaffProfile` linked to that user. A Django superuser or the user `is_staff` flag alone does not create a service technician profile. Booking requests need at least one active user with a staff profile.

## Regression checks

```bash
python manage.py test --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
node --test core/static/core/cockpit.test.cjs
```

Tests use in-memory SQLite and never use the application's MySQL data. Node is optional for the Python suite; when present it also checks rendered page JavaScript. MySQL concurrency and real-device GPS behavior require separate integration testing.

## Production configuration

Set environment variables `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` (a new random value of at least 50 characters), `DJANGO_ALLOWED_HOSTS` (comma-separated domain names), `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. Production ignores `local_settings.json`; use a restricted database account. Rotate any previously shared credentials before deployment.

Production enables HTTPS redirects, secure cookies, and HSTS. Configure TLS and static/media serving, run `collectstatic`, and use a production WSGI/ASGI server. If TLS terminates at a trusted proxy, configure Django's proxy HTTPS handling for that deployment; do not blindly trust forwarded headers.

`DJANGO_HSTS_INCLUDE_SUBDOMAINS=true` and `DJANGO_HSTS_PRELOAD=true` are optional. Enable only after confirming HTTPS coverage and the intended domain policy. Without these opt-ins, `check --deploy` reports W005/W021; the app does not enroll the domain in a browser preload list. Run `python manage.py check --deploy` with production environment values.

## Current behavior

Appointments are assigned by staff. Service work notes and notifications appear on page refresh; roadside tracking polls for updates. Map distances are straight-line distances, not driving routes or ETAs. Billing currently stores one total and free-text parts information, rather than invoice line items. Customer profile editing and downloadable receipts are future work.

---

## 🎨 UI & Design

The application features a responsive design built with custom CSS, supporting dark/light UI components, intuitive dashboards for both customers and staff, and interactive status badges for active services.

---

## 📄 License
No license file is currently included in this repository.
