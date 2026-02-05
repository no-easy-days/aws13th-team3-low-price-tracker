from dotenv import load_dotenv
from fastapi import FastAPI


load_dotenv()


from routers.auth import router as auth_router
from routers.products import router as products_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(products_router)