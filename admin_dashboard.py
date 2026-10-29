# ============================================================
# GreenTender - ADMIN DASHBOARD BACKEND
# ============================================================

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from db import db, cursor


# ------------------------------------------------------------
# BLUEPRINT
# ------------------------------------------------------------

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# ADMIN ACCESS CHECK
# ============================================================

def admin_required():

    if "user_id" not in session:
        flash("Please login first.", "error")
        return False

    if session.get("role") != "admin":
        flash("Unauthorized Access.", "error")
        return False

    return True


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route("/dashboard")
def dashboard():

    if not admin_required():
        return redirect(url_for("login"))

    try:

        # ----------------------------------------------------
        # TOTAL NURSERY USERS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total_users
            FROM users
            WHERE role = 'nursery'
        """)

        total_users = cursor.fetchone()["total_users"]


        # ----------------------------------------------------
        # REGISTERED NURSERIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total_nurseries
            FROM nursery_profiles
        """)

        total_nurseries = cursor.fetchone()["total_nurseries"]


        # ----------------------------------------------------
        # ACTIVE TENDERS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS active_tenders
            FROM tenders
            WHERE status = 'Open'
        """)

        active_tenders = cursor.fetchone()["active_tenders"]


        # ----------------------------------------------------
        # TOTAL QUOTATIONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total_quotations
            FROM quotations
        """)

        total_quotations = cursor.fetchone()["total_quotations"]


        # ----------------------------------------------------
        # PENDING QUOTATIONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS pending_quotations
            FROM quotations
            WHERE status = 'Pending'
        """)

        pending_quotations = cursor.fetchone()["pending_quotations"]


        # ----------------------------------------------------
        # APPROVED QUOTATIONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS approved_quotations
            FROM quotations
            WHERE status = 'Approved'
        """)

        approved_quotations = cursor.fetchone()["approved_quotations"]


        # ----------------------------------------------------
        # REJECTED QUOTATIONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS rejected_quotations
            FROM quotations
            WHERE status = 'Rejected'
        """)

        rejected_quotations = cursor.fetchone()["rejected_quotations"]


        # ----------------------------------------------------
        # PENDING NURSERY VERIFICATIONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS pending_verifications
            FROM nursery_profiles
            WHERE verification_status = 'Pending'
        """)

        pending_verifications = (
            cursor.fetchone()["pending_verifications"]
        )


        # ----------------------------------------------------
        # VERIFIED NURSERIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS verified_nurseries
            FROM nursery_profiles
            WHERE verification_status = 'Verified'
        """)

        verified_nurseries = (
            cursor.fetchone()["verified_nurseries"]
        )


        # ----------------------------------------------------
        # RECENT TENDERS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                tender_id,
                title,
                description,
                location,
                road_name,
                plant_type,
                quantity_required,
                estimated_budget,
                publish_date,
                closing_date,
                status
            FROM tenders
            ORDER BY tender_id DESC
            LIMIT 5
        """)

        recent_tenders = cursor.fetchall()


        # ----------------------------------------------------
        # RECENT QUOTATIONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                q.quotation_id,
                q.tender_id,
                q.nursery_id,
                q.quoted_price,
                q.quantity_available,
                q.delivery_days,
                q.status,
                q.submitted_at,

                t.title AS tender_title,

                np.nursery_name,
                np.owner_name

            FROM quotations q

            INNER JOIN tenders t
                ON q.tender_id = t.tender_id

            INNER JOIN nursery_profiles np
                ON q.nursery_id = np.nursery_id

            ORDER BY q.submitted_at DESC

            LIMIT 5
        """)

        recent_quotations = cursor.fetchall()


        # ----------------------------------------------------
        # RECENT NURSERIES
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                nursery_id,
                user_id,
                nursery_name,
                owner_name,
                registration_number,
                address,
                state,
                city,
                pincode,
                verification_status,
                created_at

            FROM nursery_profiles

            ORDER BY created_at DESC

            LIMIT 5
        """)

        recent_nurseries = cursor.fetchall()


        # ----------------------------------------------------
        # ADMIN NOTIFICATIONS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT
                notification_id,
                title,
                message,
                is_read,
                created_at

            FROM notifications

            WHERE user_id = %s

            ORDER BY created_at DESC

            LIMIT 5
        """, (session["user_id"],))

        recent_notifications = cursor.fetchall()


        # ----------------------------------------------------
        # UNREAD NOTIFICATION COUNT
        # ----------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS unread_count

            FROM notifications

            WHERE user_id = %s
            AND is_read = 0
        """, (session["user_id"],))

        unread_notifications = (
            cursor.fetchone()["unread_count"]
        )


        # ----------------------------------------------------
        # SEND DATA TO TEMPLATE
        # ----------------------------------------------------

        return render_template(
            "admin_dashboard.html",

            name=session.get(
                "full_name",
                "System Admin"
            ),

            total_users=total_users,

            total_nurseries=total_nurseries,

            active_tenders=active_tenders,

            total_quotations=total_quotations,

            pending_quotations=pending_quotations,

            approved_quotations=approved_quotations,

            rejected_quotations=rejected_quotations,

            pending_verifications=pending_verifications,

            verified_nurseries=verified_nurseries,

            recent_tenders=recent_tenders,

            recent_quotations=recent_quotations,

            recent_nurseries=recent_nurseries,

            recent_notifications=recent_notifications,

            unread_notifications=unread_notifications
        )

    except Exception as e:

        print(
            "ADMIN DASHBOARD ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to load Admin Dashboard.",
            "error"
        )

        return render_template(
            "admin_dashboard.html",

            name=session.get(
                "full_name",
                "System Admin"
            ),

            total_users=0,
            total_nurseries=0,
            active_tenders=0,
            total_quotations=0,
            pending_quotations=0,
            approved_quotations=0,
            rejected_quotations=0,
            pending_verifications=0,
            verified_nurseries=0,
            recent_tenders=[],
            recent_quotations=[],
            recent_nurseries=[],
            recent_notifications=[],
            unread_notifications=0
        )


