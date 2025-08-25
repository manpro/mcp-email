# RSS Intelligence - Mobile Access Setup Guide

This guide will help you set up secure mobile access to your RSS Intelligence dashboard using Cloudflare Tunnels.

## Prerequisites

- A domain name registered with Cloudflare (or DNS managed by Cloudflare)
- Cloudflare account with Tunnel access
- RSS Intelligence application running locally

## Quick Setup

### Option 1: Automated Setup (Recommended)

Run the automated setup script:

```bash
cd /home/micke/claude-env/rss-intel
./setup-cloudflare-tunnel.sh
```

This script will:
- Install cloudflared if needed
- Authenticate with Cloudflare
- Create a tunnel named 'rss-intel-mobile'
- Set up DNS records
- Configure the tunnel as a system service
- Create start/stop scripts

### Option 2: Manual Setup

1. **Install cloudflared**:
   ```bash
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared-linux-amd64.deb
   ```

2. **Authenticate**:
   ```bash
   cloudflared tunnel login
   ```

3. **Create tunnel**:
   ```bash
   cloudflared tunnel create rss-intel-mobile
   ```

4. **Configure DNS**:
   ```bash
   cloudflared tunnel route dns rss-intel-mobile rss.yourdomain.com
   ```

5. **Create config file** (`~/.cloudflared/config.yml`):
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: /home/micke/.cloudflared/<tunnel-id>.json
   
   ingress:
     - hostname: rss.yourdomain.com
       service: http://localhost:3000
       originRequest:
         connectTimeout: 30s
         httpHostHeader: localhost
     - service: http_status:404
   ```

6. **Start tunnel**:
   ```bash
   cloudflared tunnel run rss-intel-mobile
   ```

## Usage

### Starting RSS Intelligence with Mobile Access

```bash
# Start backend
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Start frontend
cd web && npm start &

# Start tunnel (if using automated setup)
sudo systemctl start rss-intel-tunnel

# Or run tunnel manually
cloudflared tunnel run rss-intel-mobile
```

### Access Points

- **Local**: http://localhost:3000
- **Mobile**: https://rss.yourdomain.com (replace with your domain)

### Service Management

```bash
# Check tunnel status
sudo systemctl status rss-intel-tunnel

# View tunnel logs
sudo journalctl -f -u rss-intel-tunnel

# Stop tunnel
sudo systemctl stop rss-intel-tunnel

# Restart tunnel
sudo systemctl restart rss-intel-tunnel
```

## Security Considerations

### Basic Security
- Tunnel traffic is encrypted by default
- Only expose necessary services
- Monitor access logs regularly

### Enhanced Security (Optional)

1. **Enable Cloudflare Access**:
   - Add authentication layer
   - Restrict access by email/domain
   - Enable MFA

2. **Application-Level Security**:
   - Implement user authentication
   - Use HTTPS redirects
   - Set secure headers

3. **Network Security**:
   - Firewall local ports
   - Monitor tunnel metrics
   - Regular security updates

## Troubleshooting

### Common Issues

1. **Tunnel not connecting**:
   ```bash
   # Check service status
   sudo systemctl status rss-intel-tunnel
   
   # View detailed logs
   sudo journalctl -u rss-intel-tunnel -n 50
   
   # Test connection
   cloudflared tunnel info rss-intel-mobile
   ```

2. **DNS not resolving**:
   ```bash
   # Check DNS record
   nslookup rss.yourdomain.com
   
   # Re-create DNS record
   cloudflared tunnel route dns rss-intel-mobile rss.yourdomain.com
   ```

3. **Application not accessible**:
   - Verify RSS Intelligence is running on port 3000
   - Check firewall settings
   - Ensure tunnel config points to correct local URL

### Getting Help

- Check Cloudflare Tunnel documentation
- Review tunnel logs for error messages  
- Test local application access first
- Verify domain/DNS configuration

## Mobile-Optimized Features

The RSS Intelligence dashboard includes mobile-specific optimizations:

- **Responsive Design**: Adapts to all screen sizes
- **Touch Navigation**: Mobile-friendly sidebar and controls
- **Offline Reading**: Cache articles for offline access
- **Fast Loading**: Optimized for mobile networks
- **Dark Mode**: Battery-friendly dark theme

## Next Steps

1. **Set up authentication** for secure access
2. **Configure notifications** for new articles
3. **Customize mobile layout** preferences
4. **Set up backup tunnels** for redundancy

## Support

For issues specific to:
- **Cloudflare Tunnels**: Cloudflare Support
- **RSS Intelligence**: Check application logs
- **Mobile Optimization**: Test responsive design tools

Your RSS Intelligence dashboard is now accessible from anywhere securely!