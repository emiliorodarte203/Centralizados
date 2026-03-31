import pandas as pd
import openpyxl
import csv
import streamlit as st
import os
import plotly.graph_objects as go
from io import BytesIO

# Paso 1: Importar las librerías necesarias
st.title("Carga y proceso de centralizado BAT")

# Paso 2: Subir el archivo semanal "centralizado BAT" desde la interfaz de Streamlit
archivo_subido = st.file_uploader("Sube el archivo", type=["xlsx"])

if archivo_subido is None:
    st.info("Sube el archivo de centralizado")
    st.stop()

# Opción para elegir el tipo de pedido
tipo_pedido = st.selectbox("Selecciona el tipo de pedido:", ["stock", "complementario"])

if archivo_subido:
    try:
        # Verificar que el archivo contenga la hoja 'DETALLE PEDIDO'
        with pd.ExcelFile(archivo_subido) as xls:
            if 'DETALLE PEDIDO' in xls.sheet_names:
                dataframe_bat = pd.read_excel(xls, sheet_name='DETALLE PEDIDO')
                st.write("Archivo leído correctamente.")
            else:
                st.error("La hoja 'DETALLE PEDIDO' no existe en el archivo subido.")
                st.stop()

        # Mantener solo las columnas de interés
        columnas_interes = ['PLAZA BAT', 'N TIENDA', 'UPC', 'SKU 7 ELEVEN', 'ARTICULO 7 ELEVEN', 'CAJETILLAS X PQT', 'CAJETILLAS', 'PAQUETES', 'FECHA DE PEDIDO']
        dataframe_bat = dataframe_bat[[col for col in columnas_interes if col in dataframe_bat.columns]]

        # Asegurarse de que la columna PAQUETES sea numérica
        dataframe_bat['PAQUETES'] = pd.to_numeric(dataframe_bat['PAQUETES'], errors='coerce').fillna(0)

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

    # Definir columnas sin PAQUETES
    columnas_sin_paquetes = ['UPC', 'SKU 7 ELEVEN', 'ARTICULO 7 ELEVEN', 'CAJETILLAS X PQT', 'CAJETILLAS']

    # Paso 3: Filtrar por PLAZA BAT o N TIENDA usando un botón y mostrar todas las columnas (sin la columna PAQUETES)
    st.title("Filtrar por PLAZA BAT o N TIENDA")

    # Determinar la columna para filtrar
    columna_filtrar = 'N TIENDA' if 'N TIENDA' in dataframe_bat.columns and tipo_pedido == "stock" else 'PLAZA BAT'

    # Input de usuario para seleccionar la PLAZA BAT o N TIENDA
    if columna_filtrar in dataframe_bat.columns:
        seleccion_filtrar = st.selectbox(f'Selecciona la {columna_filtrar}:', dataframe_bat[columna_filtrar].unique())
    else:
        st.error(f"La columna '{columna_filtrar}' no existe en el archivo.")

    # Botón para aplicar el filtro
    if st.button('Filtrar'):
        dataframe_filtrado = dataframe_bat[dataframe_bat[columna_filtrar] == seleccion_filtrar][columnas_sin_paquetes]
        st.write(f"Filtrado por {columna_filtrar}: {seleccion_filtrar}")
        st.write(dataframe_filtrado)

    # Paso 4: Filtrar por cada plaza y guardar en archivos separados por fecha de pedido (sin la columna PAQUETES)
    plazas = {
        'REYNOSA': '100 110',
        'MÉXICO': '200',
        'JALISCO': '300',
        'SALTILLO': '400 410',
        'MONTERREY': '500',
        'BAJA CALIFORNIA': '600 610 620',
        'HERMOSILLO': '650',
        'PUEBLA': '700',
        'CUERNAVACA': '720',
        'YUCATAN': '800',
        'QUINTANA ROO': '890'
    }

    codigos_plaza = {
        'REYNOSA': '9271',
        'MÉXICO': '9211',
        'JALISCO': '9221',
        'SALTILLO': '9261',
        'MONTERREY': '9201',
        'BAJA CALIFORNIA': '9231',
        'HERMOSILLO': '9251',
        'PUEBLA': '9291',
        'CUERNAVACA': '9281',
        'YUCATAN': '9241',
        'QUINTANA ROO': '9289'
    }

    archivos_generados = []
    fechas_pedido = dataframe_bat['FECHA DE PEDIDO'].unique()
    for fecha in fechas_pedido:
        fecha_str = pd.to_datetime(fecha).strftime("%d%m%Y")

        for plaza, numeros_plaza in plazas.items():
            df_plaza = dataframe_bat[(dataframe_bat['PLAZA BAT'] == plaza) & (dataframe_bat['FECHA DE PEDIDO'] == fecha)][columnas_sin_paquetes]

            if not df_plaza.empty:
                if tipo_pedido == "complementario":
                    df_plaza.insert(0, 'id Tienda', dataframe_bat[(dataframe_bat['PLAZA BAT'] == plaza) & (dataframe_bat['FECHA DE PEDIDO'] == fecha)]['N TIENDA'].values)
                    if 'N TIENDA' in dataframe_bat.columns:
                        df_plaza.insert(0, 'id Tienda', dataframe_bat[(dataframe_bat['PLAZA BAT'] == plaza) & (dataframe_bat['FECHA DE PEDIDO'] == fecha)]['N TIENDA'].values)
                    else:
                        st.error("La columna 'N TIENDA' no está presente en el archivo para el tipo de pedido 'complementario'.")
                        st.stop()
                else:
                    df_plaza.insert(0, 'id Tienda', codigos_plaza[plaza])

                # Cambiar nombres de columnas
                df_plaza = df_plaza[['id Tienda'] + columnas_sin_paquetes]
                df_plaza.columns = ['id Tienda', 'Codigo de Barras', 'Id Articulo', 'Descripcion', 'Unidad Empaque', 'Cantidad (Pza)']
                nombre_archivo = f"{numeros_plaza} {fecha_str}.csv"
                archivos_generados.append((nombre_archivo, df_plaza))

    # Botón para descargar archivos
    for nombre_archivo, df in archivos_generados:
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label=f"Descargar {nombre_archivo}",
            data=buffer,
            file_name=nombre_archivo,
            mime="text/csv"
        )
    st.write("Proceso completado.")