# ============================================================
# VIEW ALL NURSERIES
# ============================================================

@admin_bp.route("/nurseries")
def nurseries():

    if not admin_required():
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT
            np.nursery_id,
            np.user_id,
            np.nursery_name,
            np.owner_name,
            np.registration_number,
            np.address,
            np.state,
            np.city,
            np.pincode,
            np.verification_status,
            np.created_at,

            u.email,
            u.phone,
            u.account_status

        FROM nursery_profiles np

        INNER JOIN users u
            ON np.user_id = u.user_id

        ORDER BY np.nursery_id DESC
    """)

    nurseries = cursor.fetchall()

    return render_template(
        "admin_nurseries.html",
        nurseries=nurseries
    )


# ============================================================
# VERIFY NURSERY
# ============================================================

@admin_bp.route(
    "/nursery/<int:nursery_id>/verify",
    methods=["POST"]
)
def verify_nursery(nursery_id):

    if not admin_required():
        return redirect(url_for("login"))

    try:

        cursor.execute("""
            SELECT user_id
            FROM nursery_profiles
            WHERE nursery_id = %s
        """, (nursery_id,))

        nursery = cursor.fetchone()

        if not nursery:

            flash(
                "Nursery not found.",
                "error"
            )

            return redirect(
                url_for("admin.nurseries")
            )


        # ----------------------------------------------------
        # UPDATE NURSERY STATUS
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE nursery_profiles

            SET verification_status = 'Verified'

            WHERE nursery_id = %s
        """, (nursery_id,))


        # ----------------------------------------------------
        # USER NOTIFICATION
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO notifications
            (
                user_id,
                title,
                message
            )

            VALUES
            (
                %s,
                %s,
                %s
            )
        """, (
            nursery["user_id"],
            "Nursery Verified",
            "Your nursery profile has been verified by the administrator."
        ))


        db.commit()


        flash(
            "Nursery verified successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "NURSERY VERIFY ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to verify nursery.",
            "error"
        )


    return redirect(
        url_for("admin.nurseries")
    )


# ============================================================
# REJECT NURSERY
# ============================================================

@admin_bp.route(
    "/nursery/<int:nursery_id>/reject",
    methods=["POST"]
)
def reject_nursery(nursery_id):

    if not admin_required():
        return redirect(url_for("login"))

    try:

        cursor.execute("""
            SELECT user_id
            FROM nursery_profiles
            WHERE nursery_id = %s
        """, (nursery_id,))

        nursery = cursor.fetchone()

        if not nursery:

            flash(
                "Nursery not found.",
                "error"
            )

            return redirect(
                url_for("admin.nurseries")
            )


        cursor.execute("""
            UPDATE nursery_profiles

            SET verification_status = 'Rejected'

            WHERE nursery_id = %s
        """, (nursery_id,))


        cursor.execute("""
            INSERT INTO notifications
            (
                user_id,
                title,
                message
            )

            VALUES
            (
                %s,
                %s,
                %s
            )
        """, (
            nursery["user_id"],
            "Nursery Verification Rejected",
            "Your nursery profile verification was rejected by the administrator."
        ))


        db.commit()


        flash(
            "Nursery rejected successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "NURSERY REJECT ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to reject nursery.",
            "error"
        )


    return redirect(
        url_for("admin.nurseries")
    )


# ============================================================
# VIEW DOCUMENTS
# ============================================================

@admin_bp.route("/documents")
def documents():

    if not admin_required():
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT
            d.document_id,
            d.nursery_id,
            d.document_type,
            d.file_url,
            d.uploaded_at,

            np.nursery_name,
            np.owner_name

        FROM documents d

        INNER JOIN nursery_profiles np
            ON d.nursery_id = np.nursery_id

        ORDER BY d.uploaded_at DESC
    """)

    documents = cursor.fetchall()

    return render_template(
        "admin_documents.html",
        documents=documents
    )


