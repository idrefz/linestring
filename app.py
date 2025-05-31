
import streamlit as st
from fastkml import kml
from shapely.geometry import LineString, Point
from shapely.ops import substring
import zipfile
import io
import math
from pykml.factory import KML_ElementMaker as KML
from lxml import etree
import folium
from streamlit_folium import st_folium

# Fungsi bantu untuk menambahkan titik setiap X meter
def segment_line(line: LineString, interval: float):
    length = line.length
    points = []
    distances = [i for i in range(0, int(length), int(interval))]
    for d in distances:
        point = line.interpolate(d)
        points.append(point)
    points.append(line.interpolate(length))
    return points

# Fungsi buat KML baru dengan titik tambahan
def create_kml_with_poles(lines, label_tiang, jarak_segmentasi):
    ns = '{http://www.opengis.net/kml/2.2}'
    kml_doc = KML.kml(
        KML.Document(
            KML.Name("Generated KML with Poles")
        )
    )

    total_points = 0
    for line in lines:
        if not isinstance(line, LineString):
            continue

        points = segment_line(line, jarak_segmentasi)
        total_points += len(points)

        for idx, pt in enumerate(points):
            placemark = KML.Placemark(
                KML.name(f"{label_tiang}"),
                KML.Point(
                    KML.coordinates(f"{pt.x},{pt.y},0")
                )
            )
            kml_doc.Document.append(placemark)

    return etree.tostring(kml_doc, pretty_print=True, xml_declaration=True, encoding='UTF-8'), total_points

# Streamlit UI
st.title("Auto Tambah Tiang ke KML")

uploaded_file = st.file_uploader("Upload file KML", type=["kml"])
label_tiang = st.selectbox("Pilih Label Tiang:", ["TE", "TN"])
jarak_segmentasi = st.number_input("Jarak Segmentasi (meter):", min_value=1, value=30)
jarak_antar_titik = st.number_input("Jarak Antar Titik (meter):", min_value=1, value=30)

if uploaded_file:
    k = kml.KML()
    content = uploaded_file.read().decode('utf-8')
    k.from_string(content.encode('utf-8'))

    # Ambil semua LineString dari KML
    lines = extract_lines(k)
   def extract_lines(kml_obj):
    lines = extract_lines(k)
    def recurse(features):
        for f in features:
            if hasattr(f, 'geometry') and isinstance(f.geometry, LineString):
                lines.append(f.geometry)
            elif hasattr(f, 'features'):
                recurse(f.features())
    recurse(kml_obj.features())
    return lines

    # Tampilkan peta
    m = folium.Map(zoom_start=17)
    total_tiang = 0

    for line in lines:
        coords = list(line.coords)
        folium.PolyLine(locations=[(lat, lon) for lon, lat in coords], color="blue").add_to(m)
        points = segment_line(line, jarak_antar_titik)
        total_tiang += len(points)

        for pt in points:
            color = "red" if label_tiang == "TE" else "green"
            folium.Marker(
                location=(pt.y, pt.x),
                icon=folium.DivIcon(html=f"<div style='font-size:10px;color:{color}'>{label_tiang}</div>")
            ).add_to(m)

    st.subheader("Preview Jalur dan Titik Tiang")
    st_data = st_folium(m, width=700, height=500)

    # Tampilkan jumlah total tiang
    st.success(f"Total Tiang yang Ditambahkan: {total_tiang}")

    # Proses dan hasilkan file KML baru
    kml_output, _ = create_kml_with_poles(lines, label_tiang, jarak_antar_titik)

    st.download_button(
        label="Download KML dengan Tiang",
        data=kml_output,
        file_name="kml_dengan_tiang.kml",
        mime='application/vnd.google-earth.kml+xml'
    )
