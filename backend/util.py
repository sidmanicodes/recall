from typing import Dict
from datetime import datetime

def create_new_row(term: str, definition: str, deck_id: int) -> Dict:
    row = {
            "term": term,
            "definition": definition,
            "ease_factor": 1,
            "interval": 0,
            "graduated": False,
            "next_review": datetime.today().strftime("%Y-%m-%d"),
            "deck_id": deck_id
        }
    return row