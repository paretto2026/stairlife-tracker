# StairLife Tracker

**StairLife Tracker** is a lightweight web application for tracking daily stair climbing and estimating potential long-term health impact based on observational research.

The project demonstrates a **clean modular Python architecture**, a **minimal Flask stack**, and a **transparent analytics layer** built on top of a simple SQLite database.

The design goal is simplicity, inspectability, and extensibility.

---

# Demo Concept

The application allows a user to:

1. record daily stair climbs
2. view personal activity statistics
3. see weekly and monthly activity trends
4. estimate potential health effects using an observational model
5. export their data for further analysis

Everything runs locally with no external APIs.

---

# Key Features

## Daily Tracking

* record stair climbs per day
* overwrite entries for the same date
* persistent local storage

## Activity Statistics

Calculated metrics include:

* total climbs
* tracked days
* active days
* average climbs per day
* activity consistency
* average vs. maximum performance

## Health Impact Estimation

The application includes a **v0 observational model** derived from:

**UK Biobank stair climbing study**

Sanchez-Lastra et al., 2021

The model maps:

```
average climbs per day
```

to exposure categories reported in the study and displays:

* estimated life days gained (RMST-based)
* all-cause mortality risk reduction
* cardiovascular mortality risk reduction

Important: this is **not medical advice**, only an illustrative model.

## Trend Analysis

Visual summaries include:

**Weekly totals**

* last 8 weeks

**Monthly totals**

* last 12 months

Displayed using simple proportional bars.

## Data Management

* delete individual entries
* export full history to CSV

Example CSV structure:

```id="csvexample"
date,year,month,weekday,climbs
2026-03-05,2026,Mar,Thu,12
2026-03-04,2026,Mar,Wed,8
```

---

# Architecture

The project uses a **layered modular architecture**.

```
Presentation Layer
│
├── templates
│   └── HTML + Jinja2
│
├── static
│   └── CSS
│
Application Layer
│
├── routes
│   └── Flask blueprints
│
Business Logic
│
├── services
│   ├── stats_service
│   ├── trends_service
│   └── health_model
│
Data Layer
│
└── models
    └── database
```

Responsibilities are clearly separated:

| Layer     | Responsibility             |
| --------- | -------------------------- |
| routes    | HTTP endpoints             |
| services  | analytics and calculations |
| models    | database access            |
| templates | UI rendering               |

This structure keeps the application maintainable even as it grows.

---

# Project Structure

```id="projecttree"
stairlife-tracker
│
├── app.py
│
├── models
│   └── database.py
│
├── routes
│   └── main_routes.py
│
├── services
│   ├── health_model.py
│   ├── stats_service.py
│   └── trends_service.py
│
├── templates
│   ├── base.html
│   └── index.html
│
├── static
│   └── style.css
│
├── stairlife.db
├── requirements.txt
└── README.md
```

---

# Installation

Clone the repository:

```id="clonecmd"
git clone <repository-url>
cd stairlife-tracker
```

Create a virtual environment:

```id="venvcreate"
python -m venv .venv
```

Activate it:

Linux / macOS

```id="activate1"
source .venv/bin/activate
```

Windows

```id="activate2"
.venv\Scripts\activate
```

Install dependencies:

```id="pipinstall"
pip install -r requirements.txt
```

---

# Running the Application

Start the development server:

```id="runflask"
flask --app app run
```

Open:

```
http://127.0.0.1:5000
```

The database file `stairlife.db` will be created automatically.

---

# Data Model

## profile

Single-row table storing user attributes.

Fields:

* age
* weight
* height
* sex

## entries

Daily activity records.

Fields:

* entry_date (PRIMARY KEY)
* climbs

Re-entering a date updates the record.

---

# Health Model (v0)

Exposure categories derived from observational study:

| Flights per day | Category  |
| --------------- | --------- |
| 0               | baseline  |
| 1–5             | low       |
| 6–10            | moderate  |
| 11–15           | high      |
| ≥16             | very high |

Metrics displayed:

* hazard ratio based reductions
* RMST-based life expectancy differences

These values are approximations intended for educational visualization.

---

# Development Goals

The project intentionally avoids heavy frameworks.

Primary goals:

* transparent calculations
* minimal dependencies
* simple architecture
* reproducible local setup
* easy experimentation

---

# Possible Future Improvements

Potential extensions include:

* authentication and multi-user support
* REST API
* Docker deployment
* richer visualization (charts)
* cloud database integration
* mobile-friendly UI
* additional physical activity metrics

---

# License

This project is intended for educational and experimental use.