# ============================================================
# CREATE TENDER
# ============================================================

@admin_bp.route(
    "/tender/create",
    methods=["GET", "POST"]
)
def create_tender():

    if not admin_required():
        return redirect(url_for("login"))

    if request.method == "GET":

        return render_template(
            "create_tender.html"
        )


    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    road_name = request.form.get(
        "road_name",
        ""
    ).strip()

    plant_type = request.form.get(
        "plant_type",
        ""
    ).strip()

    quantity_required = request.form.get(
        "quantity_required",
        ""
    ).strip()

    estimated_budget = request.form.get(
        "estimated_budget",
        ""
    ).strip()

    publish_date = request.form.get(
        "publish_date",
        ""
    ).strip()

    closing_date = request.form.get(
        "closing_date",
        ""
    ).strip()


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not title:
        flash("Tender title is required.", "error")
        return redirect(url_for("admin.create_tender"))

    if not quantity_required:
        flash("Quantity is required.", "error")
        return redirect(url_for("admin.create_tender"))

    if not estimated_budget:
        flash("Estimated budget is required.", "error")
        return redirect(url_for("admin.create_tender"))

    if not publish_date:
        flash("Publish date is required.", "error")
        return redirect(url_for("admin.create_tender"))

    if not closing_date:
        flash("Closing date is required.", "error")
        return redirect(url_for("admin.create_tender"))


    try:

        cursor.execute("""
            INSERT INTO tenders
            (
                title,
                description,
                location,
                road_name,
                plant_type,
                quantity_required,
                estimated_budget,
                publish_date,
                closing_date,
                status,
                admin_id
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'Open',
                %s
            )
        """, (
            title,
            description,
            location,
            road_name,
            plant_type,
            quantity_required,
            estimated_budget,
            publish_date,
            closing_date,
            session["user_id"]
        ))


        tender_id = cursor.lastrowid


        # ----------------------------------------------------
        # NOTIFY ALL ACTIVE NURSERY USERS
        # ----------------------------------------------------

        cursor.execute("""
            SELECT user_id
            FROM users
            WHERE role = 'nursery'
            AND account_status = 'Active'
        """)

        nursery_users = cursor.fetchall()


        for user in nursery_users:

            cursor.execute("""
                INSERT INTO notifications
                (
                    user_id,
                    title,
                    message
                )

                VALUES
                (
                    %s,
                    %s,
                    %s
                )
            """, (
                user["user_id"],
                "New Tender Published",
                f"A new tender '{title}' has been published on GreenTender."
            ))


        db.commit()


        flash(
            "Tender created successfully.",
            "success"
        )

        return redirect(
            url_for("admin.tenders")
        )

    except Exception as e:

        db.rollback()

        print(
            "CREATE TENDER ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to create tender.",
            "error"
        )

        return redirect(
            url_for("admin.create_tender")
        )


