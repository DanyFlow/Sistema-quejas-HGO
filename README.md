# 📋 Sistema de quejas de nómina

Aplicación web hecha con [Streamlit](https://streamlit.io) para que los empleados registren quejas de nómina (descuentos, bonos, aguinaldo, pagos no aplicados, etc.) y para que Recursos Humanos las atienda como **tickets**, con seguimiento, respuestas y control de accesos por rol.

Los datos se guardan en **Firebase (Firestore)** y la app está pensada para publicarse en la nube, por ejemplo en [Streamlit Community Cloud](https://streamlit.io/cloud).

---

## ✨ Funcionalidades

### Para el empleado
- **Registrar una queja** en tres pasos (datos, detalle de la queja y confirmación). Se pueden enviar varias quejas a la vez (hasta 5) y adjuntar evidencias.
- **Comprobante en PDF** con el folio y la clave de consulta de cada queja, con la opción de incluir un sello de «Recibido».
- **Consultar su queja** con su número de tarjeta, el folio y la clave: ve el estatus, una línea de progreso y las respuestas de RH.
- **Responder a RH** cuando se le pide más información, adjuntando documentos.

### Para el personal de RH
- **Bandeja de tickets** con filtros por estatus y quincena, ordenada para atender primero lo más antiguo.
- **Atención del ticket:** cambiar el estatus (Pendiente, En proceso, Requiere información, Resuelto o Rechazada), responder al empleado, dejar notas internas y usar **respuestas rápidas**.
- **Aviso por WhatsApp** al empleado con el cambio de estatus.
- **Solicitudes a Control de asistencia** para pedir información de un ticket y recibir su respuesta.
- **Bandeja de notificaciones** al iniciar sesión (nuevas quejas, respuestas de empleados y de Control).
- **Archivos adjuntos** del ticket para descargar.
- **Exportación de datos** (CSV dentro de un ZIP) y **eliminación de folios**, solo para administradores.

---

## 🧾 Tipos de queja

El empleado elige uno de estos tipos al registrar su queja:

| # | Tipo |
|---|---|
| 1 | Descuento por omisión |
| 2 | Permiso no aplicado |
| 3 | Descuento por responsabilidades (Exceso de Incapacidad) |
| 4 | Bono de reyes |
| 5 | Bono del dia de las madres |
| 6 | Aguinaldo |
| 7 | Prima dominical |
| 8 | Estimulo Trimmestral |
| 9 | Estimulos anuales |
| 10 | Medidas de fin de año |
| 11 | Otro tipo de incidencia |
| 12 | Bono del Servidor Publico |
| 13 | Descuento no Reconocido (Aclaracion) |
| 14 | Tarjeta de Estimulo Mensual |

- En **«Descuento por omisión»** y **«Permiso no aplicado»** se pide además elegir los días de la incidencia (hasta 5).
- En todos los tipos el monto reclamado es obligatorio.
- No se permite registrar dos quejas abiertas con la misma tarjeta, el mismo tipo y la misma quincena.

### Administrar los tipos

Los tipos viven en la colección **`tipos_queja`** de Firestore. Cada documento tiene tres campos:

| Campo | Valor |
|---|---|
| `nombre` | Texto que ve el empleado |
| `requiere_monto` | `true` |
| `activo` | `true` para mostrarlo, `false` para ocultarlo |

- **Agregar un tipo:** crea un documento nuevo con esos tres campos.
- **Quitar un tipo:** pon `activo` en `false`. Los tickets que ya existen no se afectan.
- **Cambiar un nombre:** edita `nombre`. Los tickets anteriores conservan el nombre con el que se registraron.
- Los cambios pueden tardar hasta 5 minutos en verse, porque el catálogo se guarda en caché.
- La lista que aparece en `database.py` solo se usa para llenar la colección **cuando está vacía**; si ya existe, editarla no cambia nada.
- Si cambias el nombre de «Descuento por omisión» o «Permiso no aplicado», actualiza también `TIPOS_CON_DIAS` en `utils.py`, porque ahí se identifican por nombre.

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
- **Validación de archivos:** solo PDF, PNG y JPG, con un máximo de 5 MB por archivo.
- Todo el texto escrito por los usuarios se **limpia y se escapa** antes de mostrarse.
- **Bitácora de auditoría** de acciones del panel (inicios de sesión, cambios, etc.).
- Cada rol recibe únicamente los campos que le corresponden.

Consulta también [`PRIVACY.md`](PRIVACY.md) y [`TERMS.md`](TERMS.md).

---

## 🧰 Tecnología

- Python y [Streamlit](https://streamlit.io)
- Firebase Admin SDK (Firestore)
- pandas (tablas y exportaciones)
- ReportLab (comprobantes en PDF)

---

## 🗂️ Estructura del proyecto

```
app.py            Interfaz y navegación (páginas del empleado y panel de RH)
ui.py             Estilos (CSS) y piezas de HTML
roles.py          Roles, permisos y destinatarios de notificaciones
seguridad.py      Validaciones, hashing y utilidades de seguridad
database.py       Conexión a Firestore y catálogo de tipos de queja
utils.py          Lógica de negocio (registro de quejas, tickets, notificaciones…)
limitador.py      Límites de intentos y de uso
plantillas.py     Respuestas rápidas para RH
comprobante.py    Generación del comprobante en PDF
requirements.txt  Dependencias
```

---

## 🚀 Puesta en marcha

### 1. Preparar Firebase

1. Crea un proyecto en [Firebase](https://console.firebase.google.com) y activa **Firestore**.
2. En la configuración del proyecto, genera una **clave privada de cuenta de servicio** (se descarga un archivo JSON). Lo usarás en el paso de secretos.

### 2. Configurar los secretos

La configuración privada vive en los **Secrets** de Streamlit. En local es el archivo `.streamlit/secrets.toml`; en Streamlit Community Cloud se pega en *Settings → Secrets* de la app. **Este contenido nunca debe subirse a GitHub.**

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

# Cuenta de servicio de Firebase: los campos del JSON descargado
[firebase]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
# ...el resto de los campos del JSON
```

Si tu despliegue guarda las evidencias en Google Drive, agrega también ahí las credenciales que use tu `utils.py`.

### 3. Generar el hash de una contraseña

Desde la carpeta del proyecto, con Python instalado:

```bash
python -c "import getpass; from seguridad import hash_secreto; print(hash_secreto(getpass.getpass('Contraseña: ')))"
```

Copia el resultado en el campo `password_hash` del usuario.

### 4. Publicar en Streamlit Community Cloud

1. Sube el proyecto a un repositorio de GitHub (sin secretos).
2. En [Streamlit Community Cloud](https://streamlit.io/cloud) crea una app nueva, elige tu repositorio y marca `app.py` como archivo principal.
3. En *Advanced settings → Secrets* pega el contenido del paso 2.
4. Publica. Cada vez que subas cambios al repositorio, la app se actualiza sola.

En el plan gratuito la app puede «dormirse» tras un tiempo sin visitas y tardar unos segundos en despertar.

### Probarla en tu computadora (opcional)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (en Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

Necesitas el archivo `.streamlit/secrets.toml` con el contenido del paso 2. La app se abre en `http://localhost:8501`.

---

## 🖼️ Personalización

| Qué | Cómo |
|---|---|
| **Logo** en el menú lateral | Guarda una imagen como `logo.png` en la raíz del repositorio |
| **Sello** del comprobante | Guarda una imagen como `sello_recibido.png` en la raíz del repositorio. La inclinación se cambia con `SELLO_ANGULO` en `app.py` |
| **Nombre de la empresa** | `nombre_empresa` en los secretos |
| **Respuestas rápidas** | `plantillas.py` |
| **Roles y permisos** | `roles.py` |
| **Tipos de queja** | Colección `tipos_queja` en Firestore (ver arriba) |

Las imágenes deben estar en el repositorio para que la app las encuentre.

---

## 📄 Documentos legales

- [Aviso de privacidad](PRIVACY.md)
- [Condiciones de servicio](TERMS.md)
