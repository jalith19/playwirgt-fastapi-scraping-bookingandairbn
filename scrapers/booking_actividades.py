import asyncio
import random
from playwright.async_api import async_playwright
from datetime import datetime


async def scrape_booking_attractions():
    """Scraper de actividades de Booking.com en Colombia"""
    url = "https://www.booking.com/attractions/searchresults.es.html?selected_currency=COP&source=search_box&aid=306396&label=co-TfpBxcCAFH2vRPCcULIQggS650545686888%3Apl%3Ata%3Ap15950%3Ap2%3Aac%3Aap%3Aneg%3Afi%3Atikwd-1129948231%3Alp9249638%3Ali%3Adec%3Adm%3Appccp%3DUmFuZG9tSVYkc2RlIyh9YdnZzv7u3SiOco5fpqS0M1M&dest_id=-343779"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES",
        )

        page = await context.new_page()

        try:
            print(" Navegando a Booking Attractions Colombia...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            print(" Cargando actividades con scroll...")
            last_count = 0
            same_count = 0
            scroll_attempts = 0
            max_scrolls = 25

            while scroll_attempts < max_scrolls:
                current_count = await page.evaluate("""
                    () => document.querySelectorAll('[data-testid="card"]').length
                """)

                print(
                    f"   Scroll #{scroll_attempts + 1}: {current_count} actividades encontradas"
                )

                if current_count == last_count:
                    same_count += 1
                    if same_count >= 4:
                        break
                else:
                    same_count = 0

                last_count = current_count
                await page.evaluate("window.scrollBy(0, 600)")
                await page.wait_for_timeout(random.randint(1500, 2500))

                if scroll_attempts % 5 == 0 and scroll_attempts > 0:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(3000)

                scroll_attempts += 1

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            print(" Extrayendo datos...")
            actividades_data = await page.evaluate("""
                () => {
                    const actividades = [];
                    const cards = document.querySelectorAll('[data-testid="card"]');
                    
                    cards.forEach((card) => {
                        try {
                            const actividad = {};
                            
                            const tituloElement = card.querySelector('[data-testid="card-title"] a');
                            if (tituloElement) {
                                actividad.titulo = tituloElement.textContent.trim();
                                actividad.url = tituloElement.href;
                            }
                            
                            const ubicacionElement = card.querySelector('.css-1utx3w7');
                            if (ubicacionElement) actividad.ubicacion = ubicacionElement.textContent.trim();
                            
                            const imgElement = card.querySelector('img');
                            if (imgElement) actividad.imagen_url = imgElement.src;
                            
                            const scoreElement = card.querySelector('[data-testid="review-score"]');
                            if (scoreElement) {
                                const scoreText = scoreElement.textContent;
                                const scoreMatch = scoreText.match(/([0-9]+[.,]?[0-9]*)/);
                                if (scoreMatch) actividad.puntuacion = scoreMatch[0].replace(',', '.');
                                
                                const comentariosMatch = scoreText.match(/([0-9]+)\\s*comentarios/);
                                if (comentariosMatch) actividad.numero_comentarios = comentariosMatch[1];
                            }
                            
                            const priceElement = card.querySelector('[data-testid="price"]');
                            if (priceElement) {
                                const priceText = priceElement.textContent;
                                const montoMatch = priceText.match(/([0-9]+[.,]?[0-9]*)/);
                                if (montoMatch) actividad.precio = montoMatch[0].replace(',', '');
                                actividad.precio_formateado = priceText;
                            }
                            
                            if (actividad.titulo && actividad.titulo.length > 2) {
                                actividades.push(actividad);
                            }
                        } catch (error) {
                            console.error('Error:', error);
                        }
                    });
                    return actividades;
                }
            """)

            return actividades_data

        except Exception as e:
            print(f" Error en Booking actividades: {e}")
            return []

        finally:
            await browser.close()


def enrich_booking_activities(actividades):
    """Enriquecer datos de actividades Booking"""
    for i, act in enumerate(actividades):
        act["id"] = f"booking_act_co_{i+1:04d}"
        act["pais"] = "Colombia"
        act["fuente"] = "Booking.com Attractions"
        act["tipo"] = "actividad"
        act["fecha_scraping"] = datetime.now().isoformat()

        if "puntuacion" in act:
            try:
                act["puntuacion_numerica"] = float(act["puntuacion"])
            except:
                act["puntuacion_numerica"] = 0.0

        if "precio" in act:
            try:
                act["precio_numerico"] = float(act["precio"])
            except:
                act["precio_numerico"] = 0.0

        if "numero_comentarios" in act:
            try:
                act["total_comentarios"] = int(act["numero_comentarios"])
            except:
                act["total_comentarios"] = 0

    return actividades
