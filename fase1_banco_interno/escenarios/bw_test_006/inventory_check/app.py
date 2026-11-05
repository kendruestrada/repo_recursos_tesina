import os
import boto3
from aws_lambda_powertools import Logger

logger = Logger()

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


@logger.inject_lambda_context
def lambda_handler(event, context):
    product_id = event.get("productId")
    expected_price = event.get("price")
    quantity = event.get("quantity", 1)

    if not product_id or expected_price is None:
        return {"valid": False, "error": "productId y price son requeridos"}

    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={"productId": product_id})
        product = response.get("Item")

        if not product:
            return {"valid": False, "error": "Producto no encontrado"}

        db_price = float(product.get("price", 0))
        stock = product.get("stock", 0)

        logger.info(
            "Validando precio del checkout contra base de datos",
            productId=product_id,
            precioEnviadoPorUI=expected_price,
            precioActualEnDB=db_price,
        )

        if abs(db_price - expected_price) > 0.01:
            logger.error(
                "Inconsistencia de precio detectada",
                productId=product_id,
                precioQueMostroCache=expected_price,
                precioRealEnDB=db_price,
                diferencia=round(expected_price - db_price, 2),
            )
            return {
                "valid": False,
                "error": "Precio manipulado o desactualizado",
                "expectedPrice": expected_price,
                "actualPrice": db_price,
            }

        if stock < quantity:
            return {
                "valid": False,
                "error": "Stock insuficiente",
                "availableStock": stock,
            }

        return {
            "valid": True,
            "productId": product_id,
            "price": db_price,
            "stock": stock,
        }

    except Exception as e:
        logger.error("Error al validar inventario", error=str(e))
        return {"valid": False, "error": "Error interno del servidor"}
