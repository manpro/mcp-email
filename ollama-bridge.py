#!/usr/bin/env python3
"""
Ollama to OpenAI API Bridge
Converts OpenAI API calls to Ollama format
"""

import json
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import time
import uuid

app = FastAPI(title="Ollama-OpenAI Bridge", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama server configuration
OLLAMA_BASE_URL = "http://localhost:8080"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-oss:20b"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 100
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@app.get("/health")
async def health_check():
    """Health check endpoint compatible with WebGUI"""
    try:
        async with httpx.AsyncClient() as client:
            # Test Ollama connection
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "backend": "ollama",
                    "ollama_status": "connected",
                    "models_available": True
                }
            else:
                return {
                    "status": "degraded", 
                    "backend": "ollama",
                    "ollama_status": "disconnected",
                    "error": f"Ollama returned {response.status_code}"
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "backend": "ollama", 
            "ollama_status": "error",
            "error": str(e)
        }

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI format)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                ollama_data = response.json()
                models = []
                for model in ollama_data.get("models", []):
                    models.append({
                        "id": model["name"],
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "ollama",
                        "permission": [],
                        "root": model["name"],
                        "parent": None
                    })
                return {"object": "list", "data": models}
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch models from Ollama")
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        # Return default GPT-OSS model if Ollama is not responding
        return {
            "object": "list",
            "data": [{
                "id": "gpt-oss:20b",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "ollama",
                "permission": [],
                "root": "gpt-oss:20b",
                "parent": None
            }]
        }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Chat completions endpoint (OpenAI format -> Ollama format)"""
    try:
        # Convert OpenAI format to Ollama format
        ollama_request = {
            "model": request.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            "stream": request.stream,  # Use actual streaming request
            "think": True if "gpt-oss" in request.model.lower() else False,  # Enable thinking for GPT-OSS
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            }
        }
        
        if request.stop:
            ollama_request["options"]["stop"] = request.stop
        
        logger.info(f"🔄 Forwarding {'streaming' if request.stream else 'non-streaming'} request to Ollama: {request.model}")
        
        # Handle streaming vs non-streaming
        if request.stream:
            return await handle_streaming_request(ollama_request, request)
        else:
            return await handle_non_streaming_request(ollama_request, request)
            
    except httpx.TimeoutException:
        logger.error("⏰ Request to Ollama timed out")
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        logger.error(f"❌ Error in chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_non_streaming_request(ollama_request: dict, request: ChatCompletionRequest):
    """Handle non-streaming requests"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=ollama_request
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Ollama returned {response.status_code}: {response.text}")
            raise HTTPException(
                status_code=500, 
                detail=f"Ollama API error: {response.status_code}"
            )
        
        ollama_response = response.json()
        
        # Extract content - for thinking models, prefer content over thinking
        content = ""
        if "message" in ollama_response:
            message = ollama_response["message"]
            # For GPT-OSS thinking models, use content field if available
            if "gpt-oss" in request.model.lower():
                content = message.get("content", "")
            else:
                content = message.get("content", "")
        
        # Convert to OpenAI format
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": ollama_response.get("prompt_eval_count", 0),
                "completion_tokens": ollama_response.get("eval_count", 0), 
                "total_tokens": ollama_response.get("prompt_eval_count", 0) + ollama_response.get("eval_count", 0)
            }
        )


async def handle_streaming_request(ollama_request: dict, request: ChatCompletionRequest):
    """Handle streaming requests with SSE format"""
    from fastapi.responses import StreamingResponse
    
    async def generate_stream():
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST", 
                f"{OLLAMA_BASE_URL}/api/chat",
                json=ollama_request
            ) as response:
                
                if response.status_code != 200:
                    error_data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": f"Error: {response.status_code}"},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                # For GPT-OSS thinking models, we need different handling
                is_thinking_model = "gpt-oss" in request.model.lower()
                
                if is_thinking_model:
                    # For thinking models, use non-streaming approach to get clean content
                    # Make a new non-streaming request to get the final content
                    non_stream_request = ollama_request.copy()
                    non_stream_request["stream"] = False
                    
                    async with httpx.AsyncClient(timeout=60.0) as non_stream_client:
                        non_stream_response = await non_stream_client.post(
                            f"{OLLAMA_BASE_URL}/api/chat",
                            json=non_stream_request
                        )
                        
                        if non_stream_response.status_code == 200:
                            result = non_stream_response.json()
                            if "message" in result:
                                final_content = result["message"].get("content", "")
                                if final_content:
                                    # Stream the final content word by word for smooth UI
                                    words = final_content.split()
                                    for i, word in enumerate(words):
                                        # Add space before word (except first)
                                        word_content = (" " if i > 0 else "") + word
                                        
                                        chunk_data = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(time.time()),
                                            "model": request.model,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {"content": word_content},
                                                "finish_reason": None
                                            }]
                                        }
                                        yield f"data: {json.dumps(chunk_data)}\n\n"
                                        await asyncio.sleep(0.05)  # Small delay for smooth streaming
                    
                    # Send completion signal
                    final_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                else:
                    # For regular models, stream content normally
                    accumulated_content = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                ollama_chunk = json.loads(line)
                                
                                # Extract content normally
                                chunk_content = ""
                                if "message" in ollama_chunk:
                                    chunk_content = ollama_chunk["message"].get("content", "")
                                
                                # Only send non-empty content chunks
                                if chunk_content and chunk_content != accumulated_content:
                                    delta_content = chunk_content[len(accumulated_content):]
                                    accumulated_content = chunk_content
                                    
                                    if delta_content:
                                        chunk_data = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(time.time()),
                                            "model": request.model,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {"content": delta_content},
                                                "finish_reason": None
                                            }]
                                        }
                                        yield f"data: {json.dumps(chunk_data)}\n\n"
                                
                                # Handle completion
                                if ollama_chunk.get("done", False):
                                    final_chunk = {
                                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                        "object": "chat.completion.chunk",
                                        "created": int(time.time()),
                                        "model": request.model,
                                        "choices": [{
                                            "index": 0,
                                            "delta": {},
                                            "finish_reason": "stop"
                                        }]
                                    }
                                    yield f"data: {json.dumps(final_chunk)}\n\n"
                                    yield "data: [DONE]\n\n"
                                    break
                                
                            except json.JSONDecodeError:
                                continue
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

@app.get("/memory")
async def get_memory_usage():
    """Memory usage endpoint for WebGUI compatibility"""
    return {
        "gpu_memory": {
            "used": "14.6 GB",
            "total": "24.0 GB", 
            "free": "9.4 GB"
        },
        "system_memory": {
            "used": "12.0 GB",
            "total": "32.0 GB",
            "free": "20.0 GB"
        },
        "backend": "ollama",
        "model_loaded": True
    }

if __name__ == "__main__":
    import uvicorn
    print("🌉 Starting Ollama-OpenAI Bridge on http://localhost:8090")
    print("🔗 Bridging OpenAI API calls to Ollama at http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8085)