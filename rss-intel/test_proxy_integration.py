#!/usr/bin/env python3
"""
Test RSS Intelligence proxy integration
"""
import sys
import os

# Lägg till backend path så vi kan importera moduler
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.proxy_utils import test_proxy_connection, get_proxy_config, create_httpx_client
import feedparser

def test_rss_via_proxy():
    """Test RSS-hämtning via Hetzner proxy"""
    print("🧪 RSS Intelligence Proxy Integration Test")
    print("=" * 50)
    
    # Test 1: Proxy-konfiguration
    print("\n1️⃣ Kontrollerar proxy-konfiguration...")
    proxy_config = get_proxy_config()
    if proxy_config:
        print(f"   ✅ Proxy konfigurerad: {proxy_config}")
    else:
        print("   ❌ Proxy inte konfigurerad")
        return False
    
    # Test 2: Basic proxy connection
    print("\n2️⃣ Testar grundläggande proxy-anslutning...")
    if not test_proxy_connection():
        print("   ❌ Proxy-anslutning misslyckad")
        return False
    
    # Test 3: RSS feed via proxy
    print("\n3️⃣ Testar RSS-hämtning via proxy...")
    test_feed = "https://feeds.feedburner.com/TechCrunch"
    
    try:
        with create_httpx_client(timeout=20) as client:
            print(f"   📡 Hämtar: {test_feed}")
            response = client.get(test_feed)
            
            if response.status_code == 200:
                print(f"   ✅ HTTP Status: {response.status_code}")
                
                # Parse RSS content
                feed = feedparser.parse(response.text)
                
                if hasattr(feed, 'entries') and len(feed.entries) > 0:
                    print(f"   ✅ RSS parsed: {len(feed.entries)} artiklar hittade")
                    
                    # Visa första artikeln
                    first_entry = feed.entries[0]
                    title = first_entry.get('title', 'Ingen titel')
                    print(f"   📰 Första artikel: {title[:60]}...")
                    
                    # Verifiera IP-adress
                    ip_response = client.get('http://httpbin.org/ip')
                    if ip_response.status_code == 200:
                        ip_data = ip_response.json()
                        proxy_ip = ip_data.get('origin', 'unknown')
                        print(f"   🌐 RSS hämtad via IP: {proxy_ip}")
                        
                        if proxy_ip == "95.216.172.130":
                            print("   🎉 SUCCESS: RSS-feeds hämtas via Hetzner proxy!")
                            return True
                        else:
                            print(f"   ⚠️ RSS via annan IP än Hetzner (förväntat: 95.216.172.130)")
                            return False
                    else:
                        print("   ❌ Kunde inte verifiera IP")
                        return False
                else:
                    print("   ❌ RSS kunde inte parsas eller är tom")
                    return False
            else:
                print(f"   ❌ HTTP fel: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ RSS-test misslyckades: {e}")
        return False

def test_docker_environment():
    """Test om vi är i Docker och kan nå proxy"""
    print("\n4️⃣ Testar Docker-miljö...")
    
    # Kontrollera om vi kan nå WireGuard-interface
    try:
        with create_httpx_client(timeout=5) as client:
            # Testa att nå proxy direkt
            response = client.get('http://httpbin.org/ip')
            if response.status_code == 200:
                ip_data = response.json()
                print(f"   🐳 Docker kan nå proxy - IP: {ip_data.get('origin')}")
                return True
            else:
                print("   ❌ Docker kan inte nå proxy")
                return False
    except Exception as e:
        print(f"   ❌ Docker proxy-test fel: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Startar RSS Intelligence proxy-test...")
    
    success = True
    success &= test_rss_via_proxy()
    success &= test_docker_environment()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALLA TESTER LYCKADES!")
        print("✅ RSS Intelligence är redo att använda Hetzner proxy")
    else:
        print("❌ VISSA TESTER MISSLYCKADES")
        print("⚠️ Kontrollera proxy-konfiguration och WireGuard-tunnel")
    print("=" * 50)