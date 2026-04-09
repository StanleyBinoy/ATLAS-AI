# This module connects ATLAS to OpenRouter first and falls back to Ollama if needed.
from openai import OpenAI
import ollama

import config


def call_model(
    prompt,
    system_prompt="You are ATLAS, a helpful AI assistant.",
    model=None,
):
    """Call the configured model provider and return a plain-text response."""
    openrouter_model = model or config.PRIMARY_MODEL
    ollama_model = config.FALLBACK_MODEL

    for _ in range(config.MAX_RETRIES):
        try:
            if config.OPENROUTER_API_KEY:
                print(f"Using OpenRouter model: {openrouter_model}")
                client = OpenAI(
                    api_key=config.OPENROUTER_API_KEY,
                    base_url=config.OPENROUTER_BASE_URL,
                )
                response = client.chat.completions.create(
                    model=openrouter_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                )
                content = response.choices[0].message.content
                if content:
                    return content
        except Exception:
            pass

        try:
            print(f"Using Ollama fallback model: {ollama_model}")
            response = ollama.chat(
                model=ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response["message"]["content"]
            if content:
                return content
        except Exception:
            pass

    return "ATLAS: I could not connect to any AI model. Please check your setup."