# ============================================================
# VIEW ALL TENDERS
# ============================================================

@admin_bp.route("/tenders")
def tenders():

    if not admin_required():
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT
            tender_id,
            title,
            description,
            location,
            road_name,
            plant_type,
            quantity_required,
            estimated_budget,
            publish_date,
            closing_date,
            status

        FROM tenders

        ORDER BY tender_id DESC
    """)

    tenders = cursor.fetchall()

    return render_template(
        "admin_tenders.html",
        tenders=tenders
    )


# ============================================================
# CLOSE TENDER
# ============================================================

@admin_bp.route(
    "/tender/<int:tender_id>/close",
    methods=["POST"]
)
def close_tender(tender_id):

    if not admin_required():
        return redirect(url_for("login"))

    try:

        cursor.execute("""
            UPDATE tenders

            SET status = 'Closed'

            WHERE tender_id = %s
        """, (tender_id,))

        db.commit()


        flash(
            "Tender closed successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "CLOSE TENDER ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to close tender.",
            "error"
        )


    return redirect(
        url_for("admin.tenders")
    )


# ============================================================
# DELETE TENDER
# ============================================================

@admin_bp.route(
    "/tender/<int:tender_id>/delete",
    methods=["POST"]
)
def delete_tender(tender_id):

    if not admin_required():
        return redirect(url_for("login"))

    try:

        cursor.execute("""
            DELETE FROM tenders

            WHERE tender_id = %s
        """, (tender_id,))

        db.commit()


        flash(
            "Tender deleted successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "DELETE TENDER ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to delete tender. "
            "It may contain quotations.",
            "error"
        )


    return redirect(
        url_for("admin.tenders")
    )


# ============================================================
# VIEW ALL QUOTATIONS
# ============================================================

@admin_bp.route("/quotations")
def quotations():

    if not admin_required():
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT
            q.quotation_id,
            q.tender_id,
            q.nursery_id,
            q.quoted_price,
            q.quantity_available,
            q.delivery_days,
            q.plant_photo,
            q.quotation_description,
            q.status,
            q.submitted_at,

            t.title AS tender_title,
            t.estimated_budget,

            np.nursery_name,
            np.owner_name,
            np.registration_number

        FROM quotations q

        INNER JOIN tenders t
            ON q.tender_id = t.tender_id

        INNER JOIN nursery_profiles np
            ON q.nursery_id = np.nursery_id

        ORDER BY q.submitted_at DESC
    """)

    quotations = cursor.fetchall()

    return render_template(
        "admin_quotations.html",
        quotations=quotations
    )


# ============================================================
# VIEW QUOTATION DETAILS
# ============================================================

