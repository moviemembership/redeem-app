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

    .error {
      color: red;
      text-align: center;
      margin-top: 20px;
    }

    .code-display {
      font-size: 36px;
      color: green;
      margin: 20px auto;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>Redeem Your Temporary Code</h2>
    <form method="POST" id="redeem-form">
      <label for="email">Enter your email address:</label>
      <input type="email" name="email" placeholder="example@mantapnet.com" required>
      <input type="submit" value="Redeem Code">

    <!-- Loading Spinner -->
      <div id="loading" style="display: none; text-align: center; margin-top: 20px;">
        <img src="/loading.gif" alt="Loading..." width="50">
        <p>Fetching your access code...</p>
      </div>
    </form>

    {% if code %}
      <p><strong>Your temporary access code:</strong></p>
      <div class="code-display">{{ code }}</div>
    {% elif error %}
      <div class="error">{{ error }}</div>
    {% endif %}
  </div>

  <div class="instructions">
    <h3>How to use:</h3>
    <ol>
      Before redeeming the code, make sure you had done the steps<br><br>
      <table>
    <tr>
      <td><img src="/tv.png" width="400" height="300"></td>
      <td><img src="/fon.png" width="400"></td>
    </tr>
  </table>
      <li>Make sure you clicked send email like above.</li>
      <li>Enter your <strong>@mantapnet.com</strong> email above.</li>
      <li>Click <strong>Redeem Code</strong>.</li>
      <li>Wait a few seconds while we fetch your access email.</li>
    </ol>
  </div>

  <script>
    const form = document.getElementById("redeem-form");
    const loading = document.getElementById("loading");

    form.addEventListener("submit", function () {
      loading.style.display = "block";
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
            status, messages = mail.search(None, f'(SINCE {yesterday} SUBJECT "Temporary Access Code")')

            if messages[0]:
                message_ids = messages[0].split()
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

    return render_template_string(HTML_FORM, code=code, error=error)

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
            return None, "Unable to fetch code. Please contact customer support."
    except Exception as e:
        print("Error while extracting code:", e)
        return None, "Unable to access the verification link. Try again later."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
