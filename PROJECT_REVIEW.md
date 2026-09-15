# AutoNexa project review

Reviewed September 14, 2026 against the current working tree, including existing uncommitted changes.

**Follow-up implementation:** The findings below describe the original review snapshot. The subsequent fix includes appointment/navigation/count corrections, state guards, transactional assignment/completion, restricted tracking access, GPS validation and lifecycle handling, safe popup/photo text handling, password/cost/image/URL validation, environment-based production configuration, and regression tests. See `core/tests.py`, `core/static/core/cockpit.test.cjs`, and the README for checks and deployment instructions. Broader product ideas and the stated MySQL/device-testing limitations remain relevant.

AutoNexa has the core of a useful vehicle service and roadside assistance application. Its strongest feature is the connection between a customer's vehicles, workshop jobs, service records, and roadside requests. The next milestone should be reliable workflows and trustworthy tracking, followed by estimates, approvals, and maintenance reminders.

## Scope and verification

Reviewed project configuration, models, routes, views, migrations, templates, frontend scripts/styles, admin registration, tests, and setup documentation. Application code and existing data were not changed. This report is the only added project file.

- Installed runtime: Python 3.13.1; Django 5.2.17; mysqlclient 2.2.8; Pillow 12.3.0.
- Configured database: MySQL. The SQLite file in the repository directory is empty and is not the configured application database.
- `manage.py check`: passed.
- `manage.py test`: discovered zero tests.
- `manage.py check --deploy`: six security warnings.
- All migrations applied successfully to isolated, in-memory SQLite. Model/migration comparison found no pending changes.
- Fourteen public/customer/staff page requests returned HTTP 200 with appropriate synthetic users. Service creation and automatic technician assignment worked.
- Targeted request checks reproduced the appointment, navigation, dashboard-count, status-transition, coordinate-validation, and tracking-access problems below.

Limits: no visual browser or real-device GPS testing was performed; HTTP 200 does not establish browser JavaScript correctness. Production hosting, the actual MySQL schema/data, external map availability, and concurrent database behavior were not tested. SQLite checks do not establish MySQL compatibility. Security findings from code inspection are distinguished from reproduced request behavior.

## What is implemented

| Area | Current implementation |
|---|---|
| Accounts | Customer registration, login/logout, customer/staff profile-based routing; Django admin |
| Vehicles | Multiple vehicles per customer, unique registration number, year validation, photo upload/replacement/deletion and preview |
| Workshop | Service requests, assignment to staff with the fewest active workshop jobs, staff appointment scheduling, work notes, completion and cancellation |
| Records | One service record per booking, inspection/repair/parts text, one total service cost |
| Roadside | Request queue, staff acceptance, dispatch states, customer GPS capture, staff GPS updates, Leaflet maps, distance calculation |
| Notifications | Customer notification records and mark-as-read actions |
| History | Customer service/assistance history and staff-specific histories |

The architecture is a server-rendered Django monolith with one `core` app, seven domain models, fifteen templates, custom CSS, and small JSON endpoints. This is a reasonable structure for the project's present scope. A framework rewrite is unnecessary.

Good foundations include Django authentication, CSRF middleware and form tokens, ownership filtering on most customer actions, assigned-staff filtering on most mutations, unique vehicle registrations, decimal cost fields, migration history, and separate active/history screens.

## Findings, ordered by priority

### 1. Appointment assignment crashes — reproduced

`core/views.py:662` uses `datetime.strptime`, but `datetime` is never imported. Posting an appointment produces `NameError` and HTTP 500. Add the import, then test valid, invalid, past, and conflicting appointments. Also restrict assignment to appropriate booking states: the current lookup permits completed/cancelled bookings.

### 2. Map popups accept user-controlled HTML — code finding

`core/templates/core/staff_assistance_requests.html:273` and `roadside_assistance.html:369` insert location text into Leaflet popup strings. Other popup paths concatenate names and JSON text. `escapejs` protects a JavaScript string but does not sanitize the resulting HTML. A customer's saved location description can therefore reach a staff map popup as executable HTML.

