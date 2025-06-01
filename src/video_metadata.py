from pymediainfo import MediaInfo
import re

def get_gps_from_video(file_path):
    try:
        media_info = MediaInfo.parse(file_path)
        
        for track in media_info.tracks:
            if track.track_type == "General":
                raw_data = track.to_data()  # Acceder a todos los metadatos
                
                # Caso específico para iPhone
                if "comapplequicktimelocationiso6709" in raw_data:
                    coords = raw_data["comapplequicktimelocationiso6709"]
                    # Formato: "+42.3509-003.6889+861.611/"
                    match = re.match(r"^([+-]\d+\.\d+)([+-]\d+\.\d+)", coords)  # Extraemos latitud y longitud (ignorar altitud)
                    if match:
                        lat = float(match.group(1))
                        lon = float(match.group(2))
                        return {"lat": lat, "lon": lon}
                    
                # Caso para Google Pixel (campo 'xyz' comprobado con test3)
                if "xyz" in raw_data and isinstance(raw_data["xyz"], str):
                    match = re.match(r"^([+-]?\d+\.\d+)([+-]?\d+\.\d+)", raw_data["xyz"])
                    if match:
                        lat = float(match.group(1))
                        lon = float(match.group(2))
                        return {"lat": lat, "lon": lon}
                
                for key, value in raw_data.items():
                    if "location" in key.lower() and isinstance(value, str):
                        match = re.match(r"^([+-]\d+\.\d+)([+-]\d+\.\d+)", value)
                        if match:
                            return {
                                "lat": float(match.group(1)),
                                "lon": float(match.group(2))
                            }
        
        return None  

    except Exception as e:
        print(f"⚠️ Error: {str(e)}")
        return None

# Descomentar para probar la extracción de coordenadas con vídeos.
#coords = get_gps_from_video("../vids/UBU_Metadata_highres.mov")
#if coords:
    #print(f"✅ Coordenadas encontradas: Lat={coords['lat']}, Lon={coords['lon']}")
#else:
    #print("❌ No se encontraron metadatos GPS.")