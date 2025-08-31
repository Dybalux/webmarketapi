from fastapi import APIRouter, Depends, HTTPException, status , Query, Response
from typing import List, Optional
from bson import ObjectId

from models import Product, ProductCategory, UserRole, TokenData
from database import get_database, get_collection
from security import get_current_admin_user # Importamos la dependencia para admins
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

#Coleccion de productos
def get_products_collection():
    return get_collection("products")

#Endpoint para la gestión de productos
@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: Product,
    products_collection = Depends(get_products_collection),
    # Solo admins pueden crear productos
    current_user: TokenData = Depends(get_current_admin_user)  
):
    """ 
    Crea un nuevo producto (bebida) en el catálogo.
    Requiere permisos de administrador.
    """
    # Validar que el nombre del producto no esté duplicado
    existing_product = await products_collection.find_one({"name": product.name})
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre del producto ya existe."
        )
    product_dict = product.model_dump(exclude_unset=True, exclude={"id"}, by_alias=True)
    result = await products_collection.insert_one(product_dict)
    
    if not result.inserted_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo crear el producto.")
    
    # Obtener el producto recién creado para devolver el ID
    created_product = await products_collection.find_one({"_id": result.inserted_id})
    if created_product:
        return Product.model_validate(created_product)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Producto creado pero no se pudo recuperar.")
    
@router.get("/", response_model=List[Product])
async def read_products(
    products_collection = Depends(get_products_collection),
    category: Optional[ProductCategory] = Query(None, description="Filtrar por categoría de producto"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo del producto"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo del producto"),
    search: Optional[str] = Query(None, min_length=2, description="Buscar por nombre o descripción del producto"),
    skip: int = Query(0, ge=0, description="Número de ítems a saltar para paginación"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de ítems a devolver")
):
    """
    Obtiene una lista de productos con opciones de filtrado, búsqueda y paginación.
    Accesible para cualquier usuario (no requiere autenticación).
    """
    query = {}
    if category:
        query["category"] = category.value
    if min_price is not None:
        query["price"] = {"$gte": min_price}
    if max_price is not None:
        if "price" in query:
            query["price"]["$lte"] = max_price
        else:
            query["price"] = {"$lte": max_price}
    if search:
        # Búsqueda insensible a mayúsculas/minúsculas en nombre y descripción
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    products_cursor = products_collection.find(query).skip(skip).limit(limit)
    products_list = []
    async for product_doc in products_cursor:
        products_list.append(Product(**product_doc))
    return products_list

@router.get("/{product_id}", response_model=Product)
async def read_product(
    product_id: str,
    products_collection = Depends(get_products_collection)
):
    """
    Obtiene los detalles de un producto específico por su ID.
    Accesible para cualquier usuario.
    """
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido.")

    product_db = await products_collection.find_one({"_id": ObjectId(product_id)})
    if product_db:
        return Product(**product_db)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    product_update: Product, # Usamos Product para recibir todos los campos, Pydantic se encarga de validar
    products_collection = Depends(get_products_collection),
    # Solo administradores pueden actualizar productos
    current_admin_user: TokenData = Depends(get_current_admin_user)
):
    """
    Actualiza la información de un producto existente.
    Requiere permisos de administrador.
    """
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido.")

    # Convertir el modelo Pydantic a un diccionario, excluyendo el ID y campos no seteados
    update_data = product_update.model_dump(exclude_unset=True, by_alias=False)
    
    # No permitir cambiar el ID
    if "_id" in update_data:
        del update_data["_id"]
    if "id" in update_data:
        del update_data["id"]

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado para actualizar.")
    
    updated_product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if updated_product:
        return Product(**updated_product)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Producto actualizado pero no se pudo recuperar.")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    products_collection = Depends(get_products_collection),
    # Solo administradores pueden eliminar productos
    current_admin_user: TokenData = Depends(get_current_admin_user)
):
    """
    Elimina un producto del catálogo por su ID.
    Requiere permisos de administrador.
    """
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido.")

    result = await products_collection.delete_one({"_id": ObjectId(product_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado para eliminar.")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)