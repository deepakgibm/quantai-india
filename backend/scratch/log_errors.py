import os
import sys
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Listen to console messages
        def handle_console(msg):
            print(f"[Console {msg.type}] {msg.text}")
            if msg.location:
                print(f"  at {msg.location.get('url')}:{msg.location.get('lineNumber')}:{msg.location.get('columnNumber')}")
        
        page.on("console", handle_console)
        
        # Listen to page errors (uncaught exceptions)
        def handle_pageerror(err):
            print(f"[PageError] {err}")
            if hasattr(err, "stack"):
                print(f"Stack:\n{err.stack}")
        
        page.on("pageerror", handle_pageerror)

        # Listen to all requests
        def handle_request(req):
            print(f"[Request] {req.method} {req.url}")

        page.on("request", handle_request)

        # Listen to all responses
        def handle_response(res):
            print(f"[Response] {res.status} {res.url}")

        page.on("response", handle_response)
        
        print("Navigating to http://localhost:5173...")
        try:
            response = page.goto("http://localhost:5173", timeout=15000)
            page.wait_for_timeout(5000) # Wait 5 seconds to capture all async errors
        except Exception as e:
            print("Navigation/Wait failed:", e)
            
        print("Page URL:", page.url)
        print("Page Title:", page.title())
        # Print root element HTML
        root_html = page.evaluate("document.getElementById('root') ? document.getElementById('root').innerHTML : 'no root'")
        print("Root innerHTML:", root_html)
        
        browser.close()

if __name__ == "__main__":
    run()
