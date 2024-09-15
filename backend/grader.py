from typing import Dict
from openai import OpenAI
import json

def grade_answer(question: str, user_answer: str, correct_answer: str, client: OpenAI) -> Dict[int, str]:
    # Format user prompt given question, the user's answer, and the correct answer
    user_prompt = f"Question: {question} || User answer: {user_answer} || Correct answer: {correct_answer}Ú"
    
    # System prompt
    sys_prompt = open("system_prompt.txt", "r").read()

    # A few examples to be used for few-shot learning
    easy_example_prompt = "Question: What was Darth Vader's famous quote to Luke Skywalker in 'The Empire Strikes Back'? || User answer: No, Luke, I am your father || Correct answer: No, Luke, I am your father"
    easy_example_answer = "{\"score\": 0.1, \"reflection\": \"That's correct! Darth Vader's iconic quote is indeed, 'No, Luke, I am your father'\"}"
    good_example_prompt = "Question: What was Darth Vader's famous quote to Luke Skywalker in 'The Empire Strikes Back'? || User answer: I am your father || Correct answer: No, Luke, I am your father"
    good_example_answer = "{\"score\": 0.89, \"reflection\": \"That's pretty close! However, the correct quote is, 'No, Luke, I am your father'; the 'no' plays a vital role in the quote's authenticity\"}"
    hard_example_prompt = "Question: What was Darth Vader's famous quote to Luke Skywalker in 'The Empire Strikes Back'? || User answer: I am a distant relative of your father || Correct answer: No, Luke, I am your father"
    hard_example_answer = "{\"score\": 0.48, \"reflection\": \"Hmm... not quite! Darth Vader is not a distant relative of Luke Skywalker; he is his father. The correct quote is, 'No, Luke, I am your father'\"}"
    again_example_prompt = "Question: What was Darth Vader's famous quote to Luke Skywalker in 'The Empire Strikes Back'? || User answer: I hate sand || Correct answer: No, Luke, I am your father"
    again_example_answer = "{\"score\": 0.0, \"reflection\": \"Unfortunately this is incorrect. Darth Vader did not not inform Luke Skywalker of his hatred for sand. Rather, he said, 'No, Luke, I am your father'\"}"

    # Generate response
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": easy_example_prompt},
            {"role": "assistant", "content": easy_example_answer},
            {"role": "user", "content": good_example_prompt},
            {"role": "assistant", "content": good_example_answer},
            {"role": "user", "content": hard_example_prompt},
            {"role": "assistant", "content": hard_example_answer},
            {"role": "user", "content": again_example_prompt},
            {"role": "assistant", "content": again_example_answer},
            {"role": "user", "content": user_prompt}
        ]
    )

    # Convert reponse to JSON
    res_json = json.loads(res.choices[0].message.content)
    try:
        return {"score": float(res_json["score"]), "reflection": res_json["reflection"]} # Ensure that the score is a float
    except json.JSONDecodeError as e:
        return {"score": 0.0, "reflection": f"Error decoding generated response: {e}"}