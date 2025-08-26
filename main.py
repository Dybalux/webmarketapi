from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from config import settings
import uvicorn
import logging


# Initialize logging
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Bebidas Alcoholicas",
    description="API para gesionar productos,pedidos,carritos y autenticacion de usuarios",
    version="0.0.1",
    docs_url="/docs", # Documentacion interactiva - Swagger UI
    redoc_url="/redoc", # Documentacion alternativa - ReDoc
)

#Middleware para usar HTTPS en produccion(descomentar en produccion)
@app.middleware("http")
async def enforce_https(request, call_next):
    if settings.ENV == "production" and request.url.scheme != "https":
        logger.warning(f"HTTPS enforcement: Request to {request.url} not via HTTPS in production environment. Redirecting...")
        # En un entorno real, tu proxy inverso (Nginx, Caddy) se encargaría de esto.
        # Aquí, solo redirigimos si no es HTTPS.
        # Es crucial que tu entorno de despliegue real maneje esto de forma robusta.
        secure_url = str(request.url).replace("http://", "https://", 1)
        return RedirectResponse(url=secure_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response = await call_next(request)
    return response

@app.get("/",tags=["Root"])
async def read_root():
    return {"message": "¡Bienvenido a la API de Bebidas Alcohólicas!"}

if __name__ == "__main__":
    logger.info(f"Iniciando API en ambiente: {settings.ENV}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.ENV == "development")