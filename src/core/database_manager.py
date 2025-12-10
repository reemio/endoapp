# ENHANCED DATABASE_MANAGER.PY - LRU DROPDOWN HISTORY SYSTEM
# FILE: src/core/database_manager.py

from PySide6.QtCore import QObject, Signal
import sqlite3
from pathlib import Path
import logging
from datetime import datetime
import json
import traceback


class DatabaseManager(QObject):
   """DATABASE MANAGER WITH ENHANCED LRU DROPDOWN HISTORY"""
   
   # SIGNALS
   data_changed = Signal(str, dict)
   error_occurred = Signal(str)
   patient_added = Signal(int)
   report_added = Signal(int)
   
   def __init__(self):
       """INITIALIZE DATABASE MANAGER"""
       super().__init__()
       self.setup_logging()
       self.setup_database()
       
   def setup_logging(self):
       """SETUP LOGGING CONFIGURATION"""
       log_path = Path("data/logs/database.log")
       log_path.parent.mkdir(parents=True, exist_ok=True)
       
       logging.basicConfig(
           filename=str(log_path),
           level=logging.INFO,
           format="%(asctime)s - %(levelname)s - %(message)s",
       )
   
   def setup_database(self):
       """INITIALIZE DATABASE, TABLES, AND INDEXES"""
       try:
           self.db_path = Path("data/database/endoscopy.db")
           self.db_path.parent.mkdir(parents=True, exist_ok=True)
           
           with sqlite3.connect(str(self.db_path)) as conn:
               self.create_tables(conn)
               self.create_indices(conn)
               self.setup_triggers(conn)
           
           self.backup_path = Path("data/database/backups")
           self.backup_path.mkdir(parents=True, exist_ok=True)
           
           logging.info("Database setup completed successfully")
       except Exception as e:
           error_msg = f"Database setup failed: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
   
   def create_tables(self, conn):
       """CREATE ALL NECESSARY DATABASE TABLES"""
       tables = {
           "patients": """
               CREATE TABLE IF NOT EXISTS patients (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   patient_id TEXT UNIQUE NOT NULL,
                   hospital_name TEXT NOT NULL,
                   name TEXT NOT NULL,
                   gender TEXT CHECK(gender IN ('MALE', 'FEMALE')) NOT NULL,
                   age INTEGER CHECK(age >= 0 AND age <= 150),
                   referring_doctor TEXT,
                   medication TEXT,
                   doctor TEXT NOT NULL,
                   designation TEXT,
                   date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   notes TEXT
               )
           """,
           "reports": """
               CREATE TABLE IF NOT EXISTS reports (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   report_id TEXT UNIQUE NOT NULL,
                   patient_id TEXT NOT NULL,
                   report_title TEXT DEFAULT 'ENDOSCOPY REPORT',
                   indication TEXT,
                   findings TEXT,
                   conclusions TEXT,
                   recommendations TEXT,
                   report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'final', 'amended')),
                   last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                       ON DELETE CASCADE
                       ON UPDATE CASCADE
               )
           """,
           "images": """
               CREATE TABLE IF NOT EXISTS images (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   report_id TEXT NOT NULL,
                   image_path TEXT NOT NULL,
                   label TEXT,
                   sequence INTEGER NOT NULL,
                   capture_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (report_id) REFERENCES reports (report_id)
                       ON DELETE CASCADE
                       ON UPDATE CASCADE
               )
           """,
           "dropdown_history": """
               CREATE TABLE IF NOT EXISTS dropdown_history (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   field_name TEXT NOT NULL,
                   value TEXT NOT NULL,
                   frequency INTEGER DEFAULT 1,
                   last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   UNIQUE(field_name, value)
               )
           """,
           "audit_log": """
               CREATE TABLE IF NOT EXISTS audit_log (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   action_type TEXT NOT NULL,
                   table_name TEXT NOT NULL,
                   record_id TEXT NOT NULL,
                   old_value TEXT,
                   new_value TEXT,
                   timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )
           """,
       }
       
       cursor = conn.cursor()
       for table_name, query in tables.items():
           cursor.execute(query)
       conn.commit()
   
   def create_indices(self, conn):
       """CREATE DATABASE INDICES FOR PERFORMANCE"""
       indices = [
           "CREATE INDEX IF NOT EXISTS idx_patient_id ON patients(patient_id)",
           "CREATE INDEX IF NOT EXISTS idx_report_patient ON reports(patient_id)",
           "CREATE INDEX IF NOT EXISTS idx_image_report ON images(report_id)",
           "CREATE INDEX IF NOT EXISTS idx_dropdown_field ON dropdown_history(field_name)",
           "CREATE INDEX IF NOT EXISTS idx_dropdown_frequency ON dropdown_history(field_name, frequency DESC, last_used DESC)",
           "CREATE INDEX IF NOT EXISTS idx_audit_record ON audit_log(record_id)",
       ]
       
       cursor = conn.cursor()
       for index_query in indices:
           cursor.execute(index_query)
       conn.commit()
   
   def setup_triggers(self, conn):
       """SETUP DATABASE TRIGGERS FOR DATA INTEGRITY"""
       triggers = {
           "update_patient_timestamp": """
               CREATE TRIGGER IF NOT EXISTS update_patient_timestamp 
               AFTER UPDATE ON patients
               BEGIN
                   UPDATE patients SET last_modified = CURRENT_TIMESTAMP 
                   WHERE id = NEW.id;
               END;
           """,
           "update_report_timestamp": """
               CREATE TRIGGER IF NOT EXISTS update_report_timestamp 
               AFTER UPDATE ON reports
               BEGIN
                   UPDATE reports SET last_modified = CURRENT_TIMESTAMP 
                   WHERE id = NEW.id;
               END;
           """,
       }
       
       cursor = conn.cursor()
       for trigger_name, query in triggers.items():
           cursor.execute(query)
       conn.commit()
   
   # PATIENT MANAGEMENT METHODS
   
   def add_patient(self, patient_data):
       """ADD NEW PATIENT TO DATABASE"""
       try:
           query = """
               INSERT INTO patients (
                   patient_id, hospital_name, name, gender, age,
                   referring_doctor, medication, doctor, designation
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           """
           
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               cursor.execute(
                   query,
                   (
                       patient_data["patient_id"],
                       patient_data["hospital_name"],
                       patient_data["name"],
                       patient_data["gender"],
                       patient_data["age"],
                       patient_data["referring_doctor"],
                       patient_data["medication"],
                       patient_data["doctor"],
                       patient_data["designation"],
                   ),
               )
               
               patient_id = cursor.lastrowid
               conn.commit()
               
               self.data_changed.emit("patients", patient_data)
               self.patient_added.emit(patient_id)
               logging.info(f"Added new patient: {patient_data['patient_id']}")
               
               return patient_id
               
       except sqlite3.IntegrityError:
           error_msg = f"Patient ID already exists: {patient_data['patient_id']}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
       except Exception as e:
           error_msg = f"Error adding patient: {str(e)}"
           logging.error(f"{error_msg}\n{traceback.format_exc()}")
           self.error_occurred.emit(error_msg)
           raise
   
   def update_patient(self, patient_id, patient_data):
       """UPDATE EXISTING PATIENT"""
       try:
           query = """
               UPDATE patients
               SET hospital_name = ?, name = ?, gender = ?, age = ?,
                   referring_doctor = ?, medication = ?, doctor = ?, designation = ?
               WHERE patient_id = ?
           """
           
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               cursor.execute(
                   query,
                   (
                       patient_data["hospital_name"],
                       patient_data["name"],
                       patient_data["gender"],
                       patient_data["age"],
                       patient_data["referring_doctor"],
                       patient_data["medication"],
                       patient_data["doctor"],
                       patient_data["designation"],
                       patient_id,
                   ),
               )
               conn.commit()
               
               self.data_changed.emit("patients", patient_data)
               logging.info(f"Updated patient: {patient_id}")
               
               return cursor.rowcount > 0
               
       except Exception as e:
           error_msg = f"Error updating patient: {str(e)}"
           logging.error(f"{error_msg}\n{traceback.format_exc()}")
           self.error_occurred.emit(error_msg)
           raise
   
   def get_patient(self, patient_id):
       """GET PATIENT DATA BY ID"""
       try:
           query = "SELECT * FROM patients WHERE patient_id = ?"
           
           with sqlite3.connect(str(self.db_path)) as conn:
               conn.row_factory = sqlite3.Row
               cursor = conn.cursor()
               cursor.execute(query, (patient_id,))
               row = cursor.fetchone()
               
               if row:
                   return dict(row)
               return None
               
       except Exception as e:
           error_msg = f"Error retrieving patient: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
   
   def search_patients(self, criteria, limit=None, offset=None):
       """SEARCH PATIENTS BY VARIOUS CRITERIA"""
       try:
           query_parts = []
           params = []
           
           if "patient_id" in criteria:
               query_parts.append("p.patient_id LIKE ?")
               params.append(f"%{criteria['patient_id']}%")
           
           if "name" in criteria:
               query_parts.append("p.name LIKE ?")
               params.append(f"%{criteria['name']}%")
           
           if "doctor" in criteria:
               query_parts.append("p.doctor LIKE ?")
               params.append(f"%{criteria['doctor']}%")
           
           if "hospital" in criteria:
               query_parts.append("p.hospital_name LIKE ?")
               params.append(f"%{criteria['hospital']}%")
           
           visit_date_expr = "datetime(COALESCE(latest_reports.latest_report_date, p.date_created))"
           if "date_from" in criteria and "date_to" in criteria:
               query_parts.append(f"{visit_date_expr} BETWEEN datetime(?) AND datetime(?)")
               params.append(f"{criteria['date_from']} 00:00:00")
               params.append(f"{criteria['date_to']} 23:59:59")
           
           limit_clause = ""
           if limit is not None:
               try:
                   limit_value = int(limit)
                   if limit_value > 0:
                       limit_clause = f" LIMIT {limit_value}"
                       if offset:
                           offset_value = max(0, int(offset))
                           limit_clause += f" OFFSET {offset_value}"
               except (TypeError, ValueError):
                   logging.warning(f"Invalid limit/offset supplied to search_patients: limit={limit}, offset={offset}")
           
           base_query = """
               SELECT
                   p.patient_id,
                   p.hospital_name,
                   p.name,
                   p.gender,
                   p.age,
                   p.referring_doctor,
                   p.medication,
                   p.doctor,
                   p.designation,
                   p.date_created,
                   COALESCE(latest_reports.latest_report_date, p.date_created) AS visit_date
               FROM patients p
               LEFT JOIN (
                   SELECT patient_id, MAX(report_date) AS latest_report_date
                   FROM reports
                   GROUP BY patient_id
               ) AS latest_reports ON latest_reports.patient_id = p.patient_id
           """
           
           if query_parts:
               base_query += " WHERE " + " AND ".join(query_parts)
           
           query = f"{base_query} ORDER BY {visit_date_expr} DESC{limit_clause}"
           
           with sqlite3.connect(str(self.db_path)) as conn:
               conn.row_factory = sqlite3.Row
               cursor = conn.cursor()
               cursor.execute(query, params)
               rows = cursor.fetchall()
               
               return [dict(row) for row in rows]
               
       except Exception as e:
           error_msg = f"Error searching patients: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
   
   # REPORT MANAGEMENT METHODS
   
   def add_report(self, report_data):
       """ADD NEW REPORT"""
       try:
           query = """
               INSERT INTO reports (
                   report_id, patient_id, report_title, indication, 
                   findings, conclusions, recommendations, report_date
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           """
           
           report_date_value = report_data.get("report_date")
           if not report_date_value:
               report_date_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
           
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               cursor.execute(
                   query,
                   (
                       report_data["report_id"],
                       report_data["patient_id"],
                       report_data.get("report_title", "ENDOSCOPY REPORT"),
                       report_data.get("indication", ""),
                       report_data.get("findings", ""),
                       report_data.get("conclusions", ""),
                       report_data.get("recommendations", ""),
                       report_date_value,
                   ),
               )
               
               report_id = cursor.lastrowid
               conn.commit()
               
               self.data_changed.emit("reports", report_data)
               self.report_added.emit(report_id)
               logging.info(f"Added new report: {report_data['report_id']}")
               
               return report_id
               
       except sqlite3.IntegrityError:
           error_msg = f"Report ID already exists: {report_data['report_id']}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
       except Exception as e:
           error_msg = f"Error adding report: {str(e)}"
           logging.error(f"{error_msg}\n{traceback.format_exc()}")
           self.error_occurred.emit(error_msg)
           raise
   
   def update_report(self, report_id, report_data):
       """UPDATE EXISTING REPORT"""
       try:
           query = """
               UPDATE reports
               SET report_title = ?, indication = ?, findings = ?, 
                   conclusions = ?, recommendations = ?, report_date = ?
               WHERE report_id = ?
           """
           
           report_date_value = report_data.get("report_date")
           if not report_date_value:
               report_date_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
           
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               cursor.execute(
                   query,
                   (
                       report_data.get("report_title", "ENDOSCOPY REPORT"),
                       report_data.get("indication", ""),
                       report_data.get("findings", ""),
                       report_data.get("conclusions", ""),
                       report_data.get("recommendations", ""),
                       report_date_value,
                       report_id,
                   ),
               )
               conn.commit()
               
               self.data_changed.emit("reports", report_data)
               logging.info(f"Updated report: {report_id}")
               
               return cursor.rowcount > 0
               
       except Exception as e:
           error_msg = f"Error updating report: {str(e)}"
           logging.error(f"{error_msg}\n{traceback.format_exc()}")
           self.error_occurred.emit(error_msg)
           raise
   
   def get_report(self, report_id=None, patient_id=None):
       """GET REPORT BY ID OR PATIENT ID"""
       try:
           if report_id:
               query = "SELECT * FROM reports WHERE report_id = ?"
               # Ensure report_id is scalar for the query
               current_report_id = report_id
               if isinstance(current_report_id, tuple):
                   logging.warning(f"DatabaseManager.get_report: report_id was a tuple {current_report_id}, using first element.")
                   current_report_id = current_report_id[0]
               if not isinstance(current_report_id, (int, str)) and current_report_id is not None:
                   logging.error(f"DatabaseManager.get_report: report_id '{current_report_id}' is not a valid type for query. Raising error.")
                   raise ValueError(f"Invalid report_id type: {type(current_report_id)}")
               params = (current_report_id,)
           elif patient_id:
               query = "SELECT * FROM reports WHERE patient_id = ? ORDER BY report_date DESC LIMIT 1"
               params = (patient_id,)
           else:
               raise ValueError("Either report_id or patient_id must be provided")
           
           with sqlite3.connect(str(self.db_path)) as conn:
               conn.row_factory = sqlite3.Row
               cursor = conn.cursor()
               cursor.execute(query, params)
               row = cursor.fetchone()
               
               if row:
                   return dict(row)
               return None
               
       except Exception as e:
           error_msg = f"Error retrieving report: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise

   def search_reports(self, criteria, limit=None, offset=None):
       """SEARCH REPORTS BY VARIOUS CRITERIA"""
       try:
           query_parts = []
           params = []
           
           if "report_id" in criteria:
               query_parts.append("report_id LIKE ?")
               params.append(f"%{criteria['report_id']}%")
           
           if "patient_id" in criteria:
               query_parts.append("patient_id LIKE ?")
               params.append(f"%{criteria['patient_id']}%")
           
           if "date_from" in criteria and "date_to" in criteria:
               query_parts.append("datetime(report_date) BETWEEN datetime(?) AND datetime(?)")
               params.append(f"{criteria['date_from']} 00:00:00")
               params.append(f"{criteria['date_to']} 23:59:59")
           
           if "status" in criteria:
               query_parts.append("status = ?")
               params.append(criteria["status"])
           
           limit_clause = ""
           if limit is not None:
               try:
                   limit_value = int(limit)
                   if limit_value > 0:
                       limit_clause = f" LIMIT {limit_value}"
                       if offset:
                           offset_value = max(0, int(offset))
                           limit_clause += f" OFFSET {offset_value}"
               except (TypeError, ValueError):
                   logging.warning(f"Invalid limit/offset supplied to search_reports: limit={limit}, offset={offset}")
           
           base_query = "SELECT * FROM reports"
           if query_parts:
               base_query += " WHERE " + " AND ".join(query_parts)
           
           query = f"{base_query} ORDER BY datetime(report_date) DESC{limit_clause}"
           
           with sqlite3.connect(str(self.db_path)) as conn:
               conn.row_factory = sqlite3.Row
               cursor = conn.cursor()
               cursor.execute(query, params)
               rows = cursor.fetchall()
               
               return [dict(row) for row in rows]
               
       except Exception as e:
           error_msg = f"Error searching reports: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
   
   # IMAGE MANAGEMENT METHODS
   
   def add_report_image(self, report_id, image_path, label, sequence):
       """ADD IMAGE TO REPORT"""
       try:
           query = """
               INSERT INTO images (report_id, image_path, label, sequence)
               VALUES (?, ?, ?, ?)
           """
           
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               cursor.execute(query, (report_id, image_path, label, sequence))
               
               image_id = cursor.lastrowid
               conn.commit()
               
               image_data = {
                   "report_id": report_id,
                   "image_path": image_path,
                   "label": label,
                   "sequence": sequence,
               }
               
               self.data_changed.emit("images", image_data)
               logging.info(f"Added report image: {image_id}")
               
               return image_id
               
       except Exception as e:
           error_msg = f"Error adding report image: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
   
   def get_report_images(self, report_id):
       """GET ALL IMAGES FOR REPORT"""
       try:
           query = "SELECT * FROM images WHERE report_id = ? ORDER BY sequence"
           
           with sqlite3.connect(str(self.db_path)) as conn:
               conn.row_factory = sqlite3.Row
               cursor = conn.cursor()
               cursor.execute(query, (report_id,))
               rows = cursor.fetchall()
               
               images = [dict(row) for row in rows]
               
               # CONVERT TO (PATH, LABEL) PAIRS FOR PDF GENERATOR
               return [(img["image_path"], img["label"]) for img in images]
               
       except Exception as e:
           error_msg = f"Error retrieving report images: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           raise
   
   # ENHANCED LRU DROPDOWN HISTORY MANAGEMENT
   
   def update_dropdown_history(self, field_name, value):
       """UPDATE DROPDOWN HISTORY WITH LRU ALGORITHM (MAX 20 ENTRIES)"""
       if not value or not field_name:
           return
           
       try:
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               
               # CHECK IF ENTRY EXISTS
               cursor.execute(
                   "SELECT id, frequency FROM dropdown_history WHERE field_name = ? AND value = ?",
                   (field_name, value)
               )
               existing = cursor.fetchone()
               
               if existing:
                   # UPDATE EXISTING ENTRY
                   cursor.execute(
                       """
                       UPDATE dropdown_history
                       SET frequency = frequency + 1, last_used = CURRENT_TIMESTAMP
                       WHERE id = ?
                       """,
                       (existing[0],)
                   )
               else:
                   # CHECK IF WE NEED TO REMOVE OLD ENTRIES (LRU WITH MAX 20)
                   cursor.execute(
                       "SELECT COUNT(*) FROM dropdown_history WHERE field_name = ?",
                       (field_name,)
                   )
                   count = cursor.fetchone()[0]
                   
                   if count >= 20:
                       # REMOVE LEAST RECENTLY USED ENTRY
                       cursor.execute(
                           """
                           DELETE FROM dropdown_history 
                           WHERE field_name = ? AND id = (
                               SELECT id FROM dropdown_history 
                               WHERE field_name = ? 
                               ORDER BY frequency ASC, last_used ASC 
                               LIMIT 1
                           )
                           """,
                           (field_name, field_name)
                       )
                   
                   # INSERT NEW ENTRY
                   cursor.execute(
                       """
                       INSERT INTO dropdown_history (field_name, value, frequency, last_used)
                       VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                       """,
                       (field_name, value)
                   )
               
               conn.commit()
               
       except Exception as e:
           # DON'T EMIT ERROR - THIS IS NON-CRITICAL
           logging.warning(f"Error updating dropdown history: {str(e)}")
   
   def get_dropdown_history(self, field_name, limit=20):
       """GET DROPDOWN HISTORY FOR FIELD (ORDERED BY FREQUENCY AND RECENCY)"""
       try:
           query = """
               SELECT value
               FROM dropdown_history
               WHERE field_name = ?
               ORDER BY frequency DESC, last_used DESC
               LIMIT ?
           """
           
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               cursor.execute(query, (field_name, limit))
               rows = cursor.fetchall()
               
               return [row[0] for row in rows]
               
       except Exception as e:
           logging.warning(f"Error getting dropdown history: {str(e)}")
           return []

   def delete_dropdown_entry(self, field_name, value):
       """DELETE A SPECIFIC ENTRY FROM DROPDOWN HISTORY"""
       if not field_name or not value:
           return
       try:
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               cursor.execute(
                   "DELETE FROM dropdown_history WHERE field_name = ? AND value = ?",
                   (field_name, value)
               )
               conn.commit()
               logging.info(f"Deleted dropdown entry '{value}' for field '{field_name}'")
       except Exception as e:
           logging.warning(f"Error deleting dropdown history entry '{value}' for '{field_name}': {str(e)}")
   
   def clear_dropdown_history(self, field_name=None):
       """CLEAR DROPDOWN HISTORY FOR FIELD OR ALL FIELDS"""
       try:
           with sqlite3.connect(str(self.db_path)) as conn:
               cursor = conn.cursor()
               
               if field_name:
                   cursor.execute("DELETE FROM dropdown_history WHERE field_name = ?", (field_name,))
               else:
                   cursor.execute("DELETE FROM dropdown_history")
               
               conn.commit()
               logging.info(f"Cleared dropdown history for: {field_name or 'all fields'}")
               
       except Exception as e:
           error_msg = f"Error clearing dropdown history: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
   
   def get_dropdown_statistics(self):
       """GET DROPDOWN USAGE STATISTICS"""
       try:
           query = """
               SELECT field_name, COUNT(*) as entry_count, 
                      SUM(frequency) as total_usage,
                      MAX(last_used) as last_used
               FROM dropdown_history 
               GROUP BY field_name
               ORDER BY total_usage DESC
           """
           
           with sqlite3.connect(str(self.db_path)) as conn:
               conn.row_factory = sqlite3.Row
               cursor = conn.cursor()
               cursor.execute(query)
               rows = cursor.fetchall()
               
               return [dict(row) for row in rows]
               
       except Exception as e:
           logging.error(f"Error getting dropdown statistics: {str(e)}")
           return []
   
   # DATABASE MAINTENANCE
   
   def create_backup(self):
       """CREATE DATABASE BACKUP"""
       try:
           backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           backup_file = self.backup_path / f"endoscopy_backup_{backup_timestamp}.db"
           
           # CONNECT TO SOURCE AND DESTINATION DATABASES
           source = sqlite3.connect(str(self.db_path))
           destination = sqlite3.connect(str(backup_file))
           
           # CREATE BACKUP
           source.backup(destination)
           
           # CLOSE CONNECTIONS
           source.close()
           destination.close()
           
           logging.info(f"Database backup created: {backup_file}")
           return str(backup_file)
           
       except Exception as e:
           error_msg = f"Error creating database backup: {str(e)}"
           logging.error(error_msg)
           self.error_occurred.emit(error_msg)
           return None

   def close(self):
       """CLOSE DATABASE CONNECTIONS"""
       try:
           # CREATE CONNECTION TO CLOSE ANY ACTIVE TRANSACTIONS
           with sqlite3.connect(str(self.db_path)) as conn:
               # EXECUTE SIMPLE QUERY TO ENSURE PENDING TRANSACTIONS ARE COMMITTED
               conn.execute("SELECT 1")
               conn.commit()
           
           logging.info("Database connections closed")
           return True
           
       except Exception as e:
           error_msg = f"Error closing database connections: {str(e)}"
           logging.error(error_msg)
           return False
