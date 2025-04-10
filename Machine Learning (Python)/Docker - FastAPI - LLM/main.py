import fastapi, pydantic, uvicorn

app = fastapi.FastAPI()
RES = ['A', 'B', 'C']
idx = -1

@app.get("/")
def home():
    return {"message": "Hello world!"}

@app.post("/chat")
def chat(request: pydantic.BaseModel):
    global idx
    idx = (idx + 1) % 3
    return RES[idx]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
