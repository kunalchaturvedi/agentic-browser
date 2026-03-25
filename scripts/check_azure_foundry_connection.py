from __future__ import annotations

import sys

import httpx

from agentic_browser.config import get_settings


def main() -> int:
    settings = get_settings()

    missing = [
        name
        for name, value in (
            ("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
            ("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key),
            ("AZURE_OPENAI_DEPLOYMENT_NAME", settings.azure_openai_deployment_name),
            ("AZURE_OPENAI_API_VERSION", settings.azure_openai_api_version),
        )
        if not value
    ]
    if missing:
        print("Missing Azure AI Foundry configuration:", ", ".join(missing), file=sys.stderr)
        print("Copy .env.example to .env and fill in the Azure values before running this check.", file=sys.stderr)
        return 1

    endpoint = (
        f"{settings.azure_openai_endpoint.rstrip('/')}"
        f"/openai/deployments/{settings.azure_openai_deployment_name}/chat/completions"
    )
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "Reply with the exact text AZURE_CONNECTION_OK and nothing else.",
            },
            {
                "role": "user",
                "content": "Confirm the deployment is reachable.",
            },
        ],
        "temperature": 0.0,
        "max_tokens": 20,
    }
    headers = {
        "api-key": settings.azure_openai_api_key,
        "Content-Type": "application/json",
    }
    params = {"api-version": settings.azure_openai_api_version}

    try:
        with httpx.Client(timeout=settings.azure_openai_timeout_seconds) as client:
            response = client.post(endpoint, params=params, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Azure AI Foundry connection check failed: {exc}", file=sys.stderr)
        return 1

    try:
        content = response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"Azure AI Foundry returned an unexpected response shape: {exc}", file=sys.stderr)
        return 1

    print(f"Deployment response: {content}")
    if content != "AZURE_CONNECTION_OK":
        print("The deployment responded, but the returned content was not the expected sentinel value.", file=sys.stderr)
        return 1

    print("Azure AI Foundry connection check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
