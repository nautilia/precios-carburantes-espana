import requests
import re
import csv
from datetime import datetime, timedelta

BASE_URL = "https://energia.serviciosmin.gob.es/shpCarburantes/vista/shp.aspx"

def obtener_campos_ocultos(html):
    campos = {}
    for campo in ["__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"]:
        match = re.search(f'id="{campo}" value="([^"]+)"', html)
        if match:
            campos[campo] = match.group(1)
    return campos

def extraer_datos(html):
    pattern = r"arrayToDataTable\(\[(.*?)\]\);"
    match = re.search(pattern, html, re.S)
    if not match:
        return []

    bloque = match.group(1)
    filas = []

    for linea in bloque.split("\n"):
        if linea.strip().startswith(", ['"):
            partes = re.findall(r"'([^']*)'|([\d.]+)", linea)
            valores = [p[0] if p[0] else p[1] for p in partes]

            fecha = datetime.strptime(valores[0], "%d/%m/%Y").strftime("%Y-%m-%d")

            filas.append({
                "fecha": fecha,
                "precio": valores[1]
            })

    return filas

def consultar_producto(session, producto, fecha_inicio, fecha_fin):
    r = session.get(BASE_URL)
    campos = obtener_campos_ocultos(r.text)

    payload = {
        **campos,
        "ctl00$cph_Contenido$ddlTipoConsulta": "0",
        "ctl00$cph_Contenido$ddlTipoTemp": "0",
        "ctl00$cph_Contenido$ddlTipo": "0",
        "ctl00$cph_Contenido$ddlCCAA": "99",
        "ctl00$cph_Contenido$ddlCarburante": producto,
        "ctl00$cph_Contenido$txtFechaInicial": fecha_inicio.strftime("%d/%m/%Y"),
        "ctl00$cph_Contenido$txtFechaFinal": fecha_fin.strftime("%d/%m/%Y"),
        "ctl00$cph_Contenido$BtnAniadir": "Aceptar",
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": ""
    }

    r2 = session.post(BASE_URL, data=payload)

    return extraer_datos(r2.text)

def generar_datos_4_meses():
    session = requests.Session()
    hoy = datetime.today() - timedelta(days=1)

    gasolina = {}
    gasoleo = {}

    for i in range(4):
        fin = hoy - timedelta(days=i*30)
        inicio = fin - timedelta(days=29)

        datos_g95 = consultar_producto(session, "G95E5", inicio, fin)
        datos_goa = consultar_producto(session, "GOA", inicio, fin)

        for d in datos_g95:
            gasolina[d["fecha"]] = d["precio"]

        for d in datos_goa:
            gasoleo[d["fecha"]] = d["precio"]

    fechas = sorted(set(gasolina.keys()) | set(gasoleo.keys()))

    filas = []
    for f in fechas:
        filas.append({
            "fecha": f,
            "Gasolina 95 E5": gasolina.get(f, ""),
            "Gasóleo A": gasoleo.get(f, "")
        })

    return filas

def guardar_csv(datos):
    with open("gasolina.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fecha", "Gasolina 95 E5", "Gasóleo A"]
        )
        writer.writeheader()
        writer.writerows(datos)


if __name__ == "__main__":
    datos = generar_datos_4_meses()

    # ===== VALIDACIONES =====

    if len(datos) < 80:
        raise Exception(f"ERROR: Muy pocos datos ({len(datos)} filas).")

    ultima_fecha = max(d["fecha"] for d in datos)
    ayer = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    if ultima_fecha < ayer:
        raise Exception(f"ERROR: Última fecha incorrecta ({ultima_fecha})")

    vacios_g95 = sum(1 for d in datos if d["gasolina_95_e5"] == "")
    vacios_goa = sum(1 for d in datos if d["gasoleo_a"] == "")

    if vacios_g95 > 5 or vacios_goa > 5:
        raise Exception("ERROR: Demasiados valores vacíos en las series.")

    print("Validación correcta. Generando CSV...")

    guardar_csv(datos)

    print("CSV generado correctamente.")
