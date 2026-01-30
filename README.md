# Credit Approval System (Backend)

A **Django REST Framework–based Credit Approval System** that evaluates loan eligibility using customer credit scores derived from historical loan data and current financial constraints.

This project is built as part of a **Backend Internship Assignment**, focusing on Django, REST APIs, background processing, databases, and Dockerization.

---

## Features

- Customer registration with automatic approved credit limit calculation
- Credit score–based loan eligibility checking
- Loan creation and management
- Historical data ingestion from Excel files
- Background task processing using Celery
- Fully Dockerized setup with PostgreSQL and Redis

---

## Tech Stack

- **Backend:** Django 4.x, Django REST Framework
- **Database:** PostgreSQL
- **Background Tasks:** Celery + Redis
- **Containerization:** Docker & Docker Compose

---

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed
- Excel files placed in the project root:
  - `customer_data.xlsx`
  - `loan_data.xlsx`

---

### Running the Application

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd credit-approval-system-backend
Build and start services
docker compose up --build
