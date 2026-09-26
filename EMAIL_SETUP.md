# Email verification setup

Registration and student password recovery send a six-digit code that expires after 10 minutes. SMTP credentials are read only from server environment variables and must never be committed to GitHub.

## Gmail SMTP example

Create `/etc/ict-with-harsha.env` on the AWS server:

```ini
ICT_SMTP_HOST=smtp.gmail.com
ICT_SMTP_PORT=587
ICT_SMTP_SECURITY=starttls
ICT_SMTP_USER=your-address@gmail.com
ICT_SMTP_PASSWORD=your-google-app-password
ICT_SMTP_FROM=your-address@gmail.com
```

Protect the file with `sudo chmod 600 /etc/ict-with-harsha.env`.

Add this line inside the `[Service]` section of `/etc/systemd/system/ict-with-harsha.service`:

```ini
EnvironmentFile=/etc/ict-with-harsha.env
```

Then run:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ict-with-harsha
```

For local development only, set `ICT_EMAIL_DEBUG=1`. Verification messages are printed to the terminal instead of being sent. Never enable debug email mode on the public server.
