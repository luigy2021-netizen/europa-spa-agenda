import base64
import os
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
SPREADSHEET_ID = "1erDwwIzWkQzkEpL8RgqvXQ0dqgowSNg1PYZmlf8Yj24"
TZ = ZoneInfo("America/Ciudad_Juarez")

SERVICIOS = {
    "Relajante": 30,
    "Europa Experience": 60,
}
LIMPIEZA_MINUTOS = 10
HORA_APERTURA = time(10, 0)
HORA_CIERRE = time(22, 0)
INTERVALO_INICIOS = 10

TERAPEUTAS = {
    "Isabella": {
        "imagen": "isabella.png",
        "titulo": "La elegante",
        "descripcion": "Siempre impecable, refinada y de trato sereno.",
    },
    "Valeria": {
        "imagen": "valeria.png",
        "titulo": "La carismática",
        "descripcion": "Alegre y cercana; hace sentir cómodo a cada cliente.",
    },
    "Camila": {
        "imagen": "camila.png",
        "titulo": "La experta",
        "descripcion": "Segura, clara y profesional; transmite confianza.",
    },
    "Sofía": {
        "imagen": "sofia.png",
        "titulo": "La relajante",
        "descripcion": "Tranquila, de voz suave y una presencia que transmite paz.",
    },
    "Victoria": {
        "imagen": "victoria.png",
        "titulo": "La sofisticada",
        "descripcion": "Atención exclusiva y cuidada, con estilo concierge.",
    },
}

COLUMNAS_CITAS = [
    "Folio",
    "Fecha",
    "Hora",
    "Servicio",
    "Duracion",
    "Terapeuta",
    "Nombre",
    "WhatsApp",
    "Estado",
    "CreadaEn",
    "CanceladaEn",
]
COLUMNAS_BLOQUEOS = [
    "ID",
    "Terapeuta",
    "FechaInicio",
    "FechaFin",
    "HoraInicio",
    "HoraFin",
    "Motivo",
    "Activo",
    "CreadoEn",
]


