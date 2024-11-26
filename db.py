import certifi
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGODB_DSN = os.getenv('MONGODB_DSN')


class DB:
    def __init__(self, db_name="olx-target-db", collection_name="users"):
        # Connect to MongoDB client
        self.client = MongoClient(MONGODB_DSN, ssl=True, tlsCAFile=certifi.where())  # Assuming MongoDB is running locally
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def get_all_users(self):
        return self.collection.find()

    def get_tracked_products(self, user_id: str):
        # Retrieve the tracked products for the given user from MongoDB
        user_products = self.collection.find_one({"user_id": user_id})
        if user_products:
            return user_products.get("products", [])
        return []

    def remove_product(self, product_name: str, user_id: str):
        user_products = self.collection.find_one({"user_id": user_id})

        if user_products:
            # Filter out the product with the specified name
            updated_products = [product for product in user_products['products'] if product != product_name]

            if len(updated_products) != len(user_products['products']):
                # The product was removed, update the user's product list in the database
                self.collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"products": updated_products}}
                )

    def add_product(self, product_name: str, user_id: str):
        # Check if the user already has products in the database
        user_products = self.collection.find_one({"user_id": user_id})

        if user_products:
            # Add the new product URL to the user's list
            self.collection.update_one(
                {"user_id": user_id},
                {"$addToSet": {"products": product_name}}  # $addToSet ensures no duplicates
            )
        else:
            # Insert a new record for the user
            self.collection.insert_one({
                "user_id": user_id,
                "products": [product_name]
            })

    def is_product_exist(self, product_name: str, user_id: str) -> bool:
        # Check if the product URL exists for the given user
        user_products = self.collection.find_one({"user_id": user_id})
        if user_products:
            return product_name in user_products["products"]
        return False


db = DB()
