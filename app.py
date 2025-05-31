import streamlit as st
from shapely.geometry import LineString, Point
from shapely.ops import substring
import xml.etree.ElementTree as ET
from pykml.factory import KML_ElementMaker as KML
from lxml import etree
import folium
from streamlit_folium import st_folium

# Fungsi bantu: parsing KML dan ambil LineString
def parse_kml_lines(kml_text):
    lines = []
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    root = ET.fromstring(kml_text)

    for linestring in root.findall('.//kml:LineString', ns):
        coords_text = linestring.find('kml:coordinates', ns)
        if coords_text is not None:
            coords = []
            for coord in coords_text.text.strip().split():
                parts = coord.split(',')
                if len(parts) >= 2:
                    lon, lat = float(parts[0]), float(parts[1])
                    coords.append((lon, lat))
            if len(coords) >= 2:
                lines.append(LineString(coords))
    return lines

# Fungsi bantu untuk menambahkan titik setiap X meter
def segment_line(line: LineString, interval: float):
    length = line.length
    if length == 0:
        return []
    points = []
    distances = [i for i in range(0, int(length), int(interval))]
    for d in distances:
        point = line.interpolate(d)
        points.append(point)
    points.append(line.interpolate(length))
    return points

# Fungsi buat KML baru dengan titik tambahan
def create_kml_with_poles(lines, label_tiang, jarak_segmentasi):
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

        for pt in points:
            placemark = KML.Placemark(
                KML.name(f"{label_tiang}"),
                KML.Point(
                    KML.coordinates(f"{pt.x},{pt.y},0")
                )
            )
            kml_doc.Document.append(placemark)

    return etree.tostring(kml_doc, pretty_print=True, xml_declaration=True, encoding='UTF-8'), total_points

# UI Streamlit
st.title("Auto Tambah Tiang ke KML")

uploaded_file = st.file_uploader("Upload file KML", type=["kml"])
label_tiang = st.selectbox("Pilih Label Tiang:", ["TE", "TN"])
jarak_segmentasi = st.number_input("Jarak Segmentasi (meter):", min_value=1, value=30)
jarak_antar_titik = st.number_input("Jarak Antar Titik (meter):", min_value=1, value=30)

if uploaded_file:
    content = uploaded_file.read().decode('utf-8')
    lines = parse_kml_lines(content)

    if not lines:
        st.error("Tidak ditemukan garis (LineString) di file KML.")
    else:
        # Tampilkan peta dengan garis dan titik
        m = folium.Map(zoom_start=17)
        total_tiang = 0

        for line in lines:
            coords = list(line.coords)
            if len(coords) < 2:
                continue

            folium.PolyLine(
                locations=[(lat, lon) for lon, lat in coords],
                color="blue"
            ).add_to(m)

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

        st.success(f"Total Tiang yang Ditambahkan: {total_tiang}")

        # Buat dan download KML hasil
        kml_output, _ = create_kml_with_poles(lines, label_tiang, jarak_antar_titik)

        st.download_button(
            label="Download KML dengan Tiang",
            data=kml_output,
            file_name="kml_dengan_tiang.kml",
            mime='application/vnd.google-earth.kml+xml'
        )
