"""
Email notifications för RSS Intelligence Dashboard
Skickar alerts när proxy-systemet inte fungerar
"""
import os
import smtplib
from email.mime import text as mime_text
from email.mime import multipart as mime_multipart
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def send_proxy_failure_alert(error_details: str, attempt_count: int = 1) -> bool:
    """
    Skickar email-alert när proxy inte fungerar
    
    Args:
        error_details: Teknisk information om felet
        attempt_count: Antal misslyckade försök
    
    Returns:
        True om email skickades, False annars
    """
    
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '465'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'true').lower() == 'true'
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() == 'true'
    from_email = os.getenv('FROM_EMAIL')
    alert_email = os.getenv('ALERT_EMAIL')
    
    if not all([smtp_host, smtp_username, smtp_password, from_email, alert_email]):
        logger.error("SMTP-konfiguration ofullständig - kan inte skicka alert")
        return False
    
    try:
        # Skapa email-meddelande
        msg = mime_multipart.MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = alert_email
        msg['Subject'] = f"🚨 RSS Intelligence Proxy Failure Alert - Attempt #{attempt_count}"
        
        # Email-body
        body = f"""
RSS Intelligence Dashboard - KRITISKT FEL

PROXY-SYSTEMET FUNGERAR INTE!

Tidpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Försök: #{attempt_count}
Server: server3 (158.174.179.61)

TEKNISK INFORMATION:
{error_details}

ÅTGÄRD KRÄVS:
1. Kontrollera WireGuard-tunnel: sudo systemctl status wg-quick@wg0
2. Kontrollera proxy-anslutning: ping 10.8.0.1
3. Kontrollera Squid på Hetzner: ssh -i ~/server_key.pem root@95.216.172.130 "systemctl status squid"

RSS Intelligence kommer INTE att hämta feeds förrän proxy fungerar igen.

INGEN FALLBACK TILL DIREKTANSLUTNING - Detta är avsiktligt!

---
RSS Intelligence Dashboard
Automatisk monitoring
        """.strip()
        
        msg.attach(mime_text.MIMEText(body, 'plain'))
        
        # Skicka email
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            if smtp_use_tls:
                server.starttls()
        
        server.login(smtp_username, smtp_password)
        text = msg.as_string()
        server.sendmail(from_email, alert_email, text)
        server.quit()
        
        logger.info(f"✅ Proxy failure alert skickad till {alert_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Kunde inte skicka proxy failure alert: {e}")
        return False


def send_proxy_recovery_alert() -> bool:
    """
    Skickar email när proxy fungerar igen
    """
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '465'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'true').lower() == 'true'
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() == 'true'
    from_email = os.getenv('FROM_EMAIL')
    alert_email = os.getenv('ALERT_EMAIL')
    
    if not all([smtp_host, smtp_username, smtp_password, from_email, alert_email]):
        return False
    
    try:
        msg = mime_multipart.MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = alert_email
        msg['Subject'] = "✅ RSS Intelligence Proxy Recovery - System OK"
        
        body = f"""
RSS Intelligence Dashboard - ÅTERHÄMTNING

PROXY-SYSTEMET FUNGERAR IGEN!

Tidpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Server: server3 (158.174.179.61)
Proxy IP: 95.216.172.130 (Hetzner)

STATUS:
✅ WireGuard-tunnel aktiv
✅ Squid proxy tillgänglig  
✅ RSS-feeds kan hämtas igen

RSS Intelligence återupptar normal drift.

---
RSS Intelligence Dashboard
Automatisk monitoring
        """.strip()
        
        msg.attach(mime_text.MIMEText(body, 'plain'))
        
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            if smtp_use_tls:
                server.starttls()
        
        server.login(smtp_username, smtp_password)
        server.sendmail(from_email, alert_email, msg.as_string())
        server.quit()
        
        logger.info(f"✅ Proxy recovery alert skickad till {alert_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Kunde inte skicka proxy recovery alert: {e}")
        return False


def test_smtp_connection() -> bool:
    """
    Testar SMTP-konfiguration
    """
    try:
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT', '465'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'true').lower() == 'true'
        smtp_use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() == 'true'
        
        if not all([smtp_host, smtp_username, smtp_password]):
            print("❌ SMTP-konfiguration saknas")
            return False
        
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            if smtp_use_tls:
                server.starttls()
        
        server.login(smtp_username, smtp_password)
        server.quit()
        
        print("✅ SMTP-anslutning fungerar")
        return True
        
    except Exception as e:
        print(f"❌ SMTP-test misslyckades: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testar SMTP-konfiguration...")
    if test_smtp_connection():
        print("📧 Skickar test-alert...")
        send_proxy_failure_alert("TEST: Detta är en testnotifiering", 1)