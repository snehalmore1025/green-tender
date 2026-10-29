# 🌿 GreenTender – Landscape Quotation Management System
## 📌 Project Overview

GreenTender is a web-based Landscape Quotation Management System designed to digitize and simplify the process of government landscape plantation tender management.

The system provides a centralized platform where nursery owners can register, verify their email through OTP authentication, upload required documents, browse available tenders, submit quotations, and track the status of their submissions.

It also provides an administrator portal to manage nursery registrations, verify submitted documents, publish tenders, review quotations, approve or reject submissions, add remarks, and notify users about important updates.

GreenTender aims to replace manual, paper-based quotation management with a faster, more transparent, secure, and paperless workflow for administrators and nursery owners.

## 🎯 Project Objectives

- Digitize government landscape plantation tender management.
- Provide secure registration and login for nursery owners and administrators.
- Enable email OTP verification during registration.
- Simplify nursery profile and document management.
- Allow administrators to create, publish, and manage tenders.
- Enable online quotation submission and review.
- Support quotation approval, rejection, and remarks.
- Provide notifications and submission status tracking.
- Improve the accessibility and organization of tender-related information.

## ✨ Key Features

### 👤 User Registration and Authentication
- User registration and login.
- Email OTP verification.
- Forgot-password OTP workflow.
- Role-based access for administrators and nursery owners.
- Account status management.

### 🌱 Nursery Management
- Nursery profile management.
- Nursery registration and document uploads.
- Administrator verification of nursery details.
- Verification status tracking.

### 📋 Tender Management
- Tender creation and management by administrators.
- Tender details including location, road name, plant type, required quantity, and estimated budget.
- Tender publication and closing dates.
- Open and closed tender status.

### 💰 Quotation Management
- View available tenders.
- Submit quotations with pricing and quantity details.
- Specify delivery timelines.
- Upload plant photographs and provide quotation descriptions.
- Review, approve, or reject submitted quotations.
- Record administrator remarks.

### 🔔 Notifications
- Notifications for relevant user activities and updates.
- Read/unread notification status.
- Centralized notification management.

### 🤖 AI-Based Quotation Ranking
- AI ranking interface for quotation assessment.

*The exact ranking algorithm and criteria depend on the implementation in the source code.*

### 🚚 Delivery and Order Tracking
- Delivery status interface.
- Order and delivery status management interface.

*The precise delivery workflow and supported status transitions depend on the implemented functionality.*

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS, Bootstrap 5, JavaScript |
| Backend | Python, Flask |
| Database | MySQL |
| Database Management | MySQL Workbench |
| Email Service | Flask-Mail |
| Development Environment | Visual Studio Code |

## 🏗️ System Modules

1. **User Management** — Registration, authentication, OTP verification, and account status.
2. **Nursery Management** — Nursery profiles, document uploads, and verification.
3. **Tender Management** — Tender creation, publication, and closure.
4. **Quotation Management** — Quotation submission, review, approval, and rejection.
5. **Remarks Management** — Administrator comments associated with quotations.
6. **Notification Management** — User notifications and read/unread tracking.
7. **AI Ranking** — Interface for ranking or assessing quotations.
8. **Delivery Management** — Delivery and order status interfaces.

## 🗃️ Database Design

The system uses a MySQL relational database organized around the following eight tables.

| Table | Purpose |
|---|---|
| `USERS` | Stores user information, roles, authentication-related details, and account status. |
| `NURSERY_PROFILES` | Stores nursery registration and verification information. |
| `DOCUMENTS` | Records uploaded nursery documents. |
| `TENDERS` | Stores tender details, requirements, dates, and status. |
| `QUOTATIONS` | Stores submitted quotations, pricing, availability, and submission status. |
| `QUOTATION_REMARKS` | Stores administrator remarks associated with quotations. |
| `NOTIFICATIONS` | Stores notifications for individual users. |
| `OTP_VERIFICATION` | Stores OTP verification records and expiry information. |

### Main Relationships

