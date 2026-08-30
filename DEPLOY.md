# Deploying AVENTIX

AVENTIX uses a local SQLite database and generates Matplotlib charts dynamically at runtime, saving them to the filesystem. **Therefore, it requires a host with a persistent filesystem.**

We strongly recommend **PythonAnywhere** for a free, persistent deployment.

---

## Primary Recommended Deployment: PythonAnywhere (Free Tier)

PythonAnywhere provides a persistent disk on its free tier, ensuring your SQLite database and chart PNGs survive application restarts.

### Step-by-Step Instructions

1. **Create an Account**: Go to [PythonAnywhere](https://www.pythonanywhere.com/) and create a beginner (free) account.
2. **Open a Bash Console**: From your dashboard, click **Consoles** -> **Bash**.
3. **Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/aventix.git
   cd aventix
   ```
4. **Create a Virtual Environment**:
   ```bash
   mkvirtualenv --python=python3.10 aventix-venv
   ```
   *(Note: The prompt should change to `(aventix-venv)`)*
5. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
6. **Set up the Web App**:
   - Go to the **Web** tab on the PythonAnywhere dashboard.
   - Click **Add a new web app**.
   - Select **Manual configuration** (do *not* select Django, as we already have a project).
   - Select **Python 3.10**.
   - Under the **Virtualenv** section, enter `aventix-venv`.
   - Under the **Code** section, set the **Source code** directory to `/home/<your-username>/aventix`.
7. **Configure WSGI**:
   - In the **Code** section of the Web tab, click the link to edit the **WSGI configuration file**.
   - Delete the default contents and replace it with:
     ```python
     import os
     import sys

     path = '/home/<your-username>/aventix'
     if path not in sys.path:
         sys.path.append(path)

     os.environ['DJANGO_SETTINGS_MODULE'] = 'aventix.settings'

     from django.core.wsgi import get_wsgi_application
     application = get_wsgi_application()
     ```
   - Save the file.
8. **Set Environment Variables**:
   - Still in the **Web** tab, scroll down to the **Environment variables** section (or edit your `.env` file depending on your setup/plan). If on the free tier, you may need to set them directly in the WSGI file before importing `get_wsgi_application`:
     ```python
     os.environ['SECRET_KEY'] = 'your-secure-random-secret-key'
     os.environ['DEBUG'] = 'False'
     os.environ['ALLOWED_HOSTS'] = '<your-username>.pythonanywhere.com'
     ```
9. **Initialize the Database and Static Files**:
   - Go back to your **Bash console** (ensure the virtualenv is active) and run:
     ```bash
     python manage.py migrate
     python manage.py generate_synthetic_data
     python manage.py collectstatic --noinput
     ```
10. **Map Static and Media Files**:
    - In the **Web** tab, scroll down to **Static files**.
    - Add an entry:
      - **URL**: `/static/`
      - **Directory**: `/home/<your-username>/aventix/staticfiles`
    - Add another entry:
      - **URL**: `/media/`
      - **Directory**: `/home/<your-username>/aventix/media`
11. **Reload the App**: Scroll to the top of the Web tab and click the green **Reload** button. Your app is now live!

---

## Alternate Deployment: Render (Free Tier)

**WARNING: Ephemeral Filesystem Limitation**
Render's free web services use an ephemeral filesystem. Every time your app spins down (after inactivity) or redeploys, **all data written to SQLite and all generated Matplotlib charts in the media folder will be permanently wiped.**

Only use this method if you are fine with data resetting constantly (e.g., you will manually re-run `generate_synthetic_data` upon every visit), or if you plan to upgrade to a paid instance with a persistent disk attached.

### Instructions

1. Ensure your repository contains the `Procfile`, `runtime.txt`, and `requirements.txt` included in this project.
2. Sign up for [Render](https://render.com/).
3. Create a new **Web Service** and connect your GitHub repository.
4. Render will automatically detect Python. Set the following:
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command**: `gunicorn aventix.wsgi:application`
5. Go to the **Environment** tab and add:
   - `SECRET_KEY`: (generate a random string)
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `your-app-name.onrender.com`
6. Click **Deploy**.
7. Once deployed, you must open the **Shell** tab in the Render dashboard and run:
   ```bash
   python manage.py migrate
   python manage.py generate_synthetic_data
   ```
   *(Note: You will need to repeat step 7 every time the server restarts on the free tier).*

---

## Serverless Deployment: Vercel

Vercel runs Django as a stateless serverless function. Because of the ephemeral filesystem, we have configured the app to use a remote PostgreSQL database and generate charts as in-memory base64 strings rather than saving them to disk. 

### Instructions

1. **Connect GitHub**: Log into the [Vercel Dashboard](https://vercel.com/) and click **Add New** -> **Project**. Select your GitHub repository.
2. **Configure Database**: Before clicking deploy, go to the **Storage** tab in your Vercel project and add a Postgres (Neon) integration. This will automatically inject a `DATABASE_URL` environment variable into your project.
3. **Environment Variables**: Add the following to your project's Environment Variables:
   - `SECRET_KEY`: (generate a secure random string)
   - `DEBUG`: `False`
   *(Vercel automatically sets the `.vercel.app` domain in `ALLOWED_HOSTS` for you).*
4. **Deploy**: Trigger the deployment.
5. **Initialize Database (Stateless)**: Because the Vercel function is stateless, you should not run management commands directly on the serverless function. Instead, run them from your local machine connected to the remote database:
   - Open a terminal in your local project directory.
   - Run `vercel env pull` to download the `DATABASE_URL` to your local `.env` file.
   - Run migrations against the remote DB: `python manage.py migrate`
   - Generate initial data: `python manage.py generate_synthetic_data`

Your Vercel app will now display the data!
