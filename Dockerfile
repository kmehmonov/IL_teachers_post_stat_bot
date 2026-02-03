# Python rasmiy obrazi (kichik hajmli versiyasi)
FROM python:3.11-slim

# Vaqt mintaqasini o'rnatish
ENV TZ=Asia/Tashkent

# Konteyner ichidagi ishchi papkani belgilash
WORKDIR /app

# Talablar faylini ko'chirish
COPY requirements.txt .

# Kutubxonalarni o'rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Barcha kodlarni ko'chirish
COPY . .

# Kerakli papkalarni yaratish (agar ular bo'lmasa)
RUN mkdir -p data exports storage

# Botni ishga tushirish
CMD ["python", "bot.py"]
