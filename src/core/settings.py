import json
from pathlib import Path


class Settings:
    def __init__(self):
        self.settings_file = Path("data/settings.json")
        self.default_settings = {
            "theme": "light",
            "hospital_name": "Medical Center",
            "auto_save_interval": 300,  # 5 minutes
            "default_save_path": "data/reports",
            "camera_settings": {"default_device": 0, "resolution": "1920x1080"},
            "patient_id_counters": {},  # Track IDs per hospital
        }
        self.current_settings = self.load_settings()

    def load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.default_settings.copy()
        return self.default_settings.copy()

    def save_settings(self):
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_file, "w") as f:
            json.dump(self.current_settings, f, indent=4)

    def get(self, key, default=None):
        return self.current_settings.get(key, default)

    def set(self, key, value):
        self.current_settings[key] = value
        self.save_settings()
        
    def get_next_patient_id(self, hospital=None):
        """Generate an incremental patient ID in format 0001/25 per hospital"""
        import time
        from datetime import datetime
        
        # Get current year's last two digits
        current_year = datetime.now().strftime("%y")
        
        # If no hospital is specified or empty, use a default
        if not hospital:
            hospital = self.get("hospital_name", "General")
        
        # Initialize patient_id_counters if not present
        if "patient_id_counters" not in self.current_settings:
            self.current_settings["patient_id_counters"] = {}
            
        hospital_counters = self.current_settings["patient_id_counters"]
        
        # Initialize this hospital's counter if not present
        if hospital not in hospital_counters:
            hospital_counters[hospital] = {
                "year": current_year,
                "counter": 0
            }
        
        # Check if year has changed, reset counter if so
        if hospital_counters[hospital]["year"] != current_year:
            hospital_counters[hospital]["year"] = current_year
            hospital_counters[hospital]["counter"] = 0
        
        # Increment the counter
        hospital_counters[hospital]["counter"] += 1
        counter = hospital_counters[hospital]["counter"]
        
        # Format: 0001/25 (four digits, slash, two-digit year)
        patient_id = f"{counter:04d}/{current_year}"
        
        # Save the updated counter
        self.save_settings()
        
        return patient_id
