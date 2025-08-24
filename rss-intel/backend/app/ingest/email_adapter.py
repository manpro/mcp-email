"""Email adapter for IMAP email ingestion"""
import imaplib
import email
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import logging
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import re

from .base import BaseAdapter, RawItem, AdapterFactory

logger = logging.getLogger(__name__)


class EmailAdapter(BaseAdapter):
    """Adapter for ingesting emails via IMAP"""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.processed_message_ids = set()
    
    async def fetch_new(self) -> List[RawItem]:
        """Fetch new emails from IMAP server"""
        try:
            # Run IMAP operations in thread pool since imaplib is synchronous
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._fetch_emails_sync)
        except Exception as e:
            logger.error(f"Error fetching emails for {self.source_name}: {e}")
            return []
    
    def _fetch_emails_sync(self) -> List[RawItem]:
        """Synchronous email fetching using imaplib"""
        items = []
        
        # IMAP connection config
        imap_host = self.config.get('imap_host')
        imap_port = self.config.get('imap_port', 993)
        username = self.config.get('username')
        password = self.config.get('password')
        use_ssl = self.config.get('use_ssl', True)
        mailbox = self.config.get('mailbox', 'INBOX')
        
        if not all([imap_host, username, password]):
            logger.error(f"Missing IMAP credentials for {self.source_name}")
            return []
        
        try:
            # Connect to IMAP server
            if use_ssl:
                mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            else:
                mail = imaplib.IMAP4(imap_host, imap_port)
            
            mail.login(username, password)
            mail.select(mailbox)
            
            # Search for emails from last N days
            search_days = self.config.get('search_days', 7)
            since_date = (datetime.now() - timedelta(days=search_days)).strftime('%d-%b-%Y')
            
            # Build search criteria
            search_criteria = ['UNSEEN', f'SINCE {since_date}']
            
            # Add sender filters if configured
            allowed_senders = self.config.get('allowed_senders', [])
            allowed_domains = self.config.get('allowed_domains', [])
            
            if allowed_senders:
                sender_criteria = ' OR '.join([f'FROM "{sender}"' for sender in allowed_senders])
                search_criteria.append(f'({sender_criteria})')
            
            search_query = ' '.join(search_criteria)
            
            # Search for messages
            status, messages = mail.search(None, search_query)
            if status != 'OK':
                logger.warning(f"IMAP search failed: {status}")
                return []
            
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} emails to process")
            
            # Process each email
            for email_id in email_ids:
                try:
                    item = self._process_email(mail, email_id)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"IMAP connection error for {self.source_name}: {e}")
            return []
        
        logger.info(f"Processed {len(items)} emails from {self.source_name}")
        return items
    
    def _process_email(self, mail: imaplib.IMAP4, email_id: bytes) -> Optional[RawItem]:
        """Process a single email message"""
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        if status != 'OK':
            return None
        
        # Parse email message
        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)
        
        # Get message ID to prevent duplicates
        message_id = email_message.get('Message-ID', '')
        if message_id in self.processed_message_ids:
            return None
        self.processed_message_ids.add(message_id)
        
        # Extract basic headers
        subject = self._decode_header(email_message.get('Subject', 'No Subject'))
        from_header = email_message.get('From', '')
        date_header = email_message.get('Date', '')
        
        # Parse sender
        sender_name, sender_email = parseaddr(from_header)
        sender = sender_name or sender_email
        
        # Check if sender/domain is allowed
        if not self._is_sender_allowed(sender_email):
            return None
        
        # Parse date
        published_at = datetime.now(timezone.utc)
        if date_header:
            try:
                published_at = parsedate_to_datetime(date_header)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.debug(f"Could not parse email date {date_header}: {e}")
        
        # Extract email content
        content = self._extract_email_content(email_message)
        
        # Generate URL (could be improved with permalink if available)
        url = f"mailto:{sender_email}?subject={subject}&date={published_at.isoformat()}"
        
        # Extract any links from content for better URL
        links = re.findall(r'https?://[^\s<>"]+', content)
        if links:
            url = links[0]  # Use first link as primary URL
        
        return RawItem(
            title=subject,
            url=url,
            content=content,
            published_at=published_at,
            source=f"Email from {sender}",
            author=sender,
            metadata={
                'type': 'email',
                'sender_email': sender_email,
                'sender_name': sender_name,
                'message_id': message_id,
                'links_found': links[:5] if links else []  # Store up to 5 links
            }
        )
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header that might be encoded"""
        if not header_value:
            return ''
        
        decoded_fragments = []
        for fragment, encoding in decode_header(header_value):
            if isinstance(fragment, bytes):
                if encoding:
                    fragment = fragment.decode(encoding)
                else:
                    fragment = fragment.decode('utf-8', errors='ignore')
            decoded_fragments.append(fragment)
        
        return ''.join(decoded_fragments)
    
    def _extract_email_content(self, email_message: email.message.Message) -> str:
        """Extract text content from email message"""
        content_parts = []
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True)
                        if body:
                            content_parts.append(body.decode('utf-8', errors='ignore'))
                    except Exception as e:
                        logger.debug(f"Error decoding text/plain part: {e}")
                
                elif content_type == 'text/html':
                    try:
                        body = part.get_payload(decode=True)
                        if body:
                            html_content = body.decode('utf-8', errors='ignore')
                            # Basic HTML stripping
                            text_content = re.sub(r'<[^>]+>', '', html_content)
                            text_content = re.sub(r'\s+', ' ', text_content).strip()
                            content_parts.append(text_content)
                    except Exception as e:
                        logger.debug(f"Error decoding text/html part: {e}")
        else:
            # Single part message
            try:
                body = email_message.get_payload(decode=True)
                if body:
                    content_parts.append(body.decode('utf-8', errors='ignore'))
            except Exception as e:
                logger.debug(f"Error decoding single part message: {e}")
        
        return '\n\n'.join(content_parts) if content_parts else 'No content available'
    
    def _is_sender_allowed(self, sender_email: str) -> bool:
        """Check if sender is in allowed list"""
        if not sender_email:
            return False
        
        allowed_senders = self.config.get('allowed_senders', [])
        allowed_domains = self.config.get('allowed_domains', [])
        
        # If no restrictions configured, allow all
        if not allowed_senders and not allowed_domains:
            return True
        
        # Check exact sender match
        if sender_email.lower() in [s.lower() for s in allowed_senders]:
            return True
        
        # Check domain match
        sender_domain = sender_email.split('@')[-1].lower()
        if sender_domain in [d.lower() for d in allowed_domains]:
            return True
        
        return False


# Register the adapter
AdapterFactory.register('email', EmailAdapter)