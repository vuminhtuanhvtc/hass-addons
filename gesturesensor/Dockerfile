FROM python:3.12.7

# Cập nhật hệ thống và cài đặt các thư viện cần thiết
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libgl1-mesa-glx \
    libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /code

# Sao chép và cài đặt dependencies trước
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Chạy script chính
CMD ["python", "./gesturesensor.py"]
