# AI Integration Documentation

## Overview

MCP Email Server integrates with GPT-OSS 20B for intelligent email analysis. This document describes the architecture, implementation, and error handling mechanisms.

## Architecture

```
mcp-email → OpenAI Bridge (8085) → Ollama (8080) → GPT-OSS 20B
```

### Components

1. **MCP Email Server**: Main application providing email access via MCP protocol
2. **OpenAI Bridge** (port 8085): Translation layer converting OpenAI API format to Ollama format
3. **Ollama** (port 8080): Local LLM hosting service managing the GPT-OSS model
4. **GPT-OSS 20B**: Large language model (13GB) for email analysis

## Implementation Details

### Health Check Function

```typescript
private async checkGPTOSSAvailability(): Promise<AIServiceStatus> {
  try {
    const response = await axios.get('http://localhost:8085/v1/models', {
      timeout: 5000
    });

    const hasGPTOSS = response.data.data?.some((model: any) =>
      model.id === 'gpt-oss:20b'
    );

    if (!hasGPTOSS) {
      return {
        status: 'model_unavailable',
        message: 'GPT-OSS 20B model not available in Ollama'
      };
    }

    return {
      status: 'available',
      message: 'GPT-OSS 20B ready for email analysis'
    };
  } catch (error) {
    // Error handling logic...
  }
}
```

### Email Analysis Function

The `analyze_email_with_ai` function performs the following steps:

1. **Pre-flight check**: Verify AI service availability
2. **Fetch email**: Retrieve email content from IMAP
3. **Prepare prompt**: Structure analysis request
4. **AI request**: Send to GPT-OSS with 30s timeout
5. **Response parsing**: Extract and format JSON response
6. **Error handling**: Provide detailed feedback on failures

### Error Handling

#### Service Status Codes

| Status | Description | User Guidance |
|--------|-------------|---------------|
| `available` | Service ready | Proceed with analysis |
| `bridge_down` | Port 8085 not responding | Check if ollama-bridge.py is running |
| `timeout` | Response >5s | Service may be overloaded or starting |
| `model_unavailable` | GPT-OSS not loaded | Load model with `ollama pull gpt-oss:20b` |
| `error` | Other failures | Check logs for details |

#### Analysis Error Scenarios

1. **Connection Refused (ECONNREFUSED)**
   - Cause: OpenAI Bridge not running
   - Solution: Start `python3 ollama-bridge.py`

2. **Timeout (ETIMEDOUT)**
   - Cause: Analysis taking >30 seconds
   - Solution: Retry with shorter email or wait

3. **Service Unavailable (HTTP 503)**
   - Cause: Model loading or service restart
   - Solution: Wait a few minutes and retry

4. **Model Not Found**
   - Cause: GPT-OSS 20B not in Ollama
   - Solution: Run `ollama pull gpt-oss:20b`

## AI Capabilities

### Email Classification Categories

- `work`: Professional/business emails
- `personal`: Personal correspondence
- `newsletter`: Subscriptions and newsletters
- `spam`: Unwanted/junk mail
- `notification`: System/service notifications
- `urgent`: Time-sensitive communications

### Priority Levels

- `high`: Requires immediate attention
- `medium`: Should be addressed soon
- `low`: Can be handled later

### Action Recommendations

- `respond`: Requires a reply
- `archive`: Save for reference
- `read-later`: Review when time permits
- `delete`: Can be safely removed
- `forward`: Should be shared with others

## Configuration Requirements

### System Prerequisites

```bash
# Check Ollama service
systemctl status ollama

# Check OpenAI Bridge
ps aux | grep ollama-bridge.py

# Verify model availability
OLLAMA_HOST=http://localhost:8080 ollama list
```

### Port Configuration

- **8080**: Ollama service
- **8085**: OpenAI Bridge
- **6889**: ROCm-AI-Stack backend (if using full stack)

### Environment Variables

```bash
# Optional: Set custom Ollama host
export OLLAMA_HOST=http://localhost:8080

# Optional: Set GPU device for ROCm
export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

## Testing

### Test AI Status

```javascript
// Test script: test-ai-status.js
const axios = require('axios');

async function testAIStatus() {
  try {
    const response = await axios.get('http://localhost:8085/v1/models');
    console.log('AI Service Available:', response.data);
  } catch (error) {
    console.error('AI Service Error:', error.message);
  }
}
```

### Test Email Analysis

```javascript
// Using MCP protocol
{
  "tool": "analyze_email_with_ai",
  "arguments": {
    "connectionId": "main",
    "uid": 12345
  }
}
```

## Troubleshooting

### Common Issues

1. **"OpenAI Bridge not responding"**
   ```bash
   # Start the bridge
   cd /home/micke/claude-env
   python3 ollama-bridge.py > ollama-bridge.log 2>&1 &
   ```

2. **"Model not available"**
   ```bash
   # Load the model
   OLLAMA_HOST=http://localhost:8080 ollama pull gpt-oss:20b
   ```

3. **"Analysis timeout"**
   - Check system resources: `free -h`
   - Check GPU status: `rocm-smi`
   - Monitor Ollama logs: `journalctl -u ollama -f`

### Performance Optimization

- **Memory**: Ensure at least 16GB RAM available
- **GPU**: Verify ROCm drivers and GPU compatibility
- **Disk**: Keep 20GB free for model caching
- **Network**: Use localhost connections to minimize latency

## Security Considerations

- All AI processing occurs locally - no external API calls
- Email content remains within the local network
- Model weights stored locally in Ollama cache
- No telemetry or usage data sent externally

## Future Enhancements

- [ ] Support for multiple AI models
- [ ] Batch email analysis
- [ ] Custom prompt templates
- [ ] Fine-tuning for specific email domains
- [ ] Caching of analysis results
- [ ] Rate limiting for resource management

## Support

For issues or questions:
- Check service status: `check_ai_status` command
- Review logs: `/var/log/ollama/` and `ollama-bridge.log`
- GitHub Issues: https://github.com/manpro/mcp-email/issues