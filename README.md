# Europa Spa Agenda

Agenda digital independiente para Europa Spa. Utiliza Streamlit y Google Sheets.

## Ejecutar localmente

Desde PowerShell:

```powershell
cd "C:\Users\Luis\OneDrive\Desktop\webinar\app demo\europa_spa_agenda"
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:EUROPA_ADMIN_PASSWORD="elige-una-clave-segura"
streamlit run app.py
```

El archivo JSON de Google debe permanecer en esta carpeta solo para desarrollo
local. `.gitignore` impide que se suba accidentalmente a Git.

## Datos

- `Citas`: reservas y cancelaciones.
- `Bloqueos`: ausencias y vacaciones registradas por el dueño.
- La hoja está vinculada por su identificador, no por el nombre del archivo.
- La limpieza de 10 minutos se calcula internamente y no se muestra al cliente.

## Streamlit Community Cloud

Al desplegar, copia los datos del JSON en los Secrets usando como guía
`.streamlit/secrets.toml.example`. Configura también `admin_password`. Nunca subas
el JSON ni un archivo real `secrets.toml` al repositorio.
