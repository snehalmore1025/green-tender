import os
import random
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash

from db import db, cursor
from mail_config import mail, configure_mail
from ai_bidding import rank_quotations_for_tender, best_bid_summary
from nursery_dashboard import nursery_bp


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "GreenTender@2026")
configure_mail(app)
app.register_blueprint(nursery_bp)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def admin_required():
    """Allow only the single administrator to access admin routes."""
    return "user_id" in session and session.get("role") == "admin"


def admin_redirect():
    return redirect(url_for("admin_dashboard"))


def safe_rollback():
    try:
        db.rollback()
    except Exception:
        pass


def save_quotation_remark(quotation_id, remark):
    """Create a new remark or update the existing remark for a quotation."""
    cursor.execute(
        "SELECT remark_id FROM quotation_remarks WHERE quotation_id=%s",
        (quotation_id,)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE quotation_remarks
            SET admin_id=%s,
                remark=%s,
                remarked_at=CURRENT_TIMESTAMP
            WHERE quotation_id=%s
            """,
            (session["user_id"], remark, quotation_id)
        )
    else:
        cursor.execute(
            """
            INSERT INTO quotation_remarks (quotation_id, admin_id, remark)
            VALUES (%s, %s, %s)
            """,
            (quotation_id, session["user_id"], remark)
        )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# USERS - ADMIN ONLY
# =========================================================

@app.route("/users")
def users():
    if not admin_required():
        flash("Unauthorized Access.", "error")
        return redirect(url_for("login"))

    try:
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return cursor.fetchall()
    except Exception as e:
        print("USERS ERROR:", type(e).__name__, str(e))
        safe_rollback()
        return "Unable to load users.", 500


# =========================================================
# REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    fullname = request.form.get("fullname", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not fullname or not email or not phone or not password:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("register"))

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("register"))

    if len(password) < 6:
        flash("Password must contain at least 6 characters.", "error")
        return redirect(url_for("register"))

    if len(phone) != 10 or not phone.isdigit():
        flash("Enter a valid 10-digit phone number.", "error")
        return redirect(url_for("register"))

    try:
        cursor.execute(
            "SELECT user_id FROM users WHERE LOWER(email)=%s",
            (email,)
        )
        if cursor.fetchone():
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

        cursor.execute(
            "SELECT user_id FROM users WHERE phone=%s",
            (phone,)
        )
        if cursor.fetchone():
            flash("Phone number already registered.", "error")
            return redirect(url_for("register"))

        otp = str(random.randint(100000, 999999))

        session["registration"] = {
            "fullname": fullname,
            "email": email,
            "phone": phone,
            "password": password,
            "otp": otp,
            "otp_created": datetime.now().isoformat(),
            "otp_attempts": 0,
        }

        msg = Message(
            subject="GreenTender - Email Verification OTP",
            recipients=[email]
        )
        msg.body = f"""Hello {fullname},

Welcome to GreenTender.

Your email verification OTP is: {otp}

This OTP is valid for 5 minutes.
Do not share this OTP with anyone.

Regards,
GreenTender Team
"""

        mail.send(msg)
        flash("OTP has been sent to your email.", "success")
        return redirect(url_for("verify_otp"))

    except Exception as e:
        safe_rollback()
        session.pop("registration", None)
        print("REGISTRATION ERROR:", type(e).__name__, str(e))
        flash("Unable to complete registration. Please try again.", "error")
        return redirect(url_for("register"))


# =========================================================
# REGISTRATION OTP
# =========================================================

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    registration = session.get("registration")

    if not registration:
        flash("Registration session expired. Please register again.", "error")
        return redirect(url_for("register"))

    if request.method == "GET":
        return render_template("verify_otp.html")

    entered_otp = request.form.get("otp", "").strip()

    try:
        otp_created = datetime.fromisoformat(registration["otp_created"])
    except (KeyError, ValueError, TypeError):
        session.pop("registration", None)
        flash("Invalid OTP session. Please register again.", "error")
        return redirect(url_for("register"))

    if datetime.now() > otp_created + timedelta(minutes=5):
        session.pop("registration", None)
        flash("OTP has expired. Please register again.", "error")
        return redirect(url_for("register"))

    registration["otp_attempts"] = int(registration.get("otp_attempts", 0)) + 1
    session["registration"] = registration

    if registration["otp_attempts"] > 3:
        session.pop("registration", None)
        flash("Maximum OTP attempts exceeded. Please register again.", "error")
        return redirect(url_for("register"))

    if entered_otp != str(registration["otp"]):
        remaining = 3 - registration["otp_attempts"]
        flash(f"Invalid OTP. {remaining} attempt(s) remaining.", "error")
        return redirect(url_for("verify_otp"))

    try:
        hashed_password = generate_password_hash(registration["password"])

        cursor.execute(
            """
            INSERT INTO users
                (full_name, email, phone, password, role, account_status)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            """,
            (
                registration["fullname"],
                registration["email"],
                registration["phone"],
                hashed_password,
                "nursery",
                "Active",
            )
        )
        db.commit()

        session.pop("registration", None)
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    except Exception as e:
        safe_rollback()
        print("OTP REGISTRATION ERROR:", type(e).__name__, str(e))
        flash("Registration failed. Please try again.", "error")
        return redirect(url_for("register"))


# =========================================================
# RESEND REGISTRATION OTP
# =========================================================

@app.route("/resend-otp")
def resend_otp():
    registration = session.get("registration")

    if not registration:
        flash("Registration session expired. Please register again.", "error")
        return redirect(url_for("register"))

    otp = str(random.randint(100000, 999999))
    registration["otp"] = otp
    registration["otp_created"] = datetime.now().isoformat()
    registration["otp_attempts"] = 0
    session["registration"] = registration

    try:
        msg = Message(
            subject="GreenTender - New OTP",
            recipients=[registration["email"]]
        )
        msg.body = f"""Hello {registration['fullname']},

Your new GreenTender verification OTP is: {otp}

This OTP is valid for 5 minutes.

Regards,
GreenTender Team
"""
        mail.send(msg)
        flash("A new OTP has been sent to your email.", "success")
    except Exception as e:
        print("RESEND OTP ERROR:", type(e).__name__, str(e))
        flash("Unable to resend OTP. Please try again.", "error")

    return redirect(url_for("verify_otp"))


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Please enter your email and password.", "error")
        return redirect(url_for("login"))

    try:
        cursor.execute(
            "SELECT * FROM users WHERE LOWER(email)=%s",
            (email,)
        )
        user = cursor.fetchone()

        if user is None:
            flash("Email not registered.", "error")
            return redirect(url_for("login"))

        if user["account_status"] != "Active":
            flash("Your account is not active. Please complete email verification.", "error")
            return redirect(url_for("login"))

        try:
            valid_password = check_password_hash(user["password"], password)
        except (ValueError, TypeError):
            valid_password = False

        if not valid_password:
            flash("Incorrect password.", "error")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["user_id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        flash("Login successful!", "success")

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("nursery.dashboard"))

    except Exception as e:
        safe_rollback()
        print("LOGIN ERROR:", type(e).__name__, str(e))
        flash("Unable to login. Please try again.", "error")
        return redirect(url_for("login"))


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin-dashboard")
def admin_dashboard():
    if not admin_required():
        flash("Please login as administrator.", "error")
        return redirect(url_for("login"))

    try:
        # -----------------------------
        # STATISTICS
        # -----------------------------
        cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role='nursery'")
        total_users = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM nursery_profiles")
        total_nurseries = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM nursery_profiles WHERE verification_status='Pending'")
        pending_nurseries = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM nursery_profiles WHERE verification_status='Verified'")
        verified_nurseries = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM tenders WHERE status='Open'")
        active_tenders = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM quotations")
        total_quotations = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM quotations WHERE status='Pending'")
        pending_quotations = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM quotations WHERE status='Approved'")
        approved_quotations = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) AS c FROM quotations WHERE status='Rejected'")
        rejected_quotations = cursor.fetchone()["c"]

        # -----------------------------
        # NURSERIES
        # -----------------------------
        cursor.execute(
            """
            SELECT np.*, u.email, u.phone
            FROM nursery_profiles np
            JOIN users u ON u.user_id=np.user_id
            ORDER BY np.created_at DESC
            """
        )
        nurseries = cursor.fetchall()

        # -----------------------------
        # TENDERS
        # -----------------------------
        cursor.execute(
            """
            SELECT
                t.*,
                (
                    SELECT COUNT(*)
                    FROM quotations q
                    WHERE q.tender_id=t.tender_id
                ) AS quotation_count
            FROM tenders t
            ORDER BY t.tender_id DESC
            """
        )
        tenders = cursor.fetchall()

        # -----------------------------
        # QUOTATIONS
        # -----------------------------
        cursor.execute(
            """
            SELECT
                q.*,
                t.title AS tender_title,
                t.estimated_budget,
                np.nursery_name,
                np.owner_name,
                np.registration_number
            FROM quotations q
            JOIN tenders t ON t.tender_id=q.tender_id
            JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
            ORDER BY q.submitted_at DESC
            """
        )
        quotations = cursor.fetchall()

        # -----------------------------
        # AI BID SCORING
        # -----------------------------
        # Score every quotation against the other quotations on
        # the SAME tender, then map quotation_id -> AI result so
        # the dashboard table can show an AI Score / recommendation
        # without changing how `quotations` is used elsewhere.
        quotations_by_tender = {}
        for q in quotations:
            quotations_by_tender.setdefault(q["tender_id"], []).append(q)

        tenders_by_id = {t["tender_id"]: t for t in tenders}

        ai_scores_by_quotation_id = {}
        for tender_id, tender_quotations in quotations_by_tender.items():
            tender_row = tenders_by_id.get(tender_id, {})
            ranked = rank_quotations_for_tender(tender_row, tender_quotations)
            for r in ranked:
                ai_scores_by_quotation_id[r["quotation_id"]] = r

        for q in quotations:
            ai_result = ai_scores_by_quotation_id.get(q["quotation_id"])
            if ai_result:
                q["ai_score"] = ai_result["ai_score"]
                q["ai_recommendation"] = ai_result["ai_recommendation"]
                q["ai_rank"] = ai_result["ai_rank"]
            else:
                q["ai_score"] = None
                q["ai_recommendation"] = None
                q["ai_rank"] = None

        # -----------------------------
        # DOCUMENTS
        # -----------------------------
        cursor.execute(
            """
            SELECT d.*, np.nursery_name
            FROM documents d
            JOIN nursery_profiles np ON np.nursery_id=d.nursery_id
            ORDER BY d.uploaded_at DESC
            """
        )
        documents = cursor.fetchall()

        # -----------------------------
        # REMARKS
        # -----------------------------
        cursor.execute(
            """
            SELECT
                qr.*,
                q.quotation_id,
                np.nursery_name,
                u.full_name AS admin_name
            FROM quotation_remarks qr
            JOIN quotations q ON q.quotation_id=qr.quotation_id
            JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
            LEFT JOIN users u ON u.user_id=qr.admin_id
            ORDER BY qr.remarked_at DESC
            """
        )
        remarks = cursor.fetchall()

        # -----------------------------
        # ADMIN NOTIFICATIONS
        # -----------------------------
        cursor.execute(
            """
            SELECT *
            FROM notifications
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (session["user_id"],)
        )
        notifications = cursor.fetchall()

        cursor.execute(
            """
            SELECT COUNT(*) AS c
            FROM notifications
            WHERE user_id=%s AND is_read=0
            """,
            (session["user_id"],)
        )
        unread_notifications = cursor.fetchone()["c"]

        return render_template(
            "admin_dashboard.html",
            name=session.get("full_name", "System Admin"),
            total_users=total_users,
            total_nurseries=total_nurseries,
            pending_nurseries=pending_nurseries,
            verified_nurseries=verified_nurseries,
            active_tenders=active_tenders,
            total_quotations=total_quotations,
            pending_quotations=pending_quotations,
            approved_quotations=approved_quotations,
            rejected_quotations=rejected_quotations,
            nurseries=nurseries,
            tenders=tenders,
            quotations=quotations,
            documents=documents,
            remarks=remarks,
            notifications=notifications,
            unread_notifications=unread_notifications
        )

    except Exception as e:
        safe_rollback()
        print("ADMIN DASHBOARD ERROR:", type(e).__name__, str(e))
        flash("Unable to load the Admin Dashboard. Check the terminal.", "error")

        return render_template(
            "admin_dashboard.html",
            name=session.get("full_name", "System Admin"),
            total_users=0,
            total_nurseries=0,
            pending_nurseries=0,
            verified_nurseries=0,
            active_tenders=0,
            total_quotations=0,
            pending_quotations=0,
            approved_quotations=0,
            rejected_quotations=0,
            nurseries=[],
            tenders=[],
            quotations=[],
            documents=[],
            remarks=[],
            notifications=[],
            unread_notifications=0
        )


