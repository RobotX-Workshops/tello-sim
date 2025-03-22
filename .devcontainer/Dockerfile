FROM python:3.9
RUN apt-get update && apt-get install -y \
    fluxbox \
    x11vnc \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*
CMD ["x11vnc", "-forever", "-nopw", "-create"]