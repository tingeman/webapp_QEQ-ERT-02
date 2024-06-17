# qeq_ert
Web-app for visualizing health data from QEQ-ERT-02 timelapse station


## Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/yourproject.git
   cd yourproject
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. Create environment-specific `.env` files:
   - Create a `.env.development` file for development settings.
   - Create a `.env.production` file for production settings.
   - **Important:** Open the `.env` files and update the configuration values as needed.

4. Set the `FLASK_ENV` environment variable:
   - For development:
     ```bash
     export FLASK_ENV=development
     ```
   - For production:
     ```bash
     export FLASK_ENV=production
     ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Access settings in modules:
   - Use `app.config` to access configuration values.
   - Example:
     ```python
     from your_project import app
     print(app.config['DEBUG'])
     ```

