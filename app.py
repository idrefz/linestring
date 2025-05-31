import streamlit as st
from shapely.geometry import LineString
import xml.etree.ElementTree as ET
from pykml.factory import KML_ElementMaker as KML
from lxml import etree
import folium
from streamlit_folium import st_folium

# Fungsi parsing KML dengan toleransi tinggi
def parse_kml_lines_tolerant(kml_text):
    lines = []
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    try:
        root = ET.fromstring(kml_text)
    except ET.ParseError as e:
        st.error(f"❌ Gagal parsing XML: {e}")
        return []

    for linestring in root.findall('.//kml:LineString', ns):
        coords_text_elem = linestring.find('kml:coordinates', ns)
        if coords_text_elem is None or coords_text_elem.text is None:
            continue

        coords_raw = coords_text_elem.text.strip().split()
        coords = []

        for coord in coords_raw:
            parts = coord.strip().split(',')
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append((lon, lat))
                except:
                    continue

        if len(coords) >= 2:
            try:
                line = LineString(coords)
                lines.append(line)
            except:
                continue

    return lines

# Fungsi segmentasi garis
def segment_line(line: LineString, interval: float):
    if line.length == 0:
        return []
    distances = [i for i in range(0, int(line.length), int(interval))]
    points = [line.interpolate(d) for d in distances]
    points.append(line.interpolate(line.length))
    return points

# Fungsi buat KML baru dari titik
def create_kml_with_poles(lines, label_tiang, jarak_segmentasi):
    kml_doc = KML.kml(KML.Document(KML.Name("Generated KML with Poles")))
    counter = 1

    for line in lines:
        points = segment_line(line, jarak_segmentasi)
        for pt in points:
            kml_doc.Document.append(
                KML.Placemark(
                    KML.name(f"{label_tiang}{counter}"),
                    KML.Point(KML.coordinates(f"{pt.x},{pt.y},0"))
                )
            )
            counter += 1

    return etree.tostring(kml_doc, pretty_print=True, xml_declaration=True, encoding='UTF-8'), counter - 1

# UI Streamlit
st.set_page_config(page_title="Auto Tambah Tiang ke KML", layout="wide")
st.title("📌 Auto Tambah Tiang ke KML")

uploaded_file = st.file_uploader("Upload file KML", type=["kml"])
label_tiang = st.selectbox("Pilih Label Tiang:", ["TE", "TN"])
jarak_segmentasi = st.number_input("Jarak Segmentasi (meter):", min_value=1, value=30)

if uploaded_file:
    content = uploaded_file.read().decode('utf-8')
    lines = parse_kml_lines_tolerant(content)

    if not lines:
        st.error("❌ Tidak ditemukan LineString yang valid.")
    else:
        m = folium.Map(zoom_start=17)
        total_tiang = 0
        counter = 1

        for line in lines:
            coords = list(line.coords)
            folium.PolyLine(
                locations=[(lat, lon) for lon, lat in coords],
                color="blue"
            ).add_to(m)

            points = segment_line(line, jarak_segmentasi)
            total_tiang += len(points)

            for pt in points:
                color = "red" if label_tiang == "TE" else "green"
                folium.Marker(
                    location=(pt.y, pt.x),
                    icon=folium.DivIcon(
                        html=f"<div style='font-size:10px;color:{color}'>{label_tiang}{counter}</div>")
                ).add_to(m)
                counter += 1

        st.subheader("🗺️ Preview Jalur dan Titik Tiang")
        st_data = st_folium(m, width=800, height=600)

        st.success(f"✅ Total Tiang yang Ditambahkan: {total_tiang}")

        # Tombol download
        kml_output, _ = create_kml_with_poles(lines, label_tiang, jarak_segmentasi)
        st.download_button(
            label="⬇️ Download KML dengan Tiang",
            data=kml_output,
            file_name="kml_dengan_tiang.kml",
            mime='application/vnd.google-earth.kml+xml'
        )
