#!/usr/bin/python

from Bio import Entrez
import xml.etree.ElementTree as ET
import argparse
import os
import re

# --- ¡IMPORTANTE! ---
# El NCBI requiere que proporciones tu dirección de correo electrónico
# para un uso responsable de sus servicios E-utilities.
# ¡Cambia "tu.email@example.com" por tu dirección de correo real!
Entrez.email = "tu.email@example.com" 

def get_linaje_para_familia(nombre_familia):
    """
    Consulta la base de datos de taxonomía del NCBI para un nombre de familia dado
    y extrae su filo, clase, orden (o superorden, o subclase si no hay orden/superorden)
    y el propio nombre de la familia.
    Devuelve un diccionario con {rango: nombre} si se encuentra, o None si no.
    """
    try:
        handle = Entrez.esearch(db="taxonomy", term=nombre_familia, retmode="xml")
        record = Entrez.read(handle)
        handle.close()

        if not record["IdList"]:
            return None

        id_taxon = record["IdList"][0]

        handle = Entrez.efetch(db="taxonomy", id=id_taxon, retmode="xml")
        
        for registro_taxon in Entrez.parse(handle):
            info_linaje = {}
            if "LineageEx" in registro_taxon:
                for item_linaje in registro_taxon["LineageEx"]:
                    rango = item_linaje.get("Rank")
                    nombre_cientifico = item_linaje.get("ScientificName")
                    if rango and nombre_cientifico:
                        info_linaje[rango] = nombre_cientifico
            
            orden_a_mostrar = "N/A"

            if info_linaje.get("order"):
                orden_a_mostrar = info_linaje["order"]
            elif info_linaje.get("superorder"):
                orden_a_mostrar = f"{info_linaje['superorder']} (Superorden)"
            elif info_linaje.get("subclass"):
                orden_a_mostrar = f"{info_linaje['subclass']} (Subclase)"
            
            diccionario_resultado = {
                "filo": info_linaje.get("phylum", "N/A"),
                "clase": info_linaje.get("class", "N/A"),
                "orden": orden_a_mostrar,
                "familia": registro_taxon.get("ScientificName", nombre_familia)
            }
            
            handle.close()
            return diccionario_resultado
        
        handle.close() 
        return None

    except Exception as e:
        print(f"Error inesperado al procesar la familia '{nombre_familia}': {e}")
        return None

def generar_html_wordpress(resultados_ordenados, nombre_archivo="taxonomia_wordpress.html", link_base_url=None):
    """
    Genera un archivo HTML con los resultados en formato de tabla compatible con WordPress,
    fusionando celdas repetidas para Filo, Clase, Orden y Familia usando rowspan.
    Opcionalmente, genera enlaces para los nombres de las familias si se proporciona link_base_url.
    Añade comentarios para facilitar la copia en WordPress.
    """
    datos_para_html = [r.copy() for r in resultados_ordenados] 
    
    n_filas = len(datos_para_html)
    if n_filas == 0:
        print("No hay datos para generar la tabla HTML.")
        return 

    # Ahora incluimos 'familia' en la lista de columnas a fusionar
    columnas_fusionar = ['filo', 'clase', 'orden', 'familia']

    for col_idx, col_name in enumerate(columnas_fusionar):
        i = 0
        while i < n_filas:
            current_value = datos_para_html[i][col_name]
            span_count = 1
            j = i + 1

            while j < n_filas:
                if datos_para_html[j][col_name] != current_value:
                    break

                parents_consistent = True
                for p_col_idx in range(col_idx):
                    # Solo verificamos la consistencia de los padres para la columna actual
                    if datos_para_html[j][columnas_fusionar[p_col_idx]] != datos_para_html[i][columnas_fusionar[p_col_idx]]:
                        parents_consistent = False
                        break
                
                if parents_consistent:
                    span_count += 1
                    j += 1
                else:
                    break
            
            if span_count > 1:
                datos_para_html[i][f"{col_name}_rowspan"] = span_count
                for k in range(i + 1, j):
                    datos_para_html[k][f"{col_name}_skip"] = True
            
            i = j

    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tabla Taxonómica con Rowspan</title>
    <style>
        /* Estilos básicos para la tabla de WordPress. */
        .wp-block-table { /* Para el <figure> */
            margin: 0 0 1em 0;
        }
        .wp-block-table table { /* Para el <table> dentro de <figure> */
            border-collapse: collapse;
            width: 100%;
            background-color: #fff;
            color: #222;
        }
        .wp-block-table table.has-fixed-layout { /* Si se usa layout fijo */
            table-layout: fixed;
        }
        .wp-block-table thead {
            background-color: #f6f6f6;
        }
        .wp-block-table th, .wp-block-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
        }
        .wp-block-table th {
            font-weight: bold;
        }
        .wp-block-table tbody tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .wp-block-table tbody tr:hover {
            background-color: #f1f1f1;
        }
    </style>
