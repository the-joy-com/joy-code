# decision models

## snippet to use Nimble locally

```python
import requests
import json

def evaluate_ticket_with_nimble():
    url = "http://localhost:11434/v1/systemone"
    
    # The /v1/systemone endpoint expects 'questions' as a dictionary, 
    # not a list, so you define the question ID as the key.
    payload = {
        "model": "nimble",
        "state": {
            "ticket": "I noticed my card was charged twice on October 1st. Please refund the extra charge.",
            "customer_tier": "premium"
        },
        "questions": {
            # 1. CHOICE: Selects one option from a defined set
            "team_routing": {
                "type": "choice",
                "instructions": "Which team should handle this ticket?",
                "criteria": {
                    "billing": "Payments, refunds, and invoices",
                    "technical": "Bugs, login issues, and errors",
                    "sales": "Upgrades or new purchases",
                    "other": "None of the above"
                }
            },
            
            # 2. NOUL: Evaluates a yes/no statement (returns a 0 to 1 probability)
            "requires_human_review": {
                "type": "noul",
                "instructions": "Does the customer explicitly demand a refund or chargeback?"
            },
            
            # 3. SCORE: Rates the state against an ordered scale
            "ticket_urgency": {
                "type": "score",
                "instructions": "How urgent is this ticket based on customer tone and impact?",
                "criteria": [
                    "Routine (Standard SLA)", 
                    "Soon (Elevated Priority)", 
                    "Urgent (Immediate Action Required)"
                ]
            }
        }
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # Catch HTTP errors
        
        # The model returns structured JSON containing probabilities for every question
        result = response.json()
        print(json.dumps(result, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")

if __name__ == "__main__":
    evaluate_ticket_with_nimble()
```