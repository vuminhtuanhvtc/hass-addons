FROM python:3.12.7

WORKDIR /code

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn
COPY . .

# Đảm bảo thư mục lưu config tồn tại
RUN mkdir -p /data

CMD ["python", "./gesturesensor.py"]
