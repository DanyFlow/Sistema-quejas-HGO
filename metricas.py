"""Cálculo de métricas del panel de RH.

Solo usa pandas (sin Streamlit ni base de datos), así que se puede probar por separado.
Trabaja sobre la lista de quejas que el panel ya carga (dicts), por lo que no hace
lecturas adicionales a la base de datos.

Campos que usa de cada queja:
    folio, tipo_nombre, estatus, quincena_afectada, fecha_creacion,
    fecha_resolucion (opcional), monto_reclamado (opcional; solo si el rol lo puede ver)
"""
import datetime

import pandas as pd

ESTADOS_ORDEN = ["Pendiente", "En proceso", "Requiere información", "Resuelto", "Rechazada"]
ABIERTOS = ("Pendiente", "En proceso", "Requiere información")
FINALES = ("Resuelto", "Rechazada")

# Mismos colores que los botones de estatus del panel
COLOR_ESTATUS = {
    "Pendiente": "#f59e0b",
    "En proceso": "#3b82f6",
    "Requiere información": "#f97316",
    "Resuelto": "#22c55e",
    "Rechazada": "#ef4444",
}

COLUMNAS = ["folio", "tipo", "estatus", "quincena", "creada", "resuelta", "monto"]


def _utc_naive(valor):
    """Fecha (con o sin zona) -> Timestamp UTC sin zona; NaT si no es una fecha."""
    if valor is None or not hasattr(valor, "astimezone"):
        return pd.NaT
    if valor.tzinfo is not None:
        valor = valor.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return pd.Timestamp(valor)


