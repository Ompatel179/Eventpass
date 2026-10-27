from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home() -> dict[str,str]:
    return {"message": "Welcome to EventPass!"}