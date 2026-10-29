# ============================================================

# GreenTender - NURSERY DASHBOARD BACKEND

# ============================================================



import os



from flask import (

    Blueprint,

    render_template,

    request,

    redirect,

    url_for,

    flash,

    session,

    current_app

)



from werkzeug.utils import secure_filename



from db import db, cursor





# ------------------------------------------------------------

# BLUEPRINT

# ------------------------------------------------------------



nursery_bp = Blueprint(

    "nursery",

    __name__,

    url_prefix="/nursery"

)





# ============================================================

# NURSERY ACCESS CHECK

# ============================================================



def nursery_required():



    if "user_id" not in session:

        flash("Please login first.", "error")

        return False



    if session.get("role") != "nursery":

        flash("Unauthorized Access.", "error")

        return False



    return True





# ============================================================

# GET NURSERY PROFILE

# ============================================================



def get_nursery_profile():



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



        WHERE user_id = %s



        LIMIT 1

    """, (session["user_id"],))



    return cursor.fetchone()





# ============================================================

# NURSERY DASHBOARD

# ============================================================



@nursery_bp.route("/dashboard")

def dashboard():



    if not nursery_required():

        return redirect(url_for("login"))





    try:



        # ----------------------------------------------------

        # FIND NURSERY

        # ----------------------------------------------------



        nursery = get_nursery_profile()





        # ----------------------------------------------------

        # AVAILABLE TENDERS

        # ----------------------------------------------------



        cursor.execute("""

            SELECT COUNT(*) AS available_tenders



            FROM tenders



            WHERE status = 'Open'

            AND closing_date >= CURDATE()

        """)



        available_tenders = (

            cursor.fetchone()["available_tenders"]

        )





        # ----------------------------------------------------

        # MY QUOTATIONS

        # ----------------------------------------------------



        my_quotations = 0



        if nursery:



            cursor.execute("""

                SELECT COUNT(*) AS my_quotations



                FROM quotations



                WHERE nursery_id = %s

            """, (nursery["nursery_id"],))



            my_quotations = (

                cursor.fetchone()["my_quotations"]

            )





        # ----------------------------------------------------

        # MY APPROVED QUOTATIONS

        # ----------------------------------------------------



        my_orders = 0



        if nursery:



            cursor.execute("""

                SELECT COUNT(*) AS my_orders



                FROM quotations



                WHERE nursery_id = %s

                AND status = 'Approved'

            """, (nursery["nursery_id"],))



            my_orders = (

                cursor.fetchone()["my_orders"]

            )





        # ----------------------------------------------------

        # RECENT QUOTATION ACTIVITY

        # ----------------------------------------------------



        recent_activities = []





        if nursery:



            cursor.execute("""

                SELECT

                    q.quotation_id,

                    q.status,

                    q.submitted_at,

                    t.title AS tender_title



                FROM quotations q



                INNER JOIN tenders t

                    ON q.tender_id = t.tender_id



                WHERE q.nursery_id = %s



                ORDER BY q.submitted_at DESC



                LIMIT 10

            """, (nursery["nursery_id"],))



            quotations = cursor.fetchall()





            for quotation in quotations:



                recent_activities.append({

                    "activity":

                        "Quotation submitted for "

                        + quotation["tender_title"],



                    "date":

                        quotation["submitted_at"],



                    "status":

                        quotation["status"]

                })





        # ----------------------------------------------------

        # NOTIFICATION COUNT

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





        return render_template(

            "nursery_dashboard.html",



            name=session.get(

                "full_name",

                "Nursery Owner"

            ),



            nursery=nursery,



            available_tenders=available_tenders,



            my_quotations=my_quotations,



            my_orders=my_orders,



            recent_activities=recent_activities,



            unread_notifications=unread_notifications

        )





    except Exception as e:



        print(

            "NURSERY DASHBOARD ERROR:",

            type(e).__name__,

            str(e)

        )



        flash(

            "Unable to load Nursery Dashboard.",

            "error"

        )



        return render_template(

            "nursery_dashboard.html",



            name=session.get(

                "full_name",

                "Nursery Owner"

            ),



            nursery=None,



            available_tenders=0,



            my_quotations=0,



            my_orders=0,



            recent_activities=[],



            unread_notifications=0

        )





# ============================================================

# NURSERY PROFILE

# ============================================================



@nursery_bp.route(

    "/profile",

    methods=["GET", "POST"]

)

def profile():



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()





    # ========================================================

    # UPDATE PROFILE

    # ========================================================



    if request.method == "POST":



        nursery_name = request.form.get(

            "nursery_name",

            ""

        ).strip()



        owner_name = request.form.get(

            "owner_name",

            ""

        ).strip()



        registration_number = request.form.get(

            "registration_number",

            ""

        ).strip()



        address = request.form.get(

            "address",

            ""

        ).strip()



        state = request.form.get(

            "state",

            ""

        ).strip()



        city = request.form.get(

            "city",

            ""

        ).strip()



        pincode = request.form.get(

            "pincode",

            ""

        ).strip()





        if not nursery_name:



            flash(

                "Nursery name is required.",

                "error"

            )



            return redirect(

                url_for("nursery.profile")

            )





        if not owner_name:



            flash(

                "Owner name is required.",

                "error"

            )



            return redirect(

                url_for("nursery.profile")

            )





        if not nursery:



            # ------------------------------------------------

            # CREATE PROFILE

            # ------------------------------------------------



            try:



                cursor.execute("""

                    INSERT INTO nursery_profiles

                    (

                        user_id,

                        nursery_name,

                        owner_name,

                        registration_number,

                        address,

                        state,

                        city,

                        pincode,

                        verification_status

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

                        'Pending'

                    )

                """, (

                    session["user_id"],

                    nursery_name,

                    owner_name,

                    registration_number,

                    address,

                    state,

                    city,

                    pincode

                ))



                db.commit()



                flash(

                    "Nursery profile created successfully.",

                    "success"

                )



            except Exception as e:



                db.rollback()



                print(

                    "CREATE PROFILE ERROR:",

                    type(e).__name__,

                    str(e)

                )



                flash(

                    "Unable to create nursery profile.",

                    "error"

                )





        else:



            # ------------------------------------------------

            # UPDATE PROFILE

            # ------------------------------------------------



            try:



                cursor.execute("""

                    UPDATE nursery_profiles



                    SET

                        nursery_name = %s,

                        owner_name = %s,

                        registration_number = %s,

                        address = %s,

                        state = %s,

                        city = %s,

                        pincode = %s



                    WHERE nursery_id = %s

                    AND user_id = %s

                """, (

                    nursery_name,

                    owner_name,

                    registration_number,

                    address,

                    state,

                    city,

                    pincode,

                    nursery["nursery_id"],

                    session["user_id"]

                ))



                db.commit()



                flash(

                    "Nursery profile updated successfully.",

                    "success"

                )



            except Exception as e:



                db.rollback()



                print(

                    "UPDATE PROFILE ERROR:",

                    type(e).__name__,

                    str(e)

                )



                flash(

                    "Unable to update nursery profile.",

                    "error"

                )





        return redirect(

            url_for("nursery.profile")

        )





    return render_template(

        "nursery_profile.html",

        nursery=nursery

    )





# ============================================================

# AVAILABLE TENDERS

# ============================================================



@nursery_bp.route("/tenders")

def tenders():



    if not nursery_required():

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



        WHERE status = 'Open'

        AND closing_date >= CURDATE()



        ORDER BY closing_date ASC

    """)



    tenders = cursor.fetchall()





    return render_template(

        "nursery_tenders.html",

        tenders=tenders

    )





