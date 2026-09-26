# ICT with Harsha

Full-stack learning portal for O/L and A/L ICT students.

## Project structure

```text
ict-with-harsha/
├── server.py                 # Stable application entry point
├── backend/
│   └── app.py                # API, authentication and database logic
├── pages/
│   ├── public/               # Public class website
│   ├── student/              # Student login and learning portal
│   └── admin/                # Private administrator portal
├── assets/
│   ├── css/                  # Shared page and portal styles
│   ├── js/                   # Browser-side application logic
│   ├── images/               # Teacher and website images
│   ├── resources/            # Student learning documents
│   └── research/             # Research documents
├── docs/                     # Deployment and email setup guides
└── requirements.txt          # Python package requirements
```

The public URLs remain unchanged for backward compatibility. For example,
`/student.html` and `/admin.html` are internally served from their organized
folders by `backend/app.py`.

## Run locally

```powershell
$env:ICT_EMAIL_DEBUG="1"
python -m pip install -r requirements.txt
python server.py 5500
```

Open `http://127.0.0.1:5500/`.

## Learning-system features

- Admin quiz manager with O/L, A/L and all-student targeting
- Multiple-choice question builder, points, schedules and time limits
- Draft, published and closed quiz states
- Automatic quiz announcement when a quiz is published
- One timed attempt per student with server-side scoring
- Detailed green/red answer review and downloadable PDF result sheets
- Admin attempt/result review
- Six-digit email verification for registration and forgotten-password resets
- Expiring, hashed verification codes with attempt limits

See `docs/EMAIL_SETUP.md` before production deployment.
