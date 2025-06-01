import sounddevice as sd 
import numpy as np
import whisper 
import datetime
import os
import soundfile as sf
import tkinter as tk
from tkinter import ttk
import threading
import re
import csv
import ffmpeg
import time

# Configuración
DURACION_SEGUNDOS = 15
FREQ_MUESTREO = 16000
THRESHOLD = 0.02  # Sensibilidad al ruido de fondo
IDIOMA_DEFAULT = 'es' 
STREAM_URL = "http://10.44.85.250:8000/stream.mp3"
## sasa

#.\venv\Scripts\Activate.ps1
#.\venv\Scripts\activate.bat

# Cargar modelo de Whisper
modelo = whisper.load_model("medium")

os.makedirs("grabaciones", exist_ok=True)

grabando = False

# Detectar si hay voz (energía del audio)

def leer_stream_durante_n_segundos(url, segundos, freq=16000):
    proceso = (
        ffmpeg
        .input(url)
        .output('pipe:', format='f32le', acodec='pcm_f32le', ac=1, ar=freq)
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )

    bytes_necesarios = segundos * freq * 4  # 4 bytes por float32
    raw_audio = proceso.stdout.read(bytes_necesarios)
    audio_np = np.frombuffer(raw_audio, np.float32)
    return audio_np


def detectar_voz(audio_chunk, min_duracion=0.3, freq=FREQ_MUESTREO):
    rms = np.sqrt(np.mean(np.square(audio_chunk)))
    if rms < THRESHOLD:
        return False
    energia_fina = np.abs(audio_chunk) > 0.02
    duracion_activa = np.sum(energia_fina) / freq
    return duracion_activa >= min_duracion

def grabar_audio():
    print("🎙️ Grabando...")
    audio = sd.rec(int(DURACION_SEGUNDOS * FREQ_MUESTREO), samplerate=FREQ_MUESTREO, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

def guardar_transcripcion(texto):
    with open("transcripcion.txt", "a", encoding="utf-8") as f: 
        f.write(f"[{datetime.datetime.now()}] {texto}\n")

        
def extraer_matricula(texto):
    match = re.search(r'\b([A-Z]{2,3}-?[A-Z]{2,3})\b', texto)
    if match:
        return match.group(1)
    
    alfabeto_aviacion = {
        "alfa": "A", "bravo": "B", "charlie": "C", "delta": "D", "echo": "E", "foxtrot": "F",
        "golf": "G", "hotel": "H", "india": "I", "juliet": "J", "kilo": "K", "lima": "L",
        "mike": "M", "november": "N", "oscar": "O", "papa": "P", "quebec": "Q", "romeo": "R",
        "sierra": "S", "tango": "T", "uniform": "U", "victor": "V", "whiskey": "W", "x-ray": "X",
        "yankee": "Y", "zulu": "Z"
    }

    palabras = texto.lower().split()
    letras = [alfabeto_aviacion.get(palabra) for palabra in palabras if palabra in alfabeto_aviacion]

    if len(letras) > 3:
        return ''.join(letras[:4]).upper()

    return None

def guardar_evento(texto, accion, matricula):
    archivo = "eventos_detectados.csv"
    existe = os.path.exists(archivo)
    with open(archivo, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["FechaHora", "Accion", "Matricula", "Texto"])
        writer.writerow([datetime.datetime.now(), accion, matricula or "N/A", texto])


def detectar_y_grabar_loop():
    contador = 0
    while grabando:
        try:
            audio_array = leer_stream_durante_n_segundos(STREAM_URL, DURACION_SEGUNDOS)
            if detectar_voz(audio_array):
                nombre_archivo = f"grabaciones/audio_{contador:04d}.wav"
                sf.write(nombre_archivo, audio_array, FREQ_MUESTREO)
                print(f"🎙️ Grabado: {nombre_archivo}")
                contador += 1
        except Exception as e:
            print(f"[ERROR GRABAR]: {str(e)}")
        time.sleep(1)  


def transcribir_loop():
    ya_procesados = set()
    while grabando:
        try:
            archivos = sorted(os.listdir("grabaciones"))
            for archivo in archivos:
                if archivo.endswith(".wav") and archivo not in ya_procesados:
                    ruta = os.path.join("grabaciones", archivo)
                    result = modelo.transcribe(ruta, language=None)
                    ##idioma_detectado = result.get("language", "desconocido")
                    texto = result["text"].strip()

                    ##print(f"📄 {archivo} | Idioma: {idioma_detectado} | Texto: {texto}")
                    guardar_transcripcion(texto)
                    texto_box.insert(tk.END, texto + "\n")
                    texto_box.see(tk.END)

                    matricula = extraer_matricula(texto)
                    guardar_evento(texto, "Transcripción", matricula)

                    ya_procesados.add(archivo)
                    os.remove(ruta)
        except Exception as e:
            print(f"[ERROR TRANSCRIPCIÓN]: {str(e)}")
        time.sleep(1)
 
'''''
def grabar_transcribir_loop():
    global grabando
    while grabando: 
        try:
            # Leer stream
            audio_array = leer_stream_durante_n_segundos(STREAM_URL, DURACION_SEGUNDOS)


            if detectar_voz(audio_array):

                # Guardar a archivo temporal
                temp_audio_file = "temp.wav"
                sf.write(temp_audio_file, audio_array, FREQ_MUESTREO)
                  # Transcribir
                result = modelo.transcribe(temp_audio_file, language='es')
                idioma_detectado = result.get("language", "desconocido")
                print(f"Idioma detectado: {idioma_detectado}")
                texto = result["text"].strip()

            # Mostrar
                guardar_transcripcion(texto)
                texto_box.insert(tk.END, texto + "\n")
                texto_box.see(tk.END)

            # Extraer matrícula y guardar evento
                matricula = extraer_matricula(texto)
                guardar_evento(texto, " ", matricula)

        except Exception as e:
            texto_box.insert(tk.END, f"[ERROR]: {str(e)}\n")

        finally:
            if os.path.exists("temp.wav"):
                os.remove("temp.wav")
'''

def iniciar_detener():
    global grabando
    if not grabando:
        grabando = True
        boton_inicio.config(text='Detener')
        os.makedirs("grabaciones", exist_ok=True)
        threading.Thread(target=detectar_y_grabar_loop, daemon=True).start()
        threading.Thread(target=transcribir_loop, daemon=True).start()
    else:
        grabando = False
        boton_inicio.config(text='Iniciar')

#Interfaz

ventana = tk.Tk()
ventana.title('Transcriptor de Audio en Vivo')
ventana.geometry("600x400")

idioma_var = tk.StringVar(value=IDIOMA_DEFAULT)
idiomas_disponibles = ["es", "en", "fr", "de", "it", "pt", "ja"]

idioma_label = tk.Label(ventana, text='Idioma: ')
idioma_label.pack(pady=5)

#idioma_selector = ttk.Combobox(ventana, textvariable=idioma_var, values=idiomas_disponibles)
#idioma_selector.pack(pady=5)

boton_inicio = tk.Button(ventana, text='Iniciar', command=iniciar_detener, bg="green", fg="white", font=("Arial", 12))
boton_inicio.pack(pady=10)

texto_box = tk.Text(ventana, height=15, wrap= tk.WORD)
texto_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

ventana.mainloop()

#Transformar Matricula

