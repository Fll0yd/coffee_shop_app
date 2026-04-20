# ☕ Coffee Shop Ordering App

An interactive desktop coffee ordering application built with Python + Tkinter, featuring real-time order building, status tracking, and persistent order storage using SQLite.

This project simulates a small coffee shop system where users can:

Place orders
Track preparation time
View order history
Manage order lifecycle (Queued → Preparing → Ready)

## 🚀 Features

### 🧾 Order Management
Dynamic item selection with quantity inputs
Real-time subtotal and total calculation
Order preview before submission
Input validation and error handling

### ⏱️ Order Lifecycle Tracking
Automatic status transitions:
Queued → Preparing → Ready
Live countdown timer for active orders
Visual feedback when orders are ready

### 🗂️ Persistent Storage
SQLite database (coffee_shop.db)
Stores:
Customer name
Order items (JSON)
Total cost
Prep time
Status
Timestamps

### 📜 Order History Panel
Displays all past orders
Click to view detailed breakdown
Sorted by most recent

### 🎨 UI / UX
Clean Tkinter layout using grid()
Structured panels (Order / History / Timer)
Optional background image support

## 📁 Project Structure
CoffeeShop/
├── coffee_shop_app.py      # Main application (run this)
├── coffee_shop.db          # Auto-created database (after first run)
└── assets/
    └── background.png      # Optional UI background image

## ▶️ How to Run

### 1. Requirements
Python 3.10+

### 2. Run the app
python coffee_shop_app.py

No external dependencies required.

## 🧠 How It Works (Quick Breakdown)

### Architecture

The app is structured into 3 main layers:

Layer	Responsibility
UI (Tkinter)	Handles layout, user interaction
Service Layer	Business logic (validation, calculations)
Repository (SQLite)	Data persistence


## Order Flow
Enter customer name
Add items + quantities
Preview order
Submit order
Order is saved → timer starts → status updates automatically
Order appears in history panel


## 🛠️ Future Improvements

When you come back to this project, here’s where the real upgrades are:


### 🔥 High Impact Upgrades (Do These First)

1. Convert to Multi-Screen App
Break UI into:
Order Screen
Admin Dashboard
Order Queue View

2. Add “Barista Mode”
Create a screen where:
Orders are listed
Buttons:
“Start Preparing”
“Mark Ready”

3. Turn This Into a Web App
Rebuild using:
Flask or FastAPI
HTML/CSS frontend
Same logic, new interface.

### ⚙️ Medium-Level Improvements

4. Pricing & Menu System
Move menu into JSON or DB
Allow dynamic editing
Add categories (Hot / Cold / Specialty)

5. Receipt Generation
Export order as:
Text file
PDF

6. Add Search & Filtering
Filter history by:
Customer
Status
Date

7. Better Timer System
Persist timers across app restarts
Recalculate remaining time from DB


### 🎯 Advanced / Resume-Level Upgrades

8. Add User Accounts
Login system
Roles:
Customer
Employee
Admin

9. API Layer
Expose endpoints:
Create order
Get orders
Update status

10. Integrate AI
Suggest drinks based on past orders
Predict prep time based on load
Voice ordering assistant


## 🧪 Known Limitations
Single-user desktop app (no concurrency)
Timers reset if app closes
No authentication system
UI still basic (Tkinter constraints)
