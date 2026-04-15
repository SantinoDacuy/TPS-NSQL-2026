import os
from flask import Flask, jsonify, request
from redis import Redis
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Conexión usando variables de entorno (mejor práctica que hardcodear)
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
r = Redis(host=redis_host, port=redis_port, decode_responses=True)

GRUPOS_VALIDOS = ['cervecerias', 'universidades', 'farmacias', 'emergencias', 'supermercados']

# ── 2) Agregar un punto de interés ──────────────────────────────────────────
@app.route('/lugares/agregar', methods=['POST'])
def agregar_lugar():
    data = request.json

    if not data or not all(k in data for k in ('grupo', 'nombre', 'lat', 'lng')):
        return jsonify({"error": "Faltan campos requeridos: grupo, nombre, lat, lng"}), 400

    if data['grupo'] not in GRUPOS_VALIDOS:
        return jsonify({"error": f"Grupo inválido. Opciones: {GRUPOS_VALIDOS}"}), 400

    try:
        r.geoadd(data['grupo'], (float(data['lng']), float(data['lat']), data['nombre']))
        return jsonify({"mensaje": f"'{data['nombre']}' agregado al grupo '{data['grupo']}'"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 3) Lugares cercanos (radio 5 km) ────────────────────────────────────────
@app.route('/lugares/cercanos', methods=['GET'])
def lugares_cercanos():
    grupo = request.args.get('grupo')
    lat   = request.args.get('lat')
    lng   = request.args.get('lng')

    if not grupo or not lat or not lng:
        return jsonify({"error": "Parámetros requeridos: grupo, lat, lng"}), 400

    try:
        # geosearch reemplaza al deprecado georadius en Redis 6.2+
        resultados = r.geosearch(
            grupo,
            longitude=float(lng),
            latitude=float(lat),
            radius=5,
            unit='km',
            withdist=True,
            sort='ASC'           # ordenados de más cercano a más lejano
        )
        lista = [{"nombre": item[0], "distancia_km": round(float(item[1]), 3)} for item in resultados]
        return jsonify({"grupo": grupo, "total": len(lista), "lugares": lista})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 4) Distancia exacta entre usuario y un lugar ────────────────────────────
@app.route('/lugares/distancia', methods=['GET'])
def distancia_a_lugar():
    grupo  = request.args.get('grupo')
    nombre = request.args.get('nombre')
    lat    = request.args.get('lat')
    lng    = request.args.get('lng')

    if not all([grupo, nombre, lat, lng]):
        return jsonify({"error": "Parámetros requeridos: grupo, nombre, lat, lng"}), 400

    clave_temp = f"_usuario_temp_{nombre}"   # clave única para evitar colisiones

    try:
        r.geoadd(grupo, (float(lng), float(lat), clave_temp))
        distancia = r.geodist(grupo, nombre, clave_temp, unit='km')
        return jsonify({
            "lugar": nombre,
            "distancia_km": round(float(distancia), 3) if distancia else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        r.zrem(grupo, clave_temp)   # siempre limpiamos, incluso si hay error


# ── EXTRA) Listar todos los miembros de un grupo ────────────────────────────
@app.route('/lugares/todos', methods=['GET'])
def listar_todos():
    grupo = request.args.get('grupo')
    if not grupo:
        return jsonify({"error": "Parámetro requerido: grupo"}), 400

    try:
        miembros = r.zrange(grupo, 0, -1)
        return jsonify({"grupo": grupo, "lugares": miembros, "total": len(miembros)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)