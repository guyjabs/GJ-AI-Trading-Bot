import json
import os
from datetime import datetime
import src.utils.logger as logger

class DeveloperLog:
    """
    Manages the 'Developer Journey' log.
    Stores:
    1. Changelog entries (manual or automated from tasks)
    2. Client Events (clicks) - aggregated for display
    """
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.changelog_path = os.path.join(data_dir, "developer_changelog.json")
        self.client_events_path = os.path.join(data_dir, "client_events.json")
        self.ensure_files()

    def ensure_files(self):
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.changelog_path):
            with open(self.changelog_path, 'w') as f:
                json.dump([], f)
        if not os.path.exists(self.client_events_path):
            with open(self.client_events_path, 'w') as f:
                json.dump([], f)

    def log_change(self, title, description, walkthrough_path=None):
        """Log a code change / feature implementation"""
        try:
            entry = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "timestamp": datetime.now().isoformat(),
                "type": "change",
                "title": title,
                "description": description,
                "walkthrough_link": walkthrough_path
            }
            
            with open(self.changelog_path, 'r+') as f:
                data = json.load(f)
                data.append(entry)
                f.seek(0)
                json.dump(data, f, indent=2)
            
            logger.info(f"💾 Logged Developer Change: {title}")
            return True
        except Exception as e:
            logger.error(f"Error logging change: {e}")
            return False

    def log_client_event(self, event_type, details):
        """Log a client interaction (persisted)"""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "event",
                "event_type": event_type,
                "details": details
            }
            
            # Append to file (load-append-save for simplicity, could optimize)
            # For high volume, append-only text file is better, but JSON is easier for frontend
            with open(self.client_events_path, 'r+') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
                
                data.append(entry)
                # Keep last 1000 events to prevent massive file
                if len(data) > 1000:
                    data = data[-1000:]
                    
                f.seek(0)
                f.truncate()
                json.dump(data, f)
                
        except Exception as e:
            logger.error(f"Error logging client event: {e}")

    def get_full_log(self):
        """Return merged chronological log of changes and events"""
        try:
            with open(self.changelog_path, 'r') as f:
                changes = json.load(f)
            
            with open(self.client_events_path, 'r') as f:
                events = json.load(f)
                
            # Merge and sort
            full_log = changes + events
            full_log.sort(key=lambda x: x['timestamp'], reverse=True)
            return full_log
        except Exception as e:
            logger.error(f"Error reading dev logs: {e}")
            return []

# Global Instance
dev_log = DeveloperLog()
