import os
import boto3
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()

DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION")  # np. "fra1"
DO_SPACES_ENDPOINT = f"https://{DO_SPACES_REGION}.digitaloceanspaces.com"
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET")  # np. "zadanie9"

# Inicjalizacja klienta
session = boto3.session.Session()
client = session.client(
    's3',
    region_name=DO_SPACES_REGION,
    endpoint_url=DO_SPACES_ENDPOINT,
    aws_access_key_id=DO_SPACES_KEY,
    aws_secret_access_key=DO_SPACES_SECRET,
)

# Próba pobrania listy obiektów z bucketu
try:
    response = client.list_objects_v2(Bucket=DO_SPACES_BUCKET)

    print(f"\n📦 Pliki w buckecie: `{DO_SPACES_BUCKET}`\n")

    if 'Contents' in response:
        for obj in response['Contents']:
            print(f"🔹 {obj['Key']} ({obj['Size']} bajtów)")
    else:
        print("⚠️ Bucket istnieje, ale jest pusty.")
except Exception as e:
    print("❌ Błąd połączenia z DigitalOcean Spaces:")
    print(e)