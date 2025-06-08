import sqlite3
from datetime import datetime
import shutil

# Backup the current database
shutil.copy('tutors.db', f'tutors_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')

# Connect to the database
conn = sqlite3.connect('tutors.db')
cursor = conn.cursor()

# Add new column for cancellation timestamp
try:
    cursor.execute('ALTER TABLE bookings ADD COLUMN cancelled_at TIMESTAMP')
except sqlite3.OperationalError:
    print("Column cancelled_at already exists")

# Update cancelled_at for rejected bookings
cursor.execute('''
    UPDATE bookings 
    SET cancelled_at = approved_at 
    WHERE status = 'rejected' AND cancelled_at IS NULL
''')

conn.commit()
conn.close()

print("Migration completed successfully!") 