from fastapi import FastAPI
from pydantic import BaseModel
from graph import graph  # Import your compiled graph

app = FastAPI()

class Query(BaseModel):
    message: str

@app.post("/create_final_summary")
async def chat_endpoint(query: Query):
    # Initialize the state
    initial_state = {"input": query.message}
    
    # Use ainvoke for a single response
    result = await graph.ainvoke(initial_state)
    
    return {"response": result["final_summary"]}