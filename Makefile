.PHONY: test coverage lint format clean

# 🔍 Roda todos os testes
test:
	@echo Running tests...
	@set PYTHONPATH=. && pytest app/test -v

# 📊 Gera relatório de cobertura de testes
coverage:
	@echo Generating test coverage report...
	@set PYTHONPATH=. && pytest --cov=app app/test --cov-report=term-missing

# 🧹 Remove arquivos temporários
clean:
	@echo Cleaning temporary files...
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .coverage del .coverage
	@if exist .mypy_cache rmdir /s /q .mypy_cache
	@if exist .ruff_cache rmdir /s /q .ruff_cache

# 🔎 Verifica estilo de código com Ruff
lint:
	@echo Running Ruff linter...
	@ruff check app

# 🧼 Formata código com Ruff
format:
	@echo Formatting code with Ruff...
	@ruff format app
