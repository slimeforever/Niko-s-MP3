import os
import shutil
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import yt_dlp
import re

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/' # ¡IMPORTANTE! Cambia esto a tu clave generada

DOWNLOAD_FOLDER = os.path.join(app.root_path, 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

search_results_cache = {}

YOUTUBE_URL_REGEX = r"(?:https?:\/\/)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|v\/|)([\w-]{11})(?:\S+)?"

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    message_type = None
    message_icon = None
    videos = []
    last_query = ""

    if request.method == 'GET':
        search_results_cache.clear()
        return render_template('index.html', message=message, message_type=message_type, message_icon=message_icon, videos=[], last_query="")

    if request.method == 'POST':
        debug_action = request.form.get('debug_action')
        if debug_action:
            if debug_action == 'simulate_search_failure':
                message = "Niko no pudo encontrar el video. Intenta con otra búsqueda."
                message_type = "error-niko"
                message_icon = "nikosad.png"
            elif debug_action == 'simulate_success_message':
                message = "¡Operación completada con éxito! Todo salió de maravilla."
                message_type = "success"
                message_icon = "niko.png"
            elif debug_action == 'simulate_error_message':
                message = "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo más tarde."
                message_type = "error"
                message_icon = "nikosad.png"
            elif debug_action == 'simulate_warning_message':
                message = "Advertencia: El campo de búsqueda estaba vacío. Por favor, introduce algo."
                message_type = "warning"
                message_icon = "nikoconfuso.png"
            elif debug_action == 'reset_default':
                message = None
                message_type = None
                message_icon = None
                videos = []
                last_query = ""
            
            return render_template('index.html', message=message, message_type=message_type, message_icon=message_icon, videos=[], last_query=last_query)

        if 'search_query' in request.form:
            last_query = request.form['search_query'].strip()
            if last_query:
                try:
                    is_url = re.match(YOUTUBE_URL_REGEX, last_query)
                    
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'noplaylist': True,
                        'quiet': True,
                        'extract_flat': 'True',
                        'default_search': 'ytsearch5:' if not is_url else None,
                        'max_downloads': 5,
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        search_term = last_query
                        if is_url:
                            video_id_from_url = is_url.group(1)
                            search_term = f"https://www.youtube.com/watch?v={video_id_from_url}"
                        
                        info = ydl.extract_info(search_term, download=False)
                        
                        entries_to_process = []
                        if is_url and info and 'entries' not in info:
                            entries_to_process = [info]
                        elif 'entries' in info and info['entries']:
                            entries_to_process = info['entries']
                        
                        if entries_to_process:
                            videos = []
                            search_results_cache.clear()
                            for entry in entries_to_process:
                                if entry and 'title' in entry and 'id' in entry:
                                    thumbnail_url = entry.get('thumbnail')
                                    if not thumbnail_url:
                                        thumbnail_url = url_for('static', filename='images/default_thumbnail.png')
                                    
                                    videos.append({
                                        'id': entry['id'],
                                        'title': entry['title'],
                                        'thumbnail': thumbnail_url,
                                        # ✨ CORRECCIÓN CLAVE: Almacenar la URL canónica de YouTube ✨
                                        'url': f"https://www.youtube.com/watch?v={entry['id']}" 
                                    })
                                    # ✨ CORRECCIÓN CLAVE: Almacenar la URL canónica en el caché también ✨
                                    search_results_cache[entry['id']] = f"https://www.youtube.com/watch?v={entry['id']}"
                            
                            if not videos:
                                message = "Niko no pudo encontrar el video. Intenta con otra búsqueda."
                                message_type = "error-niko"
                                message_icon = "nikosad.png"
                        else:
                            message = "Niko no pudo encontrar el video. Intenta con otra búsqueda."
                            message_type = "error-niko"
                            message_icon = "nikosad.png"

                except yt_dlp.utils.DownloadError as e:
                    error_message = str(e)
                    if "no video" in error_message.lower() or "did not find any relevant" in error_message.lower():
                        message = "Niko no pudo encontrar el video. Intenta con otra búsqueda."
                        message_type = "error-niko"
                        message_icon = "nikosad.png"
                    elif "HTTP Error 400" in error_message or "url inválida" in error_message.lower():
                        message = "Error al buscar el video: Por favor, introduce una URL de YouTube válida."
                        message_type = "error"
                        message_icon = "nikosad.png"
                    else:
                        message = f"Ocurrió un error inesperado durante la búsqueda: {error_message}"
                        message_type = "error"
                        message_icon = "nikosad.png"
                except Exception as e:
                    message = f"Ocurrió un error inesperado: {e}"
                    message_type = "error"
                    message_icon = "nikosad.png"
            else:
                message = "Por favor, introduce un término de búsqueda o URL."
                message_type = "warning"
                message_icon = "nikoconfuso.png"
        
        elif 'download_id' in request.form:
            video_id = request.form['download_id']
            url_to_download = search_results_cache.get(video_id)

            if not url_to_download:
                message = "URL del video no encontrada para la descarga. Por favor, realiza una nueva búsqueda."
                message_type = "error"
                message_icon = "nikosad.png"
                return render_template('index.html', message=message, message_type=message_type, message_icon=message_icon, videos=[], last_query="")

            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    # Usar el ID del video para el nombre del archivo en el servidor.
                    # Esto asegura un nombre único y evita problemas si el título es genérico o tiene caracteres especiales.
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'), 
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url_to_download, download=True)
                    
                    # El nombre del archivo en el servidor ahora se basa en el ID del video.
                    server_file_name = f"{info['id']}.mp3"
                    mp3_path_expected = os.path.join(DOWNLOAD_FOLDER, server_file_name)
                    
                    if os.path.exists(mp3_path_expected):
                        song_title = info.get('title', 'Unknown Song')
                        
                        # Construir el nombre del archivo para la descarga en el navegador.
                        final_file_name_for_browser = f"{song_title} From Niko's MP3.mp3"
                        
                        response = send_from_directory(
                            DOWNLOAD_FOLDER,
                            server_file_name, # Enviamos el archivo con su nombre real en el servidor (ID.mp3)
                            as_attachment=True,
                            mimetype='audio/mpeg',
                            download_name=final_file_name_for_browser # El nombre que el navegador usará para guardar
                        )
                        
                        @response.call_on_close
                        def cleanup_file():
                            try:
                                os.remove(mp3_path_expected)
                                print(f"Archivo '{mp3_path_expected}' eliminado después de la descarga.")
                            except Exception as e:
                                print(f"Error al intentar eliminar el archivo '{mp3_path_expected}': {e}")
                        
                        return response

                    else:
                        message = "La descarga del MP3 no se completó correctamente."
                        message_type = "error"
                        message_icon = "nikosad.png"
                        return render_template('index.html', message=message, message_type=message_type, message_icon=message_icon, videos=[], last_query="")

            except yt_dlp.utils.DownloadError as e:
                error_message = str(e)
                message = f"Falló la descarga del MP3: {error_message}. Inténtalo de nuevo."
                message_type = "error"
                message_icon = "nikosad.png"
                return render_template('index.html', message=message, message_type=message_type, message_icon=message_icon, videos=[], last_query="")
            except Exception as e:
                message = f"Ocurrió un error al intentar descargar: {e}"
                message_type = "error"
                message_icon = "nikosad.png"
                return render_template('index.html', message=message, message_type=message_type, message_icon=message_icon, videos=[], last_query="")

    return render_template('index.html', message=message, message_type=message_type, message_icon=message_icon, videos=videos, last_query=last_query)

if __name__ == '__main__':
    print(f"Servidor web de descarga de MP3 iniciado. Abre tu navegador y ve a http://127.0.0.1:5000/")
    app.run(debug=True)
