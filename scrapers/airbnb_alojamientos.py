import asyncio
import random
from playwright.async_api import async_playwright
from datetime import datetime


async def scrape_airbnb_colombia():
    """Scraper de alojamientos de Airbnb en Colombia"""
    url = "https://www.airbnb.com.co/s/Colombia/homes?refinement_paths%5B%5D=%2Fhomes&place_id=ChIJo5QVrjqkFY4RQKPy7wSaDZo&acp_id=490dd28c-1a4f-49ac-aa1a-31214fc1f597&date_picker_type=calendar&query=Colombia&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2026-06-01&monthly_length=3&monthly_end_date=2026-09-01&price_filter_input_type=2&channel=EXPLORE&pagination_search=true&price_filter_num_nights=5"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-CO",
        )

        page = await context.new_page()

        try:
            print(" Navegando a Airbnb Colombia alojamientos...")
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

            all_properties = []
            current_page = 1

            while current_page <= 3:  # Limitar a 3 páginas
                print(f" Página {current_page}")

                print(" Haciendo scroll...")
                last_count = 0
                same_count = 0
                scroll_attempts = 0

                while True:
                    current_count = await page.evaluate("""
                        () => document.querySelectorAll('a[rel="noopener noreferrer nofollow"][target^="listing_"]').length
                    """)

                    if current_count == last_count:
                        same_count += 1
                        if same_count >= 5:
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

                print(" Extrayendo propiedades...")
                page_properties = await page.evaluate("""
                    () => {
                        const propiedades = [];
                        const listings = document.querySelectorAll('a[rel="noopener noreferrer nofollow"][target^="listing_"]');
                        
                        listings.forEach(listing => {
                            try {
                                const propiedad = {};
                                const target = listing.getAttribute('target');
                                if (target) propiedad.id = target.replace('listing_', '');
                                propiedad.url = listing.href;
                                
                                let container = listing.closest('[data-testid="card-container"]') || 
                                               listing.closest('div[role="group"]');
                                
                                if (container) {
                                    const tituloElement = container.querySelector('[data-testid="listing-card-title"], h3');
                                    if (tituloElement) propiedad.titulo = tituloElement.textContent.trim();
                                    
                                    const imgElement = container.querySelector('img');
                                    if (imgElement) propiedad.imagen_url = imgElement.src;
                                    
                                    const precioElements = container.querySelectorAll('span');
                                    precioElements.forEach(span => {
                                        const text = span.textContent.trim();
                                        if (text.includes('$') && (text.includes('COP') || text.includes('noche'))) {
                                            propiedad.precio_texto = text;
                                            const numeroMatch = text.match(/([0-9]+[.,]?[0-9]*)/);
                                            if (numeroMatch) propiedad.precio = numeroMatch[0].replace(',', '');
                                        }
                                    });
                                    
                                    const ratingElements = container.querySelectorAll('span[aria-hidden="true"]');
                                    ratingElements.forEach(span => {
                                        const text = span.textContent.trim();
                                        if (text.match(/^[0-9]+[.,][0-9]+$/)) propiedad.puntuacion = text.replace(',', '.');
                                        const reviewsMatch = text.match(/\\(([0-9]+)\\)/);
                                        if (reviewsMatch) propiedad.numero_resenas = reviewsMatch[1];
                                    });
                                }
                                
                                if (propiedad.id) propiedades.push(propiedad);
                            } catch (error) {
                                console.error('Error:', error);
                            }
                        });
                        return propiedades;
                    }
                """)

                all_properties.extend(page_properties)
                print(f"   ✓ {len(page_properties)} propiedades extraídas")

                # Buscar siguiente página
                next_button = None
                try:
                    next_button = await page.wait_for_selector(
                        'a[aria-label="Siguiente"]', timeout=3000
                    )
                except:
                    pass

                if next_button:
                    is_disabled = await next_button.get_attribute("aria-disabled")
                    if is_disabled == "true":
                        break

                    await next_button.scroll_into_view_if_needed()
                    await page.wait_for_timeout(1000)
                    await next_button.click()
                    await page.wait_for_timeout(4000)
                    current_page += 1
                else:
                    break

            return all_properties

        except Exception as e:
            print(f" Error en Airbnb alojamientos: {e}")
            return []

        finally:
            await browser.close()


def enrich_airbnb_properties(propiedades):
    """Enriquecer datos de propiedades Airbnb"""
    for i, prop in enumerate(propiedades):
        prop["numero"] = i + 1
        prop["fuente"] = "Airbnb"
        prop["pais"] = "Colombia"
        prop["moneda"] = "COP"
        prop["tipo"] = "alojamiento"
        prop["fecha_scraping"] = datetime.now().isoformat()

        if "precio" in prop:
            try:
                prop["precio_numerico"] = float(prop["precio"])
            except:
                prop["precio_numerico"] = 0.0

        if "puntuacion" in prop:
            try:
                prop["puntuacion_numerica"] = float(prop["puntuacion"])
            except:
                prop["puntuacion_numerica"] = 0.0

        if "numero_resenas" in prop:
            try:
                prop["total_resenas"] = int(prop["numero_resenas"])
            except:
                prop["total_resenas"] = 0

    return propiedades
