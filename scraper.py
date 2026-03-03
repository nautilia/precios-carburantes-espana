import requests
import csv
from datetime import datetime, timedelta
import io

BASE_URL = "https://energia.serviciosmin.gob.es/shpCarburantes/"

def descargar_excel(session, producto, fecha_inicio, fecha_fin):
    # Cargar página inicial
    r = session.get(BASE_URL)

    viewstate = r.text.split('id="__VIEWSTATE" value="')[1].split('"')[0]

    payload = {
        "__VIEWSTATE": viewstate,
        "ctl00$cph_Contenido$ddlTipoTemp": "0",
        "ctl00$cph_Contenido$ddlCCAA": "99",
        "ctl00$cph_Contenido$ddlCarburante": producto,
        "ctl00$cph_Contenido$txtFechaInicial": fecha_inicio.strftime("%d/%m/%Y"),
        "ctl00$cph_Contenido$txtFechaFinal": fecha_fin.strftime("%d/%m/%Y"),
        "__EVENTTARGET": "ctl00$cph_Contenido$BtnDownload",
        "__EVENTARGUMENT": f"0|99|||||{producto}"
    }

    r2 = session.post(BASE_URL, data=payload)

    return r2.content

def parsear_excel_binario(binario):
    # El Excel realmente es CSV en muchos casos
    try:
        texto = binario.decode("utf-8")
    except:
        texto = binario.decode("latin-1")

    reader = csv.reader(io.StringIO(texto), delimiter=';')

    datos = {}

    for fila in reader:
        if len(fila) < 3:
            continue
        try:
            fecha = datetime.strptime(fila[0], "%d/%m/%Y").strftime("%Y-%m-%d")
            precio = fila[2].replace(",", ".")
            datos[fecha] = precio
        except:
            continue

    return datos

def generar_datos_4_meses():
    session = requests.Session()
    hoy = datetime.today()

    gasolina = {}
    gasoleo = {}

    for i in range(4):
        fin = hoy - timedelta(days=i*30)
        inicio = fin - timedelta(days=29)

        bin_g95 = descargar_excel(session, "G95E5", inicio, fin)
        bin_goa = descargar_excel(session, "GOA", inicio, fin)

        gasolina.update(parsear_excel_binario(bin_g95))
        gasoleo.update(parsear_excel_binario(bin_goa))

    fechas = sorted(set(gasolina.keys()) | set(gasoleo.keys()))

    filas = []
    for f in fechas:
        filas.append({
            "fecha": f,
            "gasolina_95_e5": gasolina.get(f, ""),
            "gasoleo_a": gasoleo.get(f, "")
        })

    return filas

def guardar_csv(datos):
    with open("gasolina.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fecha", "gasolina_95_e5", "gasoleo_a"]
        )
        writer.writeheader()
        writer.writerows(datos)

if __name__ == "__main__":
    datos = generar_datos_4_meses()
    guardar_csv(datos)
