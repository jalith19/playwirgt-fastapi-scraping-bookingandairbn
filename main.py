from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio

from database.mongodb import (
    mongodb,
    COLLECTION_BOOKING_ALOJAMIENTOS,
    COLLECTION_BOOKING_ACTIVIDADES,
    COLLECTION_AIRBNB_ALOJAMIENTOS,
    COLLECTION_AIRBNB_ACTIVIDADES,
)
from scrapers import (
    scrape_booking_colombia,
    enrich_booking_properties,
    scrape_booking_attractions,
    enrich_booking_activities,
    scrape_airbnb_colombia,
    enrich_airbnb_properties,
    scrape_airbnb_experiences,
    enrich_airbnb_experiences,
)
from scheduler import start_scheduler, run_all_scrapers

# Crear la aplicación FastAPI
app = FastAPI(
    title="Scraping API - Booking & Airbnb Colombia",
    description="API para gestión de datos de alojamientos y actividades de Booking y Airbnb en Colombia",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapingRequest(BaseModel):
    tipo: str


def convert_objectid(data: List[Dict]) -> List[Dict]:
    """Convierte ObjectId a string para serialización JSON"""
    for item in data:
        if "_id" in item:
            item["_id"] = str(item["_id"])
    return data


# Eventos de inicio y cierre
@app.on_event("startup")
async def startup_event():
    """Conectar a MongoDB e iniciar scheduler al arrancar la API"""
    await mongodb.connect()
    start_scheduler()
    print("API iniciada correctamente")


@app.on_event("shutdown")
async def shutdown_event():
    """Cerrar conexión a MongoDB"""
    await mongodb.disconnect()


# ============== GET ENDPOINTS ==============


@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "api": "Scraping API - Booking & Airbnb Colombia",
        "version": "1.0.0",
        "endpoints": {
            "GET /booking/alojamientos": "Obtener alojamientos de Booking",
            "GET /booking/actividades": "Obtener actividades de Booking",
            "GET /airbnb/alojamientos": "Obtener alojamientos de Airbnb",
            "GET /airbnb/actividades": "Obtener actividades de Airbnb",
            "POST /scraping/booking/alojamientos": "Scraping manual de alojamientos Booking",
            "POST /scraping/booking/actividades": "Scraping manual de actividades Booking",
            "POST /scraping/airbnb/alojamientos": "Scraping manual de alojamientos Airbnb",
            "POST /scraping/airbnb/actividades": "Scraping manual de actividades Airbnb",
            "POST /scraping/all": "Ejecutar todos los scrapers",
            "GET /stats": "Estadísticas de las colecciones",
        },
    }


