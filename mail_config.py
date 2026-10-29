from flask_mail import Mail
from dotenv import load_dotenv
import os

load_dotenv()

mail = Mail()

def configure_mail(app):

    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USE_SSL"] = False

    app.config["MAIL_USERNAME"] = os.getenv("EMAIL_USER")
    app.config["MAIL_PASSWORD"] = os.getenv("EMAIL_PASSWORD")

    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("EMAIL_USER")

    mail.init_app(app)