# =========================================================
# ADMIN - NURSERY VERIFICATION
# =========================================================

@app.route("/admin/nursery/<int:nursery_id>/verify", methods=["POST"])
def verify_nursery(nursery_id):
    if not admin_required():
        return redirect(url_for("login"))

    try:
        cursor.execute(
            "SELECT user_id FROM nursery_profiles WHERE nursery_id=%s",
            (nursery_id,)
        )
        nursery = cursor.fetchone()

        if not nursery:
            flash("Nursery not found.", "error")
            return admin_redirect()

        cursor.execute(
            """
            UPDATE nursery_profiles
            SET verification_status='Verified'
            WHERE nursery_id=%s
            """,
            (nursery_id,)
        )

        cursor.execute(
            """
            INSERT INTO notifications(user_id, title, message)
            VALUES(%s, %s, %s)
            """,
            (
                nursery["user_id"],
                "Nursery Verified",
                "Your nursery profile has been verified by the administrator."
            )
        )

        db.commit()
        flash("Nursery verified successfully.", "success")

    except Exception as e:
        safe_rollback()
        print("VERIFY NURSERY ERROR:", type(e).__name__, str(e))
        flash("Unable to verify nursery.", "error")

    return admin_redirect()


@app.route("/admin/nursery/<int:nursery_id>/reject", methods=["POST"])
def reject_nursery(nursery_id):
    if not admin_required():
        return redirect(url_for("login"))

    try:
        cursor.execute(
            "SELECT user_id FROM nursery_profiles WHERE nursery_id=%s",
            (nursery_id,)
        )
        nursery = cursor.fetchone()

        if not nursery:
            flash("Nursery not found.", "error")
            return admin_redirect()

        cursor.execute(
            """
            UPDATE nursery_profiles
            SET verification_status='Rejected'
            WHERE nursery_id=%s
            """,
            (nursery_id,)
        )

        cursor.execute(
            """
            INSERT INTO notifications(user_id, title, message)
            VALUES(%s, %s, %s)
            """,
            (
                nursery["user_id"],
                "Nursery Verification Rejected",
                "Your nursery profile verification was rejected by the administrator."
            )
        )

        db.commit()
        flash("Nursery rejected successfully.", "success")

    except Exception as e:
        safe_rollback()
        print("REJECT NURSERY ERROR:", type(e).__name__, str(e))
        flash("Unable to reject nursery.", "error")

    return admin_redirect()


