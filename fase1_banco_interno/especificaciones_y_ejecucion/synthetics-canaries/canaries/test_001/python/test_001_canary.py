import os
import time
import json
from aws_synthetics.selenium import synthetics_webdriver as webdriver
from aws_synthetics.common import synthetics_logger as logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def handler(event, context):
    url = os.environ.get('FRONTEND_URL')
    logger.info(f"🌐 Iniciando navegación en: {url}")

    chrome_options = Options()
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    browser = webdriver.Chrome(chrome_options=chrome_options)
    browser.set_page_load_timeout(30)
    
    bug_reproduced = False

    try:
        browser.get(url)

        # 1. Interactuar con el formulario
        logger.info("Completando formulario de compra...")
        browser.find_element(By.ID, "n").send_keys("Maximiliano Lopez")
        browser.find_element(By.ID, "e").send_keys("usuario@example.com")
        browser.find_element(By.ID, "a").send_keys("Rancagua")

        # 2. Click en Verify
        browser.find_element(By.CSS_SELECTOR, "#f button[type='submit']").click()
        # 3. Esperar sincronización (el bug hace que address sea null pero devuelva 200)
        WebDriverWait(browser, 10).until(
            EC.text_to_be_present_in_element((By.ID, "o"), "Data synchronized.")
        )
        logger.info("Sincronización simulada exitosa. Verificando estado del botón...")

        # 4. Intentar Procesar Compra
        complete_btn = browser.find_element(By.ID, "b")
        if complete_btn.is_enabled():
            logger.info("Botón habilitado (Bug activo). Ejecutando compra...")
            complete_btn.click()
        else:
            raise Exception("El bug no se manifestó: El botón quedó deshabilitado.")

        # 5. Verificar resultado final
        logger.info("Esperando respuesta de red del servidor...")
        time.sleep(20)  # Tiempo suficiente para que la petición 400 quede registrada
        
        # Obtenemos los logs de performance (el F12 interno)
        logs = browser.get_log('performance')
        status_400_detected = False

        for entry in logs:
            log_data = json.loads(entry['message'])
            message = log_data['message']
            
            # Buscamos el evento donde el servidor responde (responseReceived)
            if message['method'] == 'Network.responseReceived':
                response = message['params']['response']
                # Verificamos si la URL es de compra y si devolvió el error 400
                if '/process-purchase' in response['url'] and response['status'] == 400:
                    logger.info(f"🎯 PRUEBA REINA: Se detectó un error HTTP 400 en: {response['url']}")
                    status_400_detected = True
                    break

        # Verificamos si el síntoma visual persiste (UI pegada)
        output_text = browser.find_element(By.ID, "o").text
        logger.info(f"Estado visual de la aplicación: {output_text}")

        # EL BUG SE REPRODUCE SI:
        # Hubo un 400 en la red Y la aplicación no mostró error (sigue en 'Processing...')
        if status_400_detected and "Processing..." in output_text:
            logger.info("🎯 BUG CONFIRMADO: El backend rechazó la compra (400) pero el frontend se congeló.")
            browser.save_screenshot("bug_001_network_confirmed.png")
            bug_reproduced = True
        else:
            logger.warning("No se cumplieron las condiciones del Bug 001.")
            bug_reproduced = False

    except Exception as e:
        logger.error(f"Error en el flujo del Canary: {str(e)}")
        browser.save_screenshot("canary_error.png")
        raise e
    finally:
        browser.quit()

    if bug_reproduced:
        return {"status": "success", "message": "Test 001 bug detected and verified"}
    else:
        raise Exception("Fallo de reproducción: La compra fue exitosa inesperadamente.")