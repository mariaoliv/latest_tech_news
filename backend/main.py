import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from graph import get_startup_summary 
import uuid

app = FastAPI(title="Latest Tech News API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173/"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/news-summary")
async def news_summary():
    try:
        thread_id = str(uuid.uuid4())
        summary_text = await get_startup_summary(thread_id=thread_id)
        return {"summary": summary_text}
    except Exception as e:
        return {"error": str(e), "summary": "Failed to fetch latest news."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)