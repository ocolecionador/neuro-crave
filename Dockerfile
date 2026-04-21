FROM python:3.11
WORKDIR /app
COPY backend/ ./backend/
COPY site/ ./site/
RUN pip install -r backend/requirements.txt
EXPOSE 10000
CMD ["python", "backend/main.py"]
