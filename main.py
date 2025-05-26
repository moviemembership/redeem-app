from flask import Flask, request, render_template_string
from datetime import datetime, timedelta
import imaplib
import email
import re
import os
import requests
from bs4 import BeautifulSoup
from flask import redirect

app = Flask(__name__)

IMAP_HOST = "mail.mantapnet.com"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASS = os.environ.get("ADMIN_PASS")

HTML_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Redeem Access Code</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      padding: 0;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f4f7f6;
      color: #333;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px 20px;
    }

    .container {
      background: #ffffff;
      max-width: 500px;
      width: 100%;
      padding: 30px 40px;
      border-radius: 12px;
      box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }

    h2 {
      text-align: center;
      color: #4CAF50;
      margin-bottom: 20px;
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
      transition: background-color 0.3s ease;
    }

    input[type="submit"]:hover {
      background-color: #43a047;
    }

    .code-display {
      font-size: 30px;
      color: #2e7d32;
      text-align: center;
      margin-top: 20px;
      font-weight: bold;
    }

    .error {
      color: #d32f2f;
      text-align: center;
      margin-top: 20px;
      font-weight: bold;
    }

    .email-info {
      text-align: center;
      margin-top: 10px;
      font-style: italic;
      color: #555;
    }

    .instructions {
      margin-top: 50px;
      max-width: 900px;
      background: #ffffff;
      padding: 25px;
      border-radius: 10px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }

    .instructions h3 {
      color: #388e3c;
      margin-top: 0;
    }

    .instructions ol {
      padding-left: 20px;
    }

    .instructions li {
      margin-bottom: 10px;
    }

    .instructions img {
      max-width: 100%;
      border-radius: 10px;
      margin: 10px 0;
    }

    #loading {
      display: none;
      text-align: center;
      margin-top: 20px;
    }

    #loading img {
      width: 40px;
    }
  </style>
</head>
<body>

  <div class="container">
    <h2>Redeem Your Access Code</h2>
    <form method="POST" id="redeem-form">
      <label for="email">Enter your @mantapnet.com email:</label>
      <input type="email" name="email" placeholder="example@mantapnet.com" required>
      <input type="submit" value="Get Code">

      <div id="loading">
        <img src="/loading.gif" alt="Loading...">
        <p>Checking for your code...</p>
      </div>
    </form>

    {% if email %}
      <div class="email-info">Entered email: {{ email }}</div>
    {% endif %}
    {% if code %}
      <div class="code-display">{{ code }}</div>
    {% elif error %}
      <div class="error">{{ error }}</div>
    {% endif %}
  </div>

  <div class="instructions">
    <h3>How to Redeem</h3>
    <ol>
      <li>On TV: Click <strong>[I'm Travelling/Saya Sedang Mengembara]</strong> → <strong>[Send Email]</strong></li>
      <li>On Phone/PC: Click <strong>[Watch Temporary]</strong> → <strong>[Send Email]</strong></li>
      <li>Enter your <strong>@mantapnet.com</strong> email above.</li>
      <li>Click <strong>Get Code</strong> and wait a few seconds.</li>
    </ol>
    <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; margin-top: 20px;">
      <img src="/tv.png" alt="TV Screenshot" width="400">
      <img src="/fon.png" alt="Phone Screenshot" width="400">
    </div>
  </div>

  <script>
    document.getElementById("redeem-form").addEventListener("submit", function () {
      document.getElementById("loading").style.display = "block";
    });
  </script>

</body>
</html>

"""

@app.route("/fon.png")
def fon_link():
  external_url = "https://github.com/moviemembership/redeem-app/blob/485881a153a2ebc785e524b94f5a7d9fe232b157/fon.png?raw=true"
  return redirect(external_url)

@app.route("/tv.png")
def tv_link():
  external_url = "https://github.com/moviemembership/redeem-app/blob/main/tv.png?raw=true"
  return redirect(external_url)

@app.route("/loading.gif")
def loading_link():
  external_url = "https://github.com/moviemembership/redeem-app/blob/main/Loading_icon.gif?raw=true"
  return redirect(external_url)

@app.route("/", methods=["GET", "POST"])
def redeem():
    code = None
    error = None

    if request.method == "POST":
        user_email = request.form["email"].strip().lower()

        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST)
            mail.login(ADMIN_EMAIL, ADMIN_PASS)
            mail.select("inbox")

            yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
            status, messages_temp = mail.search(None, f'(SINCE {yesterday} SUBJECT "Temporary Access Code")')
            status, messages_kod = mail.search(None, f'(SINCE {yesterday} SUBJECT "Kod akses sementara")')

            message_ids = messages_temp[0].split() + messages_kod[0].split()

            if message_ids:
                matched_email_id = None

                for msg_id in reversed(message_ids):
                    status, msg_data = mail.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    body = extract_email_body(msg)

                    if user_email in body:
                        matched_email_id = msg_id
                        break

                if matched_email_id:
                    status, msg_data = mail.fetch(matched_email_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    body = extract_email_body(msg)

                    match = re.search(r'https?://[^\s"<>\]]+', body)
                    link = match.group(0) if match else None

                    if link:
                        code, status_msg = extract_code_from_verification_link(link)
                        if status_msg:
                            error = status_msg
                    else:
                        error = "No link found in the email."
                else:
                    error = "No matching email found for that address."
            else:
                error = "No recent emails with subject 'Temporary Access Code' found."

            mail.logout()

        except Exception as e:
            error = f"Error: {str(e)}"

    return render_template_string(HTML_FORM, code=code, error=error, email=user_email if request.method == "POST" else "")

def extract_email_body(msg):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type in ["text/plain", "text/html"]:
                    payload = part.get_payload(decode=True)
                    return payload.decode(errors="ignore") if isinstance(payload, bytes) else str(payload)
        else:
            payload = msg.get_payload(decode=True)
            return payload.decode(errors="ignore") if isinstance(payload, bytes) else str(payload)
    except Exception:
        return ""

def extract_code_from_verification_link(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        if soup.find("div", class_="title", string="This link is no longer valid"):
            return None, "This code has expired. Please re-request on the original device. Please Make sure you have done the steps below and redeem it within 15 minutes."

        code_div = soup.find("div", {"data-uia": "travel-verification-otp"})
        if code_div:
            return code_div.text.strip(), None
        else:
            return None, "Unable to fetch code. Please Make Sure You Redeem It within 15 minutes. Contact customer support for more information."
    except Exception as e:
        print("Error while extracting code:", e)
        return None, "Unable to access the verification link. Try again later."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
