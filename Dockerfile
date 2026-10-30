FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright HEADLESS=true DATA_DIR=/data
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && groupadd --gid 10001 trialflow \
    && useradd --uid 10001 --gid trialflow --create-home trialflow \
    && mkdir -p /data && chown trialflow:trialflow /data
COPY --chown=trialflow:trialflow . ./
EXPOSE 8000
CMD ["python", "start_hosted.py"]