- A user can have an associated nursery profile.
- Nursery profiles are associated with uploaded documents.
- Administrators create and manage tenders.
- Tenders receive quotations from nursery owners.
- Quotations can have associated administrator remarks.
- Users receive notifications.
- OTP verification records are associated with users.

The database uses primary keys and foreign keys to represent relationships between entities.

## 📂 Project Structure

The following is a high-level representation of the project. Exact filenames and routes may vary depending on the implementation.

```text
GreenTender/
├── app.py
├── admin_dashboard.py
├── nursery_dashboard.py
├── ai_bidding.py
├── db.py
├── mail_config.py
├── requirements.txt
├── .gitignore
├── templates/
├── static/
├── uploads/
└── README.md
```

### Main Application Files

- `app.py` — Main Flask application and application routes.
- `admin_dashboard.py` — Administrator dashboard functionality.
- `nursery_dashboard.py` — Nursery dashboard functionality.
- `ai_bidding.py` — AI-related bidding or quotation functionality.
- `db.py` — Database-related functionality.
- `mail_config.py` — Email configuration.
- `templates/` — HTML templates for application pages.
- `static/` — Static assets such as CSS, JavaScript, and images.
- `requirements.txt` — Python dependencies.

## ⚙️ Installation and Setup

Follow these steps to run GreenTender locally.

### Prerequisites

Install the following software:

- Python
- MySQL Server
- MySQL Workbench (recommended for database management)
- Git
- Visual Studio Code (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/GreenTender.git
cd GreenTender
```

Replace `YOUR-USERNAME` with the GitHub account that hosts the repository.

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use Command Prompt instead:

```cmd
venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Database

1. Start your MySQL server.
2. Create the database required by the application.
3. Execute the project's database schema or SQL initialization scripts, if provided.
4. Configure the database connection using environment variables or the application's supported configuration method.

**Important:** The exact database name, schema initialization procedure, and required configuration variables must be confirmed from the source code. Do not assume that an empty database is sufficient.

### 5. Configure Environment Variables

Create a local `.env` file if the application uses environment variables.

Add the configuration values required by your implementation, such as:

```env
DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name

MAIL_USERNAME=your_email_address
MAIL_PASSWORD=your_email_or_app_password
```

These are illustrative placeholders, not verified variable names from the project.

Check `db.py`, `mail_config.py`, and the application code to determine the exact variable names and configuration format. Never commit your real `.env` file to GitHub.

### 6. Run the Application

Start the application using the actual Flask entry point and configuration used by the project.

For example, if `app.py` is the entry point:

```bash
python app.py
```

Open the local address displayed in the terminal. Flask applications commonly use `http://127.0.0.1:5000`, but the actual address and port depend on the application's configuration.

## 🖥️ Application Screens

The project includes interfaces for the following workflows:

- Home or index page
- Registration page
- OTP verification page
- Login page
- Nursery dashboard
- Document upload page
- Administrator dashboard
- Nursery verification page
- Nursery notifications page
- Tender creation page
- Available tenders page
- Quotation submission page
- Quotations page
- Administrator quotations page
- AI ranking page
- Quotation review page
- Delivery status page
- Orders and delivery status page

Screenshots can be added to this README after capturing them from the running application.

## 🔐 Security Considerations

- Keep database credentials and email passwords out of source control.
- Store secrets in environment variables or another appropriate secret-management mechanism.
- Exclude virtual environments, caches, and private uploaded documents from public repositories.
- Validate uploaded files and restrict permitted file types and sizes.
- Enforce authorization checks for administrator-only operations.
- Protect authentication and OTP workflows against misuse.
- Use secure password hashing and appropriate session management.

These are recommended security practices; their implementation must be verified in the source code.

## 🚧 Future Enhancements

Potential enhancements include:

- Advanced quotation comparison and ranking.
- Improved reporting and tender analytics.
- Enhanced audit trails for administrative decisions.
- More detailed delivery tracking.
- Additional automated notifications.
- Stronger input validation and security controls.
- Automated testing and deployment workflows.

These items represent possible future work, not necessarily existing features.
