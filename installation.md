### Installation

conda create --name webapp_ert python=3.11
conda config --add channels conda-forge
conda config --set channel_priority strict

conda install -c conda-forge dash
conda install -c conda-forge dash-bootstrap-components
conda install pandas numpy ipdb ipython lxml 
conda install pytables chardet pyarrow



# Project Name

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
    
3. Create a .env file:
   - The first time you run the application, it will automatically create a .env file from the .env.example template if it doesn't exist.
   - **Important**: Open the newly created .env file and update the configuration values as needed.

4. Run the application:
    ```bash
    python app.py
    ```