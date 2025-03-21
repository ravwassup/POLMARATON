import os
import boto3
from dotenv import load_dotenv

# 🔐 Wczytaj dane z .env
load_dotenv()

# 🌍 Dane konfiguracyjne
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION")  # np. "fra1"
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET")  # np. "polmaraton-space"

# 🚨 Sprawdź brakujące zmienne
missing = []
if not DO_SPACES_KEY: missing.append("DO_SPACES_KEY")
if not DO_SPACES_SECRET: missing.append("DO_SPACES_SECRET")
if not DO_SPACES_REGION: missing.append("DO_SPACES_REGION")
if not DO_SPACES_BUCKET: missing.append("DO_SPACES_BUCKET")

if missing:
    raise ValueError(f"❌ Brakuje zmiennych środowiskowych: {', '.join(missing)}. Uzupełnij je w pliku .env!")

# 🌐 Endpoint
DO_SPACES_ENDPOINT = f"https://{DO_SPACES_REGION}.digitaloceanspaces.com"

# 🔧 Konfiguracja klienta
session = boto3.session.Session()
client = session.client(
    's3',
    region_name=DO_SPACES_REGION,
    endpoint_url=DO_SPACES_ENDPOINT,
    aws_access_key_id=DO_SPACES_KEY,
    aws_secret_access_key=DO_SPACES_SECRET,
)

# 📁 Katalog do wrzucenia
upload_dir = "./polmaraton-clean"

# 🔄 Przesyłanie plików
for root, dirs, files in os.walk(upload_dir):
    for file in files:
        file_path = os.path.join(root, file)
        key = os.path.relpath(file_path, upload_dir)

        print(f"⬆️ Uploading: {file_path} -> {key}")

        client.upload_file(
            Filename=file_path,
            Bucket=DO_SPACES_BUCKET,
            Key=key,
            ExtraArgs={'ACL': 'private'}
        )

print("✅ Wszystko wysłane do DigitalOcean Spaces!")