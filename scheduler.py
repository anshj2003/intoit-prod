import os
import psycopg2
import pandas as pd
from datetime import datetime
import schedule
import time
from dotenv import load_dotenv
import logging
import pytz

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv('HOST')
DATABASE = os.getenv('DATABASE')
DB_USER = os.getenv('DB_USER')
PASSWORD = os.getenv('PASSWORD')
TIMEZONE = 'America/New_York'  # Set your local time zone

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

        tz = pytz.timezone(TIMEZONE)
        current_time = datetime.now(tz)
        current_day = current_time.strftime('%A')
        current_hour = current_time.hour

        for index, row in bars_df.iterrows():
            bar_name = row['name']
            vibe = row['populartimes']
            line_wait_time = row['time_wait']
            how_crowded = None
            
            if isinstance(vibe, str):
                try:
                    vibe = eval(vibe)
                except Exception as e:
                    logger.error("Error evaluating vibe for bar %s: %s", bar_name, e)
                    vibe = None

            if isinstance(line_wait_time, str):
                try:
                    line_wait_time = eval(line_wait_time)
                except Exception as e:
                    logger.error("Error evaluating line_wait_time for bar %s: %s", bar_name, e)
                    line_wait_time = None

            try:
                if isinstance(vibe, list):
                    day_data = next((day['data'] for day in vibe if day['name'] == current_day), None)
                    if day_data:
                        current_vibe = day_data[current_hour] / 10
                    else:
                        current_vibe = None
                else:
                    current_vibe = None
            except Exception as e:
                logger.error("Error processing vibe for bar %s: %s", bar_name, e)
                current_vibe = None

            # Determine the crowd level based on the vibe value
            if current_vibe is not None:
                if current_vibe <= 2.5:
                    how_crowded = 'empty'
                elif current_vibe > 2.5 and current_vibe <= 5:
                    how_crowded = 'medium/empty'
                elif current_vibe > 5 and current_vibe <= 7.5:
                    how_crowded = 'medium/crowded'
                elif current_vibe > 7.5 and current_vibe <= 9.8:
                    how_crowded = 'crowded'
                elif current_vibe > 9.8 and current_vibe <= 10:
                    how_crowded = 'too crowded'
            
            try:
                if isinstance(line_wait_time, list):
                    day_data = next((day['data'] for day in line_wait_time if day['name'] == current_day), None)
                    if day_data:
                        current_line_wait_time = day_data[current_hour]
                    else:
                        current_line_wait_time = None
                else:
                    current_line_wait_time = None
            except Exception as e:
                logger.error("Error processing line_wait_time for bar %s: %s", bar_name, e)
                current_line_wait_time = None
            
            query = """
                UPDATE bars
                SET vibe = %s, line_wait_time = %s, how_crowded = %s
                WHERE name = %s
            """
            cur.execute(query, (current_vibe, current_line_wait_time, how_crowded, bar_name))
            conn.commit()
        
        cur.close()
        conn.close()
        logger.info("Database updated at %s", datetime.now(tz))
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
