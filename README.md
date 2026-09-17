# Personal Finance Advisor Bot

An AI-powered personal financial planning and budgeting platform designed to help individuals, freelancers, and household managers take control of their finances with clarity and confidence. Built with **Flask**, **SQLAlchemy**, **SQLite**, **Jinja2**, **Chart.js**, and **Gemini AI**.

---

## 🌟 Core Features

- 🔐 **User Authentication & Profile Security**:
  - Secure user registration, login, password hashing (`werkzeug.security`), and session management (`Flask-Login`).
  - Strict user-level data isolation for all incomes, expenses, and savings goals.
- 💵 **Multi-Source Income Tracking**:
  - Record earnings from multiple revenue streams (e.g., Salary, Client Contracts, Freelance Projects, Side Hustles) with specific dates and source labels.
  - Interactive monthly income lists with instant deletion and real-time total recalculation.
- 💳 **Categorized Expense Logging**:
  - Itemized expense tracking across standard categories (*Rent & Housing*, *Food & Groceries*, *Transport*, *Utilities*, *Entertainment*, *Healthcare*, *Education*, *Other*).
  - Transaction history table with individual deletion and live metrics refresh.
- 🎯 **Goal-Based Savings Tracker**:
  - Create and track custom savings targets (e.g., *Emergency Fund*, *New Laptop*, *Vacation*).
  - Visual progress bars showing percentage completion toward target amounts.
  - Interactive contribution modal to quickly allocate savings to active goals.
- 💡 **Dual Financial Advisory Engine**:
  - **Embedded Local AI Advisor (Offline & Ready Out of the Box)**: When no Google API key is provided, the platform automatically runs a built-in financial intelligence and Natural Language Generation (NLG) engine ([local_advisor.py](file:///c:/Users/RAJ/Desktop/personal_finance_advisor_bot/local_advisor.py)). It classifies user personas (*Freelancer*, *Student*, *Household Manager*, *Salaried Pro*), analyzes 50/30/20 burn rates, forecasts goal horizons, and generates actionable advice locally without any cloud dependency or downloads.
  - **Google Gemini Cloud AI (Optional Upgrade)**: When `GEMINI_API_KEY` is provided in `.env`, the system seamlessly upgrades to Google's `gemini-1.5-flash` model for conversational advice.
  - **Dynamic UI Indicator**: The dashboard automatically displays whether insights are powered by `Local Advisor AI (Offline Model)` or `Gemini 1.5 Flash (Cloud AI)`.
- 📊 **Dynamic Visual Analytics**:
  - Responsive single-page dashboard styled with modern CSS Grid and Flexbox.
  - Interactive doughnut chart powered by **Chart.js** displaying real-time spending breakdowns.
- 📥 **Structured Monthly Reporting & CSV Export**:
  - One-click CSV export generating a comprehensive monthly financial summary report (Income, Expenses, Net Savings, and Goal Progress).
- 🌐 **Public Deployment via Ngrok**:
  - Integrated support for `pyngrok` to expose the local server with a secure public HTTPS tunnel for demos and testing.

---

## 🏗️ Architecture & Tech Stack

- **Backend**: Python 3, Flask, Flask-Login, Flask-SQLAlchemy, SQLite, Werkzeug Security, python-dotenv, google-generativeai, pyngrok.
- **Frontend**: HTML5, CSS3 (CSS Variables, Flexbox/Grid), JavaScript (Vanilla ES6+ Fetch API), Chart.js, Google Fonts (Inter).
- **Database Schema**:
  - `User`: `id`, `username`, `email`, `password_hash`, `created_at`
  - `Income`: `id`, `user_id`, `month`, `source`, `amount`, `date`, `created_at`
  - `Expense`: `id`, `user_id`, `month`, `category`, `amount`, `description`, `date`, `created_at`
  - `Goal`: `id`, `user_id`, `name`, `target_amount`, `current_amount`, `deadline`, `created_at`

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+ installed
- Git installed

### 2. Installation
Clone the repository (or navigate to project folder) and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Configure your `.env` parameters:
```env
SECRET_KEY=your-random-session-secret-key
GEMINI_API_KEY=your_gemini_api_key_here
PORT=5000
```

### 4. Run the Application
Start the Flask development server:
```bash
python app.py
```
Open your browser and visit: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🌐 Public Deployment with Ngrok

To generate a secure public URL for external testing, presentations, or remote access:

```bash
python app.py --ngrok
```
The console will display your public HTTPS tunnel URL:
```text
============================================================
🚀 * NGROK TUNNEL ACTIVE *
🌐 Public URL: https://xxxx-xx-xx.ngrok-free.app
💻 Local URL:  http://127.0.0.1:5000
============================================================
```

---

## 🔌 API Reference

All `/api/*` routes are protected and require user authentication.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Renders the dashboard UI (requires login) |
| `GET` | `/register` / `POST` | User registration |
| `GET` | `/login` / `POST` | User login authentication |
| `GET` | `/logout` | Signs out the current user session |
| `GET` | `/api/data?month=YYYY-MM` | Returns user's monthly income, expenses, goals, analytics, and insights |
| `POST` | `/api/income` | Records an income stream (`{ month, source, amount, date }`) |
| `DELETE`| `/api/income/<id>` | Deletes an income record |
| `POST` | `/api/expense` | Logs an expense (`{ month, category, amount, description, date }`) |
| `DELETE`| `/api/expense/<id>` | Deletes an expense transaction |
| `GET` | `/api/goals` | Lists all active savings goals |
| `POST` | `/api/goals` | Creates a new savings goal (`{ name, target_amount, deadline }`) |
| `POST` | `/api/goals/<id>/contribute` | Contributes funds to a goal (`{ amount }`) |
| `DELETE`| `/api/goals/<id>` | Deletes a savings goal |
| `GET` | `/api/export/csv?month=YYYY-MM` | Downloads monthly financial summary CSV |

---

## 🧪 Running Automated Tests

Run the automated test suite to verify authentication, scoped data isolation, multi-source income, goals, and exports:
```powershell
python -c "import sys; sys.path.insert(0, '.'); from scratch.test_app import *"
```
*(or run the provided test script)*
