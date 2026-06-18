# News Project Application

This is a Django-based web application with a MySQL database backend. Follow the instructions below to build and run the application locally using either a virtual environment (`venv`) or Docker.

---

## 🔐 Security & Database Secrets
To keep this repository secure, sensitive database credentials and passwords are not included in the source code. 

**For Grading Reviewers:** 
A temporary text file containing the exact required database passwords and tokens has been included in the capstone.txt file. Please refer to that file to fill in the required credentials during setup.

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '',  # Add database name here
        'USER': '',  # Add MySQL username here
        'PASSWORD': '',  # Add MySQL password here
        'HOST': 'host.docker.internal',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}
```

---

## 📥 Getting Started (Downloading the Project)

Before setting up your environment, you need to get a local copy of this repository on your computer. You can do this using either of the two methods below:

### Option A: Clone with Git (Recommended)
1. Open your terminal or command prompt.
2. Navigate to the directory where you want to save the project folder.
3. Run the following command to download the repository:
   ```bash
   git clone https://github.com
   ```
4. Move into the newly cloned project directory:
   ```bash
   cd news_project
   ```

### Option B: Download as a ZIP Archive
1. Go to the top of this repository page on GitHub.
2. Click the green **"Code"** button on the right-hand side.
3. Select **"Download ZIP"** from the dropdown menu.
4. Locate the downloaded file on your computer and extract (unzip) it.
5. Open your terminal, command prompt, or code editor inside the newly extracted root folder.

---

## 🛠️ Method 1: Run Locally with `venv` (Virtual Environment)

### Prerequisites
* Python 3.12 installed on your machine
* MySQL Server running locally

### Setup Steps
1. **Navigate to the project root directory:**
   ```bash
   cd news_project
   ```

2. **Create and activate a virtual environment:**
   * **Windows:**
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   * **Mac/Linux:**
     ```bash
     python3 -m venv env
     source env/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Database Secrets:**
   Open `news_project/settings.py` and ensure the `DATABASES` block matches your local MySQL username, database name, and the password provided in the capstone.txt file inside the project folder. Ensure the `HOST` is set to `'127.0.0.1'`.

5. **Run Migrations & Start Server:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
6. Open your browser and navigate to `http://127.0.0.1:8000`.

---

## 🐳 Method 2: Run with Docker (Recommended)

### Prerequisites
* Docker Desktop installed and running

### Setup Steps
1. **Configure Database Secrets for Docker:**
   Open `news_project/settings.py` and locate the `DATABASES` block. Ensure the configuration uses your MySQL credentials from the capstone.txt file and the `HOST` is explicitly set to `'host.docker.internal'` so the container can securely communicate with your machine's database.

2. **Build the Docker Image:**
   ```bash
   docker build -t news_app_image .
   ```

3. **Run the Container:**
   ```bash
   docker run -p 8000:8000 --name news_running_app news_app_image
   ```

4. **Access the Application:**
   Open your browser and navigate to `http://localhost:8000/`.

5. **Stop the Container:**
   ```bash
   docker stop news_running_app
   ```
