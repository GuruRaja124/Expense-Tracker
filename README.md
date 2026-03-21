# Expense Tracker

A personal expense tracker web application built with Flask and SQLite. Users can register, log in, record expenses, and view spending summaries on a dashboard.

## Features

- User registration and login
- Add, view, and delete expenses
- Dashboard with daily, monthly, quarterly, and yearly spending totals
- Category-wise spending breakdown with progress bars
- Recent expenses overview
- Responsive design using Bootstrap 5
- jQuery form validation and interactive UI

## Technologies Used

| Layer       | Technology              |
|-------------|-------------------------|
| Frontend    | HTML5, Bootstrap 5, CSS |
| Interaction | JavaScript, jQuery      |
| Backend     | Python, Flask           |
| Database    | SQLite                  |
| Templating  | Jinja2                  |

## Project Structure

```
expense-tracker/
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── images/
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_expense.html
│   └── expenses.html
│
├── app.py
├── database.db
├── requirements.txt
└── README.md
```

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/expense-tracker.git
   cd expense-tracker
   ```

2. **Create a virtual environment** (optional but recommended)

   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**

   ```bash
   python app.py
   ```

5. Open your browser and go to `http://127.0.0.1:5000`

## Screenshots

### Login Page
*(Add screenshot here)*

### Dashboard
*(Add screenshot here)*

### Add Expense
*(Add screenshot here)*

### Expense Table
*(Add screenshot here)*