@admin_bp.route(
    "/quotation/<int:quotation_id>"
)
def quotation_details(quotation_id):

    if not admin_required():
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT
            q.*,

            t.title AS tender_title,
            t.description AS tender_description,
            t.location,
            t.road_name,
            t.plant_type,
            t.quantity_required,
            t.estimated_budget,
            t.closing_date,

            np.nursery_name,
            np.owner_name,
            np.registration_number,
            np.address,
            np.state,
            np.city,
            np.pincode,
            np.verification_status

        FROM quotations q

        INNER JOIN tenders t
            ON q.tender_id = t.tender_id

        INNER JOIN nursery_profiles np
            ON q.nursery_id = np.nursery_id

        WHERE q.quotation_id = %s
    """, (quotation_id,))

    quotation = cursor.fetchone()


    if not quotation:

        flash(
            "Quotation not found.",
            "error"
        )

        return redirect(
            url_for("admin.quotations")
        )


    # --------------------------------------------------------
    # DOCUMENTS
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            document_id,
            document_type,
            file_url,
            uploaded_at

        FROM documents

        WHERE nursery_id = %s

        ORDER BY uploaded_at DESC
    """, (quotation["nursery_id"],))

    documents = cursor.fetchall()


    # --------------------------------------------------------
    # REMARK
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            qr.remark_id,
            qr.remark,
            qr.remarked_at,
            qr.admin_id,

            u.full_name AS admin_name

        FROM quotation_remarks qr

        LEFT JOIN users u
            ON qr.admin_id = u.user_id

        WHERE qr.quotation_id = %s
    """, (quotation_id,))

    remark = cursor.fetchone()


    return render_template(
        "admin_quotation_details.html",
        quotation=quotation,
        documents=documents,
        remark=remark
    )


# ============================================================
# APPROVE QUOTATION
# ============================================================

@admin_bp.route(
    "/quotation/<int:quotation_id>/approve",
    methods=["POST"]
)
def approve_quotation(quotation_id):

    if not admin_required():
        return redirect(url_for("login"))

    remark_text = request.form.get(
        "remark",
        ""
    ).strip()


    try:

        cursor.execute("""
            SELECT
                q.quotation_id,
                q.nursery_id,
                np.user_id,
                t.title AS tender_title

            FROM quotations q

            INNER JOIN nursery_profiles np
                ON q.nursery_id = np.nursery_id

            INNER JOIN tenders t
                ON q.tender_id = t.tender_id

            WHERE q.quotation_id = %s
        """, (quotation_id,))

        quotation = cursor.fetchone()


        if not quotation:

            flash(
                "Quotation not found.",
                "error"
            )

            return redirect(
                url_for("admin.quotations")
            )


        # ----------------------------------------------------
        # UPDATE STATUS
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE quotations

            SET status = 'Approved'

            WHERE quotation_id = %s
        """, (quotation_id,))


        # ----------------------------------------------------
        # ADD REMARK IF PROVIDED
        # ----------------------------------------------------

        if remark_text:

            cursor.execute("""
                SELECT remark_id
                FROM quotation_remarks
                WHERE quotation_id = %s
            """, (quotation_id,))

            existing_remark = cursor.fetchone()


            if existing_remark:

                cursor.execute("""
                    UPDATE quotation_remarks

                    SET
                        admin_id = %s,
                        remark = %s

                    WHERE quotation_id = %s
                """, (
                    session["user_id"],
                    remark_text,
                    quotation_id
                ))

            else:

                cursor.execute("""
                    INSERT INTO quotation_remarks
                    (
                        quotation_id,
                        admin_id,
                        remark
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s
                    )
                """, (
                    quotation_id,
                    session["user_id"],
                    remark_text
                ))


        # ----------------------------------------------------
        # NOTIFICATION
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO notifications
            (
                user_id,
                title,
                message
            )

            VALUES
            (
                %s,
                %s,
                %s
            )
        """, (
            quotation["user_id"],
            "Quotation Approved",
            f"Your quotation for '{quotation['tender_title']}' has been approved."
        ))


        db.commit()


        flash(
            "Quotation approved successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "APPROVE QUOTATION ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to approve quotation.",
            "error"
        )


    return redirect(
        url_for(
            "admin.quotation_details",
            quotation_id=quotation_id
        )
    )


# ============================================================
# REJECT QUOTATION
# ============================================================

@admin_bp.route(
    "/quotation/<int:quotation_id>/reject",
    methods=["POST"]
)
def reject_quotation(quotation_id):

    if not admin_required():
        return redirect(url_for("login"))

    remark_text = request.form.get(
        "remark",
        ""
    ).strip()


    if not remark_text:

        flash(
            "Please provide a reason for rejection.",
            "error"
        )

        return redirect(
            url_for(
                "admin.quotation_details",
                quotation_id=quotation_id
            )
        )


    try:

        cursor.execute("""
            SELECT
                q.quotation_id,
                np.user_id,
                t.title AS tender_title

            FROM quotations q

            INNER JOIN nursery_profiles np
                ON q.nursery_id = np.nursery_id

            INNER JOIN tenders t
                ON q.tender_id = t.tender_id

            WHERE q.quotation_id = %s
        """, (quotation_id,))

        quotation = cursor.fetchone()


        if not quotation:

            flash(
                "Quotation not found.",
                "error"
            )

            return redirect(
                url_for("admin.quotations")
            )


        # ----------------------------------------------------
        # UPDATE STATUS
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE quotations

            SET status = 'Rejected'

            WHERE quotation_id = %s
        """, (quotation_id,))


        # ----------------------------------------------------
        # INSERT / UPDATE REMARK
        # ----------------------------------------------------

        cursor.execute("""
            SELECT remark_id
            FROM quotation_remarks

            WHERE quotation_id = %s
        """, (quotation_id,))

        existing_remark = cursor.fetchone()


        if existing_remark:

            cursor.execute("""
                UPDATE quotation_remarks

                SET
                    admin_id = %s,
                    remark = %s

                WHERE quotation_id = %s
            """, (
                session["user_id"],
                remark_text,
                quotation_id
            ))

        else:

            cursor.execute("""
                INSERT INTO quotation_remarks
                (
                    quotation_id,
                    admin_id,
                    remark
                )

                VALUES
                (
                    %s,
                    %s,
                    %s
                )
            """, (
                quotation_id,
                session["user_id"],
                remark_text
            ))


        # ----------------------------------------------------
        # USER NOTIFICATION
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO notifications
            (
                user_id,
                title,
                message
            )

            VALUES
            (
                %s,
                %s,
                %s
            )
        """, (
            quotation["user_id"],
            "Quotation Rejected",
            f"Your quotation for '{quotation['tender_title']}' has been rejected. Please check the administrator remark."
        ))


        db.commit()


        flash(
            "Quotation rejected successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "REJECT QUOTATION ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to reject quotation.",
            "error"
        )


    return redirect(
        url_for(
            "admin.quotation_details",
            quotation_id=quotation_id
        )
    )


# ============================================================
# ADMIN NOTIFICATIONS
# ============================================================

@admin_bp.route("/notifications")
def notifications():

    if not admin_required():
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT
            notification_id,
            title,
            message,
            is_read,
            created_at

        FROM notifications

        WHERE user_id = %s

        ORDER BY created_at DESC
    """, (session["user_id"],))

    notifications = cursor.fetchall()

    return render_template(
        "admin_notifications.html",
        notifications=notifications
    )


