# 📋 Sistema de quejas de nómina

Aplicación web hecha con [Streamlit](https://streamlit.io) para que los empleados registren quejas de nómina (descuentos, pagos no aplicados, bonos, etc.) y para que Recursos Humanos las atienda como **tickets**, con seguimiento, respuestas y control de accesos por rol.

Existen **dos versiones** del mismo sistema:

| Versión | Base de datos | Evidencias (archivos) | Pensada para |
|---|---|---|---|
| **Nube** | Firebase / Firestore | En la nube | Publicarla en internet (por ejemplo, Streamlit Community Cloud) |
| **Local** | MySQL | Carpeta del equipo | Correr dentro de la empresa, sin enviar datos a servicios externos |

Las dos comparten la misma interfaz, los mismos roles y las mismas reglas de seguridad.

---

## ✨ Funcionalidades

### Para el empleado
- **Registrar una queja** en tres pasos (datos, detalle de la queja y confirmación). Se pueden enviar varias quejas a la vez y adjuntar evidencias.
- **Comprobante en PDF** con el folio y la clave de consulta de cada queja (puede incluir un sello de «Recibido»).
- **Consultar su queja** con su número de tarjeta, el folio y la clave: ve el estatus, una línea de progreso y las respuestas de RH.
- **Responder a RH** cuando se le pide más información, adjuntando documentos.

### Para el personal de RH
- **Bandeja de tickets** con filtros por estatus y quincena, ordenada para atender primero lo más antiguo.
- **Atención del ticket:** cambiar el estatus (Pendiente, En proceso, Requiere información, Resuelto, Rechazada), responder al empleado, dejar notas internas y usar **respuestas rápidas**.
- **Aviso por WhatsApp** al empleado con el cambio de estatus.
- **Solicitudes a Control de asistencia** para pedir información de un ticket y recibir su respuesta con documentos.
- **Bandeja de notificaciones** al iniciar sesión (nuevas quejas, respuestas de empleados y de Control).
- **Archivos adjuntos** del ticket para descargar.
- **Exportación de datos** y **eliminación de folios** (solo administrador).

---

## 👥 Roles y permisos

El acceso al panel interno es por usuario y contraseña. Cada usuario tiene un rol; **un rol que no esté definido no puede entrar ni hacer nada**.

| Rol | Qué puede hacer |
|---|---|
| `RH` | Ver y atender tickets, ver teléfono, monto y talón, descargar adjuntos, usar WhatsApp y pedir información a Control |
| `Administrador` | Todo lo de RH, además de exportar datos y eliminar folios |
| `Control de asistencia` | Solo lectura y responder las solicitudes que RH le haga. No ve teléfono, monto ni talón de pago y no modifica tickets |

Los permisos se definen en `roles.py`.

---

## 🔒 Seguridad

- Contraseñas y claves de consulta guardadas con **hash PBKDF2-SHA256**; nunca en texto plano.
- **Bloqueo temporal** del inicio de sesión tras varios intentos fallidos, y límites de uso para evitar envíos masivos de quejas.
- La sesión del panel **se cierra por inactividad** (30 minutos) y tiene una duración máxima de 8 horas.
- **Validación de archivos:** solo PDF, PNG y JPG, con un máximo de 5 MB por archivo y hasta 5 evidencias por queja.
- Todo el texto escrito por los usuarios se **limpia y se escapa** antes de mostrarse.
- **Bitácora de auditoría** de acciones del panel (inicios de sesión, cambios, etc.).
- Cada rol recibe únicamente los campos que le corresponden.

Consulta también [`PRIVACY.md`](PRIVACY.md) y [`TERMS.md`](TERMS.md).

---

## 🧰 Tecnología

- Python y [Streamlit](https://streamlit.io)
- pandas y openpyxl (tablas y exportaciones)
- ReportLab (comprobantes en PDF)
- **Versión nube:** Firebase / Firestore
- **Versión local:** MySQL con [PyMySQL](https://pymysql.readthedocs.io)

---

## 🗂️ Estructura del proyecto

```
app.py            Interfaz y navegación (páginas del empleado y panel de RH)
ui.py             Estilos (CSS) y piezas de HTML
roles.py          Roles, permisos y destinatarios de notificaciones
seguridad.py      Validaciones, hashing y utilidades de seguridad
database.py       Conexión y estructura de la base de datos
utils.py          Lógica de negocio (registro de quejas, ticket, notificaciones…)
limitador.py      Límites de intentos y de uso
plantillas.py     Respuestas rápidas para RH
comprobante.py    Generación del comprobante en PDF
requirements.txt  Dependencias
```

---

## 🚀 Puesta en marcha

### Requisitos
- Python 3.10 o superior
- **Versión local:** un servidor MySQL 8 en ejecución
- **Versión nube:** un proyecto de Firebase con Firestore

### 1. Descargar e instalar dependencias

```bash
git clone https://github.com/<tu-usuario>/<tu-repositorio>.git
cd <tu-repositorio>

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar los secretos

Streamlit lee la configuración privada de `.streamlit/secrets.toml` (en Streamlit Community Cloud se pega en la sección **Secrets** de la app). **Este archivo nunca debe subirse a GitHub.**

```toml
[app]
nombre_empresa = "Nombre de tu empresa"      # aparece en el menú y en el comprobante
contacto_ayuda = "Datos de contacto para dudas"

# Usuarios del panel interno (uno por persona)
[usuarios_rh.ana]
password_hash = "pbkdf2_sha256$..."          # ver «Generar el hash de una contraseña»
rol = "RH"                                   # RH, Administrador o Control de asistencia

[usuarios_rh.carlos]
password_hash = "pbkdf2_sha256$..."
rol = "Control de asistencia"

# Solo versión local (MySQL)
[mysql]
host = "127.0.0.1"
user = "quejas_app"
password = "tu-contraseña-de-mysql"
database = "sistema_quejas"
```

**Versión nube:** además de lo anterior, agrega las credenciales de tu proyecto de Firebase en los mismos secretos, con el formato que use tu `database.py`.

**Versión local:** también puedes usar variables de entorno `DB_HOST`, `DB_USER`, `DB_PASSWORD` y `DB_NAME` en lugar de la sección `[mysql]`. Se recomienda crear un usuario de MySQL exclusivo para la app (no usar `root`). Al iniciar, la app **crea la base de datos y las tablas** que falten, por lo que ese usuario necesita permiso para crearlas.

### 3. Generar el hash de una contraseña

Desde la carpeta del proyecto:

```bash
python -c "import getpass; from seguridad import hash_secreto; print(hash_secreto(getpass.getpass('Contraseña: ')))"
```

Copia el resultado en el campo `password_hash` del usuario.

### 4. Ejecutar

```bash
streamlit run app.py
```

Se abrirá en `http://localhost:8501`.

---

## 🖼️ Personalización

| Qué | Cómo |
|---|---|
| **Logo** en el menú lateral | Guarda una imagen como `logo.png` junto a `app.py` |
| **Sello** del comprobante | Guarda una imagen como `sello_recibido.png` junto a `app.py`. El ángulo se cambia con `SELLO_ANGULO` en `app.py` |
| **Nombre de la empresa** | `nombre_empresa` en los secretos |
| **Respuestas rápidas** | `plantillas.py` |
| **Roles y permisos** | `roles.py` |

En la versión nube las imágenes deben estar en el repositorio para que la app las encuentre.

### Evidencias en la versión local

Los archivos se guardan en una carpeta del equipo, organizada por tarjeta y fecha. Por defecto es `C:\respaldos_quejas` en Windows y `respaldos_quejas` junto a la app en otros sistemas. Se puede cambiar con la variable de entorno `RUTA_RESPALDOS` o con `ruta_respaldos` en la sección `[app]` de los secretos. **Incluye esta carpeta y la base de datos en tus respaldos.**

---

## 🔄 Mantener las dos versiones

Los archivos `seguridad.py`, `roles.py`, `ui.py`, `plantillas.py` y `comprobante.py` son iguales en ambas versiones. Lo que cambia es todo lo que toca los datos: `database.py`, `limitador.py`, `utils.py` y las partes de `app.py` que leen y escriben información. Se recomienda mantener una rama por versión (por ejemplo `nube` y `local`) y copiar entre ellas los arreglos de los archivos comunes.

---

## 📄 Documentos legales

- [Aviso de privacidad](PRIVACY.md)
- [Condiciones de servicio](TERMS.md)
