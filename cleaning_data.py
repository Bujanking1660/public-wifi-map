import pandas as pd
import os

def proses_data():
    jalur_input = 'data/bandung_csv/bandung.csv'
    
    if not os.path.exists(jalur_input):
        print("File sumber tidak ditemukan.")
        return

    # 1. Ambil Data Asli
    df_asli = pd.read_csv(jalur_input)

    # 2. Pembersihan Dasar (Buang data kosong)
    df_bersih = df_asli.dropna(subset=['lokasi', 'latitude', 'longitude'])
    df_bersih = df_bersih[(df_bersih['latitude'] != 0) & (df_bersih['longitude'] != 0)]

    # 3. Buat Data MAP (Rata-rata per lokasi)
    kunci = ['lokasi', 'alamat', 'latitude', 'longitude']
    df_map = df_bersih.groupby(kunci).mean(numeric_only=True).reset_index().round(1)

    # 4. Simpan ke CSV
    df_bersih.to_csv('data/bandung_wifi_raw.csv', index=False) # Data Asli
    df_map.to_csv('data/bandung_wifi_map.csv', index=False)     # Data Rata-rata

    # 5. Simpan ke Excel
    df_bersih.to_excel('data/bandung_wifi_raw.xlsx', index=False)
    df_map.to_excel('data/bandung_wifi_map.xlsx', index=False)

    print(f"Selesai! Data Raw: {len(df_bersih)} | Data Map: {len(df_map)}")

if __name__ == "__main__":
    proses_data()