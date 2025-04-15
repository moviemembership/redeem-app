from flask import Flask, request, render_template_string
from datetime import datetime, timedelta
import imaplib
import email
import re
import os

app = Flask(__name__)

IMAP_HOST = "mail.mantapnet.com"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASS = os.environ.get("ADMIN_PASS")

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Redeem Access</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #f9f9f9;
      padding: 40px;
      color: #333;
    }

    .container {
      max-width: 500px;
      margin: auto;
      background: white;
      padding: 30px 40px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
      border-radius: 12px;
    }

    h2 {
      text-align: center;
      margin-bottom: 20px;
      color: #4CAF50;
    }

    label {
      font-weight: bold;
      display: block;
      margin-bottom: 6px;
    }

    input[type="email"] {
      width: 100%;
      padding: 12px;
      margin-bottom: 20px;
      border: 1px solid #ccc;
      border-radius: 6px;
      font-size: 16px;
    }

    input[type="submit"] {
      background-color: #4CAF50;
      color: white;
      padding: 12px 20px;
      font-size: 16px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      width: 100%;
    }

    input[type="submit"]:hover {
      background-color: #45a049;
    }

    .link-area {
      margin-top: 30px;
      text-align: center;
    }

    .link-area a {
      text-decoration: none;
    }

    .link-area button {
      background-color: #2196F3;
      border: none;
      color: white;
      padding: 14px 28px;
      font-size: 16px;
      border-radius: 6px;
      cursor: pointer;
    }

    .link-area button:hover {
      background-color: #0b7dda;
    }

    .error {
      color: red;
      text-align: center;
      margin-top: 20px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>Redeem Your Temporary Code</h2>
    <form method="POST">
      <label for="email">Enter your email address:</label>
      <input type="email" name="email" placeholder="example@mantapnet.com" required>
      <input type="submit" value="Redeem Code">
    </form>

    {% if link %}
    <div class="link-area">
      <p><strong>Your Access Link:</strong></p>
      <a href="{{ link }}" target="_blank">
        <button>Open Access Link</button>
      </a>
    </div>
    {% elif error %}
    <div class="error">{{ error }}</div>
    {% endif %}
  </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def redeem():
    link = None
    error = None

    if request.method == "POST":
        user_email = request.form["email"].strip().lower()

        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST)
            mail.login(ADMIN_EMAIL, ADMIN_PASS)
            mail.select("inbox")

            # Get yesterday's date in IMAP format (e.g., 13-Apr-2025)
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")

            # Only get emails since yesterday and with matching subject
            status, messages = mail.search(None, f'(SINCE {yesterday} SUBJECT "Temporary Access Code")')

            if messages[0]:
                message_ids = messages[0].split()
                matched_email_id = None

                for msg_id in reversed(message_ids):
                    status, msg_data = mail.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Get the message body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_dispo = str(part.get("Content-Disposition"))

                            if content_type in ["text/plain", "text/html"] and "attachment" not in content_dispo:
                                payload = part.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    body = payload.decode(errors="ignore")
                                else:
                                    body = str(payload)
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            body = payload.decode(errors="ignore")
                        else:
                            body = str(payload)

                    # Check if email contains user email
                    if user_email in body:
                        matched_email_id = msg_id
                        break

                if matched_email_id:
                    # Re-fetch and extract link
                    status, msg_data = mail.fetch(matched_email_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_dispo = str(part.get("Content-Disposition"))

                            if content_type in ["text/plain", "text/html"] and "attachment" not in content_dispo:
                                payload = part.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    body = payload.decode(errors="ignore")
                                else:
                                    body = str(payload)
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            body = payload.decode(errors="ignore")
                        else:
                            body = str(payload)

                    # Extract first URL
                    match = re.search(r'https?://[^\s"<>\]]+', body)
                    link = match.group(0) if match else None

                    if not link:
                        error = "No link found in the email."
                else:
                    error = "No matching email found for that address."
            else:
                error = "No emails with subject 'Temporary Access Code' found."

            mail.logout()

        except Exception as e:
            error = f"Error: {str(e)}"

    return render_template_string(HTML_FORM, link=link, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

