from flask import Flask, jsonify, request, render_template
from redis import Redis

app = Flask(__name__)
# Conectamos a Redis (Host por defecto en VirtualBox)
r = Redis(host='localhost', port=6379, decode_responses=True)

# Listado de capítulos
CAPITULOS = {
    "1": "El mandaloriano", "2": "El niño", "3": "El pecado",
    "4": "Santuario", "5": "El pistolero", "6": "El prisionero",
    "7": "El ajuste de cuentas", "8": "Redención"
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/capitulos', methods=['GET'])
def listar_capitulos():
    lista = []
    for id_cap, nombre in CAPITULOS.items():
        estado = r.get(f"mando:{id_cap}") # [cite: 439, 477]
        if not estado:
            estado = "disponible" # [cite: 440, 478]
        lista.append({"id": id_cap, "nombre": nombre, "estado": estado})
    return jsonify(lista)

@app.route('/reservar/<id_cap>', methods=['POST'])
def reservar(id_cap):
    if r.exists(f"mando:{id_cap}"):
        return "No disponible", 400
    r.set(f"mando:{id_cap}", "reservado", ex=240) # 4 minutos de expiración [cite: 452, 479]
    return f"Capitulo {id_cap} reservado", 200

@app.route('/pagar', methods=['POST'])
def confirmar_pago():
    data = request.get_json()
    id_cap = data.get('id')
    if r.get(f"mando:{id_cap}") == "reservado":
        r.set(f"mando:{id_cap}", "alquilado", ex=86400) # 24 horas [cite: 466, 480]
        return "Pago confirmado", 200
    return "Reserva expirada", 400

if __name__ == '__main__':
    app.run(debug=True, port=5000) # [cite: 476, 485]