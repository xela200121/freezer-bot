# web_server.py
"""Server HTTP per Render"""

from aiohttp import web
import os


class WebServer:
    """Server web per health check"""
    
    @staticmethod
    async def health_check(request):
        """Endpoint per health check di Render"""
        return web.Response(text="Bot is running!")
    
    @staticmethod
    async def start_web_server():
        """Avvia un semplice web server per Render"""
        from config import PORT
        
        app = web.Application()
        app.router.add_get('/', WebServer.health_check)
        app.router.add_get('/health', WebServer.health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        print(f'✅ Web server avviato sulla porta {PORT}')
