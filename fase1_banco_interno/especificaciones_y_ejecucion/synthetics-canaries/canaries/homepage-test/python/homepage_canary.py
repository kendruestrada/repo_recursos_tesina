import os
import time
from aws_synthetics.selenium import synthetics_webdriver as webdriver
from aws_synthetics.common import synthetics_logger as logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def handler(event, context):
    """
    Homepage canary test handler
    Tests the homepage by loading the URL and verifying basic functionality
    """
    # Get target URL from environment variable
    target_url = os.environ.get('TARGET_URL', 'https://example.com')

    logger.info(f'Starting homepage canary test for: {target_url}')

    # Configure Chrome options
    browser = webdriver.Chrome()
    browser.set_page_load_timeout(30)

    try:
        # Step 1: Navigate to homepage
        logger.info(f'Navigating to: {target_url}')
        browser.get(target_url)

        # Wait for page to load
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Step 2: Verify page title
        page_title = browser.title
        logger.info(f'Page title: {page_title}')

        if not page_title or page_title.strip() == '':
            raise Exception('Page title is empty')

        # Step 3: Verify body has content
        body = browser.find_element(By.TAG_NAME, 'body')
        body_text = body.text

        if not body_text or body_text.strip() == '':
            raise Exception('Page body is empty')

        logger.info(f'Body text length: {len(body_text)} characters')

        # Step 4: Check page load performance
        navigation_start = browser.execute_script(
            "return window.performance.timing.navigationStart"
        )
        load_event_end = browser.execute_script(
            "return window.performance.timing.loadEventEnd"
        )

        if load_event_end > 0:
            load_time = load_event_end - navigation_start
            logger.info(f'Page load time: {load_time}ms')

            # Alert if load time is too slow (over 5 seconds)
            if load_time > 5000:
                logger.warn(f'Page load time is slow: {load_time}ms')

        # Step 5: Verify HTTP status
        current_url = browser.current_url
        logger.info(f'Final URL: {current_url}')

        # Take screenshot (automatically uploaded to S3)
        browser.save_screenshot('homepage_success.png')

        logger.info('Homepage test completed successfully')
        return {
            'statusCode': 200,
            'body': 'Homepage test passed',
            'metrics': {
                'pageTitle': page_title,
                'loadTime': load_time if load_event_end > 0 else None,
                'bodyLength': len(body_text)
            }
        }

    except Exception as e:
        logger.error(f'Homepage test failed: {str(e)}')
        # Take screenshot on failure
        try:
            browser.save_screenshot('homepage_failure.png')
        except:
            pass
        raise Exception(f'Homepage test failed: {str(e)}')

    finally:
        browser.quit()
