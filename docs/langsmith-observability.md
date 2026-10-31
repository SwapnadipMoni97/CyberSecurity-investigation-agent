# Optional LangSmith observability

This project uses LangGraph. LangSmith can trace graph runs so you can inspect node execution, inputs, outputs, and failures. Tracing is optional and disabled by default; the demo continues to work locally without a LangSmith account or API key.

## Enable tracing

1. Create a LangSmith account and a project at https://smith.langchain.com.
2. Create an API key in your LangSmith account settings.
3. In the project .env file, set these values:

       LANGSMITH_TRACING=true
       LANGSMITH_API_KEY=your-langsmith-api-key
       LANGSMITH_PROJECT=secops-investigation-agent

4. Restart Uvicorn, run the sample investigation, then open the project's Tracing page in LangSmith.

The application loads .env at startup. Keep the key in .env; do not commit it or paste it into source code. The repository's .gitignore already excludes .env.

## Data handling

When tracing is enabled, LangGraph sends run traces to LangSmith. Traces may include the analyst question, selected event evidence, and report outputs. Use only synthetic or sanitized security events unless you have reviewed your organization's data-handling requirements and LangSmith settings.

To disable trace export, set LANGSMITH_TRACING=false or remove the LangSmith variables, then restart the app. The local deterministic workflow remains available.

## References

- LangSmith tracing: https://docs.langchain.com/langsmith/observability
- LangGraph observability: https://docs.langchain.com/oss/python/langgraph/observability
