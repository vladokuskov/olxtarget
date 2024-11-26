class Store:
    def __init__(self):
        self.products = {}

    def add_product(self, product_url: str, user_id: str):
        if user_id not in self.products:
            self.products[user_id] = []
        self.products[user_id].append(product_url)

    def is_product_exist(self, product_url: str, user_id: str) -> bool:
        return user_id in self.products and product_url in self.products[user_id]

store = Store()