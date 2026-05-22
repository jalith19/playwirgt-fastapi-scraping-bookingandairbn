import asyncio
import random
from playwright.async_api import async_playwright
from datetime import datetime


async def scrape_booking_colombia():
    """Scraper de alojamientos de Booking.com en Colombia"""
    url = "https://www.booking.com/searchresults.es.html?label=co-TfpBxcCAFH2vRPCcULIQggS650545686888%3Apl%3Ata%3Ap15950%3Ap2%3Aac%3Aap%3Aneg%3Afi%3Atikwd-1129948231%3Alp9249638%3Ali%3Adec%3Adm%3Appccp%3DUmFuZG9tSVYkc2RlIyh9YdnZzv7u3SiOco5fpqS0M1M&aid=306396&dest_id=47&dest_type=country&group_adults=2&req_adults=2&no_rooms=1&broad_search_not_eligible=1"

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
            print("  Navegando a Booking Colombia alojamientos...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            # Cerrar popup
            try:
                close_button = await page.wait_for_selector(
                    'button[aria-label="Cerrar"]', timeout=3000
                )
                if close_button:
                    await close_button.click()
                    await page.wait_for_timeout(1000)
            except:
                pass

            print(" Cargando resultados con scroll...")
            last_count = 0
            scroll_attempts = 0
            max_scrolls = 30

            while scroll_attempts < max_scrolls:
                current_count = await page.evaluate("""
                    () => document.querySelectorAll('[data-testid="property-card"]').length
                """)

                print(
                    f"   Scroll #{scroll_attempts + 1}: {current_count} propiedades encontradas"
                )

                if current_count == last_count and scroll_attempts > 2:
                    break

                last_count = current_count
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(random.randint(1500, 2500))

                if scroll_attempts % 5 == 0:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(3000)

                scroll_attempts += 1

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            print(" Extrayendo datos...")
            propiedades_data = await page.evaluate("""
                () => {
                    const propiedades = [];
                    const cards = document.querySelectorAll('[data-testid="property-card"]');
                    
                    cards.forEach((card) => {
                        try {
                            const propiedad = {};
                            
                            const tituloElement = card.querySelector('[data-testid="title"]');
                            if (tituloElement) propiedad.nombre = tituloElement.textContent.trim();
                            
                            const linkElement = card.querySelector('a[data-testid="title-link"]');
                            if (linkElement) propiedad.url = linkElement.href;
                            
                            const imgElement = card.querySelector('img[data-testid="image"]');
                            if (imgElement) propiedad.imagen_url = imgElement.src;
                            
                            const addressElement = card.querySelector('[data-testid="address-link"]');
                            if (addressElement) propiedad.direccion = addressElement.textContent.trim();
                            
                            const scoreElement = card.querySelector('[data-testid="review-score"]');
                            if (scoreElement) {
                                const scoreText = scoreElement.textContent;
                                const scoreMatch = scoreText.match(/Puntuación:\\s*([0-9]+[.,]?[0-9]*)/);
                                if (scoreMatch) propiedad.puntuacion = scoreMatch[1].replace(',', '.');
                                
                                const comentariosMatch = scoreText.match(/([0-9]+)\\s*comentarios/);
                                if (comentariosMatch) propiedad.numero_comentarios = comentariosMatch[1];
                            }
                            
                            const priceElement = card.querySelector('[data-testid="price-and-discounted-price"]');
                            if (priceElement) propiedad.precio = priceElement.textContent.trim();
                            
                            if (propiedad.nombre && propiedad.nombre.length > 2) {
                                propiedades.push(propiedad);
                            }
                        } catch (error) {
                            console.error('Error:', error);
                        }
                    });
                    return propiedades;
                }
            """)

            return propiedades_data

        except Exception as e:
            print(f" Error en Booking alojamientos: {e}")
            return []

        finally:
            await browser.close()


def enrich_booking_properties(propiedades):
    """Enriquecer datos de propiedades Booking"""
    for i, prop in enumerate(propiedades):
        prop["id"] = f"booking_co_{i+1:04d}"
        prop["pais"] = "Colombia"
        prop["fuente"] = "Booking.com"
        prop["tipo"] = "alojamiento"
        prop["fecha_scraping"] = datetime.now().isoformat()

        if "puntuacion" in prop:
            try:
                prop["puntuacion_numerica"] = float(prop["puntuacion"])
            except:
                prop["puntuacion_numerica"] = 0.0

        if "numero_comentarios" in prop:
            try:
                prop["total_comentarios"] = int(prop["numero_comentarios"])
            except:
                prop["total_comentarios"] = 0

    return propiedades
