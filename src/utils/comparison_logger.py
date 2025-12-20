import csv
import os
import json
from datetime import datetime
from src.utils import logger

class ComparisonLogger:
    def __init__(self, filepath="data/comparison_log.csv"):
        self.filepath = filepath
        self.ensure_directory()

    def ensure_directory(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def log_decision_cycle(self, reasoning_trace, decisions):
        """
        Log a decision cycle to CSV.
        reasoning_trace: str (full text from LLM)
        decisions: list of dicts (parsed JSON)
        """
        try:
            file_exists = os.path.isfile(self.filepath)
            
            with open(self.filepath, "a", newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header if new file
                if not file_exists:
                    writer.writerow(["Timestamp", "Symbol", "Decision", "Confidence", "Reasoning_Summary", "Full_Trace_Snippet"])
                
                if not decisions:
                    # Log 'No Action' row
                    writer.writerow([
                        datetime.now().isoformat(),
                        "ALL",
                        "NO_ACTION",
                        "N/A",
                        "No trades generated",
                        reasoning_trace[:200].replace('\n', ' ') + "..."
                    ])
                
                for d in decisions:
                    writer.writerow([
                        datetime.now().isoformat(),
                        d.get("symbol", "UNKNOWN"),
                        d.get("decision", "UNKNOWN"),
                        d.get("confidence", "N/A"),
                        d.get("reasoning", "N/A"),
                        reasoning_trace[:1000] # Cap reasonably large to avoid massive CSV cells, but enough to read context
                    ])
                    
            logger.info(f"📝 Logged decision to {self.filepath}")
            
        except Exception as e:
            logger.error(f"Failed to log to comparison logger: {e}")

# Global Instance
comparison_logger = ComparisonLogger()
