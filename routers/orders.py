from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from bson import ObjectId
from datetime import datetime

from models import Order, OrderCreate, OrderItem, OrderStatus, Product, Cart, TokenData
from database import get_database, get_collection
from security import get_current_active_user_id, get_current_verified_user, get_current_admin_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Colecciones de MongoDB
def get_orders_collection(db=Depends(get_database)):
    return get_collection("orders")

def get_products_collection(db=Depends(get_database)):
    return get_collection("products")

def get_carts_collection(db=Depends(get_database)):
    return get_collection("carts")

# Endpoint para crear un pedido

@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    user_id: str = Depends(get_current_active_user_id),
    carts_collection = Depends(get_carts_collection),
    products_collection = Depends(get_products_collection),
    orders_collection = Depends(get_orders_collection),
    # Es crucial que el usuario esté verificado para hacer un pedido
    current_verified_user: TokenData = Depends(get_current_verified_user)
):
    """
    Crea un nuevo pedido a partir del carrito del usuario.
    - Valida el stock de los productos.
    - Decrementa el stock.
    - Vacía el carrito.
    Requiere que el usuario haya verificado su mayoría de edad.
    """
    # 1. Obtener el carrito del usuario
    cart_db = await carts_collection.find_one({"user_id": user_id})
    if not cart_db or not cart_db.get("items"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tu carrito está vacío.")
    
    cart_db["_id"] = str(cart_db["_id"])
    cart = Cart(**cart_db)
    order_items: List[OrderItem] = []
    total_amount = 0.0

    # 2. Iterar sobre los ítems del carrito para validar y construir el pedido
    product_ids_to_update = []
    for item in cart.items:
        product = await products_collection.find_one({"_id": ObjectId(item.product_id)})
        
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Producto con ID {item.product_id} no encontrado.")
        
        if product.get("stock", 0) < item.quantity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Stock insuficiente para '{product['name']}'. Disponible: {product.get('stock', 0)}, Solicitado: {item.quantity}.")

        # Construir el OrderItem con los datos actuales del producto
        order_item = OrderItem(
            product_id=product["_id"],
            name=product["name"],
            quantity=item.quantity,
            price_at_purchase=product["price"]
        )
        order_items.append(order_item)
        total_amount += order_item.price_at_purchase * order_item.quantity
        
        # Guardar la info para actualizar el stock después
        product_ids_to_update.append({
            "id": ObjectId(item.product_id),
            "quantity_to_decrement": item.quantity
        })

    # 3. Crear el documento del pedido
    new_order = Order(
        user_id=user_id,
        items=order_items,
        total_amount=total_amount,
        status=OrderStatus.PENDING,
        shipping_address=order_data.shipping_address
    )
    
    order_dict = new_order.model_dump(exclude={"_id"}, by_alias=False)
    result = await orders_collection.insert_one(order_dict)

    
    
    if not result.inserted_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo crear el pedido.")

    # 4. Decrementar el stock de los productos
    # NOTA: En un sistema de producción real, esto debería ser una transacción atómica con la creación del pedido.
    for p in product_ids_to_update:
        await products_collection.update_one(
            {"_id": p["id"]},
            {"$inc": {"stock": -p["quantity_to_decrement"]}}
        )

    # 5. Vaciar el carrito del usuario
    await carts_collection.update_one(
        {"user_id": user_id},
        {"$set": {"items": []}}
    )
    
    logger.info(f"Pedido {result.inserted_id} creado para el usuario {user_id}.")
    
    created_order = await orders_collection.find_one({"_id": result.inserted_id})
    return Order(**created_order)


@router.get("/me", response_model=List[Order])
async def get_my_orders(
    user_id: str = Depends(get_current_active_user_id),
    orders_collection = Depends(get_orders_collection)
):
    """Obtiene el historial de pedidos del usuario autenticado."""
    orders_cursor = orders_collection.find({"user_id": user_id}).sort("created_at", -1)
    return [Order(**order) async for order in orders_cursor]


@router.get("/{order_id}", response_model=Order)
async def get_order_details(
    order_id: str,
    user_id: str = Depends(get_current_active_user_id),
    orders_collection = Depends(get_orders_collection)
):
    """
    Obtiene los detalles de un pedido específico del usuario autenticado.
    Verifica que el pedido pertenezca al usuario que lo solicita.
    """
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de pedido inválido.")
    
    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")
    
    if order["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para ver este pedido.")
        
    return Order(**order)


# --- Endpoints para Administradores ---

@router.put("/admin/{order_id}/status", response_model=Order, tags=["Admin"])
async def update_order_status(
    order_id: str,
    new_status: OrderStatus, # Recibe el nuevo estado directamente como un valor del enum
    orders_collection = Depends(get_orders_collection),
    products_collection = Depends(get_products_collection),
    current_admin_user: TokenData = Depends(get_current_admin_user)
):
    """
    [Admin] Actualiza el estado de un pedido.
    Requiere permisos de administrador.
    """
    # 1. Validar el ID
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de pedido inválido.")
    
    # 2. Obtener el pedido actual
    current_order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not current_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado.")
    current_status = str(current_order["status"])

    # 3. Reposición de stock si corresponde
    # Lógica de reposición de stock
    if new_status in [OrderStatus.CANCELLED, OrderStatus.REFUNDED] and current_status not in [
    OrderStatus.CANCELLED.value, OrderStatus.REFUNDED.value
    ]:
        logger.info(f"El pedido {order_id} se está cancelando/reembolsando. Reponiendo stock...")
    for item in current_order["items"]:
        try:
            product_oid = ObjectId(item["product_id"])
        except Exception:
            logger.error(f"El product_id {item['product_id']} no es válido, no se repone stock.")
            continue

        result = await products_collection.update_one(
            {"_id": product_oid},
            {"$inc": {"stock": item["quantity"]}}
        )

        if result.modified_count:
            logger.info(f"Stock del producto {item['product_id']} incrementado en {item['quantity']}.")
        else:
            logger.warning(f"No se encontró producto con id {item['product_id']} para reponer stock.")

   # 4. Actualizamos el estado del pedido
    await orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": new_status.value, "updated_at": datetime.utcnow()}}
    )
    
    # 5. Devolver el pedido actualizado
    updated_order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    logger.info(f"Admin {current_admin_user.username} actualizó el estado del pedido {order_id} a '{new_status.value}'.")
    return Order(**updated_order)