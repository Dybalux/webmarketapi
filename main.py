from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse
from config import settings
from database import connect_db, close_db
from routers import auth, products, age_verification, cart, orders
from contextlib import asynccontextmanager
import uvicorn
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    logger.info("🚀 Iniciando aplicación. Conectando a MongoDB...")
    await connect_db()
    yield
    logger.info("🛑 Cerrando aplicación. Desconectando de MongoDB...")
    await close_db()

app = FastAPI(
    title="API de Bebidas Alcohólicas",
    description="API para gestionar productos, pedidos, carritos y autenticación de usuarios",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware para forzar HTTPS en producción
@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if settings.ENV.lower() == "production" and request.url.scheme != "https":
        logger.warning(f"🔐 Redirigiendo a HTTPS: {request.url}")
        secure_url = str(request.url).replace("http://", "https://", 1)
        return RedirectResponse(url=secure_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return await call_next(request)

# Rutas principales

# Montar routers
app.include_router(products.router, prefix="/products", tags=["Productos"])
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(age_verification.router, prefix="/age-verification", tags=["Verificación de Edad"])
app.include_router(cart.router, prefix="/cart", tags=["Carrito de Compras"])
app.include_router(orders.router, prefix="/orders", tags=["Pedidos"])

# Punto de entrada
if __name__ == "__main__":
    logger.info(f"🌍 Ambiente: {settings.ENV}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.ENV.lower() == "development")
