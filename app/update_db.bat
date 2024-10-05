REM SET log_file=%cd%\logfile.txt
call D:\vapp\env\Scripts\activate
cd D:\vapp
python db_preparation_thin.py
python voltage_log_processing.py