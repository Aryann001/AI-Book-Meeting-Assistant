import smtplib
import os


def send_email(to: str, subject: str, content: str):
    text = f"Subject: {subject}\n\n{content}"

    try:
        server = smtplib.SMTP(os.environ["SMTP_HOST"], os.environ["SMTP_PORT"])
        server.starttls()

        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])

        server.sendmail(os.environ["SMTP_USER"], to, text)
        server.quit()
        return {"success": True, "message": "Email sent successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}
