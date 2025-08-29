"""
Proxy utilities for RSS Intelligence Dashboard
Konfigurerar httpx-klienter att använda Hetzner proxy via WireGuard
"""
import os
import httpx
import sys
from typing import Optional, Dict, Any
from .notification_utils import send_proxy_failure_alert, send_proxy_recovery_alert
import logging

logger = logging.getLogger(__name__)


def get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Hämtar proxy-konfiguration från miljövariabler
    Returns: Dict med proxy-inställningar eller None om proxy inte är aktiverad
    """
    if not os.getenv('PROXY_ENABLED', '').lower() in ['true', '1', 'yes']:
        return None
    
    http_proxy = os.getenv('HTTP_PROXY')
    https_proxy = os.getenv('HTTPS_PROXY', http_proxy)
    
    if not http_proxy:
        return None
    
    return {
        'http://': http_proxy,
        'https://': https_proxy
    }


def create_httpx_client(timeout: float = 30.0, **kwargs) -> httpx.Client:
    """
    Skapar httpx.Client med MANDATORY proxy-konfiguration
    Args:
        timeout: Request timeout i sekunder
        **kwargs: Extra arguments till httpx.Client
    Returns: Konfigurerad httpx.Client
    Raises: SystemExit om proxy inte fungerar och PROXY_MANDATORY=true
    """
    proxy_config = get_proxy_config()
    is_mandatory = os.getenv('PROXY_MANDATORY', 'false').lower() == 'true'
    
    if not proxy_config:
        error_msg = "❌ KRITISKT FEL: Proxy inte konfigurerad men PROXY_MANDATORY=true"
        logger.error(error_msg)
        if is_mandatory:
            send_proxy_failure_alert(f"Proxy configuration missing: {error_msg}")
            print(error_msg)
            print("🚫 RSS Intelligence avstängd - ingen fallback tillåten!")
            sys.exit(1)
    
    # Testa proxy-anslutning INNAN vi skapar klient
    if is_mandatory and not test_proxy_connection_silent():
        error_msg = "❌ KRITISKT FEL: Proxy-anslutning misslyckades"
        logger.error(error_msg)
        send_proxy_failure_alert(f"Proxy connection failed: Cannot reach 10.8.0.1:3128")
        print(error_msg)
        print("🚫 RSS Intelligence avstängd - ingen fallback tillåten!")
        sys.exit(1)
    
    client_kwargs = {
        'timeout': timeout,
        'follow_redirects': True,
        **kwargs
    }
    
    # httpx använder proxy parameter
    proxy_url = proxy_config['http://']
    client_kwargs['proxy'] = proxy_url
    logger.info(f"🌐 Använder MANDATORY Hetzner proxy: {proxy_url}")
    print(f"🌐 Använder MANDATORY Hetzner proxy: {proxy_url}")
    
    return httpx.Client(**client_kwargs)


async def create_async_httpx_client(timeout: float = 30.0, **kwargs) -> httpx.AsyncClient:
    """
    Skapar httpx.AsyncClient med proxy-konfiguration
    Args:
        timeout: Request timeout i sekunder
        **kwargs: Extra arguments till httpx.AsyncClient
    Returns: Konfigurerad httpx.AsyncClient
    """
    proxy_config = get_proxy_config()
    
    client_kwargs = {
        'timeout': timeout,
        'follow_redirects': True,
        **kwargs
    }
    
    if proxy_config:
        proxy_url = proxy_config['http://']
        client_kwargs['proxy'] = proxy_url
        print(f"🌐 Använder Hetzner proxy (async): {proxy_url}")
    else:
        print("🔄 Proxy inaktiverad - använder direktanslutning (async)")
    
    return httpx.AsyncClient(**client_kwargs)


def get_proxy_headers() -> Dict[str, str]:
    """
    Returnerar headers optimerade för web scraping via proxy
    """
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


def test_proxy_connection_silent() -> bool:
    """
    Tyst proxy-test utan print-output
    Returns: True om proxy fungerar, False annars
    """
    proxy_config = get_proxy_config()
    if not proxy_config:
        return False
    
    try:
        # Skapa klient direkt utan att kalla create_httpx_client (undviker rekursion)
        proxy_url = proxy_config['http://']
        with httpx.Client(proxy=proxy_url, timeout=10.0) as client:
            response = client.get('http://httpbin.org/ip')
            if response.status_code == 200:
                data = response.json()
                ip = data.get('origin', 'unknown')
                return ip == "95.216.172.130"  # Hetzner IP
            return False
    except Exception:
        return False


def test_proxy_connection() -> bool:
    """
    Testar proxy-anslutning genom att hämta IP-adress (med output)
    Returns: True om proxy fungerar, False annars
    """
    proxy_config = get_proxy_config()
    if not proxy_config:
        print("❌ Proxy inte konfigurerad")
        return False
    
    try:
        proxy_url = proxy_config['http://']
        with httpx.Client(proxy=proxy_url, timeout=10.0) as client:
            response = client.get('http://httpbin.org/ip')
            if response.status_code == 200:
                data = response.json()
                ip = data.get('origin', 'unknown')
                print(f"✅ Proxy fungerar! Extern IP: {ip}")
                success = ip == "95.216.172.130"  # Hetzner IP
                if success and os.getenv('PROXY_MANDATORY', 'false').lower() == 'true':
                    # Skicka recovery alert om proxy fungerar igen
                    send_proxy_recovery_alert()
                return success
            else:
                print(f"❌ Proxy svarar med status: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Proxy-test misslyckades: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testar proxy-konfiguration...")
    print(f"Proxy config: {get_proxy_config()}")
    test_proxy_connection()