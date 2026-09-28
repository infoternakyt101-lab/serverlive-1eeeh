#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║   DAPUR NGEBUL CLI  🔥  Bulk Render Engine  v6.0  (2-MODE SIMPLIFIED)   ║
║   by Mas DEE  +628562626116                                             ║
╠══════════════════════════════════════════════════════════════════════════╣
║   ✔ Scan folder VIDEO + AUDIO                                           ║
║   ✔ Validasi corrupt / 0KB / durasi 0 sebelum render                   ║
║   ✔ 1 audio  →  semua video pakai audio itu (fixed target)             ║
║   ✔ Banyak audio  →  tiap video dapat audio random (bulk random)        ║
║   ✔ Output nama = nama AUDIO + .mp4                                     ║
║   ✔ Metadata iPhone sintetis: model/device profile acak                 ║
║   ✔ Anti-replace: tambah _ jika nama sudah ada                          ║
║   ✔ Progress real-time: time= speed= size=                              ║
║   ✔ Log file otomatis  render_log_YYYYMMDD_HHMMSS.txt                  ║
║   ✔ Disk guard: berhenti otomatis jika sisa disk < limit               ║
║                                                                           ║
║   HANYA 2 MODE RENDER:                                                   ║
║   [1] COPY    — video + audio CONTACT-COPY murni, TANPA re-encode      ║
║                 sama sekali (-c:v copy -c:a copy). Tercepat,            ║
║                 ukuran ≈ file asli. Metadata ditulis saat mux.          ║
║   [2] FAST    — video di-REENCODE CEPAT dgn penurunan kualitas         ║
║                 (resolusi turun, fps turun, bitrate rendah,            ║
║                 preset ultrafast) ditulis ke VIDEO TEMP dulu,          ║
║                 lalu AUDIO di-CONTACT-COPY (tanpa re-encode) ke        ║
║                 video temp itu. Proses sangat cepat, hemat disk,       ║
║                 disertai limit disk space.                              ║
╚══════════════════════════════════════════════════════════════════════════╝

