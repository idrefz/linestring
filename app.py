import streamlit as st
import xml.etree.ElementTree as ET
from shapely.geometry import LineString
from shapely import wkt
from lxml import etree
from pykml.factory import KML_ElementMaker as KML
import folium
from streamlit_folium import st_folium

# Fungsi parsing LineString dari file KML
def parse_lines_from_kml(kml_text):
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    lines = []
    try:
        root = ET.fromstring(kml_text)
        for line_elem in root.findall('.//kml:LineString', ns):
            coords_text = line_elem.find('kml:coordinates', ns)
            if coords_text is None or coords_text.text is None:
                continue
            coords = []
            for raw in coords_text.text.strip().split():
                parts = raw.split(',')
                if len(parts) >= 2:
                    try:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        coords.append((lon, lat))
                    except ValueError:
                        continue
            if len(coords) >= 2:
                lines.append(LineString(coords))
    except Exception as e:
        st.error(f"❌ Gagal parsing KML: {e}")
    return lines

# Fungsi segmentasi titik di atas garis
def segment_line(line: LineString, interval: float):
    if line.length == 0:
        return []
    distances = list(range(0, int(line.length), int(interval)))
    return [line.interpolate(d) for d in distances] + [line.interpolate(line.length)]

# Fungsi membuat KML dari titik
def create_kml(points, label_prefix):
    kml_doc = KML.kml(KML.Document(KML.Name("Generated Points")))
    for i, pt in enumerate(points, start=1):
        kml_doc.Document.append(
            KML.Placemark(
                KML.name(f"{label_prefix}{i}"),
                KML.Point(KML.coordinates(f"{pt.x},{pt.y},0"))
            )
        )
    return etree.tostring(kml_doc, pretty_print=True, xml_declaration=True, encoding='UTF-8')

# Streamlit UI
st.set_page_config(page_title="Auto Titik Tiang dari KML", layout="wide")
st.title("📍 Auto Tambah Titik Tiang dari KML")

uploaded = st.file_uploader("Upload file .KML berisi LineString", type=["kml"])
jarak = st.number_input("Jarak Antar Titik (meter):", value=45, min_value=1)
label_prefix = st.selectbox("Label Awal Tiang:", ["TE", "TN"])

if uploaded:
    kml_content = uploaded.read().decode("utf-8")
    lines = parse_lines_from_kml(kml_content)

    if not lines:
        st.warning("⚠️ Tidak ada LineString valid ditemukan.")
    else:
        all_points = []
        for line in lines:
            points = segment_line(line, jarak)
            all_points.extend(points)

        st.success(f"✅ Total LineString: {len(lines)} | Total Titik Tiang: {len(all_points)}")

        # Tampilkan peta
        st.subheader("🗺️ Visualisasi Peta")
        m = folium.Map(location=[all_points[0].y, all_points[0].x], zoom_start=17)
        for line in lines:
            folium.PolyLine([(pt[1], pt[0]) for pt in line.coords], color="blue").add_to(m)
        for i, pt in enumerate(all_points, start=1):
            folium.Marker(location=(pt.y, pt.x),
                          icon=folium.DivIcon(html=f"<div style='color:red;font-size:10px'>{label_prefix}{i}</div>")
            ).add_to(m)
        st_folium(m, width=800, height=600)

        # Download
        kml_out = create_kml(all_points, label_prefix)
        st.download_button("⬇️ Download Titik Tiang (KML)", kml_out, file_name="output_tiang.kml", mime='application/vnd.google-earth.kml+xml')
