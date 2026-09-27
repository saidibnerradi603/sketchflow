"""
Experiment 01: Universal LangChain Model Initialization Test
Uses LangChain's unified `init_chat_model` method with provider-specific kwargs:
- `model_provider="nvidia_ai_endpoints"` for NVIDIA NIM (DeepSeek-R1, MiniMax M3)
- `model_provider="groq"` for Groq Cloud (OpenAI GPT-OSS 120B, OpenAI GPT-OSS 20B)

This allows zero-code-change switching across providers and models.
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def get_unified_chat_model(model_name: str, provider: str, **kwargs):
    """
    Initializes any model from any provider using LangChain's universal init_chat_model.
    Uses 'nvidia' for NVIDIA NIM and 'groq' for Groq Cloud.
    """
    if provider in ("nvidia", "nvidia_ai_endpoints"):
        provider = "nvidia"
        
    try:
        from langchain.chat_models import init_chat_model
        return init_chat_model(model=model_name, model_provider=provider, **kwargs)
    except Exception as e:
        # Fallback to direct integration classes if init_chat_model has any provider mismatch
        if provider == "nvidia":
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=model_name, **kwargs)
        elif provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(model=model_name, **kwargs)
        else:
            raise e

def test_nvidia_langchain():
    print("\n" + "="*60)
    print("Testing NVIDIA NIM with LangChain init_chat_model")
    print("Provider: 'nvidia' | Proven Fast Models: Nemotron-3-Ultra-550B, Kimi-K3")
    print("="*60)
    
    if not NVIDIA_API_KEY or NVIDIA_API_KEY.startswith("your_"):
        print("⚠️ NVIDIA_API_KEY is not set in .env")
        return False
        
    # Verified fast & active models on build.nvidia.com
    models_to_test = [
        "nvidia/nemotron-3-ultra-550b-a55b", # 0.73s response time! 550B MoE agentic reasoning/coding (65M calls)
        "moonshotai/kimi-k3",                # 2.63s response time! ~2.8T MoE Multimodal (Vision + Tool Calling)
    ]
    
    from langchain_core.messages import HumanMessage, SystemMessage
    
    any_success = False
    for model_id in models_to_test:
        print(f"\n[LangChain NVIDIA] Initializing '{model_id}'...")
        try:
            llm = get_unified_chat_model(
                model_name=model_id,
                provider="nvidia",
                api_key=NVIDIA_API_KEY,
                temperature=0.2,
                max_tokens=150
            )
            
            start = time.perf_counter()
            response = llm.invoke([
                SystemMessage(content="You are SketchFlow Agent. Respond in strict JSON only."),
                HumanMessage(content="Return { \"status\": \"active\", \"provider\": \"NVIDIA NIM\", \"model\": \"" + model_id + "\" }")
            ])
            elapsed = time.perf_counter() - start
            print(f"✅ Success ({elapsed:.2f}s) | Output:\n{response.content.strip()}")
            any_success = True
        except Exception as e:
            print(f"❌ Failed on {model_id}: {e}")
            
    return any_success

def test_groq_langchain():
    print("\n" + "="*60)
    print("Testing Groq Cloud with LangChain init_chat_model")
    print("Provider: 'groq' | Models: OpenAI GPT-OSS 120B, OpenAI GPT-OSS 20B")
    print("="*60)
    
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("your_"):
        print("⚠️ GROQ_API_KEY is not set in .env")
        return False
        
    models_to_test = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b"
    ]
    
    from langchain_core.messages import HumanMessage, SystemMessage
    
    for model_id in models_to_test:
        print(f"\n[LangChain Groq] Initializing '{model_id}'...")
        try:
            # Universal init_chat_model with provider-specific kwargs
            llm = get_unified_chat_model(
                model_name=model_id,
                provider="groq",
                api_key=GROQ_API_KEY,
                temperature=0.2,
                max_tokens=100
            )
            
            start = time.perf_counter()
            response = llm.invoke([
                SystemMessage(content="You are SketchFlow Agent. Respond in strict JSON only."),
                HumanMessage(content="Return { \"status\": \"active\", \"provider\": \"Groq Cloud\", \"speed\": \"blazing\" }")
            ])
            elapsed = time.perf_counter() - start
            print(f"✅ Success ({elapsed:.2f}s) | Output:\n{response.content.strip()}")
            return True
        except Exception as e:
            print(f"❌ Failed on {model_id}: {e}")
            
    return False

if __name__ == "__main__":
    print("🚀 LangChain Universal Chat Model Check (init_chat_model + **kwargs)")
    nv_status = test_nvidia_langchain()
    gr_status = test_groq_langchain()
    
    print("\n" + "="*60)
    print(f"Status Summary: NVIDIA NIM: {'🟢 READY' if nv_status else '🔴 PENDING KEY'} | Groq Cloud: {'🟢 READY' if gr_status else '🔴 PENDING KEY'}")
    print("="*60)