Cara pakai:
  python dapur_ngebul_cli.py
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --output-dir ./hasil
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --list
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --dry-run
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --mode copy
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --mode fast
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --mode fast --fast-vbr 100k --fast-fps 10
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --disk-min-gb 2
"""

import sys, os, subprocess, argparse, random, time, math, shutil, re, unicodedata, traceback, uuid
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
# KONSTANTA
# ═══════════════════════════════════════════════════════════════════════════
VIDEO_EXTS       = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v', '.wmv', '.ts', '.3gp'}
AUDIO_EXTS       = {'.mp3', '.aac', '.m4a', '.opus', '.ogg', '.flac', '.wav', '.wma', '.aiff'}
MIN_FILE_BYTES   = 10 * 1024       # 10 KB — di bawah ini dianggap corrupt
MIN_DUR_SEC      = 1.0             # durasi minimum valid
OUTPUT_MIN_BYTES = 50 * 1024       # 50 KB — output di bawah ini dianggap gagal
FFMPEG_TIMEOUT   = 14400           # 4 jam maksimum per job
DISK_MIN_BYTES   = 1 * 1024 ** 3   # 1 GB — batas minimum sisa disk sebelum render

# Codec audio yang aman di-contact-copy langsung ke container MP4/TS
AUDIO_COPY_OK    = {'aac', 'mp3', 'ac3', 'eac3'}

# ── Mode FAST — reencode cepat video (turun kualitas) + audio contact-copy ──
FAST_SCALE       = 640              # lebar max output (px), tinggi auto proporsional
FAST_FPS         = 10               # frame per detik output (turun drastis)
FAST_VBR         = '100k'           # target bitrate video
FAST_MAXRATE     = '120k'           # bitrate burst maksimum
FAST_BUFSIZE     = '200k'           # buffer (≈2× maxrate)
FAST_PRESET      = 'ultrafast'      # preset tercepat
FAST_AUDIO_BR    = '128k'           # fallback bitrate audio jika codec asli tak bisa di-copy

# Profil perangkat yang dipakai sebagai metadata container sintetis untuk
# kebutuhan pengujian/organisasi file. Nilainya tidak mengubah stream video
# dan bukan bukti bahwa file benar-benar direkam oleh perangkat tersebut.
IPHONE_PROFILES = (
    {
        'identifier': 'iPhone13,2',
        'model': 'iPhone 13 Pro',
        'ios': 'iOS 17.6.1',
        'camera': 'Main Camera',
        'lens': '26mm f/1.5',
        'aperture': 'f/1.5',
    },
    {
        'identifier': 'iPhone15,2',
        'model': 'iPhone 14 Pro',
        'ios': 'iOS 17.7.2',
        'camera': 'Main Camera',
        'lens': '24mm f/1.78',
        'aperture': 'f/1.78',
    },
    {
        'identifier': 'iPhone15,4',
        'model': 'iPhone 15',
        'ios': 'iOS 18.1.1',
        'camera': 'Main Camera',
        'lens': '26mm f/1.6',
        'aperture': 'f/1.6',
    },
    {
        'identifier': 'iPhone16,1',
        'model': 'iPhone 15 Pro',
        'ios': 'iOS 18.2',
        'camera': 'Main Camera',
        'lens': '24mm f/1.78',
        'aperture': 'f/1.78',
    },
    {
        'identifier': 'iPhone17,1',
        'model': 'iPhone 16 Pro',
        'ios': 'iOS 18.5',
        'camera': 'Main Camera',
        'lens': '24mm f/1.78',
        'aperture': 'f/1.78',
    },
    {
        'identifier': 'iPhone17,2',
        'model': 'iPhone 16 Pro Max',
        'ios': 'iOS 18.5',
        'camera': 'Main Camera',
        'lens': '24mm f/1.78',
        'aperture': 'f/1.78',
    },
    {
        'identifier': 'iPhone14,2',
        'model': 'iPhone 13 Pro Max',
        'ios': 'iOS 17.5.1',
        'camera': 'Main Camera',
        'lens': '26mm f/1.5',
        'aperture': 'f/1.5',
    },
)

# ═══════════════════════════════════════════════════════════════════════════
CY = "\033[96m"; GR = "\033[92m"; YL = "\033[93m"
RD = "\033[91m"; BD = "\033[1m";  DM = "\033[2m"; RS = "\033[0m"
MG = "\033[95m"

_log_file = None

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def _wlog(msg):
    if _log_file:
        try:
            _log_file.write(re.sub(r'\033\[[0-9;]*m', '', msg) + "\n")
            _log_file.flush()
        except: pass

def plog(msg, color=""):
    line = f"{DM}[{_ts()}]{RS} {color}{msg}{RS}"
    print(line, flush=True)
    _wlog(f"[{_ts()}] {msg}")

def p_ok(m):   plog(f"✔  {m}", GR)
def p_err(m):  plog(f"✘  {m}", RD)
def p_inf(m):  plog(f"   {m}", CY)
def p_warn(m): plog(f"⚠  {m}", YL)
def p_skip(m): plog(f"→  {m}", DM)

def p_hdr(m):
    print(f"\n{BD}{YL}{'═'*66}\n  {m}\n{'═'*66}{RS}", flush=True)
    _wlog(f"\n{'='*66}\n  {m}\n{'='*66}")

def p_sub(m):
    print(f"{BD}{CY}{'─'*66}\n  {m}\n{'─'*66}{RS}", flush=True)
    _wlog(f"{'─'*66}\n  {m}\n{'─'*66}")

# ═══════════════════════════════════════════════════════════════════════════
# DISK SPACE CHECK
# ═══════════════════════════════════════════════════════════════════════════
def get_free_bytes(path):
    """Kembalikan sisa ruang disk (bytes) di partisi tempat `path` berada."""
    try:
        usage = shutil.disk_usage(str(Path(path).resolve()))
        return usage.free
    except Exception:
        return float('inf')   # jika tidak bisa cek, anggap aman

def fmt_gb(b):
    return f"{b / 1024**3:.2f} GB"

def disk_pause_if_needed(out_dir, idx, total, disk_min_bytes):
    """
    Cek sisa disk sebelum render.
    Jika < disk_min_bytes → tampilkan warning, tunggu konfirmasi user,
    CLI TIDAK menutup — user bisa hapus file lalu tekan Enter untuk lanjut.
    Return True  → lanjut render
    Return False → skip job ini (user pilih skip)
    """
    free = get_free_bytes(out_dir)
    if free >= disk_min_bytes:
        return True   # sisa disk cukup, lanjut langsung

    while True:
        print(f"\n{'━'*66}", flush=True)
        print(f"  {BD}{YL}⚠  DISK HAMPIR PENUH  —  Job [{idx}/{total}]{RS}", flush=True)
        print(f"  Sisa ruang  : {BD}{RD}{fmt_gb(free)}{RS}  (batas minimum {fmt_gb(disk_min_bytes)})", flush=True)
        print(f"  Output dir  : {Path(out_dir).resolve()}", flush=True)
        print(f"\n  Hapus file yang tidak perlu, lalu pilih:", flush=True)
        print(f"  {GR}[Y/Enter]{RS}  Lanjut render job ini", flush=True)
        print(f"  {YL}[S]{RS}        Skip job ini, lanjut ke job berikutnya", flush=True)
        print(f"  {RD}[Q]{RS}        Batalkan semua render (keluar)", flush=True)
        print(f"{'━'*66}\n", flush=True)
        _wlog(f"[DISK-PAUSE] Job [{idx}/{total}] sisa={fmt_gb(free)} < {fmt_gb(disk_min_bytes)}")

        try:
            c = input(f"  Pilihan [Y/s/q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            c = 'y'

        # Refresh cek disk setelah user selesai hapus file
        free = get_free_bytes(out_dir)
        print(f"  Sisa disk sekarang : {BD}{fmt_gb(free)}{RS}\n", flush=True)

        if c in ('', 'y', 'yes'):
            if free >= disk_min_bytes:
                p_ok("Disk sudah cukup, lanjut render...")
                return True
            else:
                p_warn(f"Disk masih kurang ({fmt_gb(free)}), silakan hapus lebih banyak file.")
                continue   # tanya lagi
        elif c in ('s', 'skip'):
            p_skip(f"Job [{idx}/{total}] di-skip oleh user (disk penuh)")
            return False
        elif c in ('q', 'quit', 'exit'):
            print(f"\n{RD}Render dibatalkan oleh user (disk penuh).{RS}", flush=True)
            raise KeyboardInterrupt("user quit — disk penuh")
        else:
            p_warn("Pilihan tidak dikenal, ketik Y / S / Q")

def fmt_t(sec):
    sec = max(0, int(sec))
    return f"{sec//3600}:{(sec%3600)//60:02d}:{sec%60:02d}"

def fmt_mb(path):
    try: return f"{Path(path).stat().st_size/1024/1024:.1f} MB"
    except: return "? MB"

# ═══════════════════════════════════════════════════════════════════════════
# FFPROBE
# ═══════════════════════════════════════════════════════════════════════════
def ffprobe_vals(path, select, entries):
    try:
        out = subprocess.check_output(
            ['ffprobe', '-v', 'error', '-select_streams', select,
             '-show_entries', entries,
             '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
            timeout=20, stderr=subprocess.DEVNULL)
        return [l.strip() for l in out.decode(errors='replace').splitlines() if l.strip()]
    except:
        return []

def probe_video(path):
    li = ffprobe_vals(path, 'v:0', 'stream=codec_name,width,height,r_frame_rate')
    d  = {'codec': None, 'w': 0, 'h': 0, 'fps': 0.0, 'dur': 0.0, 'has_video': False}
    if li:
        d['codec']     = li[0]
        d['has_video'] = True
        try: d['w'] = int(li[1])
        except: pass
        try: d['h'] = int(li[2])
        except: pass
        try:
            n, x = li[3].split('/')
            d['fps'] = round(int(n)/int(x), 3)
        except: pass
    for sel, ent in [('v:0','stream=duration'),('','format=duration')]:
        r = ffprobe_vals(path, sel, ent)
        if r:
            try: d['dur'] = float(r[0]); break
            except: pass
    return d

def probe_audio(path):
    li = ffprobe_vals(path, 'a:0', 'stream=codec_name,sample_rate,channels,duration')
    d  = {'codec': None, 'sr': '?', 'ch': '?', 'dur': 0.0, 'has_audio': False}
    if li:
        d['codec']     = li[0]
        d['has_audio'] = True
        if len(li) > 1: d['sr'] = li[1]
        if len(li) > 2: d['ch'] = li[2]
        if len(li) > 3:
            try: d['dur'] = float(li[3])
            except: pass
    return d

# ═══════════════════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════════════════
def sanitize_name(name):
    try:
        s = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode()
        s = re.sub(r'[^\w\s.-]', '', s).replace(' ', '_')
        return re.sub(r'_+', '_', s) or f"f{random.getrandbits(20)}"
    except:
        return f"f{random.getrandbits(20)}"

def safe_cp(src, tmp_dir, prefix):
    """Copy ke ASCII temp path jika nama file non-ASCII."""
    src = Path(src)
    if src.name.isascii():
        return src, False
    dst = Path(tmp_dir) / f"{prefix}_{sanitize_name(src.stem)}_{random.getrandbits(16)}{src.suffix}"
    shutil.copy2(src, dst)
    return dst, True

def tmp_f(tmp_dir, ext):
    return Path(tmp_dir) / f"dn_{random.getrandbits(28)}{ext}"

def _quality_label(width, height):
    """Label kualitas berdasarkan resolusi aktual, bukan klaim profil."""
    longest = max(int(width or 0), int(height or 0))
    if longest >= 3800:
        return '4K UHD'
    if longest >= 2500:
        return '2K QHD'
    if longest >= 1800:
        return '1K / Full HD'
    if longest >= 1200:
        return 'HD 720p'
    if longest > 0:
        return f'{width}x{height}'
    return 'Unknown resolution'

def _codec_label(codec):
    return {
        'h264': 'H.264/AVC',
        'hevc': 'H.265/HEVC',
        'h265': 'H.265/HEVC',
        'av1': 'AV1',
        'vp9': 'VP9',
    }.get((codec or '').lower(), codec or 'Unknown')

def _bitrate_label(value, fallback='unknown'):
    try:
        bits = float(value)
        if bits > 0:
            return f'{bits / 1000:.0f} kb/s'
    except (TypeError, ValueError):
        text = str(value or '').strip().lower()
        match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*([kmg]?)', text)
        if match:
            number = float(match.group(1))
            multiplier = {'': 1, 'k': 1000, 'm': 1000_000, 'g': 1000_000_000}
            return f'{number * multiplier[match.group(2)] / 1000:.0f} kb/s'
    return fallback

def build_iphone_metadata(video_info=None, audio_info=None, source_path=None):
    """Buat metadata profil iPhone sintetis untuk ditulis saat mux.

    Stream video/audio tetap diproses sesuai mode COPY/FAST. Hanya metadata
    container yang ditambahkan, dan selalu diberi penanda sintetis agar tidak
    disalahartikan sebagai bukti asal perangkat.
    """
    video_info = video_info or {}
    audio_info = audio_info or {}
    profile = random.choice(IPHONE_PROFILES)
    capture_time = datetime.now().astimezone().isoformat(timespec='seconds')
    record_id = str(uuid.uuid4())
    width = int(video_info.get('w') or 0)
    height = int(video_info.get('h') or 0)
    fps = float(video_info.get('fps') or 0)
    quality = _quality_label(width, height)
    codec = _codec_label(video_info.get('codec'))
    bitrate = _bitrate_label(video_info.get('bit_rate'))
    if bitrate == 'unknown' and source_path:
        try:
            duration = float(video_info.get('dur') or 0)
            size = Path(source_path).stat().st_size
            if duration > 0:
                bitrate = _bitrate_label(size * 8 / duration, 'unknown')
        except (OSError, ValueError, TypeError):
            pass
    fps_label = f'{fps:g} fps' if fps > 0 else 'unknown fps'
    pixel_format = video_info.get('pix_fmt') or 'yuv420p'
    audio_codec = _codec_label(audio_info.get('codec'))
    audio_rate = audio_info.get('sr') or 'unknown'
    audio_channels = audio_info.get('ch') or 'unknown'
    duration_label = fmt_t(video_info.get('dur') or 0)
    iso = random.choice((25, 32, 40, 50, 64, 80, 100, 125, 160, 200, 320))
    shutter = random.choice(('1/30', '1/60', '1/120', '1/240'))
    white_balance = random.choice(('Auto', 'Daylight', 'Cloudy'))
    stabilization = random.choice((
        'Standard Stabilization',
        'Cinematic Stabilization',
        'Action Mode',
    ))
    recording_format = f'{codec} {quality} {fps_label}'
    stamp = (
        f'[iPhone Camera] {profile["model"]} ({profile["identifier"]}) | '
        f'{quality} {width}x{height} | {recording_format} | '
        f'{profile["camera"]} | lens {profile["lens"]} | '
        f'aperture {profile["aperture"]} | '
        f'ISO {iso} | shutter {shutter} | WB {white_balance} | '
        f'{stabilization} | bitrate {bitrate} | {capture_time}'
    )
    details = (
        f"manufacturer=Apple; device={profile['model']}; "
        f"identifier={profile['identifier']}; os={profile['ios']}; "
        f"camera={profile['camera']}; lens={profile['lens']}; "
        f"aperture={profile['aperture']}; resolution={width}x{height}; "
        f"quality={quality}; fps={fps_label}; codec={codec}; "
        f"pixel_format={pixel_format}; bitrate={bitrate}; "
        f"audio={audio_codec} {audio_rate}Hz ch={audio_channels}; "
        f"duration={duration_label}; iso={iso}; shutter={shutter}; "
        f"white_balance={white_balance}; stabilization={stabilization}; "
        f"record_id={record_id}; "
        f"metadata_origin=synthetic-render-profile"
    )
    return {
        'profile': profile,
        'capture_time': capture_time,
        'record_id': record_id,
        'quality': quality,
        'stamp': stamp,
        'ffmpeg_args': [
            '-metadata', f'make=Apple',
            '-metadata', f'model={profile["model"]}',
            '-metadata', f'software={profile["ios"]}',
            '-metadata', f'creation_time={capture_time}',
            '-metadata', f'com.apple.quicktime.make=Apple',
            '-metadata', f'com.apple.quicktime.model={profile["model"]}',
            '-metadata', f'com.apple.quicktime.software={profile["ios"]}',
            '-metadata', f'com.apple.quicktime.creationdate={capture_time}',
            '-metadata', f'device_manufacturer=Apple',
            '-metadata', f'device_identifier={profile["identifier"]}',
            '-metadata', f'camera_name={profile["camera"]}',
            '-metadata', f'lens_specification={profile["lens"]}',
            '-metadata', f'aperture={profile["aperture"]}',
            '-metadata', f'recording_resolution={width}x{height}',
            '-metadata', f'recording_quality={quality}',
            '-metadata', f'recording_fps={fps_label}',
            '-metadata', f'video_codec={codec}',
            '-metadata', f'pixel_format={pixel_format}',
            '-metadata', f'video_bitrate={bitrate}',
            '-metadata', f'audio_codec={audio_codec}',
            '-metadata', f'audio_sample_rate={audio_rate} Hz',
            '-metadata', f'audio_channels={audio_channels}',
            '-metadata', f'recording_duration={duration_label}',
            '-metadata', f'iso={iso}',
            '-metadata', f'shutter_speed={shutter}',
            '-metadata', f'white_balance={white_balance}',
            '-metadata', f'image_stabilization={stabilization}',
            '-metadata', f'recording_format={recording_format}',
            '-metadata', f'record_id={record_id}',
            '-metadata', f'recording_stamp={stamp}',
            '-metadata', 'metadata_origin=synthetic-render-profile',
            '-metadata', f'recording_details={details}',
        ],
    }

# ═══════════════════════════════════════════════════════════════════════════
# VALIDASI FILE
# ═══════════════════════════════════════════════════════════════════════════
class FS:
    OK = "OK"; ZERO = "0KB"; CORRUPT = "CORRUPT"; NO_STREAM = "NOSTREAM"; SHORT = "SHORT"

def validate_video(path):
    path = Path(path)
    try:
        size = path.stat().st_size
    except:
        return FS.CORRUPT, "File tidak bisa dibaca"
    if size == 0:                      return FS.ZERO,      "File 0 byte"
    if size < MIN_FILE_BYTES:          return FS.ZERO,      f"Terlalu kecil ({size}B)"
    vi = probe_video(path)
    if not vi['has_video']:            return FS.NO_STREAM, "Tidak ada video stream"
    if vi['dur'] < MIN_DUR_SEC:        return FS.SHORT,     f"Durasi {vi['dur']:.2f}s"
    return FS.OK, f"{vi['codec']} {vi['w']}x{vi['h']} {vi['fps']}fps {fmt_t(vi['dur'])}"

def validate_audio(path):
    path = Path(path)
    try:
        size = path.stat().st_size
    except:
        return FS.CORRUPT, "File tidak bisa dibaca"
    if size == 0:                      return FS.ZERO,      "File 0 byte"
    if size < MIN_FILE_BYTES:          return FS.ZERO,      f"Terlalu kecil ({size}B)"
    ai = probe_audio(path)
    if not ai['has_audio']:            return FS.NO_STREAM, "Tidak ada audio stream"
    if ai['dur'] < MIN_DUR_SEC:        return FS.SHORT,     f"Durasi {ai['dur']:.2f}s"
    return FS.OK, f"{ai['codec']} {ai['sr']}Hz ch={ai['ch']} {fmt_t(ai['dur'])}"

# ═══════════════════════════════════════════════════════════════════════════
# SCAN + VALIDASI FOLDER
# ═══════════════════════════════════════════════════════════════════════════
def scan_and_validate(folder, exts, validator, label, emoji):
    folder = Path(folder)
    if not folder.exists():
        p_err(f"Folder tidak ditemukan: {folder}")
        return [], []

    all_files = sorted(
        [p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in exts]
    )

    p_sub(f"{emoji} {label}  ·  {folder.resolve()}  ·  {len(all_files)} file")

    valid = []; corrupt = []
    for i, f in enumerate(all_files, 1):
        mb            = f.stat().st_size / 1024 / 1024
        status, detail = validator(f)
        is_ok          = status == FS.OK

        tag_c = GR if is_ok else (YL if status == FS.SHORT else RD)
        tag   = f"{tag_c}{'  OK  ' if is_ok else f' {status:<6}'}{RS}"

        print(
            f"  {DM}{i:3d}.{RS}  [{tag}]  "
            f"{f.name:<48} {DM}{mb:6.1f} MB{RS}  "
            f"{tag_c}{DM}{detail[:55]}{RS}",
            flush=True)
        _wlog(f"  {i:3d}. [{status}]  {f.name}  {mb:.1f} MB  {detail}")

        if is_ok: valid.append(f)
        else:     corrupt.append((f, detail))

    print()
    p_inf(f"{label}: {GR}{BD}{len(valid)} valid{RS}  |  {RD}{len(corrupt)} dilewati{RS}")
    if corrupt:
        for f, r in corrupt:
            p_warn(f"  SKIP {f.name}  →  {r}")
    return valid, corrupt

# ═══════════════════════════════════════════════════════════════════════════
# ANTI-REPLACE OUTPUT NAME
# ═══════════════════════════════════════════════════════════════════════════
def safe_out_name(out_dir, audio_stem):
    """audioname.mp4 → audioname_.mp4 → audioname__.mp4 → dst"""
    out_dir = Path(out_dir)
    stem    = audio_stem
    while True:
        c = out_dir / f"{stem}.mp4"
        if not c.exists() or c.stat().st_size < OUTPUT_MIN_BYTES:
            return c
        stem += "_"

# ═══════════════════════════════════════════════════════════════════════════
# FFMPEG PROGRESS READER
# ═══════════════════════════════════════════════════════════════════════════
def _run_with_progress(cmd, target_dur=0):
    """
    Jalankan FFmpeg, tampilkan progress time=/speed=/size= tiap detik.
    target_dur = total durasi output (detik) untuk hitung persen.
    Raise CalledProcessError jika gagal.
    """
    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace'
    )

    last_print = [0.0]
    cur_sec    = [0.0]
    errs       = []

    for line in proc.stderr:
        errs.append(line)
        if 'time=' not in line and 'size=' not in line:
            continue

        now = time.time()
        if now - last_print[0] < 0.8:   # update max ~1.25×/detik
            continue
        last_print[0] = now

        m_time  = re.search(r'time=\s*(-?[\d:.]+)', line)
        m_speed = re.search(r'speed=\s*(\S+)',       line)
        m_size  = re.search(r'size=\s*(\S+)',         line)
        m_bits  = re.search(r'bitrate=\s*(\S+)',      line)

        if m_time:
            tok = m_time.group(1)
            if tok.startswith('-'):
                continue
            try:
                h, m2, s = tok.split(':')
                cur_sec[0] = int(h)*3600 + int(m2)*60 + float(s)
            except:
                pass

        parts = [f"  ⏱  {fmt_t(cur_sec[0])}"]
        if target_dur > 0 and cur_sec[0] > 0:
            pct = min(99.9, cur_sec[0] / target_dur * 100)
            bar_w = 20
            filled = int(bar_w * pct / 100)
            bar = f"[{'█'*filled}{'░'*(bar_w-filled)}]"
            parts.append(f"  {bar} {pct:5.1f}%")
        if m_speed:  parts.append(f"  🚀 {m_speed.group(1)}")
        if m_size:   parts.append(f"  💾 {m_size.group(1)}")
        if m_bits:   parts.append(f"  {m_bits.group(1)}")

        print(f"\r{''.join(parts):<90}", end='', flush=True)

    proc.wait()
    print()   # newline bersih

    if proc.returncode != 0:
        imp = [l for l in errs if any(k in l.lower()
               for k in ['error','invalid','failed','cannot','no such','unable'])]
        msg = ''.join(imp[-10:]) or ''.join(errs[-5:])
        raise subprocess.CalledProcessError(proc.returncode, cmd, stderr=msg)

# ═══════════════════════════════════════════════════════════════════════════
# DISK GUARD UNTUK TEMP FILE (dipakai sebelum & sesudah tahap berat)
# ═══════════════════════════════════════════════════════════════════════════
def check_disk_or_fail(path, disk_min_bytes, label=""):
    """Return (True, free) jika cukup, (False, free) jika kurang dari limit."""
    free = get_free_bytes(path)
    return free >= disk_min_bytes, free

# ═══════════════════════════════════════════════════════════════════════════
# MODE 1 — COPY  (contact-copy murni video + audio, TANPA re-encode)
# ═══════════════════════════════════════════════════════════════════════════
def render_copy(video_path, audio_path, out_path, tmp_dir,
                disk_min_bytes=DISK_MIN_BYTES, iphone_meta=True):
    vp = Path(video_path)
    ap = Path(audio_path)
    op = Path(out_path)
    cleanup = []

    p_sub('MODE COPY  |  video + audio CONTACT-COPY murni (no re-encode)')

    try:
        # ── Disk guard sebelum mulai ───────────────────────────
        ok_disk, free = check_disk_or_fail(tmp_dir, disk_min_bytes)
        if not ok_disk:
            return False, f'Disk tidak cukup ({fmt_gb(free)} < {fmt_gb(disk_min_bytes)}) — job dibatalkan'

        vi = probe_video(vp)
        ai = probe_audio(ap)
        if vi['dur'] <= 0: return False, "Durasi video 0"
        if ai['dur'] <= 0: return False, "Durasi audio 0"

        tdur   = ai['dur']                       # target = durasi audio
        vdur   = vi['dur']
        nl     = max(1, math.ceil(tdur / vdur))  # berapa kali video di-loop
        n_loop = nl - 1

        p_inf(f"Video  : {vp.name}  |  {vi['codec']} {vi['w']}x{vi['h']} {vi['fps']}fps  {fmt_t(vdur)}")
        p_inf(f"Audio  : {ap.name}  |  {ai['codec']} {ai['sr']}Hz  {fmt_t(tdur)}")
        p_inf(f"Loop   : {nl}×  (stream_loop={n_loop})  →  target {fmt_t(tdur)}")

        svp, vc = safe_cp(vp, tmp_dir, "cpv")
        sap, ac = safe_cp(ap, tmp_dir, "cpa")
        if vc: cleanup.append(svp)
        if ac: cleanup.append(sap)

        acodec   = (ai['codec'] or '').lower()
        use_copy = acodec in AUDIO_COPY_OK
        a_flags  = (['-c:a', 'copy'] if use_copy
                    else ['-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-ac', '2'])
        label    = 'audio copy (no re-encode)' if use_copy else f'audio fallback encode aac (codec {acodec} tak kompatibel)'
        metadata = (
            build_iphone_metadata(video_info=vi, audio_info=ai, source_path=vp)
            if iphone_meta else None
        )

        cmd = [
            'ffmpeg', '-y', '-hide_banner',
            '-stream_loop', str(n_loop),
            '-i', str(svp),
            '-i', str(sap),
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-c:v', 'copy',
            *a_flags,
            '-shortest',
            '-avoid_negative_ts', 'make_zero',
            '-movflags', '+faststart+use_metadata_tags',
            '-map_metadata', '0',
            '-map_chapters', '-1',
            *(metadata['ffmpeg_args'] if metadata else []),
            str(op)
        ]

        meta_label = (
            f"metadata={metadata['profile']['model']} / synthetic"
            if metadata else "metadata=source-preserved"
        )
        p_inf(f"[RENDER] Contact-copy  stream_loop={n_loop}  video=copy  {label}  {meta_label}  →  {fmt_t(tdur)}")
        t0 = time.time()
        _run_with_progress(cmd, target_dur=tdur)
        elapsed = time.time() - t0

        if not op.is_file() or op.stat().st_size < OUTPUT_MIN_BYTES:
            return False, f"Output kosong ({fmt_mb(op)})"

        ov = probe_video(op)
        oa = probe_audio(op)
        if not ov['has_video']: return False, "Output tidak punya video stream"
        if not oa['has_audio']: return False, "Output tidak punya audio stream"

        mb   = op.stat().st_size / 1024 / 1024
        info = (f"COPY | Loop {nl}× | {fmt_t(ov['dur'])} | "
                f"{ov['w']}x{ov['h']} | video=copy audio={'copy' if use_copy else 'aac'} | "
                f"metadata={'iphone-profile' if metadata else 'source'} | "
                f"{mb:.1f} MB | {elapsed:.0f}s")
        return True, info

    except subprocess.CalledProcessError as e:
        err = e.stderr[-400:] if e.stderr else ''
        return False, f"FFmpeg error: {err}"
    except Exception as e:
        return False, f"Exception: {e}\n{traceback.format_exc()[-400:]}"
    finally:
        for f in cleanup:
            try: Path(f).unlink(missing_ok=True)
            except: pass

# ═══════════════════════════════════════════════════════════════════════════
# MODE 2 — FAST  (video reencode cepat + turun kualitas → temp,
#                 lalu audio CONTACT-COPY tanpa re-encode ke video temp)
#
#   Step 1 : Loop+encode VIDEO-ONLY (tanpa audio) ke 1 file temp .ts,
#            turun resolusi/fps/bitrate, preset ultrafast → sangat cepat
#            karena hanya 1 pass video, tanpa sentuh audio sama sekali.
#   Step 2 : MUX video temp + AUDIO ASLI dengan CONTACT-COPY
#            (-c:a copy, TANPA re-encode audio) → mux ini stream-copy,
#            hampir instan. Fallback ke encode aac hanya jika codec
#            audio asli tidak kompatibel dengan container MP4.
#   Step 3 : Hapus temp video segera setelah mux (hemat disk + limit).
#
#   Kenapa video direncode dulu, baru audio di-mux?
#   → Video WAJIB diturunkan kualitasnya (resolusi/fps/bitrate),
#     sedangkan audio TIDAK perlu diubah → cukup stream copy.
#     Pisahkan 2 stage ini supaya audio tidak pernah ikut di-reencode.
# ═══════════════════════════════════════════════════════════════════════════
def render_fast(video_path, audio_path, out_path, tmp_dir,
                vbr=FAST_VBR, fps=FAST_FPS, scale=FAST_SCALE,
                preset=FAST_PRESET, maxrate=FAST_MAXRATE, bufsize=FAST_BUFSIZE,
                disk_min_bytes=DISK_MIN_BYTES, iphone_meta=True):
    vp  = Path(video_path)
    ap  = Path(audio_path)
    op  = Path(out_path)
    tmp = Path(tmp_dir)
    tmp.mkdir(parents=True, exist_ok=True)

    p_sub(f'MODE FAST  |  video reencode {vbr} fps={fps} scale≤{scale} {preset}  →  audio contact-copy')

    vi = probe_video(vp)
    ai = probe_audio(ap)
    if vi['dur'] <= 0: return False, 'Durasi video 0'
    if ai['dur'] <= 0: return False, 'Durasi audio 0'

    tdur   = ai['dur']                        # target = durasi audio
    vdur   = vi['dur']
    nl     = max(1, math.ceil(tdur / vdur))   # berapa kali video di-loop
    n_loop = nl - 1

    p_inf(f'Video  : {vp.name}  |  {vi["codec"]} {vi["w"]}x{vi["h"]} {vi["fps"]}fps  {fmt_t(vdur)}')
    p_inf(f'Audio  : {ap.name}  |  {ai["codec"]} {fmt_t(tdur)}  ← target durasi')
    p_inf(f'Loop   : {nl}×  (stream_loop={n_loop})  →  target {fmt_t(tdur)}')
    p_inf(f'Encode : {vbr}  fps={fps}  scale≤{scale}  preset={preset}  maxrate={maxrate}')

    rid      = random.getrandbits(24)
    vtemp_ts = tmp / f'dn_fast_v_{rid}.ts'   # temp VIDEO-ONLY
    cleanup  = [vtemp_ts]

    try:
        # ── Disk guard #1 — sebelum bikin temp video ──────────
        ok_disk, free = check_disk_or_fail(tmp_dir, disk_min_bytes)
        if not ok_disk:
            return False, f'Disk temp tidak cukup ({fmt_gb(free)} < {fmt_gb(disk_min_bytes)}) — job dibatalkan'

        # ── STEP 1: Encode VIDEO-ONLY ultrafast → temp .ts ────
        # .ts (MPEG-TS) = byte-stream, tidak butuh moov-atom di akhir,
        # jadi bisa langsung dipakai untuk mux tanpa proses tambahan.
        vf = (
            f"scale='min({scale},iw)':trunc(ow/a/2)*2:flags=fast_bilinear,"
            f"fps={fps},format=yuv420p"
        )
        svp, vc = safe_cp(vp, tmp_dir, "fsv")
        if vc: cleanup.append(svp)

        cmd_v = [
            'ffmpeg', '-y', '-hide_banner',
            '-stream_loop', str(n_loop),
            '-i', str(svp),
            '-an',                                 # video-only, audio menyusul di step 2
            '-t', f'{tdur:.3f}',
            '-c:v', 'libx264', '-preset', preset,
            '-b:v', vbr, '-maxrate', maxrate, '-bufsize', bufsize,
            '-vf', vf, '-g', '30', '-bf', '0',
            '-tune', 'fastdecode',
            '-x264-params', 'aq-mode=0',
            '-avoid_negative_ts', 'make_zero',
            '-f', 'mpegts', str(vtemp_ts),
        ]
        p_inf('[FAST 1/2]  Render video temp (turunkan resolusi/fps/bitrate, ultrafast)...')
        t_v = time.time()
        _run_with_progress(cmd_v, target_dur=tdur)

        if not vtemp_ts.exists() or vtemp_ts.stat().st_size < OUTPUT_MIN_BYTES:
            return False, f'Video temp kosong/gagal ({fmt_mb(vtemp_ts)})'
        sz_v = vtemp_ts.stat().st_size / 1024 / 1024
        p_ok(f'Video temp  {sz_v:.1f} MB  ({time.time()-t_v:.1f}s)')

        # ── Disk guard #2 — sebelum mux ke output final ───────
        check_path = out_path if Path(out_dir := str(op.parent)).exists() else tmp_dir
        ok_disk2, free2 = check_disk_or_fail(check_path, disk_min_bytes)
        if not ok_disk2:
            return False, f'Disk habis sebelum mux ({fmt_gb(free2)}) — output dibatalkan, temp dihapus'

        # ── STEP 2: MUX video temp + audio asli — CONTACT-COPY ─
        acodec = (ai['codec'] or '').lower()
        sap, ac = safe_cp(ap, tmp_dir, "fsa")
        if ac: cleanup.append(sap)

        use_copy = acodec in AUDIO_COPY_OK
        a_flags  = (['-c:a', 'copy'] if use_copy
                    else ['-c:a', 'aac', '-b:a', FAST_AUDIO_BR, '-ar', '44100', '-ac', '2'])
        label    = 'contact-copy (no re-encode)' if use_copy else f'fallback encode aac (codec {acodec} tak kompatibel mp4)'
        fast_width = min(scale, vi['w']) if vi.get('w') else 0
        fast_height = vi['h']
        if fast_width and vi.get('w') and vi.get('h'):
            fast_height = max(2, int(round(vi['h'] * fast_width / vi['w'] / 2) * 2))
        fast_video_info = {
            **vi,
            'codec': 'h264',
            'w': fast_width,
            'h': fast_height,
            'fps': fps,
            'pix_fmt': 'yuv420p',
            'bit_rate': vbr,
            'dur': tdur,
        }
        metadata = (
            build_iphone_metadata(
                video_info=fast_video_info,
                audio_info=ai,
                source_path=vp,
            )
            if iphone_meta else None
        )

        cmd_mux = [
            'ffmpeg', '-y', '-hide_banner',
            '-i', str(vtemp_ts),
            '-i', str(sap),
            # Input ketiga hanya dipakai sebagai sumber metadata. Tidak ada
            # stream dari input ini yang dipetakan ke output.
            *(['-i', str(svp)] if metadata else []),
            '-map', '0:v:0', '-map', '1:a:0',
            '-c:v', 'copy',
            *a_flags,
            '-t', f'{tdur:.3f}',
            '-shortest',
            '-avoid_negative_ts', 'make_zero',
            '-movflags', '+faststart+use_metadata_tags',
            *(['-map_metadata', '2'] if metadata else ['-map_metadata', '0']),
            '-map_chapters', '-1',
            *(metadata['ffmpeg_args'] if metadata else []),
            str(op),
        ]
        meta_label = (
            f"metadata={metadata['profile']['model']} / synthetic"
            if metadata else "metadata=source-preserved"
        )
        p_inf(f'[FAST 2/2]  Mux audio → {label}  {meta_label}...')
        t_m = time.time()
        _run_with_progress(cmd_mux, target_dur=tdur)

        if not op.exists() or op.stat().st_size < OUTPUT_MIN_BYTES:
            return False, f'Output final kosong ({fmt_mb(op)})'

        ov = probe_video(op)
        oa = probe_audio(op)
        if not ov['has_video']: return False, 'Output tidak punya video stream'
        if not oa['has_audio']: return False, 'Output tidak punya audio stream'

        mb      = op.stat().st_size / 1024 / 1024
        total_t = time.time() - t_v
        info = (f'FAST | Loop {nl}× | {fmt_t(ov["dur"])} | {ov["w"]}x{ov["h"]} | '
                f'{vbr} {fps}fps | audio={"copy" if use_copy else "aac"} | '
                f'metadata={"iphone-profile" if metadata else "source"} | '
                f'{mb:.1f} MB | {total_t:.0f}s')
        return True, info

    except subprocess.CalledProcessError as exc:
        err = exc.stderr[-400:] if exc.stderr else ''
        return False, f'FFmpeg error (rc={exc.returncode}): {err}'
    except Exception as exc:
        return False, f'FAST Exception: {exc}\n{traceback.format_exc()[-500:]}'

    finally:
        # ── CLEANUP cepat — hapus temp video segera (hemat disk) ──
        n_del = 0
        for f in cleanup:
            try:
                fp = Path(f)
                if fp.exists():
                    fp.unlink()
                    n_del += 1
            except Exception:
                pass
        if n_del:
            p_inf(f'[FAST] Cleanup: {n_del} temp file terhapus')

# ═══════════════════════════════════════════════════════════════════════════
# PAIRING LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def build_pairs(videos, audios):
    if len(audios) == 1:
        p_inf(f"Mode: FIXED — 1 audio untuk semua {len(videos)} video")
        return [(v, audios[0]) for v in videos]
    else:
        p_inf(f"Mode: RANDOM — {len(audios)} audio pool → {len(videos)} video")
        return [(v, random.choice(audios)) for v in videos]

# ═══════════════════════════════════════════════════════════════════════════
# BULK RENDER
# ═══════════════════════════════════════════════════════════════════════════
def bulk_render(pairs, out_dir, tmp_dir, mode, dry_run=False,
                fast_vbr=FAST_VBR, fast_fps=FAST_FPS, fast_scale=FAST_SCALE,
                fast_preset=FAST_PRESET, fast_maxrate=FAST_MAXRATE, fast_bufsize=FAST_BUFSIZE,
                disk_min_bytes=DISK_MIN_BYTES, iphone_meta=True):
    total   = len(pairs)
    results = {'ok': [], 'skip': [], 'fail': []}
    t_start = time.time()

    p_hdr(f"BULK RENDER  {total} job  |  mode={mode}  |  disk-limit={fmt_gb(disk_min_bytes)}")
    p_inf(f"Output dir : {Path(out_dir).resolve()}")
    if mode == 'fast':
        p_inf(f"Mode       : {MG}FAST{RS}  video-reencode {fast_vbr} fps={fast_fps} scale≤{fast_scale} {fast_preset}  →  audio contact-copy")
    else:
        p_inf(f"Mode       : {CY}COPY{RS}  {'DRY RUN' if dry_run else 'video+audio contact-copy murni (no re-encode)'}")
    p_inf(f"Metadata   : {'profil iPhone sintetis acak' if iphone_meta else 'metadata sumber dipertahankan'}")

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    for idx, (vpath, apath) in enumerate(pairs, 1):
        out_path = safe_out_name(out_dir, apath.stem)

        p_hdr(f"[{idx}/{total}]  {vpath.name}")
        p_inf(f"Audio  : {apath.name}")
        p_inf(f"Output : {out_path.name}")

        if dry_run:
            p_skip("DRY RUN — tidak render")
            results['skip'].append({'v':vpath,'a':apath,'o':out_path,'reason':'dry-run'})
            continue

        # ── Cek disk sebelum render — pause jika sisa < limit ──
        free_before = get_free_bytes(out_dir)
        p_inf(f"Sisa disk  : {fmt_gb(free_before)}")
        try:
            lanjut = disk_pause_if_needed(out_dir, idx, total, disk_min_bytes)
        except KeyboardInterrupt:
            print(f"\n{RD}Render dihentikan (disk penuh, user batalkan).{RS}")
            break   # keluar loop, tampilkan ringkasan

        if not lanjut:
            results['skip'].append({'v':vpath,'a':apath,'o':out_path,'reason':'disk-penuh-skip'})
            continue

        t0 = time.time()
        if mode == 'fast':
            ok_flag, info = render_fast(
                video_path=vpath, audio_path=apath, out_path=out_path,
                tmp_dir=tmp_dir,
                vbr=fast_vbr, fps=fast_fps, scale=fast_scale,
                preset=fast_preset, maxrate=fast_maxrate, bufsize=fast_bufsize,
                disk_min_bytes=disk_min_bytes, iphone_meta=iphone_meta)
        else:
            ok_flag, info = render_copy(
                video_path=vpath, audio_path=apath, out_path=out_path,
                tmp_dir=tmp_dir, disk_min_bytes=disk_min_bytes, iphone_meta=iphone_meta)
        elapsed = time.time() - t0

        if ok_flag:
            p_ok(f"SELESAI  {info}")
            results['ok'].append({'v':vpath,'a':apath,'o':out_path,'info':info,'t':elapsed})
        else:
            p_err(f"GAGAL  →  {info}")
            results['fail'].append({'v':vpath,'a':apath,'o':out_path,'info':info})

        time.sleep(0.15)

    # ── Ringkasan ─────────────────────────────────────────────
    total_time = time.time() - t_start
    p_hdr("RINGKASAN AKHIR")
    n_ok = len(results['ok']); n_skip = len(results['skip']); n_fail = len(results['fail'])
    n_disk_skip = sum(1 for r in results['skip'] if r.get('reason') == 'disk-penuh-skip')
    print(f"  {BD}{GR}✔ Berhasil  : {n_ok:3d}{RS}")
    print(f"  {BD}{DM}→ Skip      : {n_skip:3d}{RS}", end='')
    if n_disk_skip:
        print(f"  {YL}(termasuk {n_disk_skip} skip karena disk penuh){RS}", end='')
    print()
    print(f"  {BD}{RD}✘ Gagal     : {n_fail:3d}{RS}")
    print(f"  Total waktu : {fmt_t(total_time)}")
    print(f"  Output dir  : {Path(out_dir).resolve()}\n")
    _wlog(f"[RINGKASAN] OK={n_ok} SKIP={n_skip} FAIL={n_fail} TIME={fmt_t(total_time)}")

    if results['ok']:
        print(f"{BD}{GR}  FILE OUTPUT:{RS}")
        for r in results['ok']:
            print(f"    {GR}✔{RS}  {r['o'].name:<52} {DM}{fmt_mb(r['o'])}  {r['t']:.0f}s{RS}")
            _wlog(f"  OK  {r['o'].name}  {fmt_mb(r['o'])}")

    if results['fail']:
        print(f"\n{BD}{RD}  GAGAL:{RS}")
        for r in results['fail']:
            print(f"    {RD}✘{RS}  {r['v'].name} + {r['a'].name}")
            print(f"       {DM}{r['info'][:150]}{RS}")
            _wlog(f"  FAIL  {r['v'].name} + {r['a'].name}  →  {r['info'][:150]}")

    return n_fail == 0

# ═══════════════════════════════════════════════════════════════════════════
# ARGPARSE
# ═══════════════════════════════════════════════════════════════════════════
def get_args():
    p = argparse.ArgumentParser(
        prog='dapur_ngebul_cli',
        description='🔥 Dapur Ngebul CLI v6 — 2-Mode Bulk Render (COPY / FAST)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output nama  = nama AUDIO + .mp4
Anti-replace : lagu.mp4 → lagu_.mp4 → lagu__.mp4 ...
1 audio      → semua video pakai audio itu (fixed)
N audio      → tiap video audio random dari pool

Mode:
  copy  → video+audio contact-copy murni, TANPA re-encode (tercepat, ukuran ≈ asli)
  fast  → video reencode cepat (turun kualitas) ke temp, lalu audio contact-copy (no re-encode)
  metadata → default menambahkan profil iPhone sintetis acak saat mux

Contoh:
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --mode copy
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --mode fast
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --mode fast --fast-vbr 100k --fast-fps 10
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --list
  python dapur_ngebul_cli.py --video-dir ./videos --audio-dir ./audios --dry-run
        """
    )
    p.add_argument('--video-dir',  default=None)
    p.add_argument('--audio-dir',  default=None)
    p.add_argument('--output-dir', default=None)
    p.add_argument('--tmp-dir',    default='/home/runner/workspace/tmp_render')
    p.add_argument('--seed',       type=int, default=None)
    p.add_argument('--list',       action='store_true')
    p.add_argument('--dry-run',    action='store_true')
    p.add_argument('--no-log',     action='store_true')
    p.add_argument('--no-iphone-meta', dest='iphone_meta', action='store_false',
                   default=True,
                   help='Jangan tambahkan profil metadata iPhone sintetis; pertahankan metadata sumber')

    p.add_argument('--mode', choices=['copy', 'fast'], default=None,
                   help="Mode render: 'copy' (contact-copy murni, no re-encode) atau "
                        "'fast' (reencode video cepat + audio contact-copy)")

    p.add_argument('--fast-vbr',     default=FAST_VBR,
                   help=f'Bitrate video mode FAST (default {FAST_VBR})')
    p.add_argument('--fast-fps',     type=int, default=FAST_FPS,
                   help=f'FPS output mode FAST (default {FAST_FPS})')
    p.add_argument('--fast-scale',   type=int, default=FAST_SCALE,
                   help=f'Lebar max output mode FAST dalam px (default {FAST_SCALE})')
    p.add_argument('--fast-preset',  default=FAST_PRESET,
                   choices=['ultrafast','superfast','veryfast','faster','fast'],
                   help=f'Preset encode mode FAST (default {FAST_PRESET})')
    p.add_argument('--fast-maxrate', default=FAST_MAXRATE,
                   help=f'Maxrate burst mode FAST (default {FAST_MAXRATE})')
    p.add_argument('--fast-bufsize', default=FAST_BUFSIZE,
                   help=f'Bufsize mode FAST (default {FAST_BUFSIZE})')

    p.add_argument('--disk-min-gb', type=float, default=DISK_MIN_BYTES / 1024**3,
                   help=f'Batas minimum sisa disk dalam GB sebelum render berhenti/pause (default {DISK_MIN_BYTES/1024**3:.0f} GB)')
    return p.parse_args()

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    global _log_file
    args = get_args()

    print(f"""
{BD}{CY}╔══════════════════════════════════════════════════════════════╗
║   DAPUR NGEBUL CLI  🔥  v6.0  2-Mode: COPY / FAST            ║
║   Contact-copy murni · reencode cepat · disk guard           ║
╚══════════════════════════════════════════════════════════════╝{RS}
""", flush=True)

    # ── Input interaktif ──────────────────────────────────────
    video_dir = args.video_dir or input(f"{YL}Path folder VIDEO  : {RS}").strip().strip('"\'')
    audio_dir = args.audio_dir or input(f"{YL}Path folder AUDIO  : {RS}").strip().strip('"\'')
    if not args.output_dir:
        default = "/home/runner/workspace/hasil_render"
        inp = input(f"{YL}Folder output [{default}]  : {RS}").strip().strip('"\'')
        out_dir = inp if inp else default
    else:
        out_dir = args.output_dir

    # ── Log file ──────────────────────────────────────────────
    if not args.no_log:
        log_name = f"render_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            _log_file = open(log_name, 'w', encoding='utf-8')
            print(f"{DM}Log  : {log_name}{RS}\n", flush=True)
        except:
            _log_file = None

    if args.seed is not None:
        random.seed(args.seed)

    disk_min_bytes = max(0, int(args.disk_min_gb * 1024 ** 3))
    p_inf(f"Limit disk : {BD}{fmt_gb(disk_min_bytes)}{RS}  (render berhenti/pause jika sisa di bawah ini)")
    p_inf(f"Metadata   : {'profil iPhone sintetis acak' if args.iphone_meta else 'metadata sumber dipertahankan'}")

    # ── Pilih mode — interaktif jika tidak dari argumen ───────
    mode = args.mode
    fast_vbr, fast_fps, fast_scale = args.fast_vbr, args.fast_fps, args.fast_scale
    fast_preset, fast_maxrate, fast_bufsize = args.fast_preset, args.fast_maxrate, args.fast_bufsize

    if not mode and not args.dry_run:
        print()
        print(f"  {BD}Pilih mode render:{RS}")
        print(f"  {GR}[1]{RS}  COPY  — video+audio CONTACT-COPY murni, {BD}TANPA re-encode{RS} sama sekali.")
        print(f"             Tercepat, ukuran ≈ file asli. Disertai limit disk space.")
        print(f"  {MG}[2]{RS}  FAST  — video di-{BD}REENCODE CEPAT{RS} (turun resolusi/fps/bitrate, ultrafast)")
        print(f"             ditulis ke video temp, lalu audio di-CONTACT-COPY (no re-encode)")
        print(f"             ke video temp itu. Hemat disk, disertai limit disk space.")
        print()
        try:
            mc = input(f"  Mode [1/2] (default=1): ").strip()
        except (EOFError, KeyboardInterrupt):
            mc = '1'
        if mc == '2':
            mode = 'fast'
            try:
                vbr_in = input(f"  Bitrate video FAST [{fast_vbr}]: ").strip()
                if vbr_in: fast_vbr = vbr_in
                fps_in = input(f"  FPS FAST [{fast_fps}]: ").strip()
                if fps_in.isdigit(): fast_fps = int(fps_in)
            except (EOFError, KeyboardInterrupt):
                pass
            p_inf(f"{MG}Mode FAST dipilih{RS} — reencode {fast_vbr} fps={fast_fps} scale≤{fast_scale} {fast_preset}, audio contact-copy")
        else:
            mode = 'copy'
            p_inf("Mode COPY dipilih — video+audio contact-copy murni, tanpa re-encode")
    elif not mode:
        mode = 'copy'   # default untuk dry-run preview
    print()

    # ── Scan & validasi ───────────────────────────────────────
    p_hdr("SCAN & VALIDASI")
    valid_videos, bad_v = scan_and_validate(video_dir, VIDEO_EXTS, validate_video, "VIDEO", "📹")
    valid_audios, bad_a = scan_and_validate(audio_dir, AUDIO_EXTS, validate_audio, "AUDIO", "🎵")

    if not valid_videos:
        p_err(f"Tidak ada video valid di: {video_dir}"); sys.exit(1)
    if not valid_audios:
        p_err(f"Tidak ada audio valid di: {audio_dir}"); sys.exit(1)

    if args.list:
        print(f"\n{DM}(--list: selesai, tidak render){RS}\n")
        if _log_file: _log_file.close()
        sys.exit(0)

    # ── Pairing ───────────────────────────────────────────────
    pairs = build_pairs(valid_videos, valid_audios)

    p_hdr(f"PREVIEW  {len(pairs)} job")
    for i, (vp, ap) in enumerate(pairs, 1):
        print(
            f"  {DM}{i:3d}.{RS}  "
            f"{CY}{vp.name:<42}{RS}  ×  "
            f"{MG}{ap.name:<38}{RS}  →  "
            f"{GR}{ap.stem}.mp4{RS}",
            flush=True)
        _wlog(f"  {i:3d}. {vp.name} × {ap.name} → {ap.stem}.mp4")

    # ── Konfirmasi ────────────────────────────────────────────
    if not args.dry_run:
        if bad_v or bad_a:
            p_warn(f"{len(bad_v)} video + {len(bad_a)} audio corrupt → DILEWATI otomatis")
        print()
        try:
            c = input(f"{BD}{YL}Mulai render {len(pairs)} job  [mode={mode}]? [Y/n]: {RS}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            c = 'y'
        if c not in ('', 'y', 'yes'):
            print("Dibatalkan."); sys.exit(0)

    # ── Bulk render ───────────────────────────────────────────
    try:
        success = bulk_render(
            pairs=pairs, out_dir=out_dir, tmp_dir=args.tmp_dir, mode=mode,
            dry_run=args.dry_run,
            fast_vbr=fast_vbr, fast_fps=fast_fps, fast_scale=fast_scale,
            fast_preset=fast_preset, fast_maxrate=fast_maxrate, fast_bufsize=fast_bufsize,
            disk_min_bytes=disk_min_bytes, iphone_meta=args.iphone_meta)
    except KeyboardInterrupt:
        print(f"\n{RD}Dihentikan (Ctrl+C).{RS}")
        success = False
    finally:
        try:
            tmp = Path(args.tmp_dir)
            if tmp.exists():
                for f in tmp.glob("dn_*"):
                    try: f.unlink(missing_ok=True)
                    except: pass
        except: pass
        if _log_file:
            try: _log_file.close()
            except: pass

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