# =========================================================
# ADMIN - CREATE TENDER
# =========================================================

@app.route("/admin/tender/create", methods=["POST"])
def create_tender():
    if not admin_required():
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    road_name = request.form.get("road_name", "").strip()
    plant_type = request.form.get("plant_type", "").strip()
    quantity_required = request.form.get("quantity_required", "").strip()
    estimated_budget = request.form.get("estimated_budget", "").strip()
    publish_date = request.form.get("publish_date", "").strip()
    closing_date = request.form.get("closing_date", "").strip()

    if not all([
        title, description, location, road_name, plant_type,
        quantity_required, estimated_budget, publish_date, closing_date
    ]):
        flash("Please fill in all tender fields.", "error")
        return admin_redirect()

    try:
        quantity = int(quantity_required)
        budget = float(estimated_budget)

        if quantity <= 0 or budget <= 0:
            raise ValueError

        if closing_date < publish_date:
            flash("Closing date cannot be before publish date.", "error")
            return admin_redirect()

    except ValueError:
        flash("Quantity and budget must be valid positive numbers.", "error")
        return admin_redirect()

    try:
        cursor.execute(
            """
            INSERT INTO tenders
            (
                title, description, location, road_name, plant_type,
                quantity_required, estimated_budget, publish_date,
                closing_date, status, admin_id
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Open',%s)
            """,
            (
                title, description, location, road_name, plant_type,
                quantity, budget, publish_date, closing_date,
                session["user_id"]
            )
        )

        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE role='nursery' AND account_status='Active'
            """
        )
        nursery_users = cursor.fetchall()

        for user in nursery_users:
            cursor.execute(
                """
                INSERT INTO notifications(user_id, title, message)
                VALUES(%s, %s, %s)
                """,
                (
                    user["user_id"],
                    "New Tender Published",
                    f"A new tender '{title}' is available on GreenTender."
                )
            )

        db.commit()
        flash("Tender created and published successfully.", "success")

    except Exception as e:
        safe_rollback()
        print("CREATE TENDER ERROR:", type(e).__name__, str(e))
        flash("Unable to create tender.", "error")

    return admin_redirect()


# =========================================================
# ADMIN - CLOSE / DELETE TENDER
# =========================================================

@app.route("/admin/tender/<int:tender_id>/close", methods=["POST"])
def close_tender(tender_id):
    if not admin_required():
        return redirect(url_for("login"))

    try:
        cursor.execute(
            "UPDATE tenders SET status='Closed' WHERE tender_id=%s",
            (tender_id,)
        )
        db.commit()
        flash("Tender closed successfully.", "success")

    except Exception as e:
        safe_rollback()
        print("CLOSE TENDER ERROR:", type(e).__name__, str(e))
        flash("Unable to close tender.", "error")

    return admin_redirect()


@app.route("/admin/tender/<int:tender_id>/delete", methods=["POST"])
def delete_tender(tender_id):
    if not admin_required():
        return redirect(url_for("login"))

    try:
        cursor.execute(
            "DELETE FROM tenders WHERE tender_id=%s",
            (tender_id,)
        )
        db.commit()
        flash("Tender deleted successfully.", "success")

    except Exception as e:
        safe_rollback()
        print("DELETE TENDER ERROR:", type(e).__name__, str(e))
        flash("Tender could not be deleted because related records may exist.", "error")

    return admin_redirect()


# =========================================================
# ADMIN - AI BID RANKING
# =========================================================

@app.route("/admin/tender/<int:tender_id>/ai-ranking")
def ai_tender_ranking(tender_id):
    """
    Runs the AI bid evaluation engine over every quotation
    submitted for this tender and shows them ranked best-first,
    each with an AI Score (0-100), a recommendation label, and
    a breakdown of how the score was built (price, delivery,
    quantity match, nursery trust, description quality).
    """
    if not admin_required():
        flash("Please login as administrator.", "error")
        return redirect(url_for("login"))

    try:
        cursor.execute(
            "SELECT * FROM tenders WHERE tender_id=%s",
            (tender_id,)
        )
        tender = cursor.fetchone()

        if not tender:
            flash("Tender not found.", "error")
            return admin_redirect()

        cursor.execute(
            """
            SELECT
                q.*,
                np.nursery_name,
                np.owner_name,
                np.registration_number,
                np.verification_status
            FROM quotations q
            JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
            WHERE q.tender_id=%s
            """,
            (tender_id,)
        )
        quotations = cursor.fetchall()

        ranked_quotations = rank_quotations_for_tender(tender, quotations)
        summary = best_bid_summary(ranked_quotations)

        return render_template(
            "ai_ranking.html",
            name=session.get("full_name", "System Admin"),
            tender=tender,
            ranked_quotations=ranked_quotations,
            summary=summary
        )

    except Exception as e:
        safe_rollback()
        print("AI RANKING ERROR:", type(e).__name__, str(e))
        flash("Unable to run AI bid evaluation for this tender.", "error")
        return admin_redirect()


# =========================================================
# ADMIN - APPROVE / REJECT QUOTATION
# =========================================================

@app.route("/admin/quotation/<int:quotation_id>/approve", methods=["POST"])
def approve_quotation(quotation_id):
    if not admin_required():
        return redirect(url_for("login"))

    remark = request.form.get("remark", "").strip()

    try:
        cursor.execute(
            """
            SELECT np.user_id, t.title
            FROM quotations q
            JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
            JOIN tenders t ON t.tender_id=q.tender_id
            WHERE q.quotation_id=%s
            """,
            (quotation_id,)
        )
        quotation = cursor.fetchone()

        if not quotation:
            flash("Quotation not found.", "error")
            return admin_redirect()

        cursor.execute(
            "UPDATE quotations SET status='Approved' WHERE quotation_id=%s",
            (quotation_id,)
        )

        if remark:
            save_quotation_remark(quotation_id, remark)

        cursor.execute(
            """
            INSERT INTO notifications(user_id, title, message)
            VALUES(%s, %s, %s)
            """,
            (
                quotation["user_id"],
                "Quotation Approved",
                f"Your quotation for '{quotation['title']}' has been approved."
            )
        )

        db.commit()
        flash("Quotation approved successfully.", "success")

    except Exception as e:
        safe_rollback()
        print("APPROVE QUOTATION ERROR:", type(e).__name__, str(e))
        flash("Unable to approve quotation.", "error")

    return admin_redirect()


@app.route("/admin/quotation/<int:quotation_id>/reject", methods=["POST"])
def reject_quotation(quotation_id):
    if not admin_required():
        return redirect(url_for("login"))

    remark = request.form.get("remark", "").strip()

    if not remark:
        flash("A rejection remark is required.", "error")
        return admin_redirect()

    try:
        cursor.execute(
            """
            SELECT np.user_id, t.title
            FROM quotations q
            JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
            JOIN tenders t ON t.tender_id=q.tender_id
            WHERE q.quotation_id=%s
            """,
            (quotation_id,)
        )
        quotation = cursor.fetchone()

        if not quotation:
            flash("Quotation not found.", "error")
            return admin_redirect()

        cursor.execute(
            "UPDATE quotations SET status='Rejected' WHERE quotation_id=%s",
            (quotation_id,)
        )

        save_quotation_remark(quotation_id, remark)

        cursor.execute(
            """
            INSERT INTO notifications(user_id, title, message)
            VALUES(%s, %s, %s)
            """,
            (
                quotation["user_id"],
                "Quotation Rejected",
                f"Your quotation for '{quotation['title']}' was rejected. Please check the remark."
            )
        )

        db.commit()
        flash("Quotation rejected and remark saved.", "success")

    except Exception as e:
        safe_rollback()
        print("REJECT QUOTATION ERROR:", type(e).__name__, str(e))
        flash("Unable to reject quotation.", "error")

    return admin_redirect()


# =========================================================
# ADMIN - NOTIFICATIONS
# =========================================================

@app.route("/admin/notification/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    if not admin_required():
        return redirect(url_for("login"))

    try:
        cursor.execute(
            """
            UPDATE notifications
            SET is_read=1
            WHERE notification_id=%s AND user_id=%s
            """,
            (notification_id, session["user_id"])
        )
        db.commit()
    except Exception as e:
        safe_rollback()
        print("MARK NOTIFICATION ERROR:", type(e).__name__, str(e))

    return admin_redirect()


@app.route("/admin/notifications/read-all", methods=["POST"])
def read_all_notifications():
    if not admin_required():
        return redirect(url_for("login"))

    try:
        cursor.execute(
            "UPDATE notifications SET is_read=1 WHERE user_id=%s",
            (session["user_id"],)
        )
        db.commit()
        flash("All notifications marked as read.", "success")
    except Exception as e:
        safe_rollback()
        print("READ ALL NOTIFICATIONS ERROR:", type(e).__name__, str(e))
        flash("Unable to update notifications.", "error")

    return admin_redirect()


# =========================================================
# FORGOT PASSWORD - REQUEST OTP
# =========================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")

    email = request.form.get("email", "").strip().lower()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not email:
        flash("Please enter your registered email.", "error")
        return render_template("forgot_password.html")

    if not new_password or not confirm_password:
        flash("Please enter and confirm your new password.", "error")
        return render_template("forgot_password.html")

    if new_password != confirm_password:
        flash("New password and confirm password do not match.", "error")
        return render_template("forgot_password.html")

    if len(new_password) < 6:
        flash("Password must contain at least 6 characters.", "error")
        return render_template("forgot_password.html")

    try:
        cursor.execute(
            """
            SELECT user_id, full_name, email
            FROM users
            WHERE LOWER(email)=%s
            """,
            (email,)
        )
        user = cursor.fetchone()

        if not user:
            flash("No account is registered with this email address.", "error")
            return render_template("forgot_password.html")

        otp = str(random.randint(100000, 999999))
        hashed_password = generate_password_hash(new_password)

        session["forgot_password"] = {
            "user_id": user["user_id"],
            "email": user["email"],
            "hashed_password": hashed_password,
            "otp": otp,
            "otp_created": datetime.now().isoformat(),
            "otp_attempts": 0,
        }

        msg = Message(
            subject="GreenTender - Password Reset OTP",
            recipients=[user["email"]]
        )
        msg.body = f"""Hello {user['full_name']},