</head>
<body>
    <h1>Resultados de Linajes Taxonómicos Agrupados</h1>
    
    <figure class="wp-block-table">
        <table class="has-fixed-layout">
            <thead>
                <tr>
                    <th>Filo</th>
                    <th>Clase</th>
                    <th>Orden</th>
                    <th>Familia</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for row_data in datos_para_html:
        html_content += "                <tr>\n"
        
        # Filo
        if not row_data.get('filo_skip'):
            filo_rowspan = row_data.get('filo_rowspan', 1)
            html_content += f"                    <td rowspan=\"{filo_rowspan}\">{row_data['filo']}</td>\n"
        
        # Clase
        if not row_data.get('clase_skip'):
            clase_rowspan = row_data.get('clase_rowspan', 1)
            html_content += f"                    <td rowspan=\"{clase_rowspan}\">{row_data['clase']}</td>\n"

        # Orden
        if not row_data.get('orden_skip'):
            orden_rowspan = row_data.get('orden_rowspan', 1)
            html_content += f"                    <td rowspan=\"{orden_rowspan}\">{row_data['orden']}</td>\n"
        
        # Familia (ahora también puede ser fusionada)
        if not row_data.get('familia_skip'):
            familia_rowspan = row_data.get('familia_rowspan', 1)
            familia_nombre = row_data['familia']
            if link_base_url:
                cleaned_base_url = link_base_url.rstrip('/')
                familia_slug = familia_nombre.lower()
                html_content += f"                    <td rowspan=\"{familia_rowspan}\"><a href=\"{cleaned_base_url}/tag/{familia_slug}/\">{familia_nombre}</a></td>\n"
            else:
                html_content += f"                    <td rowspan=\"{familia_rowspan}\">{familia_nombre}</td>\n"
        
        html_content += "                </tr>\n"
    
    html_content += """            </tbody>
        </table>
    </figure>
    </body>
</html>"""

    try:
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nArchivo HTML para WordPress con rowspan y marcadores generado: {os.path.abspath(nombre_archivo)}")
    except Exception as e:
        print(f"ERROR: No se pudo generar el archivo HTML '{nombre_archivo}': {e}")


def procesar_familias_desde_archivo_y_ordenar_jerarquicamente(ruta_archivo, generar_html=False, link_base_url=None):
    """
    Lee nombres de familias desde un archivo (línea por línea o texto plano),
    consulta su linaje taxonómico e imprime los resultados ordenados jerárquicamente.
    Muestra un aviso si una familia no se encuentra y la excluye de los resultados.
    Si generar_html es True, también genera un archivo HTML compatible con WordPress.
    Opcionalmente, genera enlaces para los nombres de las familias en el HTML.
    """
    resultados_a_ordenar = []
    nombres_familias = []

    print("--- Iniciando Consulta de Linajes Taxonómicos ---")

    try:
        with open(ruta_archivo, 'r') as f:
            contenido_completo = f.read()
            familias_encontradas = re.findall(r'[a-zA-Z]+', contenido_completo)
            nombres_familias = [f for f in familias_encontradas if len(f) > 1] 

    except FileNotFoundError:
        print(f"ERROR: El archivo '{ruta_archivo}' no fue encontrado. Por favor, verifica la ruta y el nombre del archivo.")
        return
    except Exception as e:
        print(f"ERROR: Ocurrió un problema al leer el archivo '{ruta_archivo}': {e}")
        return

    if not nombres_familias:
        print("AVISO: No se encontraron nombres de familias válidos en el archivo de entrada.")
        return

    for i, nombre_familia in enumerate(nombres_familias, 1):
        print(f"Procesando familia [{i}/{len(nombres_familias)}]: {nombre_familia}...")
        resultado = get_linaje_para_familia(nombre_familia)
        
        if resultado:
            resultados_a_ordenar.append(resultado)
        else:
            print(f"AVISO: La familia '{nombre_familia}' no fue encontrada o hubo un error al procesarla. Se omitirá de la lista final.")
    
    if not resultados_a_ordenar:
        print("\n--- No se encontraron familias válidas para mostrar. ---")
        return

    # La ordenación es CRÍTICA para que la lógica de rowspan funcione correctamente
    # Asegúrate de que las columnas usadas para ordenar coincidan con las de fusión
    # y que la 'familia' esté al final del criterio de ordenación.
    resultados_a_ordenar.sort(key=lambda x: (x["filo"], x["clase"], x["orden"], x["familia"]))

    print("\n--- Resultados de Linajes Taxonómicos (Ordenados Jerárquicamente) ---")
    print("Filo\tClase\tOrden\tFamilia")
    print("---------------------------------------------------------------")

    for resultado in resultados_a_ordenar:
        print(f"{resultado['filo']}\t{resultado['clase']}\t{resultado['orden']}\t{resultado['familia']}")
    
    print("---------------------------------------------------------------")
    print(f"Consulta y ordenación completadas. Familias procesadas exitosamente: {len(resultados_a_ordenar)}")

    if generar_html:
        generar_html_wordpress(resultados_a_ordenar, link_base_url=link_base_url)

# Ejecutar la función principal
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consulta el linaje taxonómico de familias listadas en un archivo de texto, soportando múltiples formatos de entrada.")
    parser.add_argument(
        "archivo_familias", 
        help="La ruta al archivo de texto que contiene nombres de familias (una por línea o separados por espacios)."
    )
    parser.add_argument(
        "--wordpress", 
        action="store_true", 
        help="Genera un archivo HTML con la tabla en formato compatible con WordPress y celdas fusionadas (rowspan)."
    )
    parser.add_argument(
        "-l", "--link-base-url", 
        type=str, 
        help="URL base para generar enlaces de las familias (ej. 'https://tuweb.com/blog'). Los enlaces serán 'URL/tag/familia_en_minusculas/'."
    )
    
    args = parser.parse_args()
    
    procesar_familias_desde_archivo_y_ordenar_jerarquicamente(
        args.archivo_familias, 
        generar_html=args.wordpress, 
        link_base_url=args.link_base_url
    )