def imagen_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def aplicar_estilos():
    logo = imagen_base64(ASSETS_DIR / "logo-europa.png")
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: #050505;
            background-image: linear-gradient(rgba(0,0,0,.40), rgba(0,0,0,.58)),
                              url("data:image/png;base64,{logo}");
            background-position: center center;
            background-size: contain;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .block-container {{
            max-width: 1180px;
            background: rgba(5, 5, 5, .82);
            border: 1px solid rgba(203, 158, 66, .42);
            border-radius: 20px;
            padding: 2rem 2rem 3rem;
            margin-top: 1rem;
            margin-bottom: 2rem;
            backdrop-filter: blur(8px);
        }}
        h1, h2, h3 {{ color: #d8ad57 !important; }}
        p, label, .stMarkdown, [data-testid="stWidgetLabel"] {{ color: #f4ead8; }}
        [data-testid="stTabs"] button {{ color: #e7c87f; }}
        [data-testid="stImage"] img {{ border-radius: 14px; border: 1px solid #9f7730; }}
        .stButton > button[kind="primary"] {{
            background: #198754;
            border-color: #35b978;
            color: white;
            font-weight: 700;
        }}
        .stButton > button:disabled {{ opacity: .48; }}
        .perfil-seleccionado {{
            padding: .7rem 1rem;
            border: 1px solid #c9a24f;
            border-radius: 10px;
            background: rgba(201,162,79,.12);
            color: #f5ddb0;
            margin: .5rem 0 1rem;
        }}
        .nota-avatar {{ color: #b9aa8c; font-size: .78rem; text-align: center; }}
        @media (max-width: 700px) {{
            .block-container {{ padding: 1rem; margin-top: .35rem; border-radius: 12px; }}
            .stApp {{ background-size: contain; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def obtener_config(nombre, predeterminado=""):
    try:
        return st.secrets.get(nombre, predeterminado)
    except (FileNotFoundError, KeyError):
        return predeterminado


@st.cache_resource
def conectar_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        info = dict(st.secrets["gcp_service_account"])
        credenciales = Credentials.from_service_account_info(info, scopes=scopes)
        cliente = gspread.authorize(credenciales)
    except (FileNotFoundError, KeyError):
        archivos = list(BASE_DIR.glob("europa-spa-agenda-*.json"))
        if not archivos:
            raise RuntimeError("No se encontró la credencial de Google Sheets.")
        credenciales = Credentials.from_service_account_file(
            str(archivos[0]), scopes=scopes
        )
        cliente = gspread.authorize(credenciales)

    libro = cliente.open_by_key(SPREADSHEET_ID)
    return libro.worksheet("Citas"), libro.worksheet("Bloqueos")


def leer_filas(hoja, columnas):
    valores = hoja.get_all_values()
    if not valores:
        raise ValueError(f"La pestaña {hoja.title} no tiene encabezados.")
    if valores[0][: len(columnas)] != columnas:
        raise ValueError(
            f"Los encabezados de {hoja.title} no coinciden con los requeridos."
        )

    filas = []
    for numero, valores_fila in enumerate(valores[1:], start=2):
        completa = valores_fila + [""] * (len(columnas) - len(valores_fila))
        registro = dict(zip(columnas, completa[: len(columnas)]))
        registro["_fila"] = numero
        filas.append(registro)
    return filas


def fecha_pascua(anio):
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def motivo_cierre(fecha):
    if fecha.weekday() == 6:
        return "Los domingos permanecemos cerrados."
    if (fecha.month, fecha.day) == (1, 1):
        return "Cerrado por Año Nuevo."
    if (fecha.month, fecha.day) == (12, 25):
        return "Cerrado por Navidad."
    if fecha == fecha_pascua(fecha.year) - timedelta(days=2):
        return "Cerrado por Viernes Santo."
    return ""


def convertir_hora(fecha, hora_texto):
    hora = datetime.strptime(hora_texto, "%H:%M").time()
    return datetime.combine(fecha, hora, tzinfo=TZ)


def se_empalman(inicio_a, fin_a, inicio_b, fin_b):
    return inicio_a < fin_b and inicio_b < fin_a


def terapeuta_bloqueada(terapeuta, fecha, bloqueos):
    for bloqueo in bloqueos:
        if bloqueo["Terapeuta"] != terapeuta:
            continue
        if bloqueo["Activo"].strip().upper() not in {"SI", "SÍ", "TRUE", "1"}:
            continue
        try:
            inicio = datetime.strptime(bloqueo["FechaInicio"], "%Y-%m-%d").date()
            fin = datetime.strptime(bloqueo["FechaFin"], "%Y-%m-%d").date()
        except ValueError:
            continue
        if inicio <= fecha <= fin:
            return True
    return False


def horarios_disponibles(fecha, terapeuta, duracion, citas, bloqueos):
    if motivo_cierre(fecha) or terapeuta_bloqueada(terapeuta, fecha, bloqueos):
        return []

    ocupadas = []
    for cita in citas:
        if cita["Terapeuta"] != terapeuta or cita["Fecha"] != fecha.isoformat():
            continue
        if cita["Estado"].strip().lower() != "confirmada":
            continue
        try:
            inicio = convertir_hora(fecha, cita["Hora"])
            minutos = int(cita["Duracion"])
        except (ValueError, TypeError):
            continue
        fin_bloqueado = inicio + timedelta(minutes=minutos + LIMPIEZA_MINUTOS)
        ocupadas.append((inicio, fin_bloqueado))

    apertura = datetime.combine(fecha, HORA_APERTURA, tzinfo=TZ)
    cierre = datetime.combine(fecha, HORA_CIERRE, tzinfo=TZ)
    actual = apertura
    resultado = []

    while actual + timedelta(minutes=duracion) <= cierre:
        fin_bloqueado = actual + timedelta(
            minutes=duracion + LIMPIEZA_MINUTOS
        )
        if not any(
            se_empalman(actual, fin_bloqueado, inicio, fin)
            for inicio, fin in ocupadas
        ):
            resultado.append(actual.strftime("%H:%M"))
        actual += timedelta(minutes=INTERVALO_INICIOS)
    return resultado


def hora_visible(hora_24):
    return datetime.strptime(hora_24, "%H:%M").strftime("%I:%M %p").lstrip("0")


def guardar_cita(hoja_citas, hoja_bloqueos, datos):
    citas = leer_filas(hoja_citas, COLUMNAS_CITAS)
    bloqueos = leer_filas(hoja_bloqueos, COLUMNAS_BLOQUEOS)
    disponibles = horarios_disponibles(
        datos["fecha"],
        datos["terapeuta"],
        datos["duracion"],
        citas,
        bloqueos,
    )
    if datos["hora"] not in disponibles:
        return ""

    folio = f"EUR-{uuid.uuid4().hex[:8].upper()}"
    hoja_citas.append_row(
        [
            folio,
            datos["fecha"].isoformat(),
            datos["hora"],
            datos["servicio"],
            datos["duracion"],
            datos["terapeuta"],
            datos["nombre"].strip(),
            datos["whatsapp"],
            "Confirmada",
            datetime.now(TZ).isoformat(timespec="seconds"),
            "",
        ],
        value_input_option="RAW",
    )
    return folio


def mostrar_catalogo():
    st.subheader("Elige tu terapeuta")
    columnas = st.columns(5)
    for columna, (nombre, perfil) in zip(columnas, TERAPEUTAS.items()):
        with columna:
            st.image(ASSETS_DIR / perfil["imagen"], width="stretch")
            st.markdown(f"**{nombre}**  \n{perfil['titulo']}")
            st.caption(perfil["descripcion"])
            if st.button(f"Elegir {nombre}", key=f"elegir_{nombre}", width="stretch"):
                st.session_state["terapeuta"] = nombre
    st.markdown(
        '<div class="nota-avatar">Avatares digitales. Imágenes representativas.</div>',
        unsafe_allow_html=True,
    )


def pagina_reservar(hoja_citas, hoja_bloqueos):
    mostrar_catalogo()
    terapeuta = st.session_state.get("terapeuta", "")
    if not terapeuta:
        st.info("Selecciona una terapeuta para continuar.")
        return

    st.markdown(
        f'<div class="perfil-seleccionado">Seleccionaste a <b>{terapeuta}</b>.</div>',
        unsafe_allow_html=True,
    )

    servicio = st.selectbox("Servicio", list(SERVICIOS))
    duracion = SERVICIOS[servicio]
    hoy = datetime.now(TZ).date()
    fecha = st.date_input(
        "Fecha",
        min_value=hoy,
        max_value=hoy + timedelta(days=30),
        format="DD/MM/YYYY",
    )

    cierre = motivo_cierre(fecha)
    if cierre:
        st.warning(cierre)
        return

    try:
        citas = leer_filas(hoja_citas, COLUMNAS_CITAS)
        bloqueos = leer_filas(hoja_bloqueos, COLUMNAS_BLOQUEOS)
        horarios = horarios_disponibles(
            fecha, terapeuta, duracion, citas, bloqueos
        )
    except Exception as error:
        st.error(f"No fue posible consultar la agenda: {error}")
        return

    if terapeuta_bloqueada(terapeuta, fecha, bloqueos):
        st.info(f"{terapeuta} no está disponible en esta fecha.")
        return
    if not horarios:
        st.info("No hay horarios disponibles para esta fecha.")
        return

    etiquetas = {hora_visible(h): h for h in horarios}
    hora_etiqueta = st.selectbox("Horario disponible", list(etiquetas))
    hora = etiquetas[hora_etiqueta]
    nombre = st.text_input("Nombre")
    whatsapp = st.text_input("WhatsApp (10 dígitos)", max_chars=10)
    whatsapp_valido = whatsapp.isdigit() and len(whatsapp) == 10
    datos_validos = bool(nombre.strip()) and whatsapp_valido

    if whatsapp and not whatsapp_valido:
        st.caption("El WhatsApp debe contener exactamente 10 números.")

    confirmar = st.button(
        "Confirmar cita",
        type="primary",
        disabled=not datos_validos,
        width="stretch",
    )
    if confirmar:
        datos = {
            "fecha": fecha,
            "hora": hora,
            "servicio": servicio,
            "duracion": duracion,
            "terapeuta": terapeuta,
            "nombre": nombre,
            "whatsapp": whatsapp,
        }
        try:
            folio = guardar_cita(hoja_citas, hoja_bloqueos, datos)
        except Exception as error:
            st.error(f"No se pudo guardar la cita: {error}")
            return
        if not folio:
            st.error("Ese horario acaba de ocuparse. Selecciona otro horario.")
            return
        st.success(
            f"Cita confirmada con {terapeuta} el {fecha.strftime('%d/%m/%Y')} "
            f"a las {hora_visible(hora)}. Tu folio es {folio}."
        )
        st.info("Guarda tu folio; lo necesitarás si deseas cancelar.")


def pagina_cancelar(hoja_citas):
    st.subheader("Cancelar una cita")
    st.write("Puedes cancelar hasta una hora antes del servicio.")
    folio = st.text_input("Folio", key="folio_cancelar").strip().upper()
    whatsapp = st.text_input(
        "WhatsApp de la reserva", max_chars=10, key="whatsapp_cancelar"
    )
    valido = bool(folio) and whatsapp.isdigit() and len(whatsapp) == 10

    if st.button("Buscar y cancelar", disabled=not valido, width="stretch"):
        try:
            citas = leer_filas(hoja_citas, COLUMNAS_CITAS)
            cita = next(
                (
                    fila
                    for fila in citas
                    if fila["Folio"].strip().upper() == folio
                    and fila["WhatsApp"].strip() == whatsapp
                ),
                None,
            )
            if not cita:
                st.error("No encontramos una cita con esos datos.")
                return
            if cita["Estado"].strip().lower() == "cancelada":
                st.info("Esta cita ya fue cancelada.")
                return
            fecha_cita = datetime.strptime(cita["Fecha"], "%Y-%m-%d").date()
            inicio = convertir_hora(fecha_cita, cita["Hora"])
            if datetime.now(TZ) > inicio - timedelta(hours=1):
                st.error("El plazo de cancelación terminó una hora antes del servicio.")
                return
            fila = cita["_fila"]
            hoja_citas.update(
                range_name=f"I{fila}:K{fila}",
                values=[
                    [
                        "Cancelada",
                        cita["CreadaEn"],
                        datetime.now(TZ).isoformat(timespec="seconds"),
                    ]
                ],
            )
            st.success("Tu cita fue cancelada correctamente.")
        except Exception as error:
            st.error(f"No fue posible cancelar la cita: {error}")


def pagina_administracion(hoja_bloqueos):
    st.subheader("Administración")
    clave_configurada = obtener_config("admin_password") or os.getenv(
        "EUROPA_ADMIN_PASSWORD", ""
    )
    if not clave_configurada:
        st.warning("Falta configurar la contraseña del dueño.")
        return

    if not st.session_state.get("admin_autorizado"):
        clave = st.text_input("Contraseña del dueño", type="password")
        if st.button("Entrar"):
            if clave == clave_configurada:
                st.session_state["admin_autorizado"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        return

    st.write("Bloquea una terapeuta por ausencia, descanso o vacaciones.")
    terapeuta = st.selectbox("Terapeuta", list(TERAPEUTAS), key="admin_terapeuta")
    inicio = st.date_input("Primer día", key="admin_inicio", format="DD/MM/YYYY")
    fin = st.date_input(
        "Último día", min_value=inicio, key="admin_fin", format="DD/MM/YYYY"
    )
    motivo = st.text_input("Motivo", placeholder="Vacaciones, ausencia, descanso...")
    if st.button("Bloquear fechas", type="primary", disabled=not motivo.strip()):
        hoja_bloqueos.append_row(
            [
                f"BLQ-{uuid.uuid4().hex[:8].upper()}",
                terapeuta,
                inicio.isoformat(),
                fin.isoformat(),
                "",
                "",
                motivo.strip(),
                "SI",
                datetime.now(TZ).isoformat(timespec="seconds"),
            ],
            value_input_option="RAW",
        )
        st.success(f"{terapeuta} quedó bloqueada en las fechas seleccionadas.")

    st.divider()
    st.markdown("#### Bloqueos activos")
    try:
        bloqueos = leer_filas(hoja_bloqueos, COLUMNAS_BLOQUEOS)
        activos = [
            b
            for b in bloqueos
            if b["Activo"].strip().upper() in {"SI", "SÍ", "TRUE", "1"}
        ]
        if not activos:
            st.caption("No hay bloqueos activos.")
        for bloqueo in activos:
            col_texto, col_boton = st.columns([4, 1])
            col_texto.write(
                f"**{bloqueo['Terapeuta']}** · {bloqueo['FechaInicio']} a "
                f"{bloqueo['FechaFin']} · {bloqueo['Motivo']}"
            )
            if col_boton.button("Quitar", key=f"quitar_{bloqueo['ID']}"):
                hoja_bloqueos.update_cell(bloqueo["_fila"], 8, "NO")
                st.rerun()
    except Exception as error:
        st.error(f"No fue posible consultar los bloqueos: {error}")

    if st.button("Cerrar sesión"):
        st.session_state["admin_autorizado"] = False
        st.rerun()


def main():
    st.set_page_config(
        page_title="Europa Spa Agenda",
        page_icon=str(ASSETS_DIR / "logo-europa.png"),
        layout="wide",
    )
    aplicar_estilos()
    st.title("Europa Spa")
    st.caption("Agenda digital · Ciudad Juárez, Chihuahua")

    try:
        hoja_citas, hoja_bloqueos = conectar_sheets()
    except Exception as error:
        st.error(f"No fue posible conectar con la agenda: {error}")
        st.stop()

    reservar, cancelar, administrar = st.tabs(
        ["Reservar", "Cancelar", "Administración"]
    )
    with reservar:
        pagina_reservar(hoja_citas, hoja_bloqueos)
    with cancelar:
        pagina_cancelar(hoja_citas)
    with administrar:
        pagina_administracion(hoja_bloqueos)


if __name__ == "__main__":
    main()
