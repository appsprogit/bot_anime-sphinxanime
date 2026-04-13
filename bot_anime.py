import os
import smtplib
import asyncio
from email.message import EmailMessage
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
import telegram 

def enviar_correo(asunto, cuerpo_texto, cuerpo_html=None):
    print(f"Preparando correo: {asunto}")
    email_sender = os.environ.get("EMAIL_USER")
    email_password = os.environ.get("EMAIL_PASS")
    email_receiver = "eduardoguerere@gmail.com"

    if not email_sender or not email_password:
        print("Error crítico: Secretos de GitHub no encontrados.")
        return

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = email_sender
    msg['To'] = email_receiver
    msg.set_content(cuerpo_texto)
    
    if cuerpo_html:
        msg.add_alternative(cuerpo_html, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_sender, email_password)
            smtp.send_message(msg)
            print("¡Correo enviado exitosamente!")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

async def generar_captura_html_y_enviar_telegram(html_content):
    print("Generando captura para Telegram...")
    telegram_token = os.environ.get("TELEGRAM_TOKEN")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not telegram_token or not telegram_chat_id:
        print("Aviso: Secretos de Telegram no encontrados.")
        return

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1000, 'height': 2000})
            page = await context.new_page()
            
            await page.set_content(html_content)
            await page.wait_for_load_state("networkidle")
            
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            await browser.close()
            
        print("Enviando a Telegram...")
        bot = telegram.Bot(token=telegram_token)
        await bot.send_photo(chat_id=telegram_chat_id, photo=screenshot_bytes, caption="⛩️ ¡Nuevos Animes en SphinxAnime listos!")
        print("¡Imagen enviada a Telegram!")

    except Exception as e:
        print(f"Error en Telegram: {e}")

def scrapear_y_enviar_todo():
    url = "https://sphinxanime.com/"
    animes_data = []

    print("Iniciando el navegador para extraer datos...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # --- TRAMPA ANTI-BOT: Le decimos a la web que somos un humano usando Windows y Chrome ---
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            print("Entrando a SphinxAnime y esperando a que la red se estabilice...")
            # wait_until="networkidle" espera a que terminen de cargar todos los scripts
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Pausa táctica de 5 segundos para que aparezcan los animes
            print("Esperando 5 segundos extra para renderizado...")
            page.wait_for_timeout(5000) 
            
            elementos = page.query_selector_all("div.recent-item") 
            print(f"¡Se encontraron {len(elementos)} bloques de anime en la página!")
            
            for el in elementos[:12]:
                enlace_titulo = el.query_selector("h3.post-box-title a")
                imagen_el = el.query_selector("div.post-thumbnail img")
                
                if enlace_titulo and imagen_el:
                    title = enlace_titulo.inner_text()
                    link = enlace_titulo.get_attribute("href")
                    
                    image_url = imagen_el.get_attribute("src") or imagen_el.get_attribute("data-src") or imagen_el.get_attribute("srcset")
                    if image_url and ' ' in image_url:
                        image_url = image_url.split(' ')[0]
                    
                    if title and link and image_url:
                        animes_data.append({
                            'title': title.strip(),
                            'link': link,
                            'image_url': image_url
                        })
                        print(f" - Capturado: {title.strip()[:30]}...")
                        
            browser.close()
            
    except Exception as e:
        enviar_correo("⚠️ Alerta: Error de conexión en SphinxAnime", f"Error:\n{e}")
        return

    if not animes_data:
        enviar_correo("⚠️ Alerta: Bot vacío SphinxAnime", "No se encontraron animes. Hay que revisar los selectores.")
        return

    print(f"Éxito: Generando grilla para {len(animes_data)} animes...")
    
    html_anime_cards = "<table width='100%' cellpadding='0' cellspacing='0' border='0' style='max-width: 900px; margin: auto;'>\n"
    
    for i in range(0, len(animes_data), 3):
        html_anime_cards += "<tr>\n"
        row_animes = animes_data[i:i+3]
        
        for anime in row_animes:
            html_anime_cards += f"""
            <td align="center" valign="top" style="padding: 15px; width: 33.33%;">
                <div style="width: 250px; background-color: #1a1a2e; border: 2px solid #e94560; border-radius: 15px; overflow: hidden; margin: 0 auto; display: block;">
                    <a href="{anime['link']}" target="_blank" style="text-decoration: none; display: block;">
                        <div style="background-color: #0f3460; color: #fff; font-weight: bold; padding: 10px; font-size: 14px; border-bottom: 2px solid #e94560; text-align: center; height: 40px; overflow: hidden;">
                            {anime['title']}
                        </div>
                        <div style="padding: 10px; text-align: center; background-color: #1a1a2e;">
                            <img src="{anime['image_url']}" alt="{anime['title']}" width="230" height="300" style="width: 230px; height: 300px; object-fit: cover; display: block; margin: 0 auto; border: none; border-radius: 8px;">
                        </div>
                    </a>
                </div>
            </td>
            """
            
        for _ in range(3 - len(row_animes)):
            html_anime_cards += "<td style='width: 33.33%; padding: 15px;'></td>\n"
            
        html_anime_cards += "</tr>\n"
        
    html_anime_cards += "</table>\n"

    html_body_email = f"""
    <div style="font-family: Arial, sans-serif; background-color: #0d1117; padding: 20px;">
        <div style="max-width: 900px; margin: 0 auto; background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px;">
            <h1 style="color: #e94560; text-align: center; margin-bottom: 30px;">⛩️ Novedades del Día - SphinxAnime ⛩️</h1>
            <p style="font-size: 16px; text-align: center; margin-bottom: 40px; color: #c9d1d9;">
                Eduardo, aquí tienes los últimos {len(animes_data)} animes publicados:
            </p>
            {html_anime_cards}
        </div>
    </div>
    """

    enviar_correo(
        asunto="⛩️ Novedades del Día - SphinxAnime",
        cuerpo_texto="Tu cliente de correo no soporta HTML.",
        cuerpo_html=html_body_email
    )

    asyncio.run(generar_captura_html_y_enviar_telegram(html_body_email))

if __name__ == "__main__":
    scrapear_y_enviar_todo()
