# Aviso de privacidad — Sistema de Gestión de Quejas de Nómina


Última actualización:01/11/2026

## 1. Responsable del tratamiento

Hospital general de occidente / Departamento de control de asistencia, con domicilio en av. Zoquipan 1050 colonia Zoquipan, es responsable del tratamiento de los datos personales recabados mediante esta aplicación.

Contacto para temas de privacidad: rh.ssj.hgo@gmail.com

## 2. Qué datos recabamos

Al registrar una queja de nómina, la aplicación solicita:

| Categoría | Datos |
|---|---|
| Identificación | Número de tarjeta de empleado, nombre completo |
| Contacto | Teléfono / WhatsApp (10 dígitos) |
| Laborales | Turno, tipo de incidencia, quincena afectada, días de la incidencia |
| Económicos | Monto reclamado |
| Descripción | Motivo y detalle de la queja, aclaraciones posteriores |
| Documentos | Evidencias (PDF, PNG o JPG) y, opcionalmente, talón de pago |

Adicionalmente, el sistema genera: folio, código de seguimiento (solo se guarda su hash, no el código), estatus, historial de cambios, comentarios de Recursos Humanos y registros de auditoría (inicios de sesión de RH, descargas de adjuntos y eliminación de folios).

La aplicación no utiliza cookies de publicidad ni herramientas de analítica propias.

## 3. Para qué usamos los datos

- Registrar, atender y dar seguimiento a las quejas de nómina.
- Contactar al empleado (por teléfono o WhatsApp) para aclaraciones o para informar el resultado.
- Verificar la identidad de quien consulta una queja (folio + tarjeta + código de seguimiento).
- Prevenir abusos y proteger el sistema (límites de intentos y de registros por día).
- Mantener una bitácora de auditoría de las acciones del personal de RH.

No usamos los datos para fines publicitarios ni los vendemos.

## 4. Quién puede ver los datos

- **El empleado** que registró la queja, mediante su folio, tarjeta y código de seguimiento. Solo ve su propia queja y las respuestas de RH marcadas como visibles.
- **Personal de Recursos Humanos** con usuario y contraseña asignados. Las notas internas de RH nunca se muestran al empleado.
- **Administradores del sistema**, para mantenimiento y depuración.

Los usuarios de RH no se muestran a los empleados.

## 5. Con quién se comparten o dónde se almacenan

La aplicación se apoya en proveedores externos que procesan datos en nuestro nombre:

| Proveedor | Para qué | Datos |
|---|---|---|
| Google Firebase (Cloud Firestore) | Base de datos de las quejas | Datos de texto, historial, comentarios, auditoría |
| Google Drive | Almacén de evidencias | Archivos adjuntos (privados, sin enlace público) |
| Streamlit Community Cloud | Alojamiento de la aplicación | Tráfico y registros técnicos del servicio |
| WhatsApp (Meta) | Mensajes de RH al empleado | Teléfono y texto del mensaje, **solo** cuando una persona de RH decide enviarlo con el botón correspondiente |

No se transfieren datos a otros terceros salvo obligación legal o requerimiento de autoridad competente.

## 6. Cómo protegemos los datos

Medidas implementadas en el código de esta aplicación:

- Evidencias almacenadas de forma **privada** en Drive; se descargan solo desde el panel de RH autenticado.
- Contraseñas de RH almacenadas únicamente como **hash** (PBKDF2-SHA256); bloqueo temporal tras intentos fallidos y expiración de sesión por inactividad.
- Código de seguimiento de un solo uso visible al registrar; en la base solo se conserva su hash.
- Validación de datos y de archivos (formato, tamaño y contenido real) y escape del texto capturado para evitar inyección de contenido.
- Límites de intentos y de registros por día para frenar abusos.
- Base de datos accesible únicamente desde el servidor mediante cuenta de servicio con permisos mínimos; reglas de Firestore que niegan el acceso directo desde internet.
- Bitácora de auditoría de accesos y acciones sensibles de RH.
- Secretos y credenciales fuera del repositorio.

Ninguna medida elimina el riesgo por completo. Si detectas un problema de seguridad, consulta la sección 10.

## 7. Cuánto tiempo conservamos los datos

Las quejas y sus evidencias se conservan por **30 dias a partir del cierre de ticket**. Los folios eliminados desde el panel se **marcan como eliminados** y dejan de mostrarse, pero permanecen en la base de datos hasta su depuración definitiva, que se realiza **Semestralmente por el administrador del sistema**.

## 8. Tus derechos

Puedes solicitar, mediante el contacto de la sección 1:

- **Acceso:** conocer qué datos tuyos tenemos y cómo los usamos.
- **Rectificación:** corregir datos inexactos o incompletos.
- **Cancelación:** solicitar la supresión de tus datos, cuando proceda.
- **Oposición:** oponerte al uso de tus datos para fines específicos.

Para atender tu solicitud te pediremos identificarte y la responderemos en **Un maximo de 30 dias**. Algunos datos pueden conservarse por obligaciones laborales o legales.

## 9. Cambios a este aviso

Si este aviso cambia, publicaremos la nueva versión en este repositorio con su fecha de actualización. [DESCRIBE AQUÍ CÓMO SE NOTIFICARÁ A LOS EMPLEADOS, p. ej. aviso dentro de la aplicación o comunicado interno].

## 10. Seguridad del repositorio y reporte de vulnerabilidades

- **No subas** datos reales de empleados, evidencias, `secrets.toml`, llaves de cuentas de servicio, `token.json` ni archivos `.env`. El `.gitignore` incluido ya los excluye; verifica antes de cada `commit`.
- Si encuentras una vulnerabilidad, Repórtala de forma privada a **daniel.informatica.hgo** con una descripción del problema y los pasos para reproducirlo.
- Si accidentalmente se publicó una credencial, rótala de inmediato en Google Cloud y avisa al contacto anterior.
