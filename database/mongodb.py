from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any

MONGO_URI = "mongodb+srv://jalithmerinoalmeida_db_user:x0dCd6r0efJLi3Wz@scraping-booking-airbnb.gyq0lvo.mongodb.net/"
DB_NAME = "booking-airbnb"

COLLECTION_BOOKING_ALOJAMIENTOS = "booking-alojamientos"
COLLECTION_BOOKING_ACTIVIDADES = "booking-actividades"
COLLECTION_AIRBNB_ALOJAMIENTOS = "airbnb-alojamientos"
COLLECTION_AIRBNB_ACTIVIDADES = "airbnb-actividades"


class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(
                MONGO_URI,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True,
            )
            self.db = self.client[DB_NAME]
            await self.client.admin.command("ping")
            print("Conectado a MongoDB Atlas exitosamente")
            return True
        except Exception as e:
            print(f"Error conectando a MongoDB: {e}")
            return False

    async def disconnect(self):
        if self.client:
            self.client.close()
            print("Conexión a MongoDB cerrada")

    async def save_many(
        self, collection_name: str, data: List[Dict], deduplicate_field: str = None
    ):
        if not data:
            return 0
        collection = self.db[collection_name]
        if deduplicate_field:
            ids_to_remove = []
            for item in data:
                if deduplicate_field in item:
                    existing = await collection.find_one(
                        {deduplicate_field: item[deduplicate_field]}
                    )
                    if existing:
                        ids_to_remove.append(existing["_id"])
            if ids_to_remove:
                await collection.delete_many({"_id": {"$in": ids_to_remove}})
        result = await collection.insert_many(data)
        return len(result.inserted_ids)

    async def get_all(
        self, collection_name: str, limit: int = 100, skip: int = 0
    ) -> List[Dict]:
        collection = self.db[collection_name]
        cursor = collection.find().skip(skip).limit(limit)
        data = await cursor.to_list(length=limit)
        for item in data:
            item["_id"] = str(item["_id"])
        return data

    async def count(self, collection_name: str) -> int:
        collection = self.db[collection_name]
        return await collection.count_documents({})


mongodb = MongoDB()
