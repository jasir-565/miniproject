# Vehicle Service & Roadside Assistance Management System

A full-stack Django web application designed for managing vehicle servicing, real-time service tracking, and emergency roadside assistance dispatches.

## 🚀 Features

### 👤 Customer Features
- **Account Management**: Register, sign in, and manage customer profile details.
- **Vehicle Fleet Management**: Register and track multiple personal vehicles with registration numbers, brand, model, and manufacturing year.
- **Service Booking**: Schedule vehicle repair/servicing appointments with optional date and time selection.
- **Real-Time Work Tracking**: Track live updates (`current_work` status and technician notes) on ongoing vehicle repairs.
- **Emergency Roadside Assistance**: Request immediate roadside assistance with live location integration (Google Maps link) and breakdown category.
- **Service History & Receipts**: Access complete record history of all completed services, replacement parts, inspection reports, and itemized billing costs.
- **Notification System**: Instant updates on service status changes, technician assignments, and emergency dispatch tracking.

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
├── db.sqlite3               # SQLite Database
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
- **`Notification`**: Real-time alerts sent to customers regarding service and assistance status updates.

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
   pip install django mysqlclient
   ```

4. **Run Database Migrations**:
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

---

## 🎨 UI & Design

The application features a responsive design built with custom CSS, supporting dark/light UI components, intuitive dashboards for both customers and staff, and interactive status badges for active services.

---

## 📄 License
This project is open source and available under the [MIT License](LICENSE).
