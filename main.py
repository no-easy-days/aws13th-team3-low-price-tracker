
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()


from routers.auth import router as auth_router


app = FastAPI()
app.include_router(auth_router)