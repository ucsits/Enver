# Linting
black src/ tests/
isort src/ tests/
flake8 src/ tests/

# Testing
pytest --maxfail=1 --disable-warnings -q