Build popup elements with `textContent` for user values. Leaflet explicitly documents that popup strings are rendered as HTML: [Leaflet reference](https://leafletjs.com/reference.html#layer-bindpopup). This is unsafe application usage, not evidence that a library upgrade alone will fix it. No browser exploit was executed during this review.

Vehicle photo handlers also interpolate vehicle text directly into inline JavaScript (`vehicles.html:172,191,223,246`). Apostrophes can break these handlers; move values into data attributes and attach event listeners instead.

### 3. Development secrets and settings are unsuitable for deployment — checked

`config/settings.py` contains a literal Django secret and MySQL password, uses the MySQL root account, and enables DEBUG. The deployment check flags DEBUG, the insecure secret, missing HTTPS redirect/HSTS, and non-secure session/CSRF cookies.

Use environment configuration, a restricted database account, and separate production settings. Rotate credentials if they have been shared or used outside local development. Configure production static/media serving and backups. Do not copy the literal credentials into documentation. Add environment-file exclusions before introducing secret-bearing `.env` files.

### 4. Staff navigation uses the wrong relationship — reproduced

`base.html:46` and `home.html:25` check `user.staffprofile`, while the model's reverse relationship is `staff_profile`. A logged-in staff user receives customer navigation. Correct the relationship and cover both user roles in rendering tests.

### 5. Final states can be reopened — reproduced for service bookings

`update_service_status` accepts a target status without validating the current status. A direct request changed a COMPLETED booking back to IN_PROGRESS. The roadside updater has the same structural weakness. Old completion timestamps and records can then contradict the active state.

Define allowed transitions centrally, reject invalid transitions on the server, and make completion/cancellation terminal unless an explicit audited reopening feature exists. Hiding a form in a template does not enforce the rule.

### 6. Assignment and completion are not atomic — code finding

Two staff can read the same pending assistance request before either saves acceptance. Booking capacity checks can race too. Service record, booking status, and notification writes are separate, so failures can leave partial updates.

Use transactions and a conditional update or row lock for claiming work. Put related record/status writes in the same transaction. Test concurrent assignment using the actual database backend. Automatic workshop allocation should eventually account for staff activity, skills, shifts, and roadside workload rather than workshop job count alone.

### 7. Tracking access is broader than assigned work — reproduced

`core/views.py:1522` treats any staff profile as sufficient access. An unrelated staff account received another technician's request, including customer phone and coordinates. Decide whether dispatchers need broad access; represent that permission explicitly. Ordinary technicians should normally see their assigned jobs, with a deliberately limited pending queue.

Location writes also lack a request-state restriction, allowing assigned staff to update completed/cancelled requests. Restrict sharing to active states.

### 8. Coordinates and location display need correction — partly reproduced

- JSON latitude `0` was rejected because `data.get('latitude') or data.get('lat')` treats zero as missing.
- Latitude `123`, longitude `200` were accepted, despite being outside geographic ranges.
- Client truthiness checks also ignore valid zero coordinates.
- Customer maps replace missing coordinates with Bangalore coordinates, then treat that fallback as an actual breakdown position. Staff maps similarly label a fallback point as live location.
- Staff pages combine `watchPosition` with five-second polling per assigned request; customer pages poll every four seconds. Timers/watchers are not explicitly stopped on completion, and stale/error handling is limited.

Require finite, paired coordinates with latitude in [-90,90] and longitude in [-180,180]. Use explicit null checks. Separate a default map viewport from actual location markers. Show permission errors, last-update age, and stale/offline states. Stop tracking on terminal states and avoid redundant GPS watchers.

The current Haversine distance and dotted line represent straight-line distance, not road distance or a navigable route. Label them accurately; add routing/ETA only as a separate feature.

### 9. Validation is incomplete — code finding

Registration enforces only six password characters and does not call configured Django password validators. It validates a cleaned phone but saves the original string, potentially exceeding the field's length. Maximum lengths, service-type choices, map URL schemes, and decimal bounds are not consistently validated. `NaN`/infinite cost inputs are not safely handled. Image validation trusts the submitted MIME type rather than decoding the file.

Use Django forms/ModelForms, password validation, explicit coordinate/cost validators, and verified image decoding with size/dimension limits. Preserve non-password input after errors. Store user/profile creation atomically. Validate URLs before rendering clickable links. Django model save does not automatically run `full_clean`: [Django model validation](https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects).

Photo replacement deletes the old image before confirming the replacement save, risking lost images on failure. Save the replacement successfully before cleanup. Account recovery and login abuse protection are also absent from the project.

### 10. Active booking count includes cancellations — reproduced

`customer_dashboard` excludes only COMPLETED. One cancelled booking produced an active count of one, while My Bookings correctly hides it. Reuse explicit active-state definitions across queries and dashboard counters.

### 11. Maintainability and query growth — code finding

`core/views.py` contains roughly 1,590 lines with repeated role checks, validation, notification creation, and dashboard queries. Lists have no pagination and do not eagerly load relations used by templates, creating per-row query growth.

Introduce forms, small workflow functions, shared role decorators, `select_related` for displayed relationships, pagination, and consolidated count queries. Keep the single Django application until domain size justifies splitting it. Move substantial map/photo scripts into static modules and replace inline styling with reusable classes. The existing `cockpit.js` is largely a placeholder.

### 12. Setup documentation overstates or omits features

There is no pinned requirements file. The README install command omits Pillow despite the ImageField. It describes SQLite while configuration uses MySQL, lacks MySQL provisioning and staff-profile setup, links a missing LICENSE, and uses a placeholder clone URL. Settings comments say Django 6.1 while the installed runtime and migrations indicate 5.2.17.

Customer appointment selection is not implemented: staff schedule appointments. Service and notification pages require refresh; only roadside tracking polls. Billing is a single total with parts text, not itemized invoice lines. Profile editing and downloadable receipts are not present. Update the README to distinguish implemented and planned features.

## Product and interface ideas

| Idea | User benefit | Relative effort |
|---|---|---|
| Repair estimate and customer approval | Customer approves work and price before repairs begin | Medium |
| Itemized invoice and printable/downloadable receipt | Separates labor, parts, quantities, and totals | Medium |
| Timestamped service timeline | Makes diagnosis, approval, repair, testing, and readiness understandable | Medium |
| Appointment calendar with durations | Prevents overlapping work, respects opening hours and availability | Medium |
| Maintenance reminders by date/odometer | Gives customers a reason to return after a completed service | Medium |
| Reliable roadside tracking | Stale GPS indicator, arrival state, call technician action, stop-sharing controls | Medium |
| Search and filters | Find jobs by registration, customer, status, and date | Small–medium |
| Customer profile and password recovery | Lets customers maintain contact details and recover access | Small–medium |
| Manager dashboard | Reveals pending work, staff load, turnaround and completed-service revenue | Medium |
| Parts inventory | Connects stock usage to service records and future purchasing | Large |

For a focused mini-project, prioritize the first three ideas after fixing the core defects. Estimate approval plus itemized completion records demonstrates a coherent end-to-end business workflow.

Useful future models: `ServiceCatalogItem` (name, expected duration, indicative price), `ServiceStatusEvent` (actor, timestamp, state, note), `Estimate`/`EstimateLine` (price and approval), `InvoiceLine` (quantity/unit price), and `MaintenanceReminder` (date/odometer). Add only those needed for the next milestone.

Interface improvements: highlight the next appointment/current job on the customer dashboard; provide a prominent emergency action; simplify mobile navigation; preserve forms after errors; use inline field errors; add active navigation state; and make photo dialogs keyboard accessible with focus management and appropriate dialog labels. Keep emergency contact information configurable and verified before real use. Actual visual layout still needs browser testing.

## Suggested implementation order

1. Fix appointment import, staff navigation, active counts, popup handling, terminal-state guards, and coordinate validation. Establish role and ownership tests.
2. Add forms, transactions, safe assignment, production configuration, a reproducible dependency/setup guide, and a real regression suite.
3. Improve tracking lifecycle and error states, search/pagination, and mobile/modal usability.
4. Add estimate approval, service timeline, and itemized receipts as one connected feature milestone.
5. Add reminders and manager analytics once event timestamps and costs are reliable.

Priority regression scenarios: customer isolation; staff/dispatcher permissions; appointment validation and overlap; terminal-state rejection; simultaneous assistance acceptance; atomic service completion; invalid costs/images/GPS; safe popup rendering; and tracking shutdown after cancellation/completion.
