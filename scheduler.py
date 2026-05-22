from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio

from database.mongodb import mongodb, COLLECTION_BOOKING_ALOJAMIENTOS, COLLECTION_BOOKING_ACTIVIDADES, COLLECTION_AIRBNB_ALOJAMIENTOS, COLLECTION_AIRBNB_ACTIVIDADES
from scrapers import (
    scrape_booking_colombia, enrich_booking_properties,
    scrape_booking_attractions, enrich_booking_activities,
    scrape_airbnb_colombia, enrich_airbnb_properties,
    scrape_airbnb_experiences, enrich_airbnb_experiences
)


async def run_booking_alojamientos_scraper():
    """Ejecutar scraper de alojamientos Booking"""
    print(f"\n[{datetime.now()}] Ejecutando scraper de Booking alojamientos...")
    try:
        data = await scrape_booking_colombia()
        if data:
            enriched = enrich_booking_properties(data)
            await mongodb.save_many(COLLECTION_BOOKING_ALOJAMIENTOS, enriched, deduplicate_field="id")
            print(f"Guardados {len(enriched)} alojamientos de Booking")
        else:
            print("⚠ No se obtuvieron datos de Booking alojamientos")
    except Exception as e:
        print(f"Error en Booking alojamientos: {e}")


async def run_booking_actividades_scraper():
    """Ejecutar scraper de actividades Booking"""
    print(f"\n[{datetime.now()}] Ejecutando scraper de Booking actividades...")
    try:
        data = await scrape_booking_attractions()
        if data:
            enriched = enrich_booking_activities(data)
            await mongodb.save_many(COLLECTION_BOOKING_ACTIVIDADES, enriched, deduplicate_field="id")
            print(f"Guardados {len(enriched)} actividades de Booking")
        else:
            print("No se obtuvieron datos de Booking actividades")
    except Exception as e:
        print(f"Error en Booking actividades: {e}")


async def run_airbnb_alojamientos_scraper():
    """Ejecutar scraper de alojamientos Airbnb"""
    print(f"\n[{datetime.now()}] Ejecutando scraper de Airbnb alojamientos...")
    try:
        data = await scrape_airbnb_colombia()
        if data:
            enriched = enrich_airbnb_properties(data)
            await mongodb.save_many(COLLECTION_AIRBNB_ALOJAMIENTOS, enriched, deduplicate_field="id")
            print(f"Guardados {len(enriched)} alojamientos de Airbnb")
        else:
            print("⚠ No se obtuvieron datos de Airbnb alojamientos")
    except Exception as e:
        print(f"Error en Airbnb alojamientos: {e}")


async def run_airbnb_actividades_scraper():
    """Ejecutar scraper de actividades Airbnb"""
    print(f"\n[{datetime.now()}] Ejecutando scraper de Airbnb actividades...")
    try:
        data = await scrape_airbnb_experiences()
        if data:
            enriched = enrich_airbnb_experiences(data)
            await mongodb.save_many(COLLECTION_AIRBNB_ACTIVIDADES, enriched, deduplicate_field="id")
            print(f"Guardados {len(enriched)} experiencias de Airbnb")
        else:
            print("⚠ No se obtuvieron datos de Airbnb actividades")
    except Exception as e:
        print(f"Error en Airbnb actividades: {e}")


async def run_all_scrapers():
    """Ejecutar todos los scrapers"""
    print("\n" + "="*60)
    print("INICIANDO SCRAPING COMPLETO")
    print("="*60)
    
    await run_booking_alojamientos_scraper()
    await run_booking_actividades_scraper()
    await run_airbnb_alojamientos_scraper()
    await run_airbnb_actividades_scraper()
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETO FINALIZADO")
    print("="*60)


def start_scheduler():
    """Iniciar el scheduler para ejecutar scrapers cada 8 horas"""
    scheduler = BackgroundScheduler()
    
    # Programar cada 8 horas
    trigger = IntervalTrigger(hours=8)
    
    def run_async_job():
        asyncio.run(run_all_scrapers())
    
    scheduler.add_job(run_async_job, trigger)
    scheduler.start()
    
    print("Scheduler iniciado - Los scrapers se ejecutarán cada 8 horas")
    
    return scheduler