# Paso 6: Crear tabla con la suma de paquetes para cada PLAZA BAT
st.title("Tabla de Suma de Paquetes por PLAZA BAT")

# Verificar que las columnas necesarias existan en el DataFrame y no contengan valores nulos
if 'PLAZA BAT' in dataframe_bat.columns and 'FECHA DE PEDIDO' in dataframe_bat.columns and 'PAQUETES' in dataframe_bat.columns:
    # Eliminar filas con valores nulos en las columnas de interés
    dataframe_bat = dataframe_bat.dropna(subset=['PLAZA BAT', 'FECHA DE PEDIDO', 'PAQUETES'])

    # Asegurarse de que las columnas tienen el tipo de dato correcto
    dataframe_bat['PLAZA BAT'] = dataframe_bat['PLAZA BAT'].astype(str)
    dataframe_bat['FECHA DE PEDIDO'] = pd.to_datetime(dataframe_bat['FECHA DE PEDIDO'], errors='coerce')
    dataframe_bat['PAQUETES'] = pd.to_numeric(dataframe_bat['PAQUETES'], errors='coerce')

    # Verificar que no haya valores nulos después de la conversión
    dataframe_bat = dataframe_bat.dropna(subset=['PLAZA BAT', 'FECHA DE PEDIDO', 'PAQUETES'])

    # Calcular la suma de paquetes para cada PLAZA BAT
    suma_paquetes = dataframe_bat.groupby(['PLAZA BAT', 'FECHA DE PEDIDO'])['PAQUETES'].sum().reset_index()
    suma_paquetes.columns = ['PLAZA', 'FECHA DE PEDIDO', 'PAQUETES']

    # Formatear las fechas para que no incluyan la hora
    suma_paquetes['FECHA DE PEDIDO'] = suma_paquetes['FECHA DE PEDIDO'].dt.strftime('%Y-%m-%d')
    suma_paquetes['FECHA DE ENTREGA'] = (pd.to_datetime(suma_paquetes['FECHA DE PEDIDO']) + pd.to_timedelta(1, unit='d')).dt.strftime('%Y-%m-%d')

    # Crear tabla con columnas adicionales vacías
    suma_paquetes['ID PLAZA'] = suma_paquetes['PLAZA'].map(lambda x: plazas.get(x, ''))
    suma_paquetes['FOLIOS'] = ''
    suma_paquetes['TIPO DE PEDIDO'] = tipo_pedido.capitalize()

    # Ordenar las plazas de menor a mayor y las fechas de menor a mayor dentro de cada plaza
    orden_plazas = ['REYNOSA', 'MÉXICO', 'JALISCO', 'SALTILLO', 'MONTERREY', 'BAJA CALIFORNIA', 'HERMOSILLO', 'PUEBLA', 'CUERNAVACA', 'YUCATAN', 'QUINTANA ROO']
    suma_paquetes['PLAZA'] = pd.Categorical(suma_paquetes['PLAZA'], categories=orden_plazas, ordered=True)
    suma_paquetes = suma_paquetes.sort_values(['PLAZA', 'FECHA DE PEDIDO'])

    # Reorganizar las columnas
    suma_paquetes = suma_paquetes[['PLAZA', 'ID PLAZA', 'PAQUETES', 'FOLIOS', 'FECHA DE PEDIDO']]
    st.write(suma_paquetes)

    # Opción para copiar el DataFrame
    st.title("Copiar DataFrame")
    csv = suma_paquetes.to_csv(index=False)
    st.download_button(
        label="Descargar tabla",
        data=csv,
        file_name='Tabla para correo.csv',
        mime='text/csv',
    )
