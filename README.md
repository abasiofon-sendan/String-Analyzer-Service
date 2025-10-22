# String-Analyzer-Service

# String Analyzer Service (Django + DRF)

A RESTful API built with **Django REST Framework** that allows users to analyze, filter, and manage strings based on various textual and structural properties.  
It supports direct queries, advanced filters, and even **natural language queries**.

---

### Project Setup
1. **Clone the Repository**  
   ```bash
   git clone git clone https://github.com/your-username/String-Analyzer-Service.git
    cd String-Analyzer-Service
2. **Create a virtual environment**
    python -m venv venv
    source venv/bin/activate
3. Install dependencies
    pip install -r requirements.txt 
4. Run migrations
    python manage.py migrate
5. Start the development server
    python manage.py runserver      

## Tech Stack

     Python 3.13+

    Django 5.2

    Django REST Framework

    SQLite (default)

    Regex & JSONField processing     

## Features

### 🔹 1. Create and Analyze String  
**POST** `/strings/`

Automatically analyzes any string you submit and stores its properties.

#### Request Body
```json
{
  "value": "madam"
}

