import streamlit as st
import pandas as pd
import joblib
import os
import json
import numpy as np
import boto3
from dotenv import load_dotenv

# Langfuse
from langfuse import Langfuse
from langfuse.decorators import observe
from langfuse.openai import OpenAI as LangfuseOpenAI

# 📌 Wczytaj zmienne środowiskowe
load_dotenv()

# 📌 Konfiguracja Langfuse
langfuse_client = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

llm_client = LangfuseOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 📌 Konfiguracja DigitalOcean Spaces
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION")
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET")

# Tworzymy klienta S3 do Spaces
s3_client = boto3.client(
    "s3",
    region_name=DO_SPACES_REGION,
    endpoint_url=f"https://{DO_SPACES_REGION}.digitaloceanspaces.com",
    aws_access_key_id=DO_SPACES_KEY,
    aws_secret_access_key=DO_SPACES_SECRET,
)

# 📁 Wczytujemy zapisane modele ML
@st.cache_resource
def load_models():
    return {
        "10km": joblib.load("model_10km.pkl"),
        "15km": joblib.load("model_15km.pkl"),
        "20km": joblib.load("model_20km.pkl"),
        "final_time": joblib.load("model_final_time.pkl"),
    }

models = load_models()

# 🎨 Interfejs Streamlit
st.title("⏳ Szacowanie czasu ukończenia półmaratonu")
st.markdown("Wprowadź swoje dane, a model przewidzi, w jakim czasie ukończysz półmaraton i jakie miejsce zajmiesz!")

# 📌 Formularz do wprowadzania danych
plec = st.selectbox("Płeć:", ["Mężczyzna", "Kobieta"])
wiek = st.number_input("Podaj swój wiek:", min_value=15, max_value=100, value=None, step=1)
tempo_5km = st.number_input("Tempo na 5 km (min/km):", min_value=2.0, max_value=10.0, value=None, step=0.1)

# 📌 Sprawdzenie, czy użytkownik podał wszystkie dane
missing_fields = []
if not plec:
    missing_fields.append("Płeć")
if not wiek:
    missing_fields.append("Wiek")
if not tempo_5km:
    missing_fields.append("Tempo na 5 km")

# 🚨 Jeśli brakuje danych – pokaż komunikat i zakończ
if missing_fields:
    st.warning(f"❌ Brakujące pola: {', '.join(missing_fields)}. Uzupełnij dane i spróbuj ponownie.")
    st.stop()

# 📌 Formatowanie czasu
def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# 📌 Funkcja uzupełniania brakującego tempa na 5 km
@observe()
def predict_missing_tempo(plec, wiek):
    prompt = f"""
    Użytkownik nie podał tempa na 5 km. Na podstawie jego wieku i płci oszacuj jego tempo.

    - Płeć: {"Mężczyzna" if plec == 1 else "Kobieta"}
    - Wiek: {wiek}

    Podaj wynik w formacie JSON:
    {{
        "Tempo_5km": wartość (np. 5.2)
    }}
    """
    try:
        response = llm_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result["Tempo_5km"]
    except Exception as e:
        st.warning(f"⚠️ Błąd LLM: {e}")
        return 5.5

# 📌 Funkcja wysyłania pliku do Spaces
def upload_to_spaces(file_path, object_name):
    """Wysyła plik do DigitalOcean Spaces."""
    try:
        s3_client.upload_file(file_path, DO_SPACES_BUCKET, object_name)
        url = f"https://{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com/{object_name}"
        return url
    except Exception as e:
        print(f"⚠️ Błąd przesyłania na Spaces: {e}")
        return None

# 🚀 Predykcja
if st.button("🔮 Oblicz przewidywany czas"):

    plec_bin = 1 if plec == "Mężczyzna" else 0  

    if tempo_5km is None:
        tempo_5km = predict_missing_tempo(plec_bin, wiek)
        st.info(f"🔄 OpenAI oszacował tempo: {tempo_5km:.1f} min/km")

    input_data = pd.DataFrame({
        "Płeć": [plec_bin],
        "Rocznik": [2024 - wiek],
        "5_km_Tempo": [tempo_5km],
    })

    # 🔮 Predykcja modeli
    input_data["10_km_Czas"] = models["10km"].predict(input_data) * np.random.uniform(0.96, 1.04)
    input_data["15_km_Czas"] = models["15km"].predict(input_data) * np.random.uniform(0.96, 1.04)
    input_data["20_km_Czas"] = models["20km"].predict(input_data) * np.random.uniform(0.96, 1.04)
    przewidywany_czas = int(models["final_time"].predict(input_data)[0] * np.random.uniform(0.96, 1.04))

    # ✅ Zmiana kodu płci 0/1 -> tekst
    input_data["Płeć"] = input_data["Płeć"].map({1: "Mężczyzna", 0: "Kobieta"})

    # 🖼️ Wyświetlanie
    st.write("🔍 Dane wejściowe dla modelu:", input_data[["Płeć", "Rocznik", "5_km_Tempo"]])

    wynik_df = input_data[["10_km_Czas", "15_km_Czas", "20_km_Czas"]].copy()
    wynik_df = wynik_df.applymap(lambda x: format_time(x) if not pd.isnull(x) else "Brak danych")

    st.write("🔍 Przewidziane czasy na odcinkach:", wynik_df)
    st.write("🔍 Przewidywany końcowy czas:", format_time(przewidywany_czas))

    st.success(f"🏁 Przewidywany czas ukończenia półmaratonu: **{format_time(przewidywany_czas)}**")

    # 🏆 Miejsce
    liczba_uczestnikow = 5000
    czas_najlepszy = 3899  
    czas_najgorszy = 12754  

    miejsce = int(((przewidywany_czas - czas_najlepszy) / (czas_najgorszy - czas_najlepszy)) * liczba_uczestnikow)
    miejsce = max(1, min(miejsce, liczba_uczestnikow))

    st.info(f"🏆 Szacowane miejsce: **{miejsce}/{liczba_uczestnikow}**")

    # 📤 Wysyłanie wyników na Spaces
    input_data.to_csv("wyniki.csv", index=False)
    upload_url = upload_to_spaces("wyniki.csv", "wyniki_polmaraton.csv")
    if upload_url:
        st.success(f"📤 Wyniki zostały zapisane w Spaces: [Pobierz wyniki]({upload_url})")