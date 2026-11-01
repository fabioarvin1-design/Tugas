# %% Sel 1 - Baca file
import pandas as pd

pd.options.display.float_format = '{:,.0f}'.format
FILE = 'paket_a_transaksi_pos_2024_2025.csv'

df = pd.read_csv(FILE, dtype=str)   # dibaca sebagai teks dulu, dibersihkan bertahap
print(df.shape)
df.head()
# %% Sel 2 - Eksplorasi awal
print('Missing value per kolom:')
print(df.isna().sum())
print()
print('Baris duplikat persis :', df.duplicated().sum())
print('Status               :', df['status'].value_counts().to_dict())
print('Diskon (%)           :', df['diskon_persen'].value_counts().to_dict())
print('Format tanggal       :', df['tanggal'].str.replace(r'\d', '9', regex=True).value_counts().to_dict())
print('Format harga         :', df['harga_satuan'].str.replace(r'\d', '9', regex=True).value_counts().to_dict())
# %% Sel 3 - Pembersihan data
# a. Hapus duplikat persis
n_awal = len(df)
df = df.drop_duplicates().copy()
print(f'Duplikat dihapus: {n_awal - len(df)} baris -> sisa {len(df)}')

# b. Missing value kode_kasir: isi label (tidak dipakai untuk hitung pendapatan)
df['kode_kasir'] = df['kode_kasir'].fillna('TIDAK DIKETAHUI')

# c. Rapikan teks
df['kode_produk'] = df['kode_produk'].str.strip().str.upper()
df['status']      = df['status'].str.strip().str.upper()

# d. Tanggal: tiga format -> datetime
def parse_tanggal(s):
    s = s.strip()
    if s[:4].isdigit():                       # 2025-06-02
        return pd.to_datetime(s, format='%Y-%m-%d')
    return pd.to_datetime(s.replace('/', '-'), format='%d-%m-%Y')   # 26/03/2025 atau 26-03-2025

df['tanggal'] = df['tanggal'].map(parse_tanggal)
df['tahun']   = df['tanggal'].dt.year

# e. Harga: "7500,00" -> 7500 ; "13.500" -> 13500
def parse_harga(s):
    s = s.strip()
    if ',' in s:                              # koma = desimal, titik = ribuan
        return float(s.replace('.', '').replace(',', '.'))
    return float(s.replace('.', ''))          # titik = pemisah ribuan

df['harga_satuan']  = df['harga_satuan'].map(parse_harga)
df['jumlah']        = df['jumlah'].astype(int)
df['diskon_persen'] = df['diskon_persen'].astype(int)

print('Missing value setelah dibersihkan:')
print(df.isna().sum().to_dict())
print('Rentang tanggal:', df['tanggal'].min().date(), 's/d', df['tanggal'].max().date())
# %% Sel 4 - Status, jumlah tidak wajar, hitung pendapatan
print('Jumlah normal    :', sorted(df.loc[(df.jumlah > 0) & (df.jumlah <= 100), 'jumlah'].unique().tolist()))
print('Jumlah ekstrem   :', sorted(df.loc[df.jumlah > 100, 'jumlah'].tolist()))
print('Jumlah negatif   :', (df.jumlah < 0).sum(), 'baris')

# pendapatan per baris, diskon dalam persen
df['pendapatan'] = df['jumlah'] * df['harga_satuan'] * (1 - df['diskon_persen'] / 100)

BATAS_JUMLAH = 100
valid = (
    (df['status'] == 'SELESAI') &     # BATAL dan RETUR tidak dihitung
    (df['jumlah'] > 0) &              # buang jumlah negatif
    (df['jumlah'] <= BATAS_JUMLAH)    # buang jumlah ekstrem
)
df_valid = df[valid]
print(f'\nTransaksi dipakai: {len(df_valid)} dari {len(df)} baris')
# %% Sel 5 - Pendapatan per tahun
hasil = (df_valid.groupby('tahun')
                 .agg(jumlah_transaksi=('id_transaksi', 'count'),
                      pendapatan=('pendapatan', 'sum'))
                 .reset_index())
hasil['pendapatan_rp'] = hasil['pendapatan'].map(lambda x: f'Rp {x:,.0f}'.replace(',', '.'))

for _, r in hasil.iterrows():
    print(f"Pendapatan {int(r['tahun'])}: {r['pendapatan_rp']}  ({int(r['jumlah_transaksi'])} transaksi)")

p24, p25 = hasil.set_index('tahun')['pendapatan'][[2024, 2025]]
print(f'\nPerubahan 2025 vs 2024: {(p25 - p24) / p24:+.2%}')
# %% Sel 6 - Perbandingan: pengaruh status dan data kotor
def per_tahun(d): return d.groupby('tahun')['pendapatan'].sum()

banding = pd.DataFrame({
    'Semua baris (tanpa filter)'       : per_tahun(df),
    'Hanya SELESAI'                    : per_tahun(df[df.status == 'SELESAI']),
    'SELESAI + jumlah valid (dipakai)' : per_tahun(df_valid),
})
banding
# %% Sel 7 - Simpan hasil
hasil[['tahun', 'jumlah_transaksi', 'pendapatan']].to_csv('hasil_pendapatan_per_tahun.csv', index=False)
print('Tersimpan: hasil_pendapatan_per_tahun.csv')