You requested to reset your GreenTender password.

Your OTP is: {otp}

This OTP is valid for 5 minutes.
If you did not request a password reset, please ignore this email.

Regards,
GreenTender Team
"""
        mail.send(msg)

        flash("Password reset OTP has been sent to your email.", "success")
        return redirect(url_for("verify_forgot_otp"))

    except Exception as e:
        safe_rollback()
        session.pop("forgot_password", None)
        print("FORGOT PASSWORD ERROR:", type(e).__name__, str(e))
        flash("Unable to send OTP. Please check your email configuration and try again.", "error")
        return render_template("forgot_password.html")


# =========================================================
# FORGOT PASSWORD - VERIFY OTP
# =========================================================

@app.route("/verify-forgot-otp", methods=["GET", "POST"])
def verify_forgot_otp():
    reset_data = session.get("forgot_password")

    if not reset_data:
        flash("Password reset session expired. Please try again.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "GET":
        return render_template(
            "verify_forgot_otp.html",
            email=reset_data["email"]
        )

    entered_otp = request.form.get("otp", "").strip()

    try:
        otp_created = datetime.fromisoformat(reset_data["otp_created"])
    except (KeyError, ValueError, TypeError):
        session.pop("forgot_password", None)
        flash("Invalid password reset session. Please try again.", "error")
        return redirect(url_for("forgot_password"))

    if datetime.now() > otp_created + timedelta(minutes=5):
        session.pop("forgot_password", None)
        flash("OTP has expired. Please request a new password reset.", "error")
        return redirect(url_for("forgot_password"))

    reset_data["otp_attempts"] = int(reset_data.get("otp_attempts", 0)) + 1
    session["forgot_password"] = reset_data

    if reset_data["otp_attempts"] > 3:
        session.pop("forgot_password", None)
        flash("Maximum OTP attempts exceeded. Please request a new OTP.", "error")
        return redirect(url_for("forgot_password"))

    if entered_otp != str(reset_data["otp"]):
        remaining = 3 - reset_data["otp_attempts"]
        flash(f"Invalid OTP. {remaining} attempt(s) remaining.", "error")
        return render_template(
            "verify_forgot_otp.html",
            email=reset_data["email"]
        )

    try:
        cursor.execute(
            "UPDATE users SET password=%s WHERE user_id=%s",
            (reset_data["hashed_password"], reset_data["user_id"])
        )
        db.commit()

        session.pop("forgot_password", None)
        flash("Password reset successfully. Please login with your new password.", "success")
        return redirect(url_for("login"))

    except Exception as e:
        safe_rollback()
        print("VERIFY FORGOT OTP ERROR:", type(e).__name__, str(e))
        flash("Unable to update the password. Please try again.", "error")
        return render_template(
            "verify_forgot_otp.html",
            email=reset_data["email"]
        )


# =========================================================
# TEST EMAIL - ADMIN ONLY
# =========================================================

@app.route("/test-mail")
def test_mail():
    if not admin_required():
        flash("Unauthorized Access.", "error")
        return redirect(url_for("login"))

    recipient = app.config.get("MAIL_USERNAME")

    if not recipient:
        return "MAIL_USERNAME is not configured.", 500

    try:
        msg = Message(
            subject="GreenTender Test Email",
            recipients=[recipient]
        )
        msg.body = "Flask-Mail configuration is working successfully."
        mail.send(msg)
        return "Mail Sent Successfully!"
    except Exception as e:
        print("TEST MAIL ERROR:", type(e).__name__, str(e))
        return "Unable to send test mail. Check the terminal.", 500


# =========================================================
# LOGOUT
# =========================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    from flask import send_from_directory
    upload_root = os.path.join(app.root_path, "uploads")
    return send_from_directory(upload_root, filename)




# =========================================================
# ADMIN SECTION PAGES (separate navigation destinations)
# =========================================================
def _admin_page_guard():
    if not admin_required():
        flash("Please login as administrator.", "error")
        return redirect(url_for("login"))
    return None


@app.route("/admin/nurseries")
def admin_nurseries_page():
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("""
        SELECT np.*, u.email, u.phone, u.account_status
        FROM nursery_profiles np JOIN users u ON u.user_id=np.user_id
        ORDER BY np.created_at DESC
    """)
    return render_template("admin_nurseries.html", name=session.get("full_name","Admin"),
                           page_title="Nurseries", page_subtitle="Review and verify registered nurseries.",
                           active="nurseries", nurseries=cursor.fetchall())


@app.route("/admin/tenders")
def admin_tenders_page():
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("""
        SELECT t.*, (SELECT COUNT(*) FROM quotations q WHERE q.tender_id=t.tender_id) AS quotation_count
        FROM tenders t ORDER BY t.tender_id DESC
    """)
    return render_template("admin_tenders.html", name=session.get("full_name","Admin"),
                           page_title="Tenders", page_subtitle="Create and manage plantation tenders.",
                           active="tenders", tenders=cursor.fetchall())


@app.route("/admin/quotations")
def admin_quotations_page():
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("""
        SELECT q.*, t.title AS tender_title, t.estimated_budget,
               np.nursery_name, np.owner_name, np.registration_number
        FROM quotations q JOIN tenders t ON t.tender_id=q.tender_id
        JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
        ORDER BY q.submitted_at DESC
    """)
    return render_template("admin_quotations.html", name=session.get("full_name","Admin"),
                           page_title="Quotations", page_subtitle="Review nursery bids and decisions.",
                           active="quotations", quotations=cursor.fetchall())


@app.route("/admin/quotation/<int:quotation_id>/review")
def admin_quotation_details_page(quotation_id):
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("""
        SELECT q.*, t.title AS tender_title, t.estimated_budget,
               np.nursery_name, np.owner_name, np.registration_number
        FROM quotations q JOIN tenders t ON t.tender_id=q.tender_id
        JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
        WHERE q.quotation_id=%s
    """, (quotation_id,))
    q=cursor.fetchone()
    if not q:
        flash("Quotation not found.", "error")
        return redirect(url_for("admin_quotations_page"))
    return render_template("admin_quotation_detail.html", name=session.get("full_name","Admin"),
                           page_title="Quotation Review", page_subtitle="Review quotation details and take action.",
                           active="quotations", q=q)


@app.route("/admin/documents")
def admin_documents_page():
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("""
        SELECT d.*, np.nursery_name FROM documents d
        JOIN nursery_profiles np ON np.nursery_id=d.nursery_id
        ORDER BY d.uploaded_at DESC
    """)
    return render_template("admin_documents.html", name=session.get("full_name","Admin"),
                           page_title="Documents", page_subtitle="Review uploaded nursery documents.",
                           active="documents", documents=cursor.fetchall())


@app.route("/admin/remarks")
def admin_remarks_page():
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("""
        SELECT qr.*, q.quotation_id, np.nursery_name, u.full_name AS admin_name
        FROM quotation_remarks qr JOIN quotations q ON q.quotation_id=qr.quotation_id
        JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
        LEFT JOIN users u ON u.user_id=qr.admin_id
        ORDER BY qr.remarked_at DESC
    """)
    return render_template("admin_remarks.html", name=session.get("full_name","Admin"),
                           page_title="Remarks", page_subtitle="Quotation review remarks.",
                           active="remarks", remarks=cursor.fetchall())


@app.route("/admin/notifications")
def admin_notifications_page():
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC",
                   (session["user_id"],))
    return render_template("admin_notifications.html", name=session.get("full_name","Admin"),
                           page_title="Notifications", page_subtitle="Recent platform updates.",
                           active="notifications", notifications=cursor.fetchall())


@app.route("/admin/deliveries")
def admin_deliveries_page():
    guard = _admin_page_guard()
    if guard: return guard
    cursor.execute("""
        SELECT q.quotation_id, q.quantity_available, q.delivery_status,
               q.expected_delivery_date, q.actual_delivery_date,
               q.delivery_remark, q.delivery_updated_at,
               t.title, t.location, np.nursery_name, np.owner_name
        FROM quotations q
        JOIN tenders t ON t.tender_id=q.tender_id
        JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
        WHERE q.status='Approved'
        ORDER BY q.delivery_updated_at DESC, q.submitted_at DESC
    """)
    return render_template("admin_deliveries.html", name=session.get("full_name","Admin"),
                           page_title="Deliveries", page_subtitle="Monitor approved work and delivery status.",
                           active="deliveries", deliveries=cursor.fetchall())


@app.route("/admin/delivery/<int:quotation_id>/update", methods=["POST"])
def admin_update_delivery(quotation_id):
    """Allow an administrator to update delivery details for approved quotations."""
    guard = _admin_page_guard()
    if guard:
        return guard

    delivery_status = request.form.get("delivery_status", "").strip()
    expected_date = request.form.get("expected_delivery_date", "").strip() or None
    actual_date = request.form.get("actual_delivery_date", "").strip() or None
    remark = request.form.get("delivery_remark", "").strip() or None

    if delivery_status not in ("Pending", "In Progress", "Delivered"):
        flash("Select a valid delivery status.", "error")
        return redirect(url_for("admin_deliveries_page"))

    # Validate dates instead of relying only on browser-side date inputs.
    try:
        if expected_date:
            datetime.strptime(expected_date, "%Y-%m-%d")
        if actual_date:
            datetime.strptime(actual_date, "%Y-%m-%d")
    except ValueError:
        flash("Enter valid delivery dates.", "error")
        return redirect(url_for("admin_deliveries_page"))

    if delivery_status == "Delivered" and not actual_date:
        flash("Actual delivery date is required when status is Delivered.", "error")
        return redirect(url_for("admin_deliveries_page"))
    if delivery_status != "Delivered":
        actual_date = None

    try:
        cursor.execute(
            """
            SELECT np.user_id, np.nursery_name, t.title
            FROM quotations q
            JOIN nursery_profiles np ON np.nursery_id=q.nursery_id
            JOIN tenders t ON t.tender_id=q.tender_id
            WHERE q.quotation_id=%s AND q.status='Approved'
            """,
            (quotation_id,)
        )
        approved_work = cursor.fetchone()
        if not approved_work:
            flash("Approved quotation not found.", "error")
            return redirect(url_for("admin_deliveries_page"))

        cursor.execute(
            """
            UPDATE quotations
            SET delivery_status=%s,
                expected_delivery_date=%s,
                actual_delivery_date=%s,
                delivery_remark=%s,
                delivery_updated_at=CURRENT_TIMESTAMP
            WHERE quotation_id=%s AND status='Approved'
            """,
            (delivery_status, expected_date, actual_date, remark, quotation_id)
        )

        cursor.execute(
            """
            INSERT INTO notifications (user_id, title, message)
            VALUES (%s, %s, %s)
            """,
            (
                approved_work["user_id"],
                "Delivery Status Updated",
                f"The administrator updated delivery for '{approved_work['title']}' "
                f"(quotation #{quotation_id}) to {delivery_status}."
            )
        )
        db.commit()
        flash("Delivery details updated successfully.", "success")
    except Exception as exc:
        safe_rollback()
        print("ADMIN DELIVERY UPDATE ERROR:", type(exc).__name__, str(exc))
        flash("Unable to update delivery details. Check the terminal for details.", "error")

    return redirect(url_for("admin_deliveries_page"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))




if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