# ============================================================

# TENDER DETAILS

# ============================================================



@nursery_bp.route(

    "/tender/<int:tender_id>"

)

def tender_details(tender_id):



    if not nursery_required():

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



        WHERE tender_id = %s

    """, (tender_id,))



    tender = cursor.fetchone()





    if not tender:



        flash(

            "Tender not found.",

            "error"

        )



        return redirect(

            url_for("nursery.tenders")

        )





    # --------------------------------------------------------

    # CHECK WHETHER THIS NURSERY ALREADY SUBMITTED

    # --------------------------------------------------------



    already_submitted = False



    nursery = get_nursery_profile()





    if nursery:



        cursor.execute("""

            SELECT quotation_id



            FROM quotations



            WHERE tender_id = %s

            AND nursery_id = %s



            LIMIT 1

        """, (

            tender_id,

            nursery["nursery_id"]

        ))



        already_submitted = (

            cursor.fetchone() is not None

        )





    return render_template(

        "nursery_tender_details.html",



        tender=tender,



        nursery=nursery,



        already_submitted=already_submitted

    )





# ============================================================

# SUBMIT QUOTATION

# ============================================================



@nursery_bp.route(

    "/tender/<int:tender_id>/quotation",

    methods=["GET", "POST"]

)

def submit_quotation(tender_id):



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()

    print("========== QUOTATION DEBUG ==========")
    print("LOGGED-IN USER ID:", session.get("user_id"))
    print("LOADED NURSERY:", nursery)
    if nursery:
        print("VERIFICATION STATUS:", repr(nursery["verification_status"]))
    print("=====================================")





    if not nursery:



        flash(

            "Please complete your nursery profile first.",

            "error"

        )



        return redirect(

            url_for("nursery.profile")

        )





    # --------------------------------------------------------

    # NURSERY MUST BE VERIFIED

    # --------------------------------------------------------



    if nursery["verification_status"] != "Verified":



        flash(

            "Your nursery must be verified before submitting quotations.",

            "error"

        )



        return redirect(

            url_for(

                "nursery.tender_details",

                tender_id=tender_id

            )

        )





    # --------------------------------------------------------

    # GET TENDER

    # --------------------------------------------------------



    cursor.execute("""

        SELECT *

        FROM tenders

        WHERE tender_id = %s

    """, (tender_id,))



    tender = cursor.fetchone()





    if not tender:



        flash(

            "Tender not found.",

            "error"

        )



        return redirect(

            url_for("nursery.tenders")

        )





    if tender["status"] != "Open":



        flash(

            "This tender is closed.",

            "error"

        )



        return redirect(

            url_for(

                "nursery.tender_details",

                tender_id=tender_id

            )

        )





    # --------------------------------------------------------

    # CHECK DUPLICATE QUOTATION

    # --------------------------------------------------------



    cursor.execute("""

        SELECT quotation_id



        FROM quotations



        WHERE tender_id = %s

        AND nursery_id = %s



        LIMIT 1

    """, (

        tender_id,

        nursery["nursery_id"]

    ))



    existing = cursor.fetchone()





    if existing:



        flash(

            "You have already submitted a quotation for this tender.",

            "error"

        )



        return redirect(

            url_for("nursery.my_quotations")

        )





    # ========================================================

    # SHOW FORM

    # ========================================================



    if request.method == "GET":



        return render_template(

            "submit_quotation.html",

            tender=tender,nursery=nursery

        )





    # ========================================================

    # FORM DATA

    # ========================================================



    quoted_price = request.form.get(

        "quoted_price",

        ""

    ).strip()



    quantity_available = request.form.get(

        "quantity_available",

        ""

    ).strip()



    delivery_days = request.form.get(

        "delivery_days",

        ""

    ).strip()



    quotation_description = request.form.get(

        "quotation_description",

        ""

    ).strip()





    # --------------------------------------------------------

    # VALIDATION

    # --------------------------------------------------------



    if not quoted_price:



        flash(

            "Quoted price is required.",

            "error"

        )



        return redirect(

            url_for(

                "nursery.submit_quotation",

                tender_id=tender_id

            )

        )





    if not quantity_available:



        flash(

            "Available quantity is required.",

            "error"

        )



        return redirect(

            url_for(

                "nursery.submit_quotation",

                tender_id=tender_id

            )

        )





    if not delivery_days:



        flash(

            "Delivery days are required.",

            "error"

        )



        return redirect(

            url_for(

                "nursery.submit_quotation",

                tender_id=tender_id

            )

        )





    # --------------------------------------------------------

    # PLANT PHOTO

    # --------------------------------------------------------



    plant_photo_path = None



    plant_photo = request.files.get(

        "plant_photo"

    )





    if plant_photo and plant_photo.filename:



        filename = secure_filename(

            plant_photo.filename

        )



        upload_folder = os.path.join(

            current_app.root_path,

            "uploads",

            "plants"

        )



        os.makedirs(

            upload_folder,

            exist_ok=True

        )



        plant_photo.save(

            os.path.join(

                upload_folder,

                filename

            )

        )



        plant_photo_path = (

            "/uploads/plants/"

            + filename

        )





    # ========================================================

    # INSERT QUOTATION

    # ========================================================



    try:



        cursor.execute("""

            INSERT INTO quotations

            (

                tender_id,

                nursery_id,

                quoted_price,

                quantity_available,

                delivery_days,

                plant_photo,

                quotation_description,

                status

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

                'Pending'

            )

        """, (

            tender_id,

            nursery["nursery_id"],

            quoted_price,

            quantity_available,

            delivery_days,

            plant_photo_path,

            quotation_description

        ))





        # ----------------------------------------------------

        # GET ADMIN

        # ----------------------------------------------------



        cursor.execute("""

            SELECT user_id



            FROM users



            WHERE role = 'admin'



            LIMIT 1

        """)



        admin = cursor.fetchone()





        # ----------------------------------------------------

        # ADMIN NOTIFICATION

        # ----------------------------------------------------



        if admin:



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

                admin["user_id"],

                "New Quotation Submitted",

                f"A new quotation has been submitted for tender '{tender['title']}'."

            ))





        db.commit()





        flash(

            "Quotation submitted successfully.",

            "success"

        )



        return redirect(

            url_for("nursery.my_quotations")

        )





    except Exception as e:



        db.rollback()



        print(

            "SUBMIT QUOTATION ERROR:",

            type(e).__name__,

            str(e)

        )



        flash(

            "Unable to submit quotation.",

            "error"

        )



        return redirect(

            url_for(

                "nursery.submit_quotation",

                tender_id=tender_id

            )

        )





# ============================================================

# MY QUOTATIONS

# ============================================================



@nursery_bp.route("/quotations")

def my_quotations():



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()





    if not nursery:



        return render_template(

            "nursery_quotations.html",

            quotations=[]

        )





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

            t.location,

            t.road_name,

            t.plant_type,

            t.estimated_budget,

            t.closing_date



        FROM quotations q



        INNER JOIN tenders t

            ON q.tender_id = t.tender_id



        WHERE q.nursery_id = %s



        ORDER BY q.submitted_at DESC

    """, (nursery["nursery_id"],))



    quotations = cursor.fetchall()





    return render_template(

        "nursery_quotations.html",

        quotations=quotations

    )





