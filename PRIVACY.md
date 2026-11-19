# Aviso de privacidad — Sistema de Gestión de Quejas por Descuentos en la Nómina o Bonos no Pagados.


Última actualización: 19/11/2026

## 1. Responsable del tratamiento

Hospital general de occidente / Departamento de Recursos Humanos, con domicilio en av. Zoquipan 1050 colonia Seattle 45170, es responsable del tratamiento de los datos personales recabados mediante esta aplicación.

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
| Documentos | Evidencias (PDF, PNG o JPG) y talón de pago |
| Dispositivo (solo app móvil de RH) | Token de notificaciones push (FCM) |
| Credenciales guardadas (solo si se activa «Recordar mis datos») | Correo y contraseña, cifrados en el propio teléfono (Android Keystore); nunca salen del dispositivo ni se guardan en la base de datos |

Adicionalmente, el sistema genera: folio, código de seguimiento (solo se guarda su hash, no el código), estatus, historial de cambios, comentarios de Recursos Humanos y registros de auditoría (inicios de sesión de RH, descargas de adjuntos y eliminación de folios). La app móvil guarda además la sesión de Firebase Authentication en el teléfono.

La aplicación no utiliza cookies de publicidad ni herramientas de analítica propias.

## 3. Para qué usamos los datos

- Registrar, atender y dar seguimiento a las quejas de nómina.
- Avisar al personal de RH en su celular cuando hay actividad nueva (nueva queja, solicitud o respuesta de Control, aclaración del empleado).
- Contactar al empleado (por teléfono o WhatsApp) para aclaraciones o para informar el resultado.
- Verificar la identidad de quien consulta una queja (folio + tarjeta + código de seguimiento).
- Prevenir abusos y proteger el sistema (límites de intentos y de registros por día).
- Mantener una bitácora de auditoría de las acciones del personal de RH.

No usamos los datos para fines publicitarios ni los vendemos.

## 4. Quién puede ver los datos

- **El empleado** que registró la queja, mediante su folio, tarjeta y código de seguimiento. Solo ve su propia queja y las respuestas de RH marcadas como visibles.
- **Personal de Recursos Humanos** con usuario y contraseña asignados. Las notas internas de RH nunca se muestran al empleado.
- **Administradores del sistema**, para mantenimiento y depuración.
- **La app móvil (visor Android)** es solo para personal de RH autorizado. Sin un usuario RH activo no se puede entrar, aunque la aplicación esté instalada en el teléfono.

Los usuarios de RH no se muestran a los empleados.

## 5. Con quién se comparten o dónde se almacenan

La aplicación se apoya en proveedores externos que procesan datos en nuestro nombre:

| Proveedor | Para qué | Datos |
|---|---|---|
| Google Firebase (Cloud Firestore) | Base de datos de las quejas | Datos de texto, historial, comentarios, auditoría; la app móvil de RH solo lee estos datos |
| Google Firebase Authentication | Inicio de sesión del personal de RH (visor Android) | Correo y contraseña de RH |
| Google Firebase Cloud Messaging (FCM) | Avisos push al celular del personal de RH | Token del dispositivo, folio y detalle breve del aviso (sin datos personales del empleado) |
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
- La app web (Streamlit) accede a la base de datos únicamente desde el servidor, mediante cuenta de servicio con permisos mínimos. La app móvil de RH lee los datos directamente con reglas de Firestore de solo lectura (no puede crear, modificar ni borrar quejas).
- El contenido del aviso push solo incluye el folio y un detalle breve de la actividad, sin datos personales del empleado.
- Si se activa «Recordar mis datos», el correo y la contraseña quedan cifrados en el propio teléfono; al cerrar sesión se deja de recibir avisos y los datos guardados se pueden borrar con «Olvidar mis datos guardados» o desinstalando la aplicación.
- Bitácora de auditoría de accesos y acciones sensibles de RH.
- Secretos y credenciales fuera del repositorio.

Ninguna medida elimina el riesgo por completo. Si detectas un problema de seguridad, consulta la sección 10.

## 7. Cuánto tiempo conservamos los datos

Las quejas y sus evidencias se conservan por 30 dias a partir del cierre de una queja. Los folios eliminados desde el panel se marcan como "eliminados" y dejan de mostrarse, pero permanecen en la base de datos hasta su depuración definitiva, que se realiza Semestralmente (Julio y Enero) por el administrador del sistema.

Los avisos de actividad (colección `notificaciones`) se conservan 90 días. Los datos guardados en el teléfono por la app móvil (sesión y, si se activó, credenciales recordadas) se borran al cerrar sesión, al usar «Olvidar mis datos guardados» o al desinstalar la aplicación.

## 8. Tus derechos

Puedes solicitar, mediante el contacto de la sección 1:

- **Acceso:** conocer qué datos tuyos tenemos y cómo los usamos.
- **Rectificación:** corregir datos inexactos o incompletos.
- **Cancelación:** solicitar la supresión de tus datos, cuando proceda.
- **Oposición:** oponerte al uso de tus datos para fines específicos.

Para atender tu solicitud te pediremos identificarte y la responderemos en un plazo maximo de 30 dias. Algunos datos pueden conservarse por obligaciones laborales o legales.

## 9. Cambios a este aviso

Si este aviso cambia, publicaremos la nueva versión en este repositorio con su fecha de actualización mediante una notificación dentro de la aplicación.

## 10. Seguridad del repositorio y reporte de vulnerabilidades

- Si encuentras una vulnerabilidad, Repórtala de forma privada a **daniel.informatica.hgo** con una descripción del problema y los pasos para reproducirlo.
- Si accidentalmente se publicó una credencial, rótala de inmediato en Google Cloud y avisa al contacto especificado anteriormente.
