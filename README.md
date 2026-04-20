# Online Blood Bank Management System

A Django-based web app for managing blood donors and emergency requests with location-based matching.

## Features
- Donor registration with account creation and email OTP verification
- Blood request submission with urgency levels and mandatory doctor prescription image upload
- Prescription upload security checks (JPG/PNG only, size limit enforced, document-like paper+text validation, file auto-removed on cancellation/replacement)
- Click-to-select map picker for latitude/longitude in donor and request forms
- Haversine distance matching to recommend nearest donors
- Logged-in donors can view nearby incoming matching requests and accept them
- Donor email alerts include the uploaded prescription document as an attachment
- On donor acceptance, requester receives an in-app status message on the request tracker
- Requesters can track requests using request ID + phone and mark transactions as completed
- Admin panel to manage donors and requests

## Setup
1. Create the virtual environment and install dependencies:
   - `pip install django pillow`
2. Create your environment file:
   - `Copy-Item .env.example .env`
   - Update values in `.env` (especially `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`)
3. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
4. Create an admin user:
   - `python manage.py createsuperuser`
5. Start the development server:
   - `python manage.py runserver`

## Email OTP
OTP is enabled for donor registration.
- If SMTP credentials are configured, OTP is sent to the real email inbox.
- If SMTP is not configured, OTP falls back to console output in the `runserver` terminal.

## Real SMTP for OTP Email
Set these values in `.env` to send real OTP emails:
- `EMAIL_HOST=smtp.gmail.com`
- `EMAIL_PORT=587`
- `EMAIL_HOST_USER=your_email@gmail.com`
- `EMAIL_HOST_PASSWORD=your_app_password`
- `EMAIL_USE_TLS=True`
- `EMAIL_USE_SSL=False`
- `DEFAULT_FROM_EMAIL=your_email@gmail.com`

The app auto-loads `.env` on startup, so you only configure once.

## Prescription Upload Limits
- Allowed formats: `.jpg`, `.jpeg`, `.png`
- Default max upload size: `5 MB`
- Optional environment override: `PRESCRIPTION_MAX_UPLOAD_BYTES=5242880`
- Document heuristic validation: image must look like a paper document and contain visible text-like strokes

## Pages
- Home: `/`
- Donor registration: `/donors/register/`
- Donor profile: `/donors/profile/`
- Incoming nearby requests and accept action: `/donors/incoming-requests/`
- Blood request form: `/request/`
- Request tracker and completion: `/track/`
- Admin panel: `/admin/`

vgedvovpyjetfqzm




superuser: admin
email: admin2000@gmail.com
pw:adminkopassword

python manage.py runserver 0.0.0.0:8000