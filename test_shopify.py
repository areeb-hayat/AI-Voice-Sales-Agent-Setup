from app.services.shopify_client import ShopifyClient

shopify_client = ShopifyClient()

customer_email = "test@example.com"

try:
    orders = shopify_client.get_customer_orders(customer_email)
    print("Shopify orders fetched successfully:")
    for order in orders:
        print(f"- Order {order['name']} with {len(order.get('line_items', []))} items")
    
    if orders:
        last_order = orders[-1]
        for variant in last_order.get("line_items", []):
            product_id = variant.get("product_id")
            stock = shopify_client.check_stock(product_id)
            print(f"Product {variant['name']} stock: {stock}")
        shipping_estimate = shopify_client.get_shipping_estimate(last_order['name'])
        print(f"Shipping estimate for last order: {shipping_estimate}")

except Exception as e:
    print(f"Shopify test failed: {e}")
