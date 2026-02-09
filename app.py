import streamlit as st
import pandas as pd
import folium
import requests
import altair as alt
from streamlit_folium import st_folium  # Library untuk menampilkan peta Folium di Streamlit
from streamlit_js_eval import get_geolocation # Library untuk meminta akses GPS browser user
from math import radians, cos, sin, asin, sqrt # Fungsi matematika untuk hitung jarak (Haversine)

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Bandung WiFi Connect", 
    page_icon="📶",
    layout="wide"
)

# ==========================================
# 2. FUNGSI UTILITAS (MATEMATIKA)
# ==========================================
def haversine(lat1, lon1, lat2, lon2):
    """
    Rumus Matematika 'Haversine' untuk menghitung jarak lurus (as the crow flies)
    antara dua titik koordinat di permukaan bola bumi.
    Output: Jarak dalam Kilometer.
    """
    R = 6371.0 # Radius bumi dalam KM
    try:
        dLat, dLon = radians(float(lat2) - float(lat1)), radians(float(lon2) - float(lon1))
        a = sin(dLat/2)**2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dLon/2)**2
        return 2 * asin(sqrt(a)) * R
    except:
        return 999.0

# ==========================================
# 3. FUNGSI SEARCH / GEOCODING
# ==========================================
def geocode_place(query):
    url = f"https://nominatim.openstreetmap.org/search?q={query}+Bandung&format=json&limit=1"
    headers = {'User-Agent': 'BdgWiFiApp/Final'}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        if data:
            return [float(data[0]['lat']), float(data[0]['lon'])]
        return None
    except:
        return None

def handle_search():
    query = st.session_state.search_input
    if query:
        new_pos = geocode_place(query)
        if new_pos:
            st.session_state.center = new_pos
            st.session_state.zoom = 16
            st.toast(f"✈️ Terbang ke {query}...", icon="✅")
        else:
            st.toast(f"⚠️ Lokasi '{query}' tidak ditemukan.", icon="❌")
        st.session_state.search_input = ""

# ==========================================
# 4. LOAD DATA (LOCAL & SCRAPING)
# ==========================================

@st.cache_data(ttl=3600)
def load_local_data():
    try:
        df = pd.read_excel('data/bandung_wifi_map.xlsx')
    except:
        try:
            df = pd.read_csv('data/bandung_wifi_map.csv')
        except:
            return pd.DataFrame(columns=['lokasi', 'latitude', 'longitude', 'sumber'])
    
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    df['lokasi'] = df['lokasi'].fillna('WiFi Point (Local)').str.strip()
    df['sumber'] = 'Dataset Internal'
    return df

@st.cache_data(ttl=3600)
def scrape_osm_data():
    """
    Melakukan SCRAPING data Live dari OpenStreetMap menggunakan URL Overpass API langsung.
    """
    # URL lengkap dengan Query Overpass yang sudah di-encode di dalamnya
    full_url = 'https://overpass-api.de/api/interpreter?data=[out:json][timeout:25];(node(-7.00,107.50,-6.80,107.75)["internet_access"];node(-7.00,107.50,-6.80,107.75)["wifi"];node(-7.00,107.50,-6.80,107.75)["amenity"="public_wifi"];);out%20center;'
    
    try:
        # Request langsung ke URL (tanpa params terpisah)
        response = requests.get(full_url, timeout=30)
        data = response.json()
        
        osm_data = []
        for element in data.get('elements', []):
            lat = element.get('lat')
            lon = element.get('lon')
            tags = element.get('tags', {})
            
            # Ambil nama atau operator sebagai identitas lokasi
            name = tags.get('name', tags.get('operator', 'WiFi Publik OSM'))
            access = tags.get('access', 'public')
            
            if lat and lon:
                osm_data.append({
                    'lokasi': name,
                    'latitude': float(lat),
                    'longitude': float(lon),
                    'akses': access,
                    'sumber': 'Scraping Live (OSM)'
                })
        return pd.DataFrame(osm_data)
        
    except Exception as e:
        # Jika error/timeout, return dataframe kosong agar app tidak crash
        return pd.DataFrame(columns=['lokasi', 'latitude', 'longitude', 'sumber'])

