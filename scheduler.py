import os
import psycopg2
import pandas as pd
from datetime import datetime
import schedule
import time
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv('HOST')
DATABASE = os.getenv('DATABASE')
DB_USER = os.getenv('DB_USER')
PASSWORD = os.getenv('PASSWORD')

def get_db_connection():
    conn = psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=DB_USER,
        password=PASSWORD
    )
    return conn

def update_database():
    try:
        logger.info("Starting database update...")
        input_csv = 'popular_times_database.csv'
        bars_df = pd.read_csv(input_csv)
        
        conn = get_db_connection()
        cur = conn.cursor()

        for index, row in bars_df.iterrows():
            bar_name = row['name']
            vibe = row['populartimes']
            line_wait_time = row['time_wait']
            
            if isinstance(vibe, str):
                try:
                    vibe = eval(vibe)
                except Exception as e:
                    logger.error("Error evaluating vibe for bar %s: %s", bar_name, e)
                    continue

            if isinstance(line_wait_time, str):
                try:
                    line_wait_time = eval(line_wait_time)
                except Exception as e:
                    logger.error("Error evaluating line_wait_time for bar %s: %s", bar_name, e)
                    continue
            
            current_day = datetime.now().strftime('%A')
            current_hour = datetime.now().hour
            
            try:
                if isinstance(vibe, list):
                    current_vibe = next((day['data'][current_hour] for day in vibe if day['name'] == current_day), 0) / 10
                else:
                    current_vibe = 0
            except Exception as e:
                logger.error("Error processing vibe for bar %s: %s", bar_name, e)
                current_vibe = 0
            
            try:
                if isinstance(line_wait_time, list):
                    current_line_wait_time = next((day['data'][current_hour] for day in line_wait_time if day['name'] == current_day), 0)
                else:
                    current_line_wait_time = 0
            except Exception as e:
                logger.error("Error processing line_wait_time for bar %s: %s", bar_name, e)
                current_line_wait_time = 0
            
            query = """
                UPDATE bars
                SET vibe = %s, line_wait_time = %s
                WHERE name = %s
            """
            cur.execute(query, (current_vibe, current_line_wait_time, bar_name))
            conn.commit()
        
        cur.close()
        conn.close()
        logger.info("Database updated at %s", datetime.now())
    except Exception as e:
        logger.error("Error updating database: %s", e)

def run_schedule():
    logger.info("Running initial database update...")
    update_database()  # Update immediately upon starting

    logger.info("Scheduling hourly updates...")
    schedule.every().hour.at(":00").do(update_database)  # Schedule to run at the start of every hour
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    run_schedule()