else:
    st.error("Las columnas necesarias ('PLAZA BAT', 'FECHA DE PEDIDO', 'PAQUETES') no están presentes en el archivo subido.")

# Paso 7: Crear gráficos de barras comparativos de paquetes por plaza BAT y sus límites
import plotly.figure_factory as ff
import plotly.graph_objects as go

st.title("Gráfica Comparativa de Paquetes por CEDIS")

# Definir límites de paquetes por plaza
limites_paquetes = {
    'NORESTE': 22000,
    'MÉXICO': 8000,
    'PENÍNSULA': 2000,
    'HERMOSILLO': 2000,
    'JALISCO': 4000,
    'BAJA CALIFORNIA': 4000
}

# Calcular la suma de paquetes por agrupaciones específicas
paquetes_noreste = suma_paquetes[suma_paquetes['PLAZA'].isin(['REYNOSA', 'MONTERREY', 'SALTILLO'])]['PAQUETES'].sum()
paquetes_peninsula = suma_paquetes[suma_paquetes['PLAZA'].isin(['YUCATAN', 'QUINTANA ROO'])]['PAQUETES'].sum()
paquetes_mexico = suma_paquetes[suma_paquetes['PLAZA'].isin(['MÉXICO', 'PUEBLA', 'CUERNAVACA'])]['PAQUETES'].sum()

# Crear un nuevo DataFrame con las agrupaciones
data = {
    'Plaza': ['NORESTE', 'MÉXICO', 'PENÍNSULA', 'HERMOSILLO', 'JALISCO', 'BAJA CALIFORNIA'],
    'Paquetes': [
        paquetes_noreste,
        paquetes_mexico,
        paquetes_peninsula,
        suma_paquetes[suma_paquetes['PLAZA'] == 'HERMOSILLO']['PAQUETES'].sum(),
        suma_paquetes[suma_paquetes['PLAZA'] == 'JALISCO']['PAQUETES'].sum(),
        suma_paquetes[suma_paquetes['PLAZA'] == 'BAJA CALIFORNIA']['PAQUETES'].sum()
    ],
    'Límite': [22000, 8000, 2000, 2000, 4000, 4000]
}

df_comparativa = pd.DataFrame(data)

# Crear una tabla para la comparación
table_data = [['Plaza', 'Paquetes', 'Límite']] + df_comparativa.values.tolist()

# Inicializar la figura con la tabla
fig = ff.create_table(table_data, height_constant=60)

# Crear trazos para la gráfica de barras
trace1 = go.Bar(x=df_comparativa['Plaza'], y=df_comparativa['Paquetes'], xaxis='x2', yaxis='y2',
                marker=dict(color='darkorange'),
                name='Paquetes')
trace2 = go.Bar(x=df_comparativa['Plaza'], y=df_comparativa['Límite'], xaxis='x2', yaxis='y2',
                marker=dict(color='green'),
                name='Límite')

# Añadir trazos a la figura
fig.add_traces([trace1, trace2])

# Inicializar ejes x2 y y2
fig['layout']['xaxis2'] = {}
fig['layout']['yaxis2'] = {}

# Editar el diseño para subplots
fig.layout.yaxis.update({'domain': [0, .45]})
fig.layout.yaxis2.update({'domain': [.6, 1]})

# Anclar los ejes x2 y y2
fig.layout.yaxis2.update({'anchor': 'x2'})
fig.layout.xaxis2.update({'anchor': 'y2'})
fig.layout.yaxis2.update({'title': 'Cantidad de Paquetes'})

# Actualizar los márgenes para añadir título y ver las etiquetas
fig.layout.margin.update({'t':75, 'l':50})
fig.layout.update({'title': 'Comparativa de Paquetes por CEDIS'})

st.plotly_chart(fig)