# ============================================================

# QUOTATION DETAILS

# ============================================================



@nursery_bp.route(

    "/quotation/<int:quotation_id>"

)

def quotation_details(quotation_id):



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()





    if not nursery:



        flash(

            "Nursery profile not found.",

            "error"

        )



        return redirect(

            url_for("nursery.profile")

        )





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

            t.publish_date,

            t.closing_date



        FROM quotations q



        INNER JOIN tenders t

            ON q.tender_id = t.tender_id



        WHERE q.quotation_id = %s

        AND q.nursery_id = %s

    """, (

        quotation_id,

        nursery["nursery_id"]

    ))



    quotation = cursor.fetchone()





    if not quotation:



        flash(

            "Quotation not found.",

            "error"

        )



        return redirect(

            url_for("nursery.my_quotations")

        )





    # --------------------------------------------------------

    # ADMIN REMARK

    # --------------------------------------------------------



    cursor.execute("""

        SELECT

            qr.remark,

            qr.remarked_at,



            u.full_name AS admin_name



        FROM quotation_remarks qr



        LEFT JOIN users u

            ON qr.admin_id = u.user_id



        WHERE qr.quotation_id = %s

    """, (quotation_id,))



    remark = cursor.fetchone()





    return render_template(

        "nursery_quotation_details.html",



        quotation=quotation,



        remark=remark

    )





# ============================================================

# APPROVED QUOTATIONS / ORDERS

# ============================================================



@nursery_bp.route("/orders")

def orders():



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()





    if not nursery:



        return render_template(

            "nursery_orders.html",

            orders=[]

        )





    # --------------------------------------------------------

    # IMPORTANT

    # --------------------------------------------------------

    # Your current database does not contain a separate

    # "orders" table.

    #

    # Therefore approved quotations are treated as the

    # nursery's order/approved-work records.

    # --------------------------------------------------------



    cursor.execute("""

        SELECT

            q.quotation_id,

            q.quoted_price,

            q.quantity_available,

            q.delivery_days,

            q.delivery_status,

            q.expected_delivery_date,

            q.actual_delivery_date,

            q.delivery_remark,

            q.delivery_updated_at,

            q.submitted_at,



            t.tender_id,

            t.title,

            t.location,

            t.road_name,

            t.plant_type,

            t.closing_date



        FROM quotations q



        INNER JOIN tenders t

            ON q.tender_id = t.tender_id



        WHERE q.nursery_id = %s

        AND q.status = 'Approved'



        ORDER BY q.submitted_at DESC

    """, (nursery["nursery_id"],))



    orders = cursor.fetchall()





    return render_template(

        "nursery_orders.html",

        orders=orders

    )





# ============================================================

# DOCUMENTS

# ============================================================



@nursery_bp.route("/documents")

def documents():



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()





    if not nursery:



        return render_template(

            "nursery_documents.html",

            documents=[]

        )





    cursor.execute("""

        SELECT

            document_id,

            nursery_id,

            document_type,

            file_url,

            uploaded_at



        FROM documents



        WHERE nursery_id = %s



        ORDER BY uploaded_at DESC

    """, (nursery["nursery_id"],))



    documents = cursor.fetchall()





    return render_template(

        "nursery_documents.html",

        documents=documents,

        nursery=nursery

    )





# ============================================================

# UPLOAD DOCUMENT

# ============================================================



@nursery_bp.route(

    "/documents/upload",

    methods=["POST"]

)

def upload_document():



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()





    if not nursery:



        flash(

            "Please create your nursery profile first.",

            "error"

        )



        return redirect(

            url_for("nursery.profile")

        )





    document_type = request.form.get(

        "document_type",

        ""

    ).strip()





    allowed_document_types = [

        "Aadhaar",

        "Registration Certificate",

        "Nursery Photo"

    ]





    if document_type not in allowed_document_types:



        flash(

            "Invalid document type.",

            "error"

        )



        return redirect(

            url_for("nursery.documents")

        )





    uploaded_file = request.files.get(

        "document"

    )





    if not uploaded_file:



        flash(

            "Please select a document.",

            "error"

        )



        return redirect(

            url_for("nursery.documents")

        )





    if not uploaded_file.filename:



        flash(

            "Please select a document.",

            "error"

        )



        return redirect(

            url_for("nursery.documents")

        )





    try:



        filename = secure_filename(

            uploaded_file.filename

        )





        upload_folder = os.path.join(

            current_app.root_path,

            "uploads",

            "documents"

        )





        os.makedirs(

            upload_folder,

            exist_ok=True

        )





        uploaded_file.save(

            os.path.join(

                upload_folder,

                filename

            )

        )





        file_url = (

            "/uploads/documents/"

            + filename

        )





        cursor.execute("""

            INSERT INTO documents

            (

                nursery_id,

                document_type,

                file_url

            )



            VALUES

            (

                %s,

                %s,

                %s

            )

        """, (

            nursery["nursery_id"],

            document_type,

            file_url

        ))





        db.commit()





        flash(

            "Document uploaded successfully.",

            "success"

        )





    except Exception as e:



        db.rollback()



        print(

            "DOCUMENT UPLOAD ERROR:",

            type(e).__name__,

            str(e)

        )



        flash(

            "Unable to upload document.",

            "error"

        )





    return redirect(

        url_for("nursery.documents")

    )





# ============================================================

# DELETE DOCUMENT

# ============================================================



@nursery_bp.route(

    "/documents/<int:document_id>/delete",

    methods=["POST"]

)

def delete_document(document_id):



    if not nursery_required():

        return redirect(url_for("login"))





    nursery = get_nursery_profile()





    if not nursery:



        return redirect(

            url_for("nursery.documents")

        )





    try:



        cursor.execute("""

            SELECT file_url



            FROM documents



            WHERE document_id = %s

            AND nursery_id = %s

        """, (

            document_id,

            nursery["nursery_id"]

        ))



        document = cursor.fetchone()





        if not document:



            flash(

                "Document not found.",

                "error"

            )



            return redirect(

                url_for("nursery.documents")

            )





        cursor.execute("""

            DELETE FROM documents



            WHERE document_id = %s

            AND nursery_id = %s

        """, (

            document_id,

            nursery["nursery_id"]

        ))





        db.commit()





        # ----------------------------------------------------

        # DELETE PHYSICAL FILE

        # ----------------------------------------------------



        file_url = document["file_url"]





        if file_url:



            relative_path = file_url.lstrip("/")



            physical_path = os.path.join(

                current_app.root_path,

                relative_path

            )





            if os.path.exists(physical_path):



                os.remove(

                    physical_path

                )





        flash(

            "Document deleted successfully.",

            "success"

        )





    except Exception as e:



        db.rollback()



        print(

            "DELETE DOCUMENT ERROR:",

            type(e).__name__,

            str(e)

        )



        flash(

            "Unable to delete document.",

            "error"

        )





    return redirect(

        url_for("nursery.documents")

    )





# ============================================================

# NOTIFICATIONS

# ============================================================



@nursery_bp.route("/notifications")

def notifications():



    if not nursery_required():

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

        "nursery_notifications.html",

        notifications=notifications

    )





# ============================================================

# MARK NOTIFICATION AS READ

# ============================================================



@nursery_bp.route(

    "/notification/<int:notification_id>/read",

    methods=["POST"]

)

def mark_notification_read(notification_id):



    if not nursery_required():

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

            "NURSERY NOTIFICATION ERROR:",

            type(e).__name__,

            str(e)

        )





    return redirect(

        url_for("nursery.notifications")

    )





# ============================================================

# MARK ALL NOTIFICATIONS READ

# ============================================================



@nursery_bp.route(

    "/notifications/read-all",

    methods=["POST"]

)

def mark_all_notifications_read():



    if not nursery_required():

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

            "READ ALL ERROR:",

            type(e).__name__,

            str(e)

        )



        flash(

            "Unable to update notifications.",

            "error"

        )





    return redirect(

        url_for("nursery.notifications")

    )