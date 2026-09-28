# serverlive

## Menjalankan aplikasi

Aplikasi ini menggunakan Streamlit. Jalankan dengan:

```bash
python -m streamlit run streamlit_app.py
```

Video yang diunggah disimpan di direktori `streamlit_uploads/`. Batas upload
Streamlit dikonfigurasi hingga 4 GB per file, bergantung pada ruang disk
workspace yang tersedia.

Di halaman **Video File Library**, pilih file untuk:

- melihat file yang sudah tersimpan beserta ukuran dan waktu modifikasinya;
- mengunduh file yang dipilih;
- melihat preview video;
- memakai file tersebut sebagai sumber tombol **Start Streaming**.

Untuk Streamlit Cloud, gunakan `streamlit_app.py` sebagai **Main file path**.
Repository dan branch pada halaman deploy harus menunjuk ke repository GitHub
yang benar-benar ada dan memiliki file tersebut.

## Render audio + video di Streamlit

`app.py` sekarang menjalankan engine di `render.py` melalui panel **Render
Audio + Video**. Alurnya:

1. Upload satu atau beberapa video mentah.
2. Upload satu atau beberapa audio mentah.
3. Pilih mode `COPY` atau `FAST`.
4. Klik **Mulai Render**.
5. Pilih output MP4 dari daftar hasil render untuk preview, download, atau
   `Start Streaming`.

File render disimpan terpisah:

```text
streamlit_uploads/render_input_videos/
streamlit_uploads/render_input_audio/
streamlit_uploads/rendered/
streamlit_uploads/render_tmp/
```