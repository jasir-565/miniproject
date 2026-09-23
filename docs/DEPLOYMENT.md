# Running and deploying AutoNexa

## Apply this update

Back up the existing database and media before changing an installation. In the project's Python environment:

```sh
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

Migration 0008 adds estimates, receipt snapshots, timeline events, schedules, availability and notification links. Existing bookings are retained. Review staff approval states in the admin before accepting new work.

## Configuration

Use environment variables or the existing ignored local settings file for secrets. Configure `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. Use a dedicated database account. Set `DJANGO_TIME_ZONE` for the workshop; the default is Asia/Kolkata. `WORKSHOP_OPEN` and `WORKSHOP_CLOSE` default to 09:00 and 18:00. `WORKSHOP_DAYS` is a comma-separated list with Monday=0 and Sunday=6; the default includes every day. Staff shifts and time off are managed in Django admin.

Password reset uses the console email backend by default. Real delivery requires `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL`. Verify delivery and the reset link using the actual public HTTPS hostname before launch.

## Production handover

Set `DJANGO_DEBUG=false`, a unique `DJANGO_SECRET_KEY` (at least 50 characters), `DJANGO_ALLOWED_HOSTS` (comma-separated hostnames), and `DJANGO_CSRF_TRUSTED_ORIGINS` (comma-separated HTTPS origins). If the HTTPS proxy overwrites the incoming X-Forwarded-Proto header, set `DJANGO_TRUST_PROXY=true`. Run `python manage.py check --deploy` and `python manage.py collectstatic --noinput`. Serve `config.wsgi:application` with a production WSGI server behind that reverse proxy; configure the proxy to serve collected static files and uploaded media. Django's development server and `tools/preview_ui.py` are not production entry points.

Keep database and media backups together and test restoration. Forward application error logs to the hosting platform, monitor availability, and verify the customer booking, approval, receipt and roadside flows after deployment. No deployment or live database migration is performed by the automated test suite.

## Checks

```sh
python manage.py test --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
node --test core/static/core/cockpit.test.cjs
```

GitHub Actions also runs browser checks and the test suite against a disposable MySQL service. To run that job locally, supply `MYSQL_TEST_PASSWORD` and the test connection settings in `config/mysql_test_settings.py`; the test user must be able to create/drop its dedicated test database. Never point this configuration at production.
