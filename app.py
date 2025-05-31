import streamlit as st
from shapely.geometry import LineString
from pykml.factory import KML_ElementMaker as KML
from lxml import etree
import folium
from streamlit_folium import st_folium
import xml.etree.ElementTree as ET

# Fungsi parsing LineString
def parse_kml_lines_safe(kml_text):
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    lines = []

    try:
        root = ET.fromstring(kml_text)
    except ET.ParseError as e:
        st.error(f"❌ Gagal parsing XML: {e}")
        return []

    for linestring in root.findall('.//kml:LineString', ns):
        coords_elem = linestring.find('kml:coordinates', ns)
        if coords_elem is None or not coords_elem.text:
            continue

        coords_raw = coords_elem.text.strip().split()
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
            lines.append(LineString(coords))
    return lines

# Segmentasi garis
def segment_line(line: LineString, interval: float):
    length = line.length
    if length == 0:
        return []
    distances = [i for i in range(0, int(length), int(interval))]
    points = [line.interpolate(d) for d in distances]
    points.append(line.interpolate(length))
    return points

# Buat KML dari titik-titik
def create_kml_with_poles(lines, label, interval):
    kml_doc = KML.kml(KML.Document(KML.Name("Tiang dari LineString")))
    count = 1
    for line in lines:
        points = segment_line(line, interval)
        for pt in points:
            kml_doc.Document.append(
                KML.Placemark(
                    KML.name(f"{label}{count}"),
                    KML.Point(KML.coordinates(f"{pt.x},{pt.y},0"))
                )
            )
            count += 1
    return etree.tostring(kml_doc, pretty_print=True, xml_declaration=True, encoding='UTF-8'), count - 1

# UI Streamlit
st.set_page_config("Auto Tambah Tiang", layout="wide")
st.title("📌 Auto Tambah Titik Tiang dari KML")

uploaded = st.file_uploader("Upload File KML", type="kml")
label = st.selectbox("Label Tiang", ["TE", "TN", "TP", "TI"])
interval = st.number_input("Jarak Antar Titik (meter)", min_value=1, value=30)

if uploaded:
    kml_text = uploaded.read().decode("utf-8")
    lines = parse_kml_lines_safe(kml_text)

    if not lines:
        st.warning("⚠️ Tidak ada LineString valid ditemukan.")
    else:
        m = folium.Map(zoom_start=17)
        counter = 1
        total_tiang = 0

        for line in lines:
            coords = list(line.coords)
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coords], color="blue").add_to(m)

            points = segment_line(line, interval)
            total_tiang += len(points)

            for pt in points:
                folium.Marker(
                    location=(pt.y, pt.x),
                    icon=folium.DivIcon(html=f"<div style='font-size:10px;color:red'>{label}{counter}</div>")
                ).add_to(m)
                counter += 1

        st.subheader("🗺️ Preview Titik Tiang")
        st_data = st_folium(m, width=800, height=600)

        st.success(f"✅ Total Tiang: {total_tiang}")

        kml_output, _ = create_kml_with_poles(lines, label, interval)
        st.download_button(
            label="⬇️ Download KML dengan Titik Tiang",
            data=kml_output,
            file_name="hasil_tiang.kml",
            mime="application/vnd.google-earth.kml+xml"
        )