@app.get("/booking/alojamientos")
async def get_booking_alojamientos(limit: int = 100, skip: int = 0):
    """Obtener alojamientos de Booking almacenados en MongoDB"""
    try:
        data = await mongodb.get_all(COLLECTION_BOOKING_ALOJAMIENTOS, limit, skip)
        data = convert_objectid(data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/booking/actividades")
async def get_booking_actividades(limit: int = 100, skip: int = 0):
    """Obtener actividades de Booking almacenadas en MongoDB"""
    try:
        data = await mongodb.get_all(COLLECTION_BOOKING_ACTIVIDADES, limit, skip)
        data = convert_objectid(data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/airbnb/alojamientos")
async def get_airbnb_alojamientos(limit: int = 100, skip: int = 0):
    """Obtener alojamientos de Airbnb almacenados en MongoDB"""
    try:
        data = await mongodb.get_all(COLLECTION_AIRBNB_ALOJAMIENTOS, limit, skip)
        data = convert_objectid(data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/airbnb/actividades")
async def get_airbnb_actividades(limit: int = 100, skip: int = 0):
    """Obtener actividades de Airbnb almacenadas en MongoDB"""
    try:
        data = await mongodb.get_all(COLLECTION_AIRBNB_ACTIVIDADES, limit, skip)
        data = convert_objectid(data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Obtener estadísticas de todas las colecciones"""
    try:
        stats = {
            "booking_alojamientos": await mongodb.count(
                COLLECTION_BOOKING_ALOJAMIENTOS
            ),
            "booking_actividades": await mongodb.count(COLLECTION_BOOKING_ACTIVIDADES),
            "airbnb_alojamientos": await mongodb.count(COLLECTION_AIRBNB_ALOJAMIENTOS),
            "airbnb_actividades": await mongodb.count(COLLECTION_AIRBNB_ACTIVIDADES),
            "ultima_actualizacion": datetime.now().isoformat(),
        }
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== POST ENDPOINTS (Scraping Manual) ==============


@app.post("/scraping/booking/alojamientos")
async def scrape_booking_alojamientos_manual():
    """Ejecutar scraping manual de alojamientos de Booking"""
    try:
        data = await scrape_booking_colombia()
        if data and len(data) > 0:
            enriched = enrich_booking_properties(data)
            await mongodb.save_many(
                COLLECTION_BOOKING_ALOJAMIENTOS, enriched, deduplicate_field="id"
            )
            return {
                "success": True,
                "message": f"Scraping completado. Se guardaron {len(enriched)} alojamientos",
                "count": len(enriched),
                "data": convert_objectid(enriched[:10]),
            }
        else:
            return {
                "success": False,
                "message": "No se obtuvieron datos del scraping. Puede que la página haya cambiado o haya bloqueado el acceso.",
                "count": 0,
                "data": [],
            }
    except Exception as e:
        print(f"Error detallado: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scraping/booking/actividades")
async def scrape_booking_actividades_manual():
    """Ejecutar scraping manual de actividades de Booking"""
    try:
        data = await scrape_booking_attractions()
        if data and len(data) > 0:
            enriched = enrich_booking_activities(data)
            await mongodb.save_many(
                COLLECTION_BOOKING_ACTIVIDADES, enriched, deduplicate_field="id"
            )
            return {
                "success": True,
                "message": f"Scraping completado. Se guardaron {len(enriched)} actividades",
                "count": len(enriched),
                "data": convert_objectid(enriched[:10]),
            }
        else:
            return {
                "success": False,
                "message": "No se obtuvieron datos del scraping",
                "count": 0,
                "data": [],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scraping/airbnb/alojamientos")
async def scrape_airbnb_alojamientos_manual():
    """Ejecutar scraping manual de alojamientos de Airbnb"""
    try:
        data = await scrape_airbnb_colombia()
        if data and len(data) > 0:
            enriched = enrich_airbnb_properties(data)
            await mongodb.save_many(
                COLLECTION_AIRBNB_ALOJAMIENTOS, enriched, deduplicate_field="id"
            )
            return {
                "success": True,
                "message": f"Scraping completado. Se guardaron {len(enriched)} alojamientos",
                "count": len(enriched),
                "data": convert_objectid(enriched[:10]),
            }
        else:
            return {
                "success": False,
                "message": "No se obtuvieron datos del scraping",
                "count": 0,
                "data": [],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scraping/airbnb/actividades")
async def scrape_airbnb_actividades_manual():
    """Ejecutar scraping manual de actividades de Airbnb"""
    try:
        data = await scrape_airbnb_experiences()
        if data and len(data) > 0:
            enriched = enrich_airbnb_experiences(data)
            await mongodb.save_many(
                COLLECTION_AIRBNB_ACTIVIDADES, enriched, deduplicate_field="id"
            )
            return {
                "success": True,
                "message": f"Scraping completado. Se guardaron {len(enriched)} experiencias",
                "count": len(enriched),
                "data": convert_objectid(enriched[:10]),
            }
        else:
            return {
                "success": False,
                "message": "No se obtuvieron datos del scraping",
                "count": 0,
                "data": [],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scraping/all")
async def scrape_all_manual():
    """Ejecutar todos los scrapers manualmente"""
    try:
        resultados = {}

        # Booking alojamientos
        data = await scrape_booking_colombia()
        if data:
            enriched = enrich_booking_properties(data)
            await mongodb.save_many(
                COLLECTION_BOOKING_ALOJAMIENTOS, enriched, deduplicate_field="id"
            )
            resultados["booking_alojamientos"] = len(enriched)

        # Booking actividades
        data = await scrape_booking_attractions()
        if data:
            enriched = enrich_booking_activities(data)
            await mongodb.save_many(
                COLLECTION_BOOKING_ACTIVIDADES, enriched, deduplicate_field="id"
            )
            resultados["booking_actividades"] = len(enriched)

        # Airbnb alojamientos
        data = await scrape_airbnb_colombia()
        if data:
            enriched = enrich_airbnb_properties(data)
            await mongodb.save_many(
                COLLECTION_AIRBNB_ALOJAMIENTOS, enriched, deduplicate_field="id"
            )
            resultados["airbnb_alojamientos"] = len(enriched)

        # Airbnb actividades
        data = await scrape_airbnb_experiences()
        if data:
            enriched = enrich_airbnb_experiences(data)
            await mongodb.save_many(
                COLLECTION_AIRBNB_ACTIVIDADES, enriched, deduplicate_field="id"
            )
            resultados["airbnb_actividades"] = len(enriched)

        return {
            "success": True,
            "message": "Scraping completo finalizado",
            "resultados": resultados,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
