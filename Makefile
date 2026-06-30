.PHONY: dev run cli test lint mcp-start mcp-stop clean

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 9900 --reload

run:
	uvicorn app.main:app --host 0.0.0.0 --port 9900

cli:
	python cli.py

# MCP 服务管理
mcp-start:
	python mcp_servers/log_server.py &
	python mcp_servers/linux_server.py &
	python mcp_servers/search_server.py &

mcp-stop:
	-pkill -f "mcp_servers/" 2>/dev/null || echo "no mcp servers running"

# 质量
format:
	ruff format app/ tests/ mcp_servers/

lint:
	ruff check app/ tests/ mcp_servers/

test:
	python -m pytest tests/ -v

# 数据
ingest:
	python scripts/ingest_knowledge.py

clean:
	rm -rf chroma_data/ uploads/ logs/ __pycache__ .pytest_cache
	find . -name "*.pyc" -delete
