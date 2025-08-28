from fastapi import APIRouter, Depends, HTTPException
from models import UserLogin  # si tenés un modelo de entrada
from security import authenticate_user  # lógica de autenticación

router = APIRouter()

@router.post("/login", summary="Autenticación de usuario")
async def login(user: UserLogin):
    user_data = await authenticate_user(user)
    if not user_data:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return {"token": "jwt-token-aquí"}