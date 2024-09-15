import os
import supabase
from grader import grade_answer
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from datetime import timedelta, datetime
from util import create_new_row

# Load API key from .env
load_dotenv()

# Create OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

# Create Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")
supabase_client = supabase.create_client(supabase_url=supabase_url, supabase_key=supabase_key)

# Basic card before embedding
class BaseCard(BaseModel):
    deck_id: int
    term: str
    definition: str

class UpdatedCard(BaseModel):
    card_id: int
    new_term: str
    new_definition: str

class DeletedCard(BaseModel):
    card_id: int

class CardList(BaseModel):
    cards: list[BaseCard]

class UserAnswer(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    ease_factor: float
    graduated: bool
    interval: float
    next_review: str

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Endpoint hit!"}

@app.post("/insert-card")
async def insert_card(req: BaseCard):
    try:
        # Create a new row to insert into the deck
        row = create_new_row(term=req.term, definition=req.definition, deck_id=req.deck_id)

        # Insert data
        data, _ = supabase_client.table("cards").insert(row).execute()

        # Raise HTTP Exception in case we aren't able to properly insert the data
        if not data:
            raise HTTPException(status_code="500", detail="Failed to insert card into Supabase")
        
        return {"message": "Successfully inserted card into Supabase!"}
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=f"Validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
@app.post("/update-card")
async def update_card(req: UpdatedCard):
    try:
        # Update card in supabase
        data, _ = supabase_client.table("cards").update({"term": req.new_term, "definition": req.new_definition}).eq("card_id", req.card_id).execute()

        # Raise HTTP Exception in case we aren't able to properly update the data
        if not data:
            raise HTTPException(status_code="500", detail="Failed to update card in Supabase")
        
        return {"message": "Successfully updated card in Supabase!"}
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=f"Validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@app.post("/delete-card")
async def delete_card(req: DeletedCard):
    try:
        # Delete card in supabase
        data, _ = supabase_client.table("cards").delete().eq("card_id", req.card_id).execute()

        # Raise HTTP Exception in case we aren't able to properly delete the data
        if not data:
            raise HTTPException(status_code="500", detail="Failed to delete card in Supabase")
        
        return {"message": "Successfully deleted card from Supabase!"}
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=f"Validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
    
@app.post("/eval-card")
async def eval_card(req: UserAnswer):
    try:
        # Grade the user's answer
        res = grade_answer(
            question=req.question, 
            user_answer=req.user_answer,
            correct_answer=req.correct_answer,
            client=openai_client
            )
        
        print(res)
        
        score = res["score"]
        reflection = res["reflection"]
        
        if type(score) != float:
            raise HTTPException(500, detail="Internal type error occured")
        
        # Update logic for card comprehension
        res = {
            "reflection": reflection,
            "ease_factor": req.ease_factor,
            "graduated": req.graduated,
            "interval": req.interval,
            "next_review": req.next_review,
            "score": score
        }

        # --------------------------------------
        # Specific updates made because of score
        # --------------------------------------

        # Easy
        if score <= 1.0 and score > 0.75:
            # Upgrade ease factor
            res["ease_factor"] += 0.15 if res["ease_factor"] < 4 else res["ease_factor"]

            # Update interval
            if res["interval"] in (0, 0.5):
                res["interval"] = 1
            else:
                res["interval"] *= res["ease_factor"]
        
        # Good
        elif score <= 0.75 and score > 0.5:
            # Update interval
            if res["interval"] == 0:
                res["interval"] = 0.5
            elif res["interval"] == 0.5:
                res["interval"] = 1
            else:
                res["interval"] *= res["ease_factor"]

        # Hard
        elif score <= 0.5 and score > 0.25:
            # Downgrade ease factor
            res["ease_factor"] -= 0.2 if res["ease_factor"] > 1.3 else res["ease_factor"]
            res["interval"] *= res["ease_factor"]

        # Again
        elif score <= 0.25 and score >= 0.0:
            # Downgrade ease factor
            res["ease_factor"] -= 0.2 if res["ease_factor"] > 1.3 else res["ease_factor"]

            # Reset interval
            res["interval"] = 0

        # --------------------------------
        # Stuff we do no matter what score
        # --------------------------------
        if res["interval"] >= 1:
            res["graduated"] = True
        else:
            res["graduated"] = False

        # Update next review date
        next_review_datetime = datetime.strptime(res["next_review"], '%Y-%m-%d') + timedelta(days=res["interval"])
        res["next_review"] = str(next_review_datetime.date())

        return res
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=f"Validation error: {e.errors()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")