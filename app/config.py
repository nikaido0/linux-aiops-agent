from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Linux AIOps Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9900

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # DashScope Embedding
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_embedding_model: str = "text-embedding-v4"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # RAG
    rag_top_k: int = 10
    rag_rerank_top_k: int = 3
    chunk_size: int = 600
    chunk_overlap: int = 100

    # MCP
    mcp_log_transport: str = "streamable-http"
    mcp_log_url: str = "http://localhost:8003/mcp"
    mcp_linux_transport: str = "streamable-http"
    mcp_linux_url: str = "http://localhost:8004/mcp"
    mcp_search_transport: str = "streamable-http"
    mcp_search_url: str = "http://localhost:8005/mcp"

    @property
    def mcp_servers(self) -> dict:
        return {
            "log": {"transport": self.mcp_log_transport, "url": self.mcp_log_url},
            "linux": {"transport": self.mcp_linux_transport, "url": self.mcp_linux_url},
            "search": {"transport": self.mcp_search_transport, "url": self.mcp_search_url},
        }


config = Settings()
