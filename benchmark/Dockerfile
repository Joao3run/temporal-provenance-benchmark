FROM python:3.11-slim
WORKDIR /experiment
COPY . .
CMD ["sh", "-c", "python3 src/generate_benchmark.py && python3 src/analyze.py"]
