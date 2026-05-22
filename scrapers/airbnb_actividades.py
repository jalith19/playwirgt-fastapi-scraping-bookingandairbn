import asyncio
import random
from playwright.async_api import async_playwright
from datetime import datetime


async def scrape_airbnb_experiences():
    """Scraper de experiencias de Airbnb en Colombia"""
    url = "https://www.airbnb.com.co/s/Colombia/experiences?place_id=ChIJo5QVrjqkFY4RQKPy7wSaDZo&refinement_paths%5B%5D=%2Fexperiences&location_bb=QYCRSMKFsVDAh0R8wqOp1Q%3D%3D&acp_id=490dd28c-1a4f-49ac-aa1a-31214fc1f597&date_picker_type=calendar&source=structured_search_input_header&search_type=autocomplete_click"

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
            print(" Navegando a Airbnb Experiences Colombia...")
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

            print(" Cargando experiencias con scroll...")
            last_count = 0
            same_count = 0
            scroll_attempts = 0
            target_experiences = 50

            while True:
                current_count = await page.evaluate("""
                    () => document.querySelectorAll('a[rel="noopener noreferrer nofollow"][target="_blank"]').length
                """)

                print(
                    f"   Scroll #{scroll_attempts + 1}: {current_count} experiencias encontradas"
                )

                if current_count >= target_experiences:
                    break

                if current_count == last_count:
                    same_count += 1
                    if same_count >= 5:
                        break
                else:
                    same_count = 0

                last_count = current_count
                await page.evaluate("window.scrollBy(0, 800)")
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
            experiencias_data = await page.evaluate("""
                () => {
                    const experiencias = [];
                    const listings = document.querySelectorAll('a[rel="noopener noreferrer nofollow"][target="_blank"]');
                    
                    listings.forEach(listing => {
                        try {
                            const experiencia = {};
                            const href = listing.href;
                            const idMatch = href.match(/\\/experiences\\/([0-9]+)/);
                            if (idMatch) experiencia.id = idMatch[1];
                            experiencia.url = href;
                            
                            let container = listing.closest('[data-testid="card-container"]') || 
                                           listing.closest('div[role="group"]');
                            
                            if (container) {
                                const tituloElement = container.querySelector('h3, [data-testid="listing-card-title"]');
                                if (tituloElement) experiencia.titulo = tituloElement.textContent.trim();
                                
                                const imgElement = container.querySelector('img');
                                if (imgElement) experiencia.imagen_url = imgElement.src;
                                
                                const allSpans = container.querySelectorAll('span');
                                allSpans.forEach(span => {
                                    const text = span.textContent.trim();
                                    if (text.includes('$') && text.match(/[0-9,]+/)) {
                                        experiencia.precio_texto = text;
                                        const numeroMatch = text.match(/([0-9,]+)/);
                                        if (numeroMatch) experiencia.precio = numeroMatch[0].replace(/,/g, '');
                                    }
                                    if (text.match(/^[0-9]\\.[0-9]+$/)) experiencia.puntuacion = text;
                                    const reviewsMatch = text.match(/\\(([0-9,]+)\\)/);
                                    if (reviewsMatch) experiencia.numero_resenas = reviewsMatch[1].replace(/,/g, '');
                                });
                            }
                            
                            if (experiencia.id || experiencia.titulo) experiencias.push(experiencia);
                        } catch (error) {
                            console.error('Error:', error);
                        }
                    });
                    return experiencias;
                }
            """)

            return experiencias_data

        except Exception as e:
            print(f" Error en Airbnb experiencias: {e}")
            return []

        finally:
            await browser.close()


def enrich_airbnb_experiences(experiencias):
    """Enriquecer datos de experiencias Airbnb"""
    for i, exp in enumerate(experiencias):
        exp["numero"] = i + 1
        exp["fuente"] = "Airbnb Experiences"
        exp["pais"] = "Colombia"
        exp["moneda"] = "COP"
        exp["tipo"] = "actividad"
        exp["fecha_scraping"] = datetime.now().isoformat()

        if "precio" in exp:
            try:
                exp["precio_numerico"] = float(exp["precio"])
            except:
                exp["precio_numerico"] = 0.0

        if "puntuacion" in exp:
            try:
                exp["puntuacion_numerica"] = float(exp["puntuacion"])
            except:
                exp["puntuacion_numerica"] = 0.0

        if "numero_resenas" in exp:
            try:
                exp["total_resenas"] = int(exp["numero_resenas"])
            except:
                exp["total_resenas"] = 0

    return experiencias
