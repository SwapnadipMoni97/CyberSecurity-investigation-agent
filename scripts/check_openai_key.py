"""Make one small API request to verify credentials and model access."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)


def main() -> int:
    project_env = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(project_env)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set. Add it to secops-investigation-agent/.env first.")
        return 2

    model = os.getenv("OPENAI_MODEL", "gpt-6.1-terra")
    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=model,
            input="Reply with exactly: API key check passed.",
            max_output_tokens=32,
            store=False,
        )
    except AuthenticationError:
        print("Authentication failed. Check that OPENAI_API_KEY is copied correctly and active.")
        return 1
    except PermissionDeniedError:
        print(f"The key is valid, but this project may not have access to model {model}.")
        return 1
    except RateLimitError:
        print("The request was rate-limited or the API project has no usable quota/credits.")
        return 1
    except APIConnectionError:
        print("Could not connect to the API. Check network access and try again.")
        return 1
    except APIStatusError as exc:
        print(f"API request failed with HTTP {exc.status_code} ({type(exc).__name__}).")
        return 1

    print(f"API request succeeded. Model: {model}")
    print(f"Response: {response.output_text.strip() or '[empty response]'}")
    if response.usage:
        print(
            "Tokens: "
            f"{response.usage.input_tokens} input, "
            f"{response.usage.output_tokens} output"
        )
    print("This verifies the key and model access with one short billable API request.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