def get_combined_map_data():
    df_local = load_local_data()
    df_osm = scrape_osm_data()
    return pd.concat([df_local, df_osm], ignore_index=True)

@st.cache_data(ttl=3600)
def load_stats_data():
    try:
        return pd.read_csv('data/bandung_wifi_raw.csv')
    except:
        return pd.DataFrame()

# ==========================================
# 5. STATE MANAGEMENT
# ==========================================
if 'center' not in st.session_state:
    st.session_state.center = [-6.9175, 107.6191] # Default Bandung
if 'zoom' not in st.session_state:
    st.session_state.zoom = 14
if 'menu' not in st.session_state:
    st.session_state.menu = "peta"
if 'user_located_once' not in st.session_state:
    st.session_state.user_located_once = False

# ==========================================
# 6. SIDEBAR NAVIGASI
# ==========================================
with st.sidebar:
    st.title("📶 WiFi Bandung")
    st.caption("Integrasi Dataset & OSM Scraping")
    
    if st.button("🛰️ Radar Peta", use_container_width=True, type="primary" if st.session_state.menu == "peta" else "secondary"):
        st.session_state.menu = "peta"
        st.rerun()
    if st.button("📊 Analitik Data", use_container_width=True, type="primary" if st.session_state.menu == "stats" else "secondary"):
        st.session_state.menu = "stats"
        st.rerun()
    if st.button("🗄️ Dataset & Scraping", use_container_width=True, type="primary" if st.session_state.menu == "data" else "secondary"):
        st.session_state.menu = "data"
        st.rerun()
        
    st.divider()
    
    if st.button("🔄 Reset & Refresh", use_container_width=True):
        st.cache_data.clear()
        st.session_state.center = [-6.9175, 107.6191]
        st.session_state.zoom = 14
        st.session_state.user_located_once = False 
        st.rerun()

# ==========================================
# 7. LOGIKA UTAMA (MAIN APP)
# ==========================================

# --- MENU 1: PETA RADAR ---
if st.session_state.menu == "peta":
    st.header("🛰️ Radar WiFi")
    
    user_loc = get_geolocation()
    current_lat, current_lon = st.session_state.center
    has_user_loc = False
    
    if user_loc:
        u_lat = user_loc['coords']['latitude']
        u_lon = user_loc['coords']['longitude']
        has_user_loc = True
        
        if not st.session_state.user_located_once:
            st.session_state.center = [u_lat, u_lon]
            st.session_state.zoom = 16
            st.session_state.user_located_once = True 
            st.toast("📍 Lokasi ditemukan! Memusatkan peta...", icon="🎯")
            st.rerun()
    
    current_lat, current_lon = st.session_state.center

    with st.container(border=True):
        col_search, col_act = st.columns([3, 1])
        with col_search:
            st.text_input(
                "🔍 Cari Tempat :", 
                placeholder="Misal: Gedung Sate...", 
                key="search_input", 
                on_change=handle_search
            )
    
    df_map = get_combined_map_data()
    
    if not df_map.empty:
        df_map['jarak'] = df_map.apply(
            lambda x: haversine(current_lat, current_lon, x['latitude'], x['longitude']), 
            axis=1
        )
        
        df_near = df_map[df_map['jarak'] <= 3.0].sort_values('jarak')
        
        m = folium.Map(
            location=st.session_state.center, 
            zoom_start=st.session_state.zoom, 
            tiles='CartoDB Positron' 
        )
        
        folium.Marker(
            st.session_state.center, 
            popup="Lokasi Pusat", 
            icon=folium.Icon(color='red', icon='user', prefix='fa')
        ).add_to(m)

        for _, row in df_near.iterrows():
            color = "#0078D7" if row['sumber'] == 'Dataset Internal' else "#FF9800"
            gmap_link = f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"
            
            popup_html = f"""
            <div style="font-family: sans-serif; min-width: 200px;">
                <h5 style="margin: 0; color: {color};">{row['lokasi']}</h5>
                <p style="font-size: 11px; color: #666; margin: 2px 0;">{row['sumber']}</p>
                <p style="margin: 5px 0;">📏 <b>{round(row['jarak']*1000)} m</b></p>
                <a href="{gmap_link}" target="_blank" style="
                    display: inline-block; background-color: {color}; color: white;
                    padding: 6px 10px; text-decoration: none; border-radius: 4px; font-size: 12px;">
                    🗺️ Buka Google Maps
                </a>
            </div>
            """
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(m)

        c_map, c_list = st.columns([3, 1])
        with c_map:
            st_folium(m, width="100%", height=500, key="map_render")
            
            status_text = "📍 Menggunakan Lokasi GPS Anda" if has_user_loc and st.session_state.user_located_once else "📍 Menggunakan Pusat Kota Default"
            st.caption(f"{status_text} | 🔵 Internal | 🟠 OSM Live")
            
        with c_list:
            st.subheader("Terdekat")
            if not df_near.empty:
                for _, r in df_near.head(5).iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{r['lokasi']}**")
                        st.caption(f"{r['sumber']} • {int(r['jarak']*1000)} m")
                        st.link_button("Rute ↗️", f"https://www.google.com/maps/search/?api=1&query={r['latitude']},{r['longitude']}", use_container_width=True)
            else:
                st.info("Tidak ada titik WiFi dalam radius 3 KM.")