# ============================================================
# MARK NOTIFICATION AS READ
# ============================================================

@admin_bp.route(
    "/notification/<int:notification_id>/read",
    methods=["POST"]
)
def mark_notification_read(notification_id):

    if not admin_required():
        return redirect(url_for("login"))

    try:

        cursor.execute("""
            UPDATE notifications

            SET is_read = 1

            WHERE notification_id = %s
            AND user_id = %s
        """, (
            notification_id,
            session["user_id"]
        ))

        db.commit()

    except Exception as e:

        db.rollback()

        print(
            "NOTIFICATION READ ERROR:",
            type(e).__name__,
            str(e)
        )


    return redirect(
        url_for("admin.notifications")
    )


# ============================================================
# MARK ALL NOTIFICATIONS AS READ
# ============================================================

@admin_bp.route(
    "/notifications/read-all",
    methods=["POST"]
)
def mark_all_notifications_read():

    if not admin_required():
        return redirect(url_for("login"))

    try:

        cursor.execute("""
            UPDATE notifications

            SET is_read = 1

            WHERE user_id = %s
        """, (session["user_id"],))

        db.commit()

        flash(
            "All notifications marked as read.",
            "success"
        )

    except Exception as e:

        db.rollback()

        print(
            "READ ALL NOTIFICATIONS ERROR:",
            type(e).__name__,
            str(e)
        )

        flash(
            "Unable to update notifications.",
            "error"
        )


    return redirect(
        url_for("admin.notifications")
    )