import requests
import re
import csv
from datetime import datetime, timedelta

BASE_URL = "https://energia.serviciosmin.gob.es/shpCarburantes/"

def obtener_viewstate(html):
    match = re.search(r'id="__VIEWSTATE" value="([^"]+)"', html)
    return match.group(1) if match else None

def obtener_bloque_js(html):
    pattern = r"arrayToDataTable\(\[(.*?)\]\);"
    match = re.search(pattern, html, re.S)
    return match.group(1) if match else None

def parsear_datos(js_block):
    filas = []
    lineas = js_block.split("\n")

    for linea in lineas:
        if linea.strip().startswith(", ['"):
            partes = re.findall(r"'([^']*)'|([\d.]+)", linea)
            valores = []
            for p in partes:
                valores.append(p[0] if p[0] else p[1])

            fecha = datetime.strptime(valores[0], "%d/%m/%Y").strftime("%Y-%m-%d")

            filas.append({
                "fecha": fecha,
                "gasoleo_a": valores[1],
                "gasolina_95_e5": valores[2]
            })

    return filas

def consultar_rango(session, fecha_inicio, fecha_fin):
    r = session.get(BASE_URL)
    viewstate = obtener_viewstate(r.text)

    payload = {
        "__VIEWSTATE": viewstate,
        "ctl00$cph_Contenido$ddlTipoTemp": "0",
        "ctl00$cph_Contenido$ddlCCAA": "99",
        "ctl00$cph_Contenido$ddlCarburante": "G95E5",
        "ctl00$cph_Contenido$txtFechaInicial": fecha_inicio.strftime("%d/%m/%Y"),
        "ctl00$cph_Contenido$txtFechaFinal": fecha_fin.strftime("%d/%m/%Y"),
    }

    r2 = session.post(BASE_URL, data=payload)
    js_block = obtener_bloque_js(r2.text)

    return parsear_datos(js_block)

def generar_datos_ultimos_4_meses():
    session = requests.Session()
    hoy = datetime.today()
    datos_totales = []

    for i in range(4):
        fin = hoy - timedelta(days=i*30)
        inicio = fin - timedelta(days=29)
        datos = consultar_rango(session, inicio, fin)
        datos_totales.extend(datos)

    # eliminar duplicados por fecha
    datos_unicos = {d["fecha"]: d for d in datos_totales}

    return sorted(datos_unicos.values(), key=lambda x: x["fecha"])

def guardar_csv(datos):
    with open("gasolina.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fecha", "gasolina_95_e5", "gasoleo_a"]
        )
        writer.writeheader()
        writer.writerows(datos)

if __name__ == "__main__":
    datos = generar_datos_ultimos_4_meses()
    guardar_csv(datos)
