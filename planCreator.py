from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Behavioral Plan Designer Chatbot!"}

class PlanParameters(BaseModel):
    topic: str
    goal: str
    individual_or_group: str
    target_market: str
    length: int
    competency: int
    time_available: int
    preferred_time: str
    challenge_level: int
    existing_sources: bool

@app.post("/create_plan/")
def create_plan(plan_params: PlanParameters):
    # Store the user input in variables
    topic = plan_params.topic
    goal = plan_params.goal
    individual_or_group = plan_params.individual_or_group
    target_market = plan_params.target_market
    length = plan_params.length
    competency = plan_params.competency
    time_available = plan_params.time_available
    preferred_time = plan_params.preferred_time
    challenge_level = plan_params.challenge_level
    existing_sources = plan_params.existing_sources

    # Call the function to generate the plan and return the result
    plan = generate_plan(topic, goal, individual_or_group, target_market, length, competency, time_available, preferred_time, challenge_level, existing_sources)
    return plan

def generate_plan(topic, goal, individual_or_group, target_market, length, competency, time_available, preferred_time, challenge_level, existing_sources):
    # Your plan generation logic goes here
    # This function should return a dictionary representing the entire plan
    # Format the plan according to the template provided in the description

    # Sample plan dictionary
    plan = {
        "topic": topic,
        "goal": goal,
        "individual_or_group": individual_or_group,
        # Include other plan details here
        "weeks": [
            {
                "week": 1,
                "goal": "Complete introductory course on " + topic,
                "days": [
                    {
                        "day": "Day 1",
                        "day_number": 1,
                        "day_of_the_week": "Monday",
                        "behavior": "Watch",
                        "category": "Learn",
                        "specifics": "Introductory video course link",
                        "time": preferred_time,
                        "duration": 20,
                        "location": "Online",
                        "prompts": ["What concepts did you learn today?", "Rate your understanding on a scale of 1-10."],
                        "milestones": "Finish the course",
                    },
                    # Include other days of the week here
                ],
            },
            # Include other weeks here
        ],
    }

    return plan
