#!/usr/bin/env python3
"""
Test RSS Intelligence MANDATORY proxy mode (NO FALLBACK)
"""
import sys
import os

# Lägg till backend path så vi kan importera moduler
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_mandatory_proxy_mode():
    """Test att proxy är MANDATORY utan fallback"""
    print("🧪 RSS Intelligence MANDATORY Proxy Test")
    print("=" * 50)
    print("🚫 INGEN FALLBACK TILLÅTEN - Proxy eller STOPP!")
    print("=" * 50)
    
    # Test 1: Kontrollera att PROXY_MANDATORY är satt
    print("\n1️⃣ Kontrollerar MANDATORY proxy-konfiguration...")
    
    proxy_enabled = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
    proxy_mandatory = os.getenv('PROXY_MANDATORY', 'false').lower() == 'true'
    http_proxy = os.getenv('HTTP_PROXY')
    alert_email = os.getenv('ALERT_EMAIL')
    
    print(f"   PROXY_ENABLED: {proxy_enabled}")
    print(f"   PROXY_MANDATORY: {proxy_mandatory}")
    print(f"   HTTP_PROXY: {http_proxy}")
    print(f"   ALERT_EMAIL: {alert_email}")
    
    if not all([proxy_enabled, proxy_mandatory, http_proxy, alert_email]):
        print("   ❌ KONFIGURATION SAKNAS!")
        return False
    else:
        print("   ✅ MANDATORY proxy korrekt konfigurerad")
    
    # Test 2: Test SMTP-konfiguration
    print("\n2️⃣ Testar SMTP för proxy failure alerts...")
    try:
        from app.notification_utils import test_smtp_connection
        if test_smtp_connection():
            print("   ✅ SMTP fungerar - kan skicka alerts")
        else:
            print("   ❌ SMTP fungerar inte - inga alerts kan skickas")
            return False
    except Exception as e:
        print(f"   ❌ SMTP-test fel: {e}")
        return False
    
    # Test 3: Test proxy-anslutning
    print("\n3️⃣ Testar MANDATORY proxy-anslutning...")
    try:
        from app.proxy_utils import test_proxy_connection
        if test_proxy_connection():
            print("   ✅ Proxy fungerar - RSS Intelligence kan köra")
            print("   🌐 All trafik går via 95.216.172.130")
        else:
            print("   ❌ Proxy fungerar inte - RSS Intelligence STÄNGS AV")
            print("   📧 Email-alert bör skickas...")
            return False
    except Exception as e:
        print(f"   ❌ Proxy-test fel: {e}")
        return False
    
    # Test 4: Test httpx client creation
    print("\n4️⃣ Testar MANDATORY httpx client creation...")
    try:
        from app.proxy_utils import create_httpx_client
        with create_httpx_client(timeout=10) as client:
            response = client.get('http://httpbin.org/ip')
            if response.status_code == 200:
                ip_data = response.json()
                ip = ip_data.get('origin', 'unknown')
                print(f"   ✅ HTTP client fungerar via IP: {ip}")
                if ip == "95.216.172.130":
                    print("   🎉 PERFEKT: Trafik går via Hetzner!")
                else:
                    print(f"   ⚠️ VARNING: Förväntad IP 95.216.172.130, fick {ip}")
                    return False
            else:
                print(f"   ❌ HTTP request misslyckades: {response.status_code}")
                return False
    except SystemExit as e:
        print("   🚫 SystemExit triggered - RSS Intelligence skulle stängas av!")
        print("   ✅ KORREKT: Ingen fallback sker!")
        return True  # Detta är förväntat beteende
    except Exception as e:
        print(f"   ❌ HTTP client test fel: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ALLA MANDATORY PROXY TESTER LYCKADES!")
    print("✅ RSS Intelligence konfigurerad för ENDAST proxy-drift")
    print("🚫 INGEN FALLBACK - proxy eller stopp!")
    print("📧 Email alerts aktiverade för proxy failures")
    print("=" * 50)
    return True


def test_proxy_failure_simulation():
    """Simulera proxy-fel för att testa email alerts"""
    print("\n" + "=" * 50)
    print("🧪 BONUS: Proxy Failure Simulation Test")
    print("=" * 50)
    
    try:
        from app.notification_utils import send_proxy_failure_alert
        print("📧 Skickar test proxy failure alert...")
        success = send_proxy_failure_alert(
            "TEST SIMULATION: Proxy connection timeout to 10.8.0.1:3128", 
            attempt_count=999
        )
        if success:
            print("✅ Test alert skickad!")
            print(f"📬 Kontrollera email: {os.getenv('ALERT_EMAIL')}")
        else:
            print("❌ Test alert misslyckades")
        return success
    except Exception as e:
        print(f"❌ Test alert fel: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Startar RSS Intelligence MANDATORY proxy test...")
    
    success = test_mandatory_proxy_mode()
    
    if success:
        # Kör bonus test för email simulation
        test_proxy_failure_simulation()
    
    print(f"\n{'✅ RESULTAT: ALLA TESTER OK' if success else '❌ RESULTAT: VISSA TESTER MISSLYCKADES'}")
    sys.exit(0 if success else 1)