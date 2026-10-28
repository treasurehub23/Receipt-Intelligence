# Receipt-Intelligence

Receipt-Intelligence is an intelligent expense-tracking API that extracts information from receipts, categorizes individual expense items using machine learning, and provides spending analytics.

The project combines optical character recognition (OCR), AI-assisted receipt data extraction, machine learning, and a REST API to simplify expense recording and tracking.

## Features

- **Receipt processing:** Upload receipt images or PDF files for information extraction.
- **OCR and data extraction:** Extract receipt text and identify information such as merchant, purchase date, currency, total amount, and line items.
- **Machine learning categorization:** Automatically assign expense categories using a trained classification model.
- **Expense management:** Create expenses from receipt line items, retrieve records, update expense details, and delete expenses.
- **Spending analytics:** Retrieve spending totals and analyze expenses by category and month.
- **Authentication and authorization:** Register and log in users using password hashing and JWT-based authentication.
- **Data isolation:** Restrict expense records and analytics to the authenticated user.
- **REST API:** Interact with the system through documented API endpoints.

## Technology Stack

- **Language:** Python
- **API framework:** FastAPI
- **Database:** PostgreSQL
- **ORM and database access:** SQLAlchemy
- **Database migrations:** Alembic
- **Authentication:** JWT and password hashing
- **OCR and receipt extraction:** OCR preprocessing and Groq-powered extraction
- **Machine learning:** A trained expense classification model
- **Deployment:** Render
## Installation and Setup

### Prerequisites

Before running Receipt-Intelligence locally, ensure you have:

- Python 3.12 or a compatible Python version.
- PostgreSQL database access.
- Git.
- A Groq API key for AI-powered receipt extraction.

### 1. Clone the Repository

```bash
git clone https://github.com/treasurehub23/Receipt-Intelligence.git
cd Receipt-Intelligence
```

### 2. Create and Activate a Virtual Environment

On Linux or macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory. Configure the following variables with your own credentials:

```dotenv
DATABASE_URL=your_postgresql_connection_string
SECRET_KEY=your_secret_key
GROQ_API_KEY=your_groq_api_key
```

Replace the example values with your actual credentials. Never commit `.env` or expose API keys, passwords, or other secrets in the repository.

### 5. Apply Database Migrations

With your virtual environment activated and database configuration set, run:

```bash
alembic upgrade head
```

This applies the database migrations defined by the project.

### 6. Start the API Server

Run the application from the project root:

```bash
uvicorn app.main:app --reload
```

The local API should be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```
## Project Status

The API has been deployed to Render. Core functionality includes authentication, receipt processing, expense management, and spending analytics.

## API Endpoints

### Authentication
- **POST /auth/register** — Registers a new user using an email and password. Returns a user_id, email and the time created.

- **POST /auth/login** - Authenticates a user using email and password. Returns an access token which enables users to perform operations on protected endpoints.

### Expenses
- **POST /expenses/upload** - Accepts a receipt in jpeg, jpg, png or pdf format. The endpoint extracts receipt information, classifies the expense and saves it in the database. It returns a list of expense item objects.

- **PATCH /expenses/{expense_id}** - Receives an expense-id and  retrieves the expense object from the database. The endpoint allows the update of specific fields - category, purchase date, quantity, unit price and description. It returns the updated expense object.

- **DELETE /expenses/{expense_id}** - Receives an expense-id. The endpoint retrieves the expense object and deletes it from the the database. It returns status code 204 when successful. 

### Analytics
- **GET /analytics/summary** -Retrieves a summary of the authenticated user's expenses, including total spending, expense count, spending breakdown by category, and monthly spending. Supports optional category, start_date, and end_date query parameters to filter the results by category and purchase date range. 
## API Documentation

FastAPI provides interactive API documentation, allowing users to inspect endpoints and send requests.

Once deployed, open the `/docs` route on the deployed API to explore the available endpoints.

## Security

- Passwords are hashed before storage.
- Protected endpoints require authentication.
- Expense operations are scoped to the authenticated user.
- Secrets and database credentials should be supplied through environment variables rather than committed to version control.

## Future Improvements

Potential extensions include:

- Spending insights and unusual-spending detection.
- CSV export of expense records.
- A user-facing frontend integrated with the API.

## Author

**Treasure Okegbola**

Computer Engineering student interested in machine learning, AI systems, and deploying practical ML applications.