# --- MENU 2: STATISTIK ---
elif st.session_state.menu == "stats":
    st.header("📊 Analitik Pengguna (Raw Data)")
    df_raw = load_stats_data()
    
    if not df_raw.empty:
        if 'jumlah_pengguna' in df_raw.columns:
            # agg_data = df_raw.groupby('lokasi')['jumlah_pengguna'].sum().reset_index()
            agg_data = df_raw.groupby('lokasi')['jumlah_pengguna'].mean().reset_index()
            agg_data['jumlah_pengguna'] = agg_data['jumlah_pengguna'].round(1).astype(int)
            agg_data = agg_data.sort_values('jumlah_pengguna', ascending=False)
            y_val = 'jumlah_pengguna'
            x_title = "Rata-rata Pengguna"
        else:
            agg_data = df_raw['lokasi'].value_counts().reset_index()
            agg_data.columns = ['lokasi', 'count']
            y_val = 'count'
            x_title = "Frekuensi Data"

        m1, m2 = st.columns(2)
        m1.metric("Total Data", len(df_raw))
        m2.metric("Top Lokasi", agg_data.iloc[0]['lokasi'] if not agg_data.empty else "-")
        
        st.write("---")
        chart = alt.Chart(agg_data.head(15)).mark_bar(cornerRadiusTopRight=5).encode(
            x=alt.X(f'{y_val}:Q', title=x_title),
            y=alt.Y('lokasi:N', sort='-x', title="Lokasi"),
            color=alt.Color(f'{y_val}:Q', scale=alt.Scale(scheme='orangered')),
            tooltip=['lokasi', y_val]
        ).properties(height=500)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.error("File 'bandung_wifi_raw.csv' tidak ditemukan.")

# --- MENU 3: DATASET ---
elif st.session_state.menu == "data":
    st.header("🗄️ Master Database")
    
    tab1, tab2 = st.tabs(["📁 Dataset Internal", "🌐 Data Scrapping (OSM Live)"])
    
    with tab1:
        st.info("Data statis dari file `bandung_wifi_map.xlsx`.")
        df_excel = load_local_data()
        st.dataframe(df_excel, use_container_width=True, hide_index=True)
        csv_excel = df_excel.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Unduh CSV (Internal)", csv_excel, "internal_wifi_bandung.csv", "text/csv")
        
    with tab2:
        st.info("Data live yang diambil dari OpenStreetMap menggunakan URL Overpass langsung.")
        with st.spinner("Mengambil data live dari OpenStreetMap..."):
            df_osm = scrape_osm_data()
            
        if not df_osm.empty:
            st.dataframe(df_osm, use_container_width=True, hide_index=True)
            csv_osm = df_osm.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Unduh CSV (Scraping Result)", csv_osm, "scraped_osm_wifi.csv", "text/csv")
        else:
            st.warning("Tidak ada data scraping yang ditemukan atau API timeout.")