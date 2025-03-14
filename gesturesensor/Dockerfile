FROM python:3.12.7

# Cập nhật và cài đặt các gói cần thiết
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

RUN rm -rf /var/lib/apt/lists/*  # Dọn dẹp cache để giảm dung lượng image

# Thiết lập thư mục làm việc
WORKDIR /code

# Tạo môi trường ảo
RUN python -m venv /code/venv

# Sao chép requirements.txt vào container
COPY requirements.txt .

# Cài đặt dependencies trong môi trường ảo
RUN /code/venv/bin/pip install --upgrade pip && \
    /code/venv/bin/pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Chạy script trong môi trường ảo
CMD [ "/code/venv/bin/python", "./gesturesensor.py" ]