def _monto(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float("nan")


def construir_df(quejas, ahora=None):
    """Lista de quejas -> DataFrame con columnas calculadas (días abierta / días de resolución)."""
    if ahora is None:
        ahora = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    ahora = pd.Timestamp(ahora)

    filas = []
    for q in quejas:
        filas.append({
            "folio": str(q.get("folio", "") or ""),
            "tipo": str(q.get("tipo_nombre", "") or "Sin tipo"),
            "estatus": str(q.get("estatus", "") or "Sin estatus"),
            "quincena": str(q.get("quincena_afectada", "") or ""),
            "creada": _utc_naive(q.get("fecha_creacion")),
            "resuelta": _utc_naive(q.get("fecha_resolucion")),
            "monto": _monto(q.get("monto_reclamado")),
        })
    df = pd.DataFrame(filas, columns=COLUMNAS)
    df["creada"] = pd.to_datetime(df["creada"])
    df["resuelta"] = pd.to_datetime(df["resuelta"])

    df["abierta"] = df["estatus"].isin(ABIERTOS)
    df["cerrada"] = df["estatus"].isin(FINALES)

    dias_abierta = (ahora - df["creada"]).dt.total_seconds() / 86400
    df["dias_abierta"] = dias_abierta.where(df["abierta"]).clip(lower=0)

    dias_res = (df["resuelta"] - df["creada"]).dt.total_seconds() / 86400
    df["dias_resolucion"] = dias_res.where(df["cerrada"]).clip(lower=0)
    return df


def filtrar(df, quincena=None, tipo=None):
    """Aplica los filtros del panel (None = sin filtro)."""
    if quincena:
        df = df[df["quincena"] == quincena]
    if tipo:
        df = df[df["tipo"] == tipo]
    return df


def resumen(df, umbral_dias=7):
    """Números clave. Los que no se pueden calcular valen None."""
    total = int(len(df))
    abiertas = int(df["abierta"].sum())
    resueltas = int((df["estatus"] == "Resuelto").sum())
    rechazadas = int((df["estatus"] == "Rechazada").sum())

    dias_res = df["dias_resolucion"].dropna()
    dias_ab = df["dias_abierta"].dropna()
    hay_monto = bool(df["monto"].notna().any())

    return {
        "total": total,
        "abiertas": abiertas,
        "resueltas": resueltas,
        "rechazadas": rechazadas,
        "pct_resueltas": (resueltas / total * 100) if total else None,
        "pct_rechazadas": (rechazadas / total * 100) if total else None,
        "res_promedio": float(dias_res.mean()) if len(dias_res) else None,
        "res_mediana": float(dias_res.median()) if len(dias_res) else None,
        "res_n": int(len(dias_res)),
        "abiertas_antiguedad": float(dias_ab.mean()) if len(dias_ab) else None,
        "abiertas_vencidas": int((dias_ab > umbral_dias).sum()),
        "monto_abiertas": float(df.loc[df["abierta"], "monto"].fillna(0).sum()) if hay_monto else None,
    }


def por_estatus(df):
    """Quejas por estatus, con los cinco estatus siempre presentes (aunque tengan 0)."""
    cuenta = df["estatus"].value_counts()
    orden = ESTADOS_ORDEN + [e for e in cuenta.index if e not in ESTADOS_ORDEN]
    return pd.DataFrame({"Estatus": orden, "Quejas": [int(cuenta.get(e, 0)) for e in orden]})


def por_tipo(df):
    """Quejas por tipo, de mayor a menor."""
    cuenta = df["tipo"].value_counts()
    return pd.DataFrame({"Tipo": cuenta.index.astype(str), "Quejas": cuenta.values.astype(int)})


def por_quincena(df):
    """Quejas por quincena afectada, en orden cronológico (el formato AAAA-MMQ1/Q2 ordena como texto)."""
    d = df[df["quincena"] != ""]
    cuenta = d["quincena"].value_counts().sort_index()
    return pd.DataFrame({"Quincena": cuenta.index.astype(str), "Quejas": cuenta.values.astype(int)})


def por_semana(df, tz=None):
    """Quejas registradas por semana (lunes a domingo, en hora local), incluyendo semanas con 0."""
    creada = df["creada"].dropna()
    if creada.empty:
        return pd.DataFrame({"Semana": pd.to_datetime([]), "Quejas": []})
    local = creada.dt.tz_localize("UTC")
    if tz is not None:
        try:
            local = local.dt.tz_convert(tz)
        except Exception:
            pass
    local = local.dt.tz_localize(None)
    inicio = local.dt.normalize() - pd.to_timedelta(local.dt.dayofweek, unit="D")
    cuenta = inicio.value_counts().sort_index()
    semanas = pd.date_range(cuenta.index.min(), cuenta.index.max(), freq="7D")
    cuenta = cuenta.reindex(semanas, fill_value=0)
    return pd.DataFrame({"Semana": semanas, "Quejas": cuenta.values.astype(int)})


def mas_antiguas(df, n=10):
    """Las quejas abiertas que llevan más tiempo sin resolverse."""
    d = df[df["abierta"]].sort_values("dias_abierta", ascending=False).head(n)
    return pd.DataFrame({
        "Folio": d["folio"].values,
        "Tipo": d["tipo"].values,
        "Estatus": d["estatus"].values,
        "Días abierta": d["dias_abierta"].fillna(0).astype(int).values,
        "Quincena": d["quincena"].values,
    })


# ---------------------------------------------------------------------------
# Periodos: trimestres de calendario y años
# ---------------------------------------------------------------------------
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _trimestre_de(fecha):
    return fecha.year, (fecha.month - 1) // 3 + 1


def _trimestre_anterior(anio, q):
    return (anio, q - 1) if q > 1 else (anio - 1, 4)


def _nombre_trimestre(anio, q):
    return f"{MESES[3 * (q - 1)]}–{MESES[3 * (q - 1) + 2]} {anio}"


def _limites(inicio_local, fin_local, tz):
    """Fechas locales (sin zona) -> (desde, hasta) en UTC con zona; 'hasta' no se incluye."""
    utc = datetime.timezone.utc
    return (inicio_local.replace(tzinfo=tz).astimezone(utc),
            fin_local.replace(tzinfo=tz).astimezone(utc))


def _limites_trimestre(anio, q, tz):
    inicio = datetime.datetime(anio, 3 * (q - 1) + 1, 1)
    fin = datetime.datetime(anio + 1, 1, 1) if q == 4 else datetime.datetime(anio, 3 * q + 1, 1)
    return _limites(inicio, fin, tz)


def opciones_periodo(ahora_local, tz, n_trimestres=8):
    """Periodos para el selector de métricas, el primero es el trimestre actual.

    ahora_local: datetime con zona (la hora local de hoy). Cada periodo es un dict:
      menu       texto del selector
      nombre     nombre del periodo (ej. 'Octubre–Diciembre 2026')
      desde/hasta límites en UTC con zona; 'hasta' no se incluye
      incompleto True si el periodo todavía no termina
      previo     {'nombre', 'desde', 'hasta'} del trimestre anterior (None si es un año)
    """
    ahora_utc = ahora_local.astimezone(datetime.timezone.utc)
    periodos = []
    anio, q = _trimestre_de(ahora_local)
    for i in range(n_trimestres):
        desde, hasta = _limites_trimestre(anio, q, tz)
        pa, pq = _trimestre_anterior(anio, q)
        p_desde, p_hasta = _limites_trimestre(pa, pq, tz)
        nombre = _nombre_trimestre(anio, q)
        periodos.append({
            "menu": nombre + (" (actual)" if i == 0 else ""),
            "nombre": nombre, "desde": desde, "hasta": hasta, "incompleto": hasta > ahora_utc,
            "previo": {"nombre": _nombre_trimestre(pa, pq), "desde": p_desde, "hasta": p_hasta},
        })
        anio, q = pa, pq
    for a in (ahora_local.year, ahora_local.year - 1):
        desde, hasta = _limites(datetime.datetime(a, 1, 1), datetime.datetime(a + 1, 1, 1), tz)
        periodos.append({
            "menu": f"Año {a}" + (" (en curso)" if a == ahora_local.year else ""),
            "nombre": f"Año {a}", "desde": desde, "hasta": hasta, "incompleto": hasta > ahora_utc,
            "previo": None,
        })
    return periodos
