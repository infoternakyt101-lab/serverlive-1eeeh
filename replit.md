# Project notes

## Run command

```bash
python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 5000
```

The Replit workflow already runs this command with headless mode enabled.

## Video storage

Uploaded videos are stored in `streamlit_uploads/`. The Streamlit upload limit
is configured to 4096 MB in `.streamlit/config.toml`. The available disk space
in the workspace is still the effective limit.

`streamlit_app.py` is the deployment entry point and delegates to the existing
application in `app.py`.

## Rendering

`app.py` imports the uploaded `render.py` engine and exposes its `COPY` and
`FAST` modes in the **Render Audio + Video** panel. Source video/audio files
are uploaded into separate folders under `streamlit_uploads/`; successful MP4
outputs go to `streamlit_uploads/rendered/` and are included in the video
library so they can be previewed, downloaded, and streamed.