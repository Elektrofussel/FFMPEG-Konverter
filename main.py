import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QThread, Qt, Signal, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QInputDialog,
    QDialog,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_TITLE = "FFmpeg Konverter"
LANGUAGE_OPTIONS = [("English", "en"), ("Deutsch", "de")]
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".ts",
    ".m2ts",
    ".mts",
    ".3gp",
    ".mpg",
    ".mpeg",
    ".vob",
}


def resolve_config_file() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata) / "FFmpeg-Konverter"
    else:
        base = Path.home() / ".ffmpeg-konverter"
    return base / "config.json"


CONFIG_FILE = resolve_config_file()

PRESETS = {
    "MP4 schnell klein (GPU HEVC)": {
        "export_mode": "Video + Audio",
        "container": "mp4",
        "video_encoder": "hevc_amf",
        "audio_codec": "aac stereo",
        "quality": "Schnell",
        "auto_bitrate": True,
        "amf_quality": "speed",
    },
    "MKV beste Qualität (GPU HEVC + Audio Copy)": {
        "export_mode": "Video + Audio",
        "container": "mkv",
        "video_encoder": "hevc_amf",
        "audio_codec": "copy",
        "quality": "Beste Qualität",
        "auto_bitrate": True,
        "amf_quality": "quality",
    },
    "MP4 beste CPU Qualität (x264 CRF16)": {
        "export_mode": "Video + Audio",
        "container": "mp4",
        "video_encoder": "libx264",
        "audio_codec": "aac 320k stereo",
        "quality": "Beste Qualität",
        "auto_bitrate": False,
        "video_preset_override": "slow",
        "video_crf_override": 16,
    },
    "MKV Archiv (x265 CRF18)": {
        "export_mode": "Video + Audio",
        "container": "mkv",
        "video_encoder": "libx265",
        "audio_codec": "copy",
        "quality": "Beste Qualität",
        "auto_bitrate": False,
        "video_preset_override": "slow",
        "video_crf_override": 18,
    },
    "MKV kompatibel (CPU x264 + AAC Stereo)": {
        "export_mode": "Video + Audio",
        "container": "mkv",
        "video_encoder": "libx264",
        "audio_codec": "aac stereo",
        "quality": "Gut",
        "auto_bitrate": False,
        "video_preset_override": "medium",
        "video_crf_override": 20,
    },
    "Audio Podcast (MP3 192k)": {
        "export_mode": "Nur Audio",
        "container": "mp3",
        "video_encoder": "libx264",
        "audio_codec": "mp3",
        "quality": "Gut",
        "auto_bitrate": False,
    },
    "Audio Master (WAV PCM)": {
        "export_mode": "Nur Audio",
        "container": "wav",
        "video_encoder": "libx264",
        "audio_codec": "wav pcm_s16le",
        "quality": "Beste Qualität",
        "auto_bitrate": False,
    },
    "Audio Archiv (FLAC)": {
        "export_mode": "Nur Audio",
        "container": "flac",
        "video_encoder": "libx264",
        "audio_codec": "flac",
        "quality": "Beste Qualität",
        "auto_bitrate": False,
    },
    "Nur Video Web (MP4 H.264)": {
        "export_mode": "Nur Video",
        "container": "mp4",
        "video_encoder": "libx264",
        "audio_codec": "aac stereo",
        "quality": "Gut",
        "auto_bitrate": False,
        "video_preset_override": "medium",
        "video_crf_override": 20,
    },
    "Nur Video Archiv (MKV x265)": {
        "export_mode": "Nur Video",
        "container": "mkv",
        "video_encoder": "libx265",
        "audio_codec": "copy",
        "quality": "Beste Qualität",
        "auto_bitrate": False,
        "video_preset_override": "slow",
        "video_crf_override": 18,
    },
}

WIZARD_PREFERENCE_KEYS = [
    "best_quality",
    "smallest_size",
    "fastest",
    "balanced",
    "archive",
    "audio_podcast_mp3",
    "audio_master_wav",
    "audio_archive_flac",
    "video_web_mp4",
    "video_archive_mkv",
]

EXPORT_MODES = ["Video + Audio", "Nur Audio", "Nur Video"]
DEVICE_PROFILES = ["Allgemein", "Smartphone", "TV", "YouTube", "Archiv"]
DEVICE_PROFILE_KEYS = ["Allgemein", "Smartphone", "TV", "YouTube", "Archiv"]
EXPORT_MODE_KEYS = ["Video + Audio", "Nur Audio", "Nur Video"]
QUALITY_KEYS = ["Schnell", "Gut", "Beste Qualität", "Klein"]
CONFLICT_KEYS = ["Nummerieren", "Überspringen", "Überschreiben"]

VIDEO_FORMAT_PROFILES = {
    "mp4": {"label": "MP4", "help": "Sehr kompatibel (Web, Mobil, TVs). Opus ist in MP4 nicht empfohlen/zulässig."},
    "mov": {"label": "MOV", "help": "Apple-/Schnitt-orientiertes Containerformat."},
    "avi": {"label": "AVI", "help": "Älteres Containerformat, oft größer und weniger modern."},
    "asf": {"label": "WMV/ASF", "help": "Microsoft-Container (z. B. WMV)." },
    "flv": {"label": "FLV", "help": "Legacy-Webformat, heute selten, aber weiterhin nutzbar."},
    "mkv": {"label": "MKV", "help": "Sehr flexibel, gut für Archiv und komplexe Streams."},
    "webm": {"label": "WebM/HTML5", "help": "Web-orientiert, ideal für HTML5-Playback."},
    "mpg": {"label": "MPEG-2", "help": "Klassisch für ältere Workflows/Player."},
}

AUDIO_FORMAT_PROFILES = {
    "mp3": {"label": "MP3", "help": "Maximal kompatibel, verlustbehaftet."},
    "wav": {"label": "WAV", "help": "Unkomprimiert/PCM, große Dateien."},
    "flac": {"label": "FLAC", "help": "Verlustfrei, deutlich kleiner als WAV."},
    "m4a": {"label": "M4A (AAC)", "help": "AAC-Audio im MP4-Audiocontainer."},
    "aac": {"label": "AAC", "help": "Roh-AAC-Container."},
    "opus": {"label": "Opus", "help": "Sehr effizient bei geringer Bitrate."},
    "wma": {"label": "WMA", "help": "Microsoft Audio (ASF-basiert)."},
}

VIDEO_ENCODERS = [
    "libx264",
    "libx265",
    "h264_nvenc",
    "hevc_nvenc",
    "h264_amf",
    "hevc_amf",
    "h264_qsv",
    "hevc_qsv",
    "libvpx",
    "libvpx-vp9",
    "mpeg2video",
    "wmv2",
]
AUDIO_CODECS = ["copy", "aac stereo", "aac 320k stereo", "aac 5.1", "opus", "mp3", "flac", "wav pcm_s16le", "wma"]
QUALITY_LEVELS = ["Schnell", "Gut", "Beste Qualität", "Klein"]
AMF_QUALITY_LEVELS = ["speed", "quality"]

VIDEO_ENCODERS_BY_FORMAT = {
    "mp4": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv"],
    "mov": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv"],
    "avi": ["libx264", "mpeg2video", "wmv2"],
    "asf": ["wmv2", "libx264"],
    "flv": ["libx264", "libx265"],
    "mkv": ["libx264", "libx265", "h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv", "libvpx", "libvpx-vp9"],
    "webm": ["libvpx", "libvpx-vp9"],
    "mpg": ["mpeg2video"],
}


@dataclass
class VideoEntry:
    source_path: Path
    relative_path: Path
    duration: float
    video_codec: str
    width: int
    height: int
    resolution: str
    fps: float
    bitrate_kbps: int
    audio_codec: str
    audio_channels: int


class ConfigManager:
    defaults = {
        "source_dir": "",
        "target_dir": "",
        "recursive": True,
        "max_jobs": 1,
        "preset": "MP4 schnell klein (GPU HEVC)",
        "export_mode": "Video + Audio",
        "container": "mp4",
        "video_encoder": "libx264",
        "audio_codec": "aac stereo",
        "quality": "Gut",
        "amf_quality": "quality",
        "amf_bitrate_k": 8000,
        "amf_maxrate_k": 12000,
        "amf_bufsize_k": 16000,
        "auto_bitrate": False,
        "filter_name": "",
        "filter_ext": "*",
        "only_visible_selection": True,
        "overwrite_existing": False,
        "conflict_policy": "Nummerieren",
        "name_prefix": "",
        "name_suffix": "",
        "name_timestamp": False,
        "mirror_subfolders": True,
        "test_run_30s": False,
        "custom_presets": {},
        "custom_templates": {},
        "enable_hw_auto_profile": False,
        "enable_job_report": False,
        "enable_dragdrop": False,
        "enable_analysis_export": False,
        "strict_target_protection": False,
        "device_profile": "Allgemein",
        "show_favorite_presets_only": False,
        "favorite_presets": [],
        "only_changed_since_last_run": False,
        "last_run_mtimes": {},
        "generated_auto_preset_names": [],
        "language": "en",
    }

    def __init__(self, path: Path):
        self.path = path
        self._migrate_legacy_config_if_needed()

    def _legacy_candidates(self) -> List[Path]:
        candidates = []
        try:
            candidates.append(Path(__file__).resolve().parent / "config.json")
        except Exception:
            pass
        if getattr(sys, "frozen", False):
            try:
                candidates.append(Path(sys.executable).resolve().parent / "config.json")
            except Exception:
                pass
        return candidates

    def _migrate_legacy_config_if_needed(self) -> None:
        if self.path.exists():
            return
        for candidate in self._legacy_candidates():
            if candidate.exists():
                try:
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    self.path.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
                    break
                except Exception:
                    continue

    def load(self) -> Dict:
        if not self.path.exists():
            return dict(self.defaults)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            merged = dict(self.defaults)
            merged.update(data)
            return merged
        except Exception:
            return dict(self.defaults)

    def save(self, data: Dict) -> None:
        merged = dict(self.defaults)
        merged.update(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_fraction(value: str) -> float:
    try:
        if not value or value == "0/0":
            return 0.0
        return float(Fraction(value))
    except Exception:
        return 0.0


def bitrate_profile_for_resolution(width: int, height: int) -> Tuple[int, int, int]:
    if width <= 720 and height <= 400:
        bitrate_k = 2800
    elif width <= 1280 and height <= 720:
        bitrate_k = 6000
    elif width >= 1920 or height >= 1080:
        bitrate_k = 9000
    else:
        bitrate_k = 7500
    maxrate_k = int(round(bitrate_k * 1.5))
    bufsize_k = bitrate_k * 2
    return bitrate_k, maxrate_k, bufsize_k


def ffprobe_analyze(ffprobe_path: str, file_path: Path) -> VideoEntry:
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(file_path),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    fmt = payload.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)
    resolution = f"{width}x{height}" if width and height else "?"

    duration = 0.0
    try:
        duration = float(fmt.get("duration", 0.0))
    except Exception:
        duration = 0.0

    bitrate_kbps = 0
    try:
        bitrate_kbps = int(int(fmt.get("bit_rate", 0)) / 1000)
    except Exception:
        bitrate_kbps = 0

    return VideoEntry(
        source_path=file_path,
        relative_path=Path(file_path.name),
        duration=duration,
        video_codec=video_stream.get("codec_name", "?"),
        width=int(width) if width else 0,
        height=int(height) if height else 0,
        resolution=resolution,
        fps=parse_fraction(video_stream.get("avg_frame_rate", "0/0")),
        bitrate_kbps=bitrate_kbps,
        audio_codec=audio_stream.get("codec_name", "-"),
        audio_channels=int(audio_stream.get("channels", 0)) if audio_stream.get("channels") else 0,
    )


def duration_to_text(seconds: float) -> str:
    total = int(seconds or 0)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02}:{m:02}:{s:02}"


def find_binaries() -> Tuple[Optional[str], Optional[str]]:
    local_ffmpeg = Path(__file__).resolve().parent / "ffmpeg.exe"
    local_ffprobe = Path(__file__).resolve().parent / "ffprobe.exe"

    ffmpeg_path = str(local_ffmpeg) if local_ffmpeg.exists() else shutil.which("ffmpeg")
    ffprobe_path = str(local_ffprobe) if local_ffprobe.exists() else shutil.which("ffprobe")
    return ffmpeg_path, ffprobe_path


class ScanWorker(QObject):
    progress = Signal(str)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, source_dir: Path, recursive: bool, ffprobe_path: str):
        super().__init__()
        self.source_dir = source_dir
        self.recursive = recursive
        self.ffprobe_path = ffprobe_path

    def run(self) -> None:
        try:
            file_iter = self.source_dir.rglob("*") if self.recursive else self.source_dir.glob("*")
            files = [p for p in file_iter if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
            self.progress.emit(f"{len(files)} Video-Datei(en) gefunden.")
            entries = []
            for index, file_path in enumerate(files, start=1):
                try:
                    entry = ffprobe_analyze(self.ffprobe_path, file_path)
                    entry.relative_path = file_path.relative_to(self.source_dir)
                    entries.append(entry)
                    self.progress.emit(f"Analyse {index}/{len(files)}: {file_path.name}")
                except subprocess.CalledProcessError as exc:
                    err = (exc.stderr or exc.stdout or "Unbekannter ffprobe-Fehler").strip()
                    self.progress.emit(f"Fehler bei Analyse ({file_path.name}): {err}")
                except Exception as exc:
                    self.progress.emit(f"Fehler bei Analyse ({file_path.name}): {exc}")
            self.finished.emit(entries)
        except Exception as exc:
            self.failed.emit(str(exc))


class ConvertWorker(QObject):
    log = Signal(str)
    file_started = Signal(int)
    file_progress = Signal(int, float)
    file_metrics = Signal(int, str, str, str)
    file_finished = Signal(int, bool, str)
    all_finished = Signal()

    def __init__(
        self,
        entries: List[VideoEntry],
        selected_rows: List[int],
        source_dir: Path,
        target_dir: Path,
        ffmpeg_path: str,
        options: Dict,
        max_jobs: int,
    ):
        super().__init__()
        self.entries = entries
        self.selected_rows = selected_rows
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.ffmpeg_path = ffmpeg_path
        self.options = options
        self.max_jobs = max(1, min(3, max_jobs))
        self._stop_requested = False
        self._paused = False
        self._process_lock = threading.Lock()
        self._running_processes: Dict[int, subprocess.Popen] = {}

    def set_paused(self, paused: bool) -> None:
        self._paused = bool(paused)
        state = "PAUSIERT" if self._paused else "FORTGESETZT"
        self.log.emit(f"[Queue] {state}")

    def stop(self) -> None:
        self._stop_requested = True
        with self._process_lock:
            processes = list(self._running_processes.items())

        def _force_stop(row_index: int, proc: subprocess.Popen) -> None:
            try:
                proc.wait(timeout=2.0)
            except Exception:
                try:
                    if proc.poll() is None:
                        proc.kill()
                        self.log.emit(f"[Stop] Prozess hart beendet: {self.entries[row_index].source_path.name}")
                except Exception as exc:
                    self.log.emit(f"[Warnung] Hard-Stop fehlgeschlagen ({self.entries[row_index].source_path.name}): {exc}")

        for row_index, proc in processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    self.log.emit(f"[Stop] Prozess beendet: {self.entries[row_index].source_path.name}")
                    threading.Thread(target=_force_stop, args=(row_index, proc), daemon=True).start()
            except Exception as exc:
                self.log.emit(f"[Warnung] Stop fehlgeschlagen ({self.entries[row_index].source_path.name}): {exc}")

    def run(self) -> None:
        threads = []
        sem = threading.Semaphore(self.max_jobs)

        def task(row_index: int) -> None:
            with sem:
                if self._stop_requested:
                    self.file_finished.emit(row_index, False, "Abgebrochen")
                    return
                while self._paused and not self._stop_requested:
                    time.sleep(0.2)
                if self._stop_requested:
                    self.file_finished.emit(row_index, False, "Abgebrochen")
                    return
                self.file_started.emit(row_index)
                try:
                    self._convert_one(row_index)
                except Exception as exc:
                    self.log.emit(f"[Fehler] {self.entries[row_index].source_path.name}: {exc}")
                    self.file_finished.emit(row_index, False, str(exc))

        for row in self.selected_rows:
            th = threading.Thread(target=task, args=(row,), daemon=True)
            threads.append(th)
            th.start()

        for th in threads:
            th.join()

        self.all_finished.emit()

    def _quality_params(self, encoder: str, quality: str) -> List[str]:
        override_preset = self.options.get("video_preset_override")
        override_crf = self.options.get("video_crf_override")
        if encoder in {"libx264", "libx265"}:
            if override_preset and override_crf is not None:
                return ["-preset", str(override_preset), "-crf", str(override_crf)]
            x_map = {
                "Schnell": ("veryfast", "28"),
                "Gut": ("medium", "23"),
                "Beste Qualität": ("slow", "18"),
                "Klein": ("slow", "30"),
            }
            preset, crf = x_map.get(quality, ("medium", "23"))
            return ["-preset", preset, "-crf", crf]

        if encoder in {"h264_nvenc", "hevc_nvenc"}:
            nv_map = {
                "Schnell": "p1",
                "Gut": "p4",
                "Beste Qualität": "p7",
                "Klein": "p5",
            }
            preset = nv_map.get(quality, "p4")
            return ["-preset", preset]

        if encoder in {"h264_qsv", "hevc_qsv"}:
            q_map = {
                "Schnell": "32",
                "Gut": "26",
                "Beste Qualität": "20",
                "Klein": "34",
            }
            gq = q_map.get(quality, "26")
            return ["-global_quality", gq]

        return []

    def _nvenc_cq_params(self, quality: str) -> List[str]:
        cq_map = {
            "Schnell": "30",
            "Gut": "24",
            "Beste Qualität": "18",
            "Klein": "32",
        }
        cq = cq_map.get(quality, "24")
        return ["-rc", "vbr", "-cq", cq, "-b:v", "0"]

    def _dynamic_rate_params(self, entry: VideoEntry) -> List[str]:
        bitrate_k, maxrate_k, bufsize_k = bitrate_profile_for_resolution(entry.width, entry.height)
        return ["-b:v", f"{bitrate_k}k", "-maxrate", f"{maxrate_k}k", "-bufsize", f"{bufsize_k}k"]

    def _amf_quality_from_ui_quality(self, quality: str) -> str:
        if quality == "Schnell":
            return "speed"
        return "quality"

    def _amf_params(self, ui_quality: str, entry: VideoEntry, auto_bitrate: bool) -> List[str]:
        amf_quality = self.options.get("amf_quality", "") or self._amf_quality_from_ui_quality(ui_quality)
        if amf_quality not in {"speed", "quality"}:
            amf_quality = self._amf_quality_from_ui_quality(ui_quality)
        if auto_bitrate:
            bitrate_k, maxrate_k, bufsize_k = bitrate_profile_for_resolution(entry.width, entry.height)
        else:
            bitrate_k = int(self.options.get("amf_bitrate_k", 8000))
            maxrate_k = int(self.options.get("amf_maxrate_k", 12000))
            bufsize_k = int(self.options.get("amf_bufsize_k", 16000))
        return [
            "-quality",
            amf_quality,
            "-rc",
            "vbr_peak",
            "-b:v",
            f"{bitrate_k}k",
            "-maxrate",
            f"{maxrate_k}k",
            "-bufsize",
            f"{bufsize_k}k",
            "-pix_fmt",
            "yuv420p",
        ]

    def _audio_params(self, codec: str, quality: str, container: str, entry: VideoEntry) -> List[str]:
        bitrate_map = {
            "Schnell": "128k",
            "Gut": "160k",
            "Beste Qualität": "192k",
            "Klein": "96k",
        }
        br = bitrate_map.get(quality, "160k")

        if codec == "copy":
            return ["-c:a", "copy"]
        if codec == "aac stereo":
            if entry.audio_channels > 2:
                self.log.emit(f"[Audio] Downmix {entry.audio_channels} -> 2 Kanaele: {entry.source_path.name}")
            return ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]
        if codec == "aac 320k stereo":
            if entry.audio_channels > 2:
                self.log.emit(f"[Audio] Downmix {entry.audio_channels} -> 2 Kanaele: {entry.source_path.name}")
            return ["-c:a", "aac", "-b:a", "320k", "-ac", "2"]
        if codec == "aac 5.1":
            if entry.audio_channels > 6:
                self.log.emit(f"[Audio] Downmix {entry.audio_channels} -> 6 Kanaele: {entry.source_path.name}")
            return ["-c:a", "aac", "-b:a", "384k", "-ac", "6"]
        if codec == "opus":
            if container == "mp4":
                self.log.emit(f"[Audio] Opus in MP4 unzulaessig, nutze AAC Stereo: {entry.source_path.name}")
                if entry.audio_channels > 2:
                    self.log.emit(f"[Audio] Downmix {entry.audio_channels} -> 2 Kanaele: {entry.source_path.name}")
                return ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]
            return ["-c:a", "libopus", "-b:a", br]
        if codec == "mp3":
            return ["-c:a", "libmp3lame", "-b:a", br]
        if codec == "wav pcm_s16le":
            return ["-c:a", "pcm_s16le"]
        if codec == "flac":
            return ["-c:a", "flac"]
        if codec == "wma":
            return ["-c:a", "wmav2", "-b:a", "192k"]
        return ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]

    def _build_output_path(self, entry: VideoEntry) -> Path:
        container = self.options["container"]
        relative = entry.relative_path
        target_dir = self.target_dir / relative.parent
        if not bool(self.options.get("mirror_subfolders", True)):
            target_dir = self.target_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        stem = entry.source_path.stem
        prefix = str(self.options.get("name_prefix", "") or "")
        suffix = str(self.options.get("name_suffix", "") or "")
        if bool(self.options.get("name_timestamp", False)):
            suffix = f"{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        safe_stem = f"{prefix}{stem}{suffix}"
        candidate = target_dir / f"{safe_stem}.{container}"

        try:
            same_file = candidate.resolve() == entry.source_path.resolve()
        except Exception:
            same_file = False

        overwrite_existing = bool(self.options.get("overwrite_existing", False))
        conflict_policy = str(self.options.get("conflict_policy", "Nummerieren"))

        if same_file and not overwrite_existing:
            conflict_policy = "Nummerieren"
        if same_file and overwrite_existing:
            conflict_policy = "Überschreiben"

        if not candidate.exists():
            return candidate

        if conflict_policy == "Überspringen":
            return Path("")
        if conflict_policy == "Überschreiben" and overwrite_existing:
            return candidate

        base = target_dir / f"{safe_stem}_conv"
        numbered = base.with_suffix(f".{container}")
        i = 1
        while numbered.exists():
            numbered = target_dir / f"{base.name}_{i}.{container}"
            i += 1
        return numbered

    @staticmethod
    def _pretty_size(num_bytes: int) -> str:
        if num_bytes <= 0:
            return "-"
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(num_bytes)
        for unit in units:
            if value < 1024.0 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{num_bytes} B"

    @staticmethod
    def _format_eta(seconds: float) -> str:
        if seconds < 0:
            return "-"
        s = int(seconds)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02}:{m:02}:{sec:02}"

    @staticmethod
    def _diagnose_error(text: str) -> str:
        lower = text.lower()
        if "unknown encoder" in lower:
            return "Hinweis: Gewählter Encoder ist in deiner ffmpeg-Build nicht verfügbar."
        if "invalid argument" in lower:
            return "Hinweis: Mindestens eine Option passt nicht zum gewählten Format/Encoder."
        if "no such file or directory" in lower:
            return "Hinweis: Datei oder Pfad nicht gefunden. Prüfe Quelle/Ziel."
        if "permission denied" in lower:
            return "Hinweis: Keine Schreib-/Leserechte auf Quelle oder Ziel."
        if "could not write header" in lower:
            return "Hinweis: Container/Codec-Kombination ist wahrscheinlich ungültig."
        if "device or resource busy" in lower:
            return "Hinweis: Datei wird evtl. von anderem Programm verwendet."
        if "no stream" in lower or "stream map" in lower:
            return "Hinweis: Gewünschter Audio-/Videostream fehlt in der Eingabedatei."
        return ""

    def _build_command(self, entry: VideoEntry, output_path: Path) -> List[str]:
        export_mode = self.options.get("export_mode", "Video + Audio")
        container = self.options["container"]
        encoder = self.options["video_encoder"]
        quality = self.options["quality"]
        audio = self.options["audio_codec"]
        auto_bitrate = bool(self.options.get("auto_bitrate", False))
        compatibility = self.options.get("compatibility", False)

        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-y",
            "-i",
            str(entry.source_path),
        ]

        if export_mode == "Nur Audio":
            cmd.extend(["-map", "0:a:0?", "-vn"])
            cmd.extend(self._audio_params(audio, quality, container, entry))
        elif export_mode == "Nur Video":
            cmd.extend(["-map", "0:v:0", "-an", "-c:v", encoder])
            cmd.extend(self._quality_params(encoder, quality))
            if encoder in {"h264_amf", "hevc_amf"}:
                cmd.extend(self._amf_params(quality, entry, auto_bitrate))
            elif encoder in {"h264_nvenc", "hevc_nvenc"}:
                if auto_bitrate:
                    cmd.extend(["-rc", "vbr"])
                    cmd.extend(self._dynamic_rate_params(entry))
                else:
                    cmd.extend(self._nvenc_cq_params(quality))
            elif encoder in {"h264_qsv", "hevc_qsv"} and auto_bitrate:
                cmd.extend(self._dynamic_rate_params(entry))
            elif encoder in {"libx264", "libx265"} and auto_bitrate:
                cmd.extend(self._dynamic_rate_params(entry))
        else:
            cmd.extend(["-map", "0:v:0", "-map", "0:a?", "-c:v", encoder])
            cmd.extend(self._quality_params(encoder, quality))
            if encoder in {"h264_amf", "hevc_amf"}:
                cmd.extend(self._amf_params(quality, entry, auto_bitrate))
            elif encoder in {"h264_nvenc", "hevc_nvenc"}:
                if auto_bitrate:
                    cmd.extend(["-rc", "vbr"])
                    cmd.extend(self._dynamic_rate_params(entry))
                else:
                    cmd.extend(self._nvenc_cq_params(quality))
            elif encoder in {"h264_qsv", "hevc_qsv"} and auto_bitrate:
                cmd.extend(self._dynamic_rate_params(entry))
            elif encoder in {"libx264", "libx265"} and auto_bitrate:
                cmd.extend(self._dynamic_rate_params(entry))
            cmd.extend(self._audio_params(audio, quality, container, entry))

        if container in {"mp4", "mov", "m4a"}:
            cmd.extend(["-movflags", "+faststart"])

        if compatibility and container == "mp4" and encoder == "libx264" and export_mode != "Nur Audio":
            cmd.extend(["-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1"])

        if bool(self.options.get("test_run_30s", False)):
            cmd.extend(["-t", "30"])

        cmd.extend([
            "-progress",
            "pipe:1",
            "-nostats",
            "-loglevel",
            "error",
            str(output_path),
        ])
        return cmd

    def _convert_one(self, row_index: int) -> None:
        entry = self.entries[row_index]
        export_mode = self.options.get("export_mode", "Video + Audio")
        if export_mode == "Nur Audio" and entry.audio_channels <= 0:
            raise RuntimeError("Datei enthält keine Audiospur für Audio-Export.")
        output_path = self._build_output_path(entry)
        if str(output_path) == "":
            self.log.emit(f"[Skip] Existiert bereits: {entry.source_path.name}")
            self.file_finished.emit(row_index, True, "SKIPPED_EXISTING")
            return
        cmd = self._build_command(entry, output_path)

        self.log.emit(f"[Start] {entry.source_path.name} -> {output_path.name}")
        self.log.emit("[CMD] " + " ".join(f'"{c}"' if " " in c else c for c in cmd))

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True,
            bufsize=1,
        )
        with self._process_lock:
            self._running_processes[row_index] = proc

        duration_ms = max(entry.duration * 1000.0, 1.0)
        start_ts = time.time()
        last_speed = "-"
        last_size = "-"
        err_lines: List[str] = []

        def _read_stderr() -> None:
            assert proc.stderr is not None
            for raw_err in proc.stderr:
                err_line = raw_err.strip()
                if err_line:
                    err_lines.append(err_line)
                    self.log.emit(f"[ffmpeg] {err_line}")

        stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
        stderr_thread.start()

        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.strip()
            if not line:
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "out_time_ms":
                    try:
                        done_ms = float(value) / 1000.0
                        progress = min(99.0, max(0.0, (done_ms / duration_ms) * 100.0))
                        self.file_progress.emit(row_index, progress)
                        speed_factor = 0.0
                        if last_speed.endswith("x"):
                            try:
                                speed_factor = float(last_speed[:-1])
                            except Exception:
                                speed_factor = 0.0
                        eta_sec = ((duration_ms - done_ms) / 1000.0) / max(speed_factor, 0.01)
                        self.file_metrics.emit(row_index, last_speed, self._format_eta(max(0.0, eta_sec)), last_size)
                    except Exception:
                        pass
                elif key == "speed":
                    last_speed = value
                    elapsed = max(0.001, time.time() - start_ts)
                    _ = elapsed
                elif key == "total_size":
                    try:
                        last_size = self._pretty_size(int(value))
                    except Exception:
                        pass
                elif key == "progress" and value == "end":
                    self.file_progress.emit(row_index, 100.0)
                    self.file_metrics.emit(row_index, last_speed, "00:00:00", last_size)
                continue

            self.log.emit(f"[ffmpeg] {line}")

        rc = proc.wait()
        stderr_thread.join(timeout=1.0)
        with self._process_lock:
            self._running_processes.pop(row_index, None)

        if rc == 0:
            self.log.emit(f"[OK] {entry.source_path.name}")
            self.file_finished.emit(row_index, True, str(output_path))
        else:
            if self._stop_requested:
                self.log.emit(f"[Abbruch] {entry.source_path.name}")
                self.file_finished.emit(row_index, False, "Abgebrochen")
            else:
                err_blob = " | ".join(err_lines[-5:]) if err_lines else f"Exit-Code {rc}"
                hint = self._diagnose_error(err_blob)
                if hint:
                    self.log.emit(f"[Diagnose] {hint}")
                self.log.emit(f"[Fehler] {entry.source_path.name} (Exit {rc})")
                msg = f"Exit-Code {rc}. {hint}".strip()
                self.file_finished.emit(row_index, False, msg)


class WingetInstallWorker(QObject):
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        cmd = [
            "winget",
            "install",
            "--id",
            "Gyan.FFmpeg",
            "-e",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--silent",
        ]
        self.status.emit("Starting installation with winget...")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                bufsize=1,
            )
        except Exception as exc:
            self.finished.emit(False, f"Could not start winget: {exc}")
            return

        assert proc.stdout is not None
        for raw in proc.stdout:
            if self._stop_requested:
                try:
                    proc.terminate()
                except Exception:
                    pass
                self.finished.emit(False, "Installation was canceled.")
                return
            line = raw.strip()
            if line:
                self.status.emit(line)

        rc = proc.wait()
        if rc != 0:
            self.finished.emit(False, f"winget installation failed (exit {rc}).")
            return

        # Nachinstallation kurz prüfen, ob ffmpeg/ffprobe gefunden werden.
        for _ in range(30):
            ffmpeg, ffprobe = find_binaries()
            if ffmpeg and ffprobe:
                self.finished.emit(True, "ffmpeg/ffprobe were installed successfully.")
                return
            if self._stop_requested:
                self.finished.emit(False, "Installation was canceled.")
                return
            time.sleep(1.0)

        self.finished.emit(
            True,
            "Installation completed, binaries may only be detected after restarting the app/session.",
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 800)
        self.setMinimumSize(1080, 740)

        self.config_manager = ConfigManager(CONFIG_FILE)
        self.config = self.config_manager.load()
        self.custom_presets: Dict[str, Dict] = dict(self.config.get("custom_presets", {}))
        self.custom_templates: Dict[str, Dict] = dict(self.config.get("custom_templates", {}))
        self.current_language: str = str(self.config.get("language", "en")).lower().strip() or "en"
        self.favorite_presets: List[str] = list(self.config.get("favorite_presets", []))
        self.last_run_mtimes: Dict[str, float] = dict(self.config.get("last_run_mtimes", {}))
        self.generated_auto_preset_names: List[str] = list(self.config.get("generated_auto_preset_names", []))

        self.ffmpeg_path, self.ffprobe_path = find_binaries()

        self.entries: List[VideoEntry] = []
        self.selected_rows_active: List[int] = []
        self.progress_by_row: Dict[int, float] = {}
        self.failed_rows: List[int] = []
        self.failed_messages: Dict[int, str] = {}
        self.active_preset_name: Optional[str] = None
        self.active_preset_options: Optional[Dict] = None
        self.available_encoders_cache: Optional[set] = None
        self.available_decoders_cache: Optional[set] = None
        self.hw_runtime_status_cache: Optional[Dict[str, bool]] = None
        self.wizard_waiting_scan = False
        self.last_wizard_recommendation: Optional[str] = None
        self.last_wizard_preference: Optional[str] = None
        self.queue_paused = False
        self.job_results: List[Dict] = []
        self.active_conversion_thread: Optional[QThread] = None
        self.active_conversion_worker: Optional[ConvertWorker] = None
        self.selected_rows_runtime: List[int] = []
        self.install_thread: Optional[QThread] = None
        self.install_worker: Optional[WingetInstallWorker] = None
        self.install_dialog: Optional[QDialog] = None
        self.install_status_label: Optional[QLabel] = None
        self.install_poll_timer: Optional[QTimer] = None

        self._build_ui()
        self._load_config_to_ui()
        self._startup_ffmpeg_check()

    def _t(self, en: str, de: str) -> str:
        return en if self.current_language == "en" else de

    def _wizard_pref_label(self, key: str) -> str:
        labels = {
            "best_quality": self._t("Best quality", "Beste Qualität"),
            "smallest_size": self._t("Smallest file size", "Kleinste Dateigröße"),
            "fastest": self._t("Fastest conversion", "Schnellste Konvertierung"),
            "balanced": self._t("Balanced (quality/size/speed)", "Ausgewogen (Qualität/Größe/Geschwindigkeit)"),
            "archive": self._t("Archive / long-term", "Archiv / Langzeit"),
            "audio_podcast_mp3": self._t("Audio only (Podcast MP3)", "Nur Audio (Podcast MP3)"),
            "audio_master_wav": self._t("Audio only (Master WAV)", "Nur Audio (Master WAV)"),
            "audio_archive_flac": self._t("Audio only (Archive FLAC)", "Nur Audio (Archiv FLAC)"),
            "video_web_mp4": self._t("Video only (Web MP4)", "Nur Video (Web MP4)"),
            "video_archive_mkv": self._t("Video only (Archive MKV x265)", "Nur Video (Archiv MKV x265)"),
        }
        return labels.get(key, key)

    def _tr_dynamic(self, text: str) -> str:
        if not text:
            return text
        pairs = [
            ("Rekursiv scannen", "Scan Recursively"),
            ("Scan / Analyse starten", "Scan / Analyze"),
            ("Wizard starten", "Start Wizard"),
            ("Preset anwenden", "Apply Preset"),
            ("Preset Favorit", "Preset Favorite"),
            ("Favorit entfernen", "Remove Favorite"),
            ("Nur Favoriten", "Favorites Only"),
            ("Exportmodus", "Export Mode"),
            ("Exportformat", "Output Format"),
            ("Video-Encoder", "Video Encoder"),
            ("Qualitätsstufe", "Quality"),
            ("Audio-Codec", "Audio Codec"),
            ("Parallel-Jobs", "Parallel Jobs"),
            ("Nur sichtbare Auswahl konvertieren", "Convert only visible selection"),
            ("Nur geaenderte Dateien seit letztem Lauf", "Only changed files since last run"),
            ("Alle markieren", "Select All"),
            ("Keine markieren", "Select None"),
            ("Priorität hoch", "Priority Up"),
            ("Priorität runter", "Priority Down"),
            ("Fehlgeschlagene erneut", "Retry Failed"),
            ("Queue starten", "Start Queue"),
            ("Queue stoppen", "Stop Queue"),
            ("Queue pausieren", "Pause Queue"),
            ("Filter Dateiname", "Name Filter"),
            ("Filter Endung", "Extension Filter"),
            ("Analyse exportieren", "Export Analysis"),
            ("Log speichern", "Save Log"),
            ("Testlauf 30s", "Test run 30s"),
            ("Vorhandene Dateien überschreiben", "Overwrite existing files"),
            ("Konfliktverhalten", "Conflict Behavior"),
            ("Dateiname Prefix", "Filename Prefix"),
            ("Dateiname Suffix", "Filename Suffix"),
            ("Zeitstempel", "Timestamp"),
            ("Unterordnerstruktur", "Subfolder Structure"),
            ("Auto Hardware-Profil", "Auto Hardware Profile"),
            ("Analyse-Export aktivieren", "Enable Analysis Export"),
            ("Ziel darf nicht ersetzt werden", "Target must not be overwritten"),
            ("Template speichern", "Save Template"),
            ("Template laden", "Load Template"),
            ("Template löschen", "Delete Template"),
            ("Hardware/Codecs aktualisieren", "Refresh Hardware/Codecs"),
            ("Auto-Presets erzeugen", "Generate Auto Presets"),
            ("Generierte Auto-Presets resetten", "Reset Generated Auto Presets"),
            ("Hardware-Stabilitaetstest", "Hardware Stability Test"),
            ("Auto-Preset Zielprofil", "Auto-Preset Target Profile"),
            ("Hardware-Status", "Hardware Status"),
            ("Generierte Auto-Presets Anzahl", "Generated Auto Presets Count"),
            ("Codec-Übersicht", "Codec Overview"),
            ("Preset speichern", "Save Preset"),
            ("Custom Preset löschen", "Delete Custom Preset"),
            ("Presets exportieren", "Export Presets"),
            ("Presets importieren", "Import Presets"),
            ("ffmpeg Status", "ffmpeg Status"),
            ("Schnellstart", "Quick Start"),
            ("Hilfe-Hinweis", "Help Hint"),
            ("Quellordner", "Source Folder"),
            ("Zielordner", "Target Folder"),
            ("Quellordner-Pfad", "Source Folder Path"),
            ("Zielordner-Pfad", "Target Folder Path"),
            ("Quellordner wählen", "Choose Source Folder"),
            ("Zielordner wählen", "Choose Target Folder"),
            ("Container", "Container"),
            ("Qualität", "Quality"),
            ("Ungültiger Quellordner", "Invalid source folder"),
            ("Ungültiger Zielordner", "Invalid target folder"),
            ("Keine Daten", "No data"),
            ("Keine Auswahl", "No selection"),
            ("Keine geaenderten Dateien", "No changed files"),
            ("ffmpeg fehlt", "ffmpeg missing"),
            ("ffprobe fehlt", "ffprobe missing"),
            ("Analyse abgeschlossen", "Analysis finished"),
            ("Analyse fehlgeschlagen", "Analysis failed"),
            ("Analysefehler", "Analysis error"),
            ("Start abgebrochen", "Start aborted"),
            ("Encoder nicht verfuegbar", "Encoder not available"),
            ("Audio-Encoder nicht verfuegbar", "Audio encoder not available"),
            ("Queue beendet.", "Queue finished."),
            ("Erfolgreich", "Successful"),
            ("Fehler", "Error"),
            ("Wartet", "Waiting"),
            ("Läuft", "Running"),
            ("Übersprungen", "Skipped"),
            ("Abgebrochen", "Aborted"),
            ("Konflikt", "Conflict"),
            ("Vorhandene Dateien überschreiben", "Overwrite existing files"),
            ("Keine Zielkonflikte in aktueller Auswahl erkannt.", "No target conflicts detected for current selection."),
            ("Bitte zuerst Scan/Analyse durchführen.", "Please run scan/analysis first."),
            ("Bitte mindestens eine Datei markieren.", "Please select at least one file."),
            ("Bitte Quellordner prüfen.", "Please verify source folder."),
            ("Bitte Zielordner prüfen.", "Please verify target folder."),
            ("Bitte einen gültigen Quellordner auswählen.", "Please select a valid source folder."),
            ("ffprobe wurde nicht gefunden.", "ffprobe was not found."),
            ("Starte Analyse in:", "Starting analysis in:"),
            ("Datei(en) bereit.", "file(s) ready."),
            ("Stop angefordert. Bereits laufende Dateien werden noch abgeschlossen.", "Stop requested. Running files will finish."),
            ("Log speichern fehlgeschlagen", "Saving log failed"),
            ("Installation fehlgeschlagen", "Installation failed"),
            ("Installation abgeschlossen", "Installation completed"),
            ("Neustart empfohlen", "Restart recommended"),
            ("Automatischer Neustart fehlgeschlagen", "Automatic restart failed"),
            ("Starte Installation mit winget...", "Starting installation with winget..."),
            ("winget konnte nicht gestartet werden:", "Could not start winget:"),
            ("Installation wurde abgebrochen.", "Installation was canceled."),
            ("winget Installation fehlgeschlagen (Exit ", "winget installation failed (exit "),
            ("ffmpeg/ffprobe wurden erfolgreich installiert.", "ffmpeg/ffprobe were installed successfully."),
            ("Installation abgeschlossen, Binaries werden evtl. erst nach Neustart der App/Session erkannt.", "Installation completed, binaries may only be detected after restarting the app/session."),
            ("Keine Encoderinformationen verfügbar.", "No encoder information available."),
            ("Keine generierten Auto-Presets vorhanden.", "No generated auto presets available."),
            ("Top 5 Auto-Presets", "Top 5 Auto Presets"),
            ("Hardware-Stabilitaetstest", "Hardware stability test"),
            ("Keine Hardware-Encoder in dieser ffmpeg-Build gefunden.", "No hardware encoders found in this ffmpeg build."),
            ("Bitte Option 'Analyse-Export aktivieren' einschalten.", "Please enable the 'Enable analysis export' option."),
            ("Keine Analysedaten vorhanden.", "No analysis data available."),
            ("Durchsucht auch Unterordner. Default: aktiviert, weil so komplette Ordnerstrukturen automatisch erkannt werden.", "Scans subfolders too. Default: enabled, because complete folder structures are detected automatically."),
            ("Liest alle Videodateien ein und analysiert sie via ffprobe (Codec, Auflösung, FPS, Audio usw.).", "Reads all video files and analyzes them via ffprobe (codec, resolution, FPS, audio, etc.)."),
            ("Geführter Ablauf: Quelle/Ziel prüfen, Analyse ausführen, passende Einstellungen vorschlagen und optional direkt starten.", "Guided flow: verify source/target, run analysis, suggest matching settings, and optionally start directly."),
            ("Vordefinierte Kombinationen aus Container, Encoder und Audio. Default: MP4 schnell klein (GPU HEVC), da meistens gutes Verhältnis aus Qualität/Speed/Dateigröße.", "Predefined combinations of container, encoder, and audio. Default: MP4 fast small (GPU HEVC), usually a good quality/speed/size balance."),
            ("Übernimmt alle Werte des gewählten Presets in die Felder und sperrt diese Konfiguration für den nächsten Job, bis du manuell änderst.", "Applies all values of the selected preset to the fields and locks this configuration for the next job until you change settings manually."),
            ("Bestimmt ob Video+Audio, nur Audio oder nur Video exportiert wird.", "Determines whether to export video+audio, audio-only, or video-only."),
            ("Ausgabeformat der Datei. Verfügbare Optionen passen sich an den Exportmodus an.", "Output file format. Available options adapt to the selected export mode."),
            ("Codec/Hardwarepfad für Video. AMD: AMF, NVIDIA: NVENC, Intel iGPU: QSV, CPU: x264/x265.", "Video codec/hardware path. AMD: AMF, NVIDIA: NVENC, Intel iGPU: QSV, CPU: x264/x265."),
            ("Steuert Preset/CRF/CQ-Balance. Default: presetabhängig. 'Gut' ist meist der beste Alltagspunkt.", "Controls preset/CRF/CQ balance. Default depends on preset. 'Good' is usually the best daily setting."),
            ("Audio-Strategie. Default: presetabhängig. 'aac stereo' ist meist am kompatibelsten.", "Audio strategy. Default depends on preset. 'aac stereo' is usually most compatible."),
            ("AMF-Priorität: speed oder quality. Default: quality für bessere Bildqualität bei ähnlicher Bitrate.", "AMF priority: speed or quality. Default: quality for better image quality at similar bitrate."),
            ("Zielbitrate Video (kbps). Default: 8000. Höher = bessere Qualität, größere Dateien.", "Target video bitrate (kbps). Default: 8000. Higher = better quality, larger files."),
            ("Bitratenobergrenze (kbps). Default: 12000. Wichtig für Streaming- und Kompatibilitätsgrenzen.", "Bitrate cap (kbps). Default: 12000. Important for streaming and compatibility limits."),
            ("Puffergröße (kbps). Default: 16000. Stabilisiert variable Bitrate.", "Buffer size (kbps). Default: 16000. Stabilizes variable bitrate."),
            ("Anzahl gleichzeitiger Konvertierungen (1-3). Default: 1 für stabile Last.", "Number of parallel conversions (1-3). Default: 1 for stable load."),
            ("Wenn aktiv, werden nur markierte Dateien konvertiert, die aktuell nicht weggefiltert sind. Default: aktiv.", "If enabled, only selected files currently visible (not filtered out) are converted. Default: enabled."),
            ("Verarbeitet nur Dateien, deren Änderungszeit seit dem letzten erfolgreichen Lauf verändert ist.", "Processes only files whose modification time changed since the last successful run."),
            ("Markiert alle aktuell sichtbaren Tabellenzeilen für die Queue.", "Selects all currently visible table rows for the queue."),
            ("Entfernt Markierung für alle aktuell sichtbaren Tabellenzeilen.", "Clears selection for all currently visible table rows."),
            ("Verschiebt markierte Datei in der Tabelle nach oben (frühere Verarbeitung).", "Moves selected file up in the table (earlier processing)."),
            ("Verschiebt markierte Datei in der Tabelle nach unten (spätere Verarbeitung).", "Moves selected file down in the table (later processing)."),
            ("Markiert fehlgeschlagene Jobs erneut und startet optional die Queue.", "Marks failed jobs again and optionally restarts the queue."),
            ("Startet die Konvertierung der markierten Dateien mit den aktuellen oder gelockten Preset-Einstellungen.", "Starts conversion of selected files with current or locked preset settings."),
            ("Stoppt laufende Jobs kontrolliert (terminate, dann hard kill bei Timeout).", "Stops running jobs gracefully (terminate, then hard-kill on timeout)."),
            ("Pausiert die Queue (bereits laufende Dateien laufen weiter, neue starten erst nach Fortsetzen).", "Pauses the queue (already running files continue, new files start after resume)."),
            ("Filtert Tabellenzeilen nach Dateinamen (Teiltext). Default: leer = keine Einschränkung.", "Filters table rows by filename substring. Default: empty = no restriction."),
            ("Filtert nach Eingabe-Dateiendung (z. B. .mp4). Default: Alle.", "Filters by input file extension (e.g. .mp4). Default: All."),
            ("Exportiert die ffprobe-Analyse als JSON/CSV. Nur verfügbar, wenn die Option aktiviert ist.", "Exports ffprobe analysis as JSON/CSV. Available only when this option is enabled."),
            ("Speichert den aktuellen Logtext als Datei für Dokumentation oder Fehlersuche.", "Saves current log text as file for documentation or troubleshooting."),
            ("Wenn aktiv, wird pro Datei nur ein 30-Sekunden-Test exportiert.", "If enabled, exports only a 30-second test per file."),
            ("Default AUS. Nur wenn aktiv, darf Konfliktmodus 'Überschreiben' bestehende Dateien ersetzen.", "Default OFF. Only if enabled, conflict mode 'Overwrite' may replace existing files."),
            ("Regelt Verhalten bei vorhandener Ausgabedatei: Nummerieren, Überspringen oder Überschreiben.", "Controls behavior when output file already exists: Number, Skip, or Overwrite."),
            ("Text, der vor den Originalnamen gesetzt wird.", "Text prepended to original filename."),
            ("Text, der hinter den Originalnamen gesetzt wird.", "Text appended to original filename."),
            ("Hängt Datum/Uhrzeit an den Ausgabedateinamen an.", "Appends date/time to output filename."),
            ("Wenn aktiv, bleibt die Quellordner-Struktur im Ziel erhalten.", "If enabled, source folder structure is preserved in target."),
            ("Optional: Beim Start passende Hardware-Defaults (Encoder/Jobs) setzen.", "Optional: Apply matching hardware defaults (encoder/jobs) at startup."),
            ("Optional: Nach Queue-Ende automatisch einen JSON-Report im Zielordner speichern.", "Optional: Automatically save a JSON report in target folder when queue finishes."),
            ("Optional: Ordner/Dateien auf das Fenster ziehen, um Quelle zu setzen.", "Optional: Drag folders/files onto the window to set source."),
            ("Optional: Analyse als Datei exportieren (JSON/CSV).", "Optional: Export analysis as file (JSON/CSV)."),
            ("Optional: Start bricht ab, wenn Zielkonflikte erkannt werden.", "Optional: Start aborts when target conflicts are detected."),
            ("Gespeicherte Job-Vorlagen inkl. Filter, Namensregeln und Optionen.", "Saved job templates including filters, naming rules, and options."),
            ("Speichert den gesamten aktuellen Job-Setup als Vorlage.", "Saves the complete current job setup as template."),
            ("Lädt eine gespeicherte Vorlage in alle Felder.", "Loads a saved template into all fields."),
            ("Löscht die aktuell gewählte Vorlage.", "Deletes currently selected template."),
            ("Liest verfügbare ffmpeg-Encoder/Decoder neu ein und aktualisiert die Übersicht.", "Reloads available ffmpeg encoders/decoders and updates overview."),
            ("Erstellt automatisch kompatible Presets für alle aktuell möglichen Exportformate.", "Automatically creates compatible presets for all currently possible export formats."),
            ("Erstellt nur fünf empfohlene Presets für typische Alltagsfälle.", "Creates only five recommended presets for typical daily use."),
            ("Entfernt nur automatisch generierte Presets (AUTO/AUTO TOP5), manuelle Custom-Presets bleiben erhalten.", "Removes only automatically generated presets (AUTO/AUTO TOP5); manual custom presets stay untouched."),
            ("Testet verfügbare Hardware-Encoder mit kurzem 10-Sekunden-Testclip.", "Tests available hardware encoders with a short 10-second test clip."),
            ("Steuert die Priorisierung der automatisch erzeugten Presets (z. B. Smartphone, TV, YouTube, Archiv).", "Controls prioritization of auto-generated presets (e.g. smartphone, TV, YouTube, archive)."),
            ("Zeigt erkannte Hardware-Pfade (AMD AMF, NVIDIA NVENC, Intel QSV, CPU).", "Shows detected hardware paths (AMD AMF, NVIDIA NVENC, Intel QSV, CPU)."),
            ("Zeigt, wie viele automatisch generierte Presets aktuell vorhanden sind.", "Shows how many automatically generated presets currently exist."),
            ("Zeigt welche in diesem Tool relevanten Video-/Audio-Encoder verfügbar sind.", "Shows which video/audio encoders relevant to this tool are available."),
            ("Speichert aktuelle Einstellungen als eigenes Preset.", "Saves current settings as a custom preset."),
            ("Löscht ein selbst erstelltes Preset.", "Deletes a user-created preset."),
            ("Exportiert benutzerdefinierte Presets als JSON.", "Exports user-defined presets as JSON."),
            ("Importiert benutzerdefinierte Presets aus JSON.", "Imports user-defined presets from JSON."),
            ("Zeigt, welche ffmpeg/ffprobe-Binaries genutzt werden. Grünfall: Pfad vorhanden und nutzbar.", "Shows which ffmpeg/ffprobe binaries are used. Green case: path exists and is usable."),
            ("Kurzanleitung für den typischen Ablauf in drei Schritten.", "Quick guide for typical 3-step workflow."),
            ("Hover über Labels/Felder zeigt Details, Defaults und Empfehlungen.", "Hover labels/fields to see details, defaults, and recommendations."),
            ("Ordner mit Eingabevideos.", "Folder containing input videos."),
            ("Ordner für konvertierte Ausgaben.", "Folder for converted outputs."),
            ("Aktueller Quellordner.", "Current source folder."),
            ("Aktueller Zielordner.", "Current target folder."),
            ("Ordnerdialog für Eingaben.", "Folder dialog for input."),
            ("Ordnerdialog für Ausgaben.", "Folder dialog for output."),
            ("Schneller Einstieg über getestete Voreinstellungen.", "Quick start via tested presets."),
            ("Filtert die Dateiliste nach Teilstrings.", "Filters file list by substrings."),
            ("Filtert nach Dateiendung der Eingabedateien.", "Filters by input file extension."),
            ("Video + Audio: normal. Nur Audio: extrahiert/konvertiert Ton. Nur Video: exportiert stummes Video.", "Video + Audio: normal. Audio only: extracts/converts audio. Video only: exports muted video."),
            ("Ausgabeformat der Videodatei.", "Output format of video file."),
            ("Video-Codec und Hardwarepfad.", "Video codec and hardware path."),
            ("Qualitäts-/Geschwindigkeitsprofil.", "Quality/speed profile."),
            ("Mehr Jobs = schneller, aber höhere Systemlast.", "More jobs = faster, but higher system load."),
            ("Definiert, wie Audiospuren übernommen/umkodiert werden. Empfehlung: aac stereo für breite Kompatibilität.", "Defines how audio tracks are copied/re-encoded. Recommendation: aac stereo for broad compatibility."),
            ("AMF quality", "AMF quality"),
            ("AMF maxrate", "AMF maxrate"),
            ("AMF bufsize", "AMF bufsize"),
            ("Auto-Presets (Top 5 empfohlen)", "Auto Presets (Top 5 recommended)"),
            ("Batch-Template", "Batch Template"),
            ("Drag&Drop aktivieren", "Enable Drag & Drop"),
            ("Filter Name", "Name Filter"),
            ("Job-Report JSON", "Job Report JSON"),
            ("Preset", "Preset"),
            ("AMF Qualitätsmodus.", "AMF quality mode."),
            ("Zielbitrate in kbps.", "Target bitrate in kbps."),
            ("Maximale Spitzenbitrate in kbps.", "Maximum peak bitrate in kbps."),
            ("Bitratenpuffer in kbps.", "Bitrate buffer in kbps."),
        ]
        out = text
        if self.current_language == "en":
            for de, en in pairs:
                out = out.replace(de, en)
        else:
            for de, en in pairs:
                out = out.replace(en, de)
        return out

    def _retranslate_help_texts(self) -> None:
        for widget in self.findChildren(QWidget):
            try:
                tip = widget.toolTip()
                if tip:
                    widget.setToolTip(self._tr_dynamic(tip))
                whats = widget.whatsThis()
                if whats:
                    widget.setWhatsThis(self._tr_dynamic(whats))
                st = widget.statusTip()
                if st:
                    widget.setStatusTip(self._tr_dynamic(st))
            except Exception:
                continue

    def _status_text(self, key: str) -> str:
        status = {
            "waiting": self._t("Waiting", "Wartet"),
            "running": self._t("Running", "Läuft"),
            "ok": "OK",
            "error": self._t("Error", "Fehler"),
            "skipped": self._t("Skipped", "Übersprungen"),
        }
        return status.get(key, key)

    def msg_info(self, title: str, text: str) -> None:
        QMessageBox.information(self, self._tr_dynamic(title), self._tr_dynamic(text))

    def msg_warn(self, title: str, text: str) -> None:
        QMessageBox.warning(self, self._tr_dynamic(title), self._tr_dynamic(text))

    def msg_critical(self, title: str, text: str) -> None:
        QMessageBox.critical(self, self._tr_dynamic(title), self._tr_dynamic(text))

    def msg_question_yes_no(self, title: str, text: str, default_yes: bool = True) -> bool:
        default = QMessageBox.Yes if default_yes else QMessageBox.No
        reply = QMessageBox.question(
            self,
            self._tr_dynamic(title),
            self._tr_dynamic(text),
            QMessageBox.Yes | QMessageBox.No,
            default,
        )
        return reply == QMessageBox.Yes

    def on_language_changed(self, *_args) -> None:
        code = str(self.language_combo.currentData() or "en")
        if code == self.current_language:
            return
        self.current_language = code
        self._retranslate_ui()
        self.save_config()

    def _populate_localized_choice_combos(self) -> None:
        # Keep stable internal values in itemData, while display text is localized.
        export_cur = "Video + Audio"
        quality_cur = "Gut"
        conflict_cur = "Nummerieren"
        if hasattr(self, "export_mode_combo"):
            export_cur = self.export_mode_combo.currentData() or self.export_mode_combo.currentText() or "Video + Audio"
        if hasattr(self, "quality_combo"):
            quality_cur = self.quality_combo.currentData() or self.quality_combo.currentText() or "Gut"
        if hasattr(self, "conflict_policy_combo"):
            conflict_cur = self.conflict_policy_combo.currentData() or self.conflict_policy_combo.currentText() or "Nummerieren"

        export_labels = {
            "Video + Audio": self._t("Video + Audio", "Video + Audio"),
            "Nur Audio": self._t("Audio Only", "Nur Audio"),
            "Nur Video": self._t("Video Only", "Nur Video"),
        }
        quality_labels = {
            "Schnell": self._t("Fast", "Schnell"),
            "Gut": self._t("Good", "Gut"),
            "Beste Qualität": self._t("Best Quality", "Beste Qualität"),
            "Klein": self._t("Small", "Klein"),
        }
        conflict_labels = {
            "Nummerieren": self._t("Number", "Nummerieren"),
            "Überspringen": self._t("Skip", "Überspringen"),
            "Überschreiben": self._t("Overwrite", "Überschreiben"),
        }

        if hasattr(self, "export_mode_combo"):
            self.export_mode_combo.blockSignals(True)
            self.export_mode_combo.clear()
            for key in EXPORT_MODE_KEYS:
                self.export_mode_combo.addItem(export_labels[key], key)
            self._set_combo_value(self.export_mode_combo, str(export_cur))
            self.export_mode_combo.blockSignals(False)

        if hasattr(self, "quality_combo"):
            self.quality_combo.blockSignals(True)
            self.quality_combo.clear()
            for key in QUALITY_KEYS:
                self.quality_combo.addItem(quality_labels[key], key)
            self._set_combo_value(self.quality_combo, str(quality_cur))
            self.quality_combo.blockSignals(False)

        if hasattr(self, "conflict_policy_combo"):
            self.conflict_policy_combo.blockSignals(True)
            self.conflict_policy_combo.clear()
            for key in CONFLICT_KEYS:
                self.conflict_policy_combo.addItem(conflict_labels[key], key)
            self._set_combo_value(self.conflict_policy_combo, str(conflict_cur))
            self.conflict_policy_combo.blockSignals(False)

        # Extension filter first entry localized but internally stable.
        if hasattr(self, "filter_ext_combo"):
            current_ext = self.filter_ext_combo.currentData() or self.filter_ext_combo.currentText() or "*"
            self.filter_ext_combo.blockSignals(True)
            self.filter_ext_combo.clear()
            self.filter_ext_combo.addItem(self._t("All", "Alle"), "*")
            for ext in sorted(VIDEO_EXTENSIONS):
                self.filter_ext_combo.addItem(ext, ext)
            self._set_combo_value(self.filter_ext_combo, str(current_ext))
            self.filter_ext_combo.blockSignals(False)

        # Device profile localized labels
        if hasattr(self, "device_profile_combo"):
            profile_cur = self.device_profile_combo.currentData() or self.device_profile_combo.currentText() or "Allgemein"
            profile_legacy_map = {
                "General": "Allgemein",
                "Smartphone": "Smartphone",
                "TV": "TV",
                "YouTube": "YouTube",
                "Archive": "Archiv",
            }
            profile_cur = profile_legacy_map.get(str(profile_cur), str(profile_cur))
            profile_labels = {
                "Allgemein": self._t("General", "Allgemein"),
                "Smartphone": self._t("Smartphone", "Smartphone"),
                "TV": self._t("TV", "TV"),
                "YouTube": self._t("YouTube", "YouTube"),
                "Archiv": self._t("Archive", "Archiv"),
            }
            self.device_profile_combo.blockSignals(True)
            self.device_profile_combo.clear()
            for key in DEVICE_PROFILE_KEYS:
                self.device_profile_combo.addItem(profile_labels[key], key)
            self._set_combo_value(self.device_profile_combo, str(profile_cur))
            self.device_profile_combo.blockSignals(False)

    def _export_mode_value(self) -> str:
        return str(self.export_mode_combo.currentData() or self.export_mode_combo.currentText())

    def _quality_value(self) -> str:
        return str(self.quality_combo.currentData() or self.quality_combo.currentText())

    def _conflict_value(self) -> str:
        return str(self.conflict_policy_combo.currentData() or self.conflict_policy_combo.currentText())

    def _preset_value(self) -> str:
        return str(self.preset_combo.currentData() or self.preset_combo.currentText())

    def _filter_ext_value(self) -> str:
        return str(self.filter_ext_combo.currentData() or self.filter_ext_combo.currentText() or "*")

    def _device_profile_value(self) -> str:
        raw = str(self.device_profile_combo.currentData() or self.device_profile_combo.currentText() or "Allgemein")
        legacy = {
            "General": "Allgemein",
            "Archive": "Archiv",
        }
        return legacy.get(raw, raw)

    def _preset_display_name(self, key: str) -> str:
        builtins = {
            "MP4 schnell klein (GPU HEVC)": self._t("MP4 fast small (GPU HEVC)", "MP4 schnell klein (GPU HEVC)"),
            "MKV beste Qualität (GPU HEVC + Audio Copy)": self._t("MKV best quality (GPU HEVC + Audio Copy)", "MKV beste Qualität (GPU HEVC + Audio Copy)"),
            "MP4 beste CPU Qualität (x264 CRF16)": self._t("MP4 best CPU quality (x264 CRF16)", "MP4 beste CPU Qualität (x264 CRF16)"),
            "MKV Archiv (x265 CRF18)": self._t("MKV archive (x265 CRF18)", "MKV Archiv (x265 CRF18)"),
            "MKV kompatibel (CPU x264 + AAC Stereo)": self._t("MKV compatible (CPU x264 + AAC Stereo)", "MKV kompatibel (CPU x264 + AAC Stereo)"),
            "Audio Podcast (MP3 192k)": self._t("Audio podcast (MP3 192k)", "Audio Podcast (MP3 192k)"),
            "Audio Master (WAV PCM)": self._t("Audio master (WAV PCM)", "Audio Master (WAV PCM)"),
            "Audio Archiv (FLAC)": self._t("Audio archive (FLAC)", "Audio Archiv (FLAC)"),
            "Nur Video Web (MP4 H.264)": self._t("Video-only web (MP4 H.264)", "Nur Video Web (MP4 H.264)"),
            "Nur Video Archiv (MKV x265)": self._t("Video-only archive (MKV x265)", "Nur Video Archiv (MKV x265)"),
        }
        return builtins.get(key, key)

    def _retranslate_ui(self) -> None:
        self._populate_localized_choice_combos()
        self._reload_preset_combo()
        self.setWindowTitle(self._t("FFmpeg Converter", "FFmpeg Konverter"))
        self.path_group.setTitle(self._t("Folders", "Ordner"))
        self.scan_group.setTitle(self._t("Analysis", "Analyse"))
        self.filter_group_top.setTitle(self._t("Filter", "Filter"))
        self.video_group.setTitle(self._t("Video", "Video"))
        self.audio_group.setTitle(self._t("Audio", "Audio"))
        self.naming_group.setTitle(self._t("Filename & Conflicts", "Dateiname & Konflikte"))
        self.preset_tools_group.setTitle(self._t("Preset Manager", "Preset-Manager"))
        self.template_group.setTitle(self._t("Batch Templates", "Batch-Templates"))
        self.advanced_group.setTitle(self._t("Optional Features", "Optionale Features"))
        self.amf_group.setTitle("AMF (AMD GPU)")
        self.feature_group.setTitle(self._t("Feature Checklist", "Feature-Checkliste"))
        self.summary_group.setTitle(self._t("Summary", "Zusammenfassung"))
        self.log_group.setTitle(self._t("Progress & Log", "Fortschritt & Log"))
        self.hardware_group.setTitle(self._t("Hardware Status", "Hardware-Status"))
        self.codec_group.setTitle(self._t("Available Codecs (ffmpeg)", "Verfügbare Codecs (ffmpeg)"))

        self.language_label.setText(self._t("Language", "Sprache"))
        self.source_label.setText(self._t("Source", "Quelle"))
        self.target_label.setText(self._t("Target", "Ziel"))
        self.scan_preset_label.setText("Preset")
        self.filter_name_label_top.setText(self._t("Name Filter", "Filter Name"))
        self.filter_ext_label_top.setText(self._t("Extension Filter", "Filter Endung"))
        self.mode_label.setText(self._t("Export Mode", "Exportmodus"))
        self.container_label.setText(self._t("Output Format", "Exportformat"))
        self.encoder_label.setText(self._t("Video Encoder", "Video-Encoder"))
        self.quality_label.setText(self._t("Quality", "Qualität"))
        self.parallel_label.setText(self._t("Parallel Jobs", "Parallel-Jobs"))
        self.audio_label.setText(self._t("Audio Codec", "Audio-Codec"))
        self.prefix_label.setText(self._t("Prefix", "Prefix"))
        self.suffix_label.setText(self._t("Suffix", "Suffix"))
        self.conflict_label.setText(self._t("Conflict", "Konflikt"))
        if hasattr(self, "profile_row_label"):
            self.profile_row_label.setText(self._t("Auto-preset target profile", "Auto-Preset Zielprofil"))

        self.recursive_check.setText(self._t("Scan Recursively", "Rekursiv scannen"))
        self.scan_btn.setText(self._t("Scan / Analyze", "Scan / Analyse starten"))
        self.wizard_btn.setText(self._t("Start Wizard", "Wizard starten"))
        self.apply_preset_btn.setText(self._t("Apply Preset", "Preset anwenden"))
        self.preset_fav_add_btn.setText(self._t("Preset Favorite", "Preset Favorit"))
        self.preset_fav_remove_btn.setText(self._t("Remove Favorite", "Favorit entfernen"))
        self.show_favs_only_check.setText(self._t("Favorites Only", "Nur Favoriten"))
        self.source_btn.setText(self._t("Source Folder...", "Quellordner..."))
        self.target_btn.setText(self._t("Target Folder...", "Zielordner..."))
        self.name_prefix_edit.setPlaceholderText(self._t("Prefix", "Prefix"))
        self.name_suffix_edit.setPlaceholderText(self._t("Suffix", "Suffix"))
        self.filter_name_edit.setPlaceholderText(self._t("Filter filename...", "Filter Dateiname..."))
        self.select_all_btn.setText(self._t("Select All", "Alle markieren"))
        self.select_none_btn.setText(self._t("Select None", "Keine markieren"))
        self.move_up_btn.setText(self._t("Priority Up", "Priorität hoch"))
        self.move_down_btn.setText(self._t("Priority Down", "Priorität runter"))
        self.only_visible_check.setText(self._t("Convert only visible selection", "Nur sichtbare Auswahl konvertieren"))
        self.only_changed_check.setText(self._t("Only changed files since last run", "Nur geaenderte Dateien seit letztem Lauf"))
        self.retry_failed_btn.setText(self._t("Retry Failed", "Fehlgeschlagene erneut"))
        self.start_btn.setText(self._t("Start Queue", "Queue starten"))
        self.stop_btn.setText(self._t("Stop Queue", "Queue stoppen"))
        self.pause_btn.setText(self._t("Pause Queue", "Queue pausieren") if not self.queue_paused else self._t("Resume Queue", "Queue fortsetzen"))
        self.save_log_btn.setText(self._t("Save Log...", "Log speichern..."))
        self.analysis_export_btn.setText(self._t("Export Analysis...", "Analyse exportieren..."))
        self.test_run_check.setText(self._t("Test run 30s", "Testlauf 30s"))
        self.overwrite_existing_check.setText(self._t("Overwrite existing files", "Vorhandene Dateien überschreiben"))
        self.name_timestamp_check.setText(self._t("Append timestamp", "Zeitstempel anhängen"))
        self.mirror_subfolders_check.setText(self._t("Keep subfolder structure", "Unterordnerstruktur beibehalten"))
        self.preset_save_btn.setText(self._t("Save Preset...", "Preset speichern..."))
        self.preset_delete_btn.setText(self._t("Delete Custom Preset", "Custom Preset löschen"))
        self.preset_export_btn.setText(self._t("Export Presets...", "Presets exportieren..."))
        self.preset_import_btn.setText(self._t("Import Presets...", "Presets importieren..."))
        self.enable_hw_profile_check.setText(self._t("Auto Hardware Profile", "Auto Hardware-Profil"))
        self.enable_job_report_check.setText(self._t("Job Report JSON", "Job-Report JSON"))
        self.enable_dragdrop_check.setText(self._t("Enable Drag & Drop", "Drag&Drop aktivieren"))
        self.enable_analysis_export_check.setText(self._t("Enable Analysis Export", "Analyse-Export aktivieren"))
        self.strict_target_check.setText(self._t("Target must not be overwritten", "Ziel darf nicht ersetzt werden"))
        self.template_save_btn.setText(self._t("Save Template...", "Template speichern..."))
        self.template_load_btn.setText(self._t("Load Template", "Template laden"))
        self.template_delete_btn.setText(self._t("Delete Template", "Template löschen"))
        self.hardware_refresh_btn.setText(self._t("Refresh Hardware/Codecs", "Hardware/Codecs aktualisieren"))
        self.generate_auto_presets_btn.setText(self._t("Generate Auto Presets", "Auto-Presets erzeugen"))
        self.generate_top5_presets_btn.setText(self._t("Generate Auto Presets (Top 5)", "Auto-Presets (Top 5 empfohlen)"))
        self.reset_generated_presets_btn.setText(self._t("Reset Generated Auto Presets", "Generierte Auto-Presets resetten"))
        self.hw_stability_test_btn.setText(self._t("Hardware Stability Test (10s)", "Hardware-Stabilitaetstest (10s)"))

        self.quickstart_label.setText(
            self._t(
                "Quick start: 1) Choose source/target  2) Start scan and mark files  3) Open tab '3) Summary' and start queue.",
                "Schnellstart: 1) Quelle/Ziel wählen  2) Scan starten und Dateien markieren  3) Tab '3) Zusammenfassung' öffnen und Queue starten.",
            )
        )
        self.help_hint_label.setText(
            self._t(
                "Hint: Hover labels or fields to see explanations and recommendations.",
                "Hinweis: Fahre mit dem Cursor auf Labels oder Eingabefelder, um Erklärungen und Empfehlungen zu sehen.",
            )
        )

        self.tabs.setTabText(0, self._t("1) Source & Media", "1) Quelle & Medien"))
        self.tabs.setTabText(1, self._t("2) Conversion", "2) Konvertierung"))
        self.tabs.setTabText(2, self._t("3) Summary", "3) Zusammenfassung"))
        self.tabs.setTabText(3, self._t("4) Progress & Log", "4) Fortschritt & Log"))
        self.tabs.setTabText(4, self._t("5) Hardware & Codecs", "5) Hardware & Codecs"))
        if hasattr(self, "save_action"):
            self.save_action.setText(self._t("Save settings", "Einstellungen speichern"))
        self.batch_label.setText(self._t("0 / 0 completed", "0 / 0 abgeschlossen"))
        self.batch_label_log.setText(self._t("0 / 0 completed", "0 / 0 abgeschlossen"))

        self.table.setHorizontalHeaderLabels(
            [
                self._t("Select", "Auswahl"),
                self._t("File", "Datei"),
                self._t("Duration", "Dauer"),
                self._t("Resolution", "Auflösung"),
                "FPS",
                self._t("Bitrate (kbps)", "Bitrate (kbps)"),
                self._t("Video", "Video"),
                self._t("Audio", "Audio"),
                self._t("Channels", "Kanäle"),
                self._t("Status", "Status"),
                self._t("Progress", "Fortschritt"),
                "Speed",
                "ETA",
                "Size",
            ]
        )
        self._retranslate_help_texts()
        self._refresh_hardware_codec_tab()
        self.refresh_summary()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        def set_help(widget: QWidget, title: str, body: str) -> None:
            tip = f"<b>{title}</b><br>{body}"
            widget.setToolTip(tip)
            widget.setWhatsThis(tip)
            widget.setStatusTip(body)

        self.tabs = QTabWidget()

        self.path_group = QGroupBox("Folders")
        path_layout = QGridLayout(self.path_group)
        self.language_label = QLabel("Language")
        self.language_combo = QComboBox()
        for label, code in LANGUAGE_OPTIONS:
            self.language_combo.addItem(label, code)
        self.recursive_check = QCheckBox("Rekursiv scannen")
        self.scan_btn = QPushButton("Scan / Analyse starten")
        self.wizard_btn = QPushButton("Wizard starten")
        self.preset_combo = QComboBox()
        self.apply_preset_btn = QPushButton("Preset anwenden")
        self.preset_fav_add_btn = QPushButton("Preset Favorit")
        self.preset_fav_remove_btn = QPushButton("Favorit entfernen")
        self.show_favs_only_check = QCheckBox("Nur Favoriten")

        self.export_mode_combo = QComboBox()
        self.container_combo = QComboBox()
        self.container_combo.addItems(list(VIDEO_FORMAT_PROFILES.keys()))

        self.video_encoder_combo = QComboBox()
        self.video_encoder_combo.addItems(VIDEO_ENCODERS)

        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(AUDIO_CODECS)

        self.quality_combo = QComboBox()

        self.amf_quality_combo = QComboBox()
        self.amf_quality_combo.addItems(AMF_QUALITY_LEVELS)
        self.amf_bitrate_spin = QSpinBox()
        self.amf_bitrate_spin.setRange(500, 200000)
        self.amf_bitrate_spin.setSuffix(" kbps")
        self.amf_maxrate_spin = QSpinBox()
        self.amf_maxrate_spin.setRange(500, 200000)
        self.amf_maxrate_spin.setSuffix(" kbps")
        self.amf_bufsize_spin = QSpinBox()
        self.amf_bufsize_spin.setRange(500, 400000)
        self.amf_bufsize_spin.setSuffix(" kbps")

        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 3)

        self.select_all_btn = QPushButton("Alle markieren")
        self.select_none_btn = QPushButton("Keine markieren")
        self.move_up_btn = QPushButton("Priorität hoch")
        self.move_down_btn = QPushButton("Priorität runter")
        self.retry_failed_btn = QPushButton("Fehlgeschlagene erneut")
        self.only_visible_check = QCheckBox("Nur sichtbare Auswahl konvertieren")
        self.only_visible_check.setChecked(True)
        self.only_changed_check = QCheckBox("Nur geaenderte Dateien seit letztem Lauf")
        self.start_btn = QPushButton("Queue starten")
        self.stop_btn = QPushButton("Queue stoppen")
        self.stop_btn.setEnabled(False)
        self.pause_btn = QPushButton("Queue pausieren")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setEnabled(False)
        self.save_log_btn = QPushButton("Log speichern...")
        self.test_run_check = QCheckBox("Testlauf 30s")

        self.overwrite_existing_check = QCheckBox("Vorhandene Dateien überschreiben")
        self.overwrite_existing_check.setChecked(False)
        self.conflict_policy_combo = QComboBox()
        self._populate_localized_choice_combos()
        self._reload_preset_combo()
        self.name_prefix_edit = QLineEdit()
        self.name_prefix_edit.setPlaceholderText("Prefix")
        self.name_suffix_edit = QLineEdit()
        self.name_suffix_edit.setPlaceholderText("Suffix")
        self.name_timestamp_check = QCheckBox("Zeitstempel anhängen")
        self.mirror_subfolders_check = QCheckBox("Unterordnerstruktur beibehalten")
        self.mirror_subfolders_check.setChecked(True)

        self.preset_save_btn = QPushButton("Preset speichern...")
        self.preset_delete_btn = QPushButton("Custom Preset löschen")
        self.preset_export_btn = QPushButton("Presets exportieren...")
        self.preset_import_btn = QPushButton("Presets importieren...")

        self.binary_status = QLabel()
        self.binary_status.setWordWrap(True)
        self.binary_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.quickstart_label = QLabel(
            "Schnellstart: 1) Quelle/Ziel wählen  2) Scan starten und Dateien markieren  3) Tab '3) Zusammenfassung' öffnen und Queue starten."
        )
        self.quickstart_label.setWordWrap(True)
        self.help_hint_label = QLabel(
            "Hinweis: Fahre mit dem Cursor auf Labels oder Eingabefelder, um Erklärungen und Empfehlungen zu sehen."
        )
        self.help_hint_label.setWordWrap(True)
        self.filter_name_edit = QLineEdit()
        self.filter_name_edit.setPlaceholderText(self._t("Filter filename...", "Filter Dateiname..."))
        self.filter_ext_combo = QComboBox()
        self.analysis_export_btn = QPushButton("Analyse exportieren...")

        self.enable_hw_profile_check = QCheckBox("Auto Hardware-Profil")
        self.enable_job_report_check = QCheckBox("Job-Report JSON")
        self.enable_dragdrop_check = QCheckBox("Drag&Drop aktivieren")
        self.enable_analysis_export_check = QCheckBox("Analyse-Export aktivieren")
        self.strict_target_check = QCheckBox("Ziel darf nicht ersetzt werden")

        self.template_combo = QComboBox()
        self.template_save_btn = QPushButton("Template speichern...")
        self.template_load_btn = QPushButton("Template laden")
        self.template_delete_btn = QPushButton("Template löschen")
        self.hardware_refresh_btn = QPushButton("Hardware/Codecs aktualisieren")
        self.generate_auto_presets_btn = QPushButton("Auto-Presets erzeugen")
        self.generate_top5_presets_btn = QPushButton("Auto-Presets (Top 5 empfohlen)")
        self.reset_generated_presets_btn = QPushButton("Generierte Auto-Presets resetten")
        self.hw_stability_test_btn = QPushButton("Hardware-Stabilitaetstest (10s)")
        self.device_profile_combo = QComboBox()
        self.hardware_status_label = QLabel("-")
        self.generated_presets_count_label = QLabel("Generierte Auto-Presets: 0")
        self.hardware_status_label.setWordWrap(True)
        self.hardware_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.hardware_status_label.setTextFormat(Qt.RichText)
        self.codec_report_view = QTextEdit()
        self.codec_report_view.setReadOnly(True)
        self.codec_report_view.setLineWrapMode(QTextEdit.NoWrap)
        set_help(self.recursive_check, "Rekursiv scannen", "Durchsucht auch Unterordner. Default: aktiviert, weil so komplette Ordnerstrukturen automatisch erkannt werden.")
        set_help(self.scan_btn, "Scan / Analyse starten", "Liest alle Videodateien ein und analysiert sie via ffprobe (Codec, Auflösung, FPS, Audio usw.).")
        set_help(self.wizard_btn, "Wizard starten", "Geführter Ablauf: Quelle/Ziel prüfen, Analyse ausführen, passende Einstellungen vorschlagen und optional direkt starten.")
        set_help(self.preset_combo, "Preset", "Vordefinierte Kombinationen aus Container, Encoder und Audio. Default: MP4 schnell klein (GPU HEVC), da meistens gutes Verhältnis aus Qualität/Speed/Dateigröße.")
        set_help(self.apply_preset_btn, "Preset anwenden", "Übernimmt alle Werte des gewählten Presets in die Felder und sperrt diese Konfiguration für den nächsten Job, bis du manuell änderst.")
        set_help(self.preset_fav_add_btn, "Preset Favorit", "Fügt das aktuell gewählte Preset zur Favoritenliste hinzu.")
        set_help(self.preset_fav_remove_btn, "Favorit entfernen", "Entfernt das aktuell gewählte Preset aus der Favoritenliste.")
        set_help(self.show_favs_only_check, "Nur Favoriten", "Zeigt im Preset-Dropdown nur Favoriten an.")
        set_help(self.export_mode_combo, "Exportmodus", "Bestimmt ob Video+Audio, nur Audio oder nur Video exportiert wird.")
        set_help(self.container_combo, "Exportformat", "Ausgabeformat der Datei. Verfügbare Optionen passen sich an den Exportmodus an.")
        set_help(self.video_encoder_combo, "Video-Encoder", "Codec/Hardwarepfad für Video. AMD: AMF, NVIDIA: NVENC, Intel iGPU: QSV, CPU: x264/x265.")
        set_help(self.quality_combo, "Qualitätsstufe", "Steuert Preset/CRF/CQ-Balance. Default: presetabhängig. 'Gut' ist meist der beste Alltagspunkt.")
        set_help(self.audio_codec_combo, "Audio-Codec", "Audio-Strategie. Default: presetabhängig. 'aac stereo' ist meist am kompatibelsten.")
        set_help(self.amf_quality_combo, "AMF quality", "AMF-Priorität: speed oder quality. Default: quality für bessere Bildqualität bei ähnlicher Bitrate.")
        set_help(self.amf_bitrate_spin, "AMF b:v", "Zielbitrate Video (kbps). Default: 8000. Höher = bessere Qualität, größere Dateien.")
        set_help(self.amf_maxrate_spin, "AMF maxrate", "Bitratenobergrenze (kbps). Default: 12000. Wichtig für Streaming- und Kompatibilitätsgrenzen.")
        set_help(self.amf_bufsize_spin, "AMF bufsize", "Puffergröße (kbps). Default: 16000. Stabilisiert variable Bitrate.")
        set_help(self.parallel_spin, "Parallel-Jobs", "Anzahl gleichzeitiger Konvertierungen (1-3). Default: 1 für stabile Last.")
        set_help(self.only_visible_check, "Nur sichtbare Auswahl konvertieren", "Wenn aktiv, werden nur markierte Dateien konvertiert, die aktuell nicht weggefiltert sind. Default: aktiv.")
        set_help(self.only_changed_check, "Nur geaenderte Dateien seit letztem Lauf", "Verarbeitet nur Dateien, deren Änderungszeit seit dem letzten erfolgreichen Lauf verändert ist.")
        set_help(self.select_all_btn, "Alle markieren", "Markiert alle aktuell sichtbaren Tabellenzeilen für die Queue.")
        set_help(self.select_none_btn, "Keine markieren", "Entfernt Markierung für alle aktuell sichtbaren Tabellenzeilen.")
        set_help(self.move_up_btn, "Priorität hoch", "Verschiebt markierte Datei in der Tabelle nach oben (frühere Verarbeitung).")
        set_help(self.move_down_btn, "Priorität runter", "Verschiebt markierte Datei in der Tabelle nach unten (spätere Verarbeitung).")
        set_help(self.retry_failed_btn, "Fehlgeschlagene erneut", "Markiert fehlgeschlagene Jobs erneut und startet optional die Queue.")
        set_help(self.start_btn, "Queue starten", "Startet die Konvertierung der markierten Dateien mit den aktuellen oder gelockten Preset-Einstellungen.")
        set_help(self.stop_btn, "Queue stoppen", "Stoppt laufende Jobs kontrolliert (terminate, dann hard kill bei Timeout).")
        set_help(self.pause_btn, "Queue pausieren", "Pausiert die Queue (bereits laufende Dateien laufen weiter, neue starten erst nach Fortsetzen).")
        set_help(self.filter_name_edit, "Filter Dateiname", "Filtert Tabellenzeilen nach Dateinamen (Teiltext). Default: leer = keine Einschränkung.")
        set_help(self.filter_ext_combo, "Filter Endung", "Filtert nach Eingabe-Dateiendung (z. B. .mp4). Default: Alle.")
        set_help(self.analysis_export_btn, "Analyse exportieren", "Exportiert die ffprobe-Analyse als JSON/CSV. Nur verfügbar, wenn die Option aktiviert ist.")
        set_help(self.save_log_btn, "Log speichern", "Speichert den aktuellen Logtext als Datei für Dokumentation oder Fehlersuche.")
        set_help(self.test_run_check, "Testlauf 30s", "Wenn aktiv, wird pro Datei nur ein 30-Sekunden-Test exportiert.")
        set_help(self.overwrite_existing_check, "Vorhandene Dateien überschreiben", "Default AUS. Nur wenn aktiv, darf Konfliktmodus 'Überschreiben' bestehende Dateien ersetzen.")
        set_help(self.conflict_policy_combo, "Konfliktverhalten", "Regelt Verhalten bei vorhandener Ausgabedatei: Nummerieren, Überspringen oder Überschreiben.")
        set_help(self.name_prefix_edit, "Dateiname Prefix", "Text, der vor den Originalnamen gesetzt wird.")
        set_help(self.name_suffix_edit, "Dateiname Suffix", "Text, der hinter den Originalnamen gesetzt wird.")
        set_help(self.name_timestamp_check, "Zeitstempel", "Hängt Datum/Uhrzeit an den Ausgabedateinamen an.")
        set_help(self.mirror_subfolders_check, "Unterordnerstruktur", "Wenn aktiv, bleibt die Quellordner-Struktur im Ziel erhalten.")
        set_help(self.enable_hw_profile_check, "Auto Hardware-Profil", "Optional: Beim Start passende Hardware-Defaults (Encoder/Jobs) setzen.")
        set_help(self.enable_job_report_check, "Job-Report JSON", "Optional: Nach Queue-Ende automatisch einen JSON-Report im Zielordner speichern.")
        set_help(self.enable_dragdrop_check, "Drag&Drop aktivieren", "Optional: Ordner/Dateien auf das Fenster ziehen, um Quelle zu setzen.")
        set_help(self.enable_analysis_export_check, "Analyse-Export aktivieren", "Optional: Analyse als Datei exportieren (JSON/CSV).")
        set_help(self.strict_target_check, "Ziel darf nicht ersetzt werden", "Optional: Start bricht ab, wenn Zielkonflikte erkannt werden.")
        set_help(self.template_combo, "Batch-Template", "Gespeicherte Job-Vorlagen inkl. Filter, Namensregeln und Optionen.")
        set_help(self.template_save_btn, "Template speichern", "Speichert den gesamten aktuellen Job-Setup als Vorlage.")
        set_help(self.template_load_btn, "Template laden", "Lädt eine gespeicherte Vorlage in alle Felder.")
        set_help(self.template_delete_btn, "Template löschen", "Löscht die aktuell gewählte Vorlage.")
        set_help(self.hardware_refresh_btn, "Hardware/Codecs aktualisieren", "Liest verfügbare ffmpeg-Encoder/Decoder neu ein und aktualisiert die Übersicht.")
        set_help(self.generate_auto_presets_btn, "Auto-Presets erzeugen", "Erstellt automatisch kompatible Presets für alle aktuell möglichen Exportformate.")
        set_help(self.generate_top5_presets_btn, "Auto-Presets (Top 5 empfohlen)", "Erstellt nur fünf empfohlene Presets für typische Alltagsfälle.")
        set_help(self.reset_generated_presets_btn, "Generierte Auto-Presets resetten", "Entfernt nur automatisch generierte Presets (AUTO/AUTO TOP5), manuelle Custom-Presets bleiben erhalten.")
        set_help(self.hw_stability_test_btn, "Hardware-Stabilitaetstest", "Testet verfügbare Hardware-Encoder mit kurzem 10-Sekunden-Testclip.")
        set_help(self.device_profile_combo, "Auto-Preset Zielprofil", "Steuert die Priorisierung der automatisch erzeugten Presets (z. B. Smartphone, TV, YouTube, Archiv).")
        set_help(self.hardware_status_label, "Hardware-Status", "Zeigt erkannte Hardware-Pfade (AMD AMF, NVIDIA NVENC, Intel QSV, CPU).")
        set_help(self.generated_presets_count_label, "Generierte Auto-Presets Anzahl", "Zeigt, wie viele automatisch generierte Presets aktuell vorhanden sind.")
        set_help(self.codec_report_view, "Codec-Übersicht", "Zeigt welche in diesem Tool relevanten Video-/Audio-Encoder verfügbar sind.")
        set_help(self.preset_save_btn, "Preset speichern", "Speichert aktuelle Einstellungen als eigenes Preset.")
        set_help(self.preset_delete_btn, "Custom Preset löschen", "Löscht ein selbst erstelltes Preset.")
        set_help(self.preset_export_btn, "Presets exportieren", "Exportiert benutzerdefinierte Presets als JSON.")
        set_help(self.preset_import_btn, "Presets importieren", "Importiert benutzerdefinierte Presets aus JSON.")
        set_help(self.binary_status, "ffmpeg Status", "Zeigt, welche ffmpeg/ffprobe-Binaries genutzt werden. Grünfall: Pfad vorhanden und nutzbar.")
        set_help(self.quickstart_label, "Schnellstart", "Kurzanleitung für den typischen Ablauf in drei Schritten.")
        set_help(self.help_hint_label, "Hilfe-Hinweis", "Hover über Labels/Felder zeigt Details, Defaults und Empfehlungen.")

        self.source_edit = QLineEdit()
        self.target_edit = QLineEdit()
        self.source_btn = QPushButton("Quellordner...")
        self.target_btn = QPushButton("Zielordner...")
        self.source_label = QLabel("Source")
        self.target_label = QLabel("Target")
        set_help(self.source_label, "Quellordner", "Ordner mit Eingabevideos.")
        set_help(self.target_label, "Zielordner", "Ordner für konvertierte Ausgaben.")
        set_help(self.source_edit, "Quellordner-Pfad", "Aktueller Quellordner.")
        set_help(self.target_edit, "Zielordner-Pfad", "Aktueller Zielordner.")
        set_help(self.source_btn, "Quellordner wählen", "Ordnerdialog für Eingaben.")
        set_help(self.target_btn, "Zielordner wählen", "Ordnerdialog für Ausgaben.")
        path_layout.addWidget(self.language_label, 0, 0)
        path_layout.addWidget(self.language_combo, 0, 1)
        path_layout.addWidget(self.source_label, 1, 0)
        path_layout.addWidget(self.source_edit, 1, 1)
        path_layout.addWidget(self.source_btn, 1, 2)
        path_layout.addWidget(self.target_label, 2, 0)
        path_layout.addWidget(self.target_edit, 2, 1)
        path_layout.addWidget(self.target_btn, 2, 2)

        page_media = QWidget()
        media_layout = QVBoxLayout(page_media)
        media_layout.addWidget(self.quickstart_label)
        media_layout.addWidget(self.path_group)

        self.scan_group = QGroupBox("Analysis")
        scan_layout = QGridLayout(self.scan_group)
        scan_layout.addWidget(self.recursive_check, 0, 0)
        scan_layout.addWidget(self.scan_btn, 0, 1)
        scan_layout.addWidget(self.wizard_btn, 0, 2)
        self.scan_preset_label = QLabel("Preset")
        set_help(self.scan_preset_label, "Preset", "Schneller Einstieg über getestete Voreinstellungen.")
        scan_layout.addWidget(self.scan_preset_label, 1, 0)
        scan_layout.addWidget(self.preset_combo, 1, 1)
        scan_layout.addWidget(self.apply_preset_btn, 1, 2)
        scan_layout.addWidget(self.preset_fav_add_btn, 2, 1)
        scan_layout.addWidget(self.preset_fav_remove_btn, 2, 2)
        scan_layout.addWidget(self.show_favs_only_check, 2, 0)
        scan_layout.addWidget(self.binary_status, 3, 0, 1, 3)
        media_layout.addWidget(self.scan_group)

        self.filter_group_top = QGroupBox("Filter")
        filter_top_layout = QGridLayout(self.filter_group_top)
        self.filter_name_label_top = QLabel("Name Filter")
        self.filter_ext_label_top = QLabel("Extension Filter")
        set_help(self.filter_name_label_top, "Filter Name", "Filtert die Dateiliste nach Teilstrings.")
        set_help(self.filter_ext_label_top, "Filter Endung", "Filtert nach Dateiendung der Eingabedateien.")
        filter_top_layout.addWidget(self.filter_name_label_top, 0, 0)
        filter_top_layout.addWidget(self.filter_name_edit, 0, 1)
        filter_top_layout.addWidget(self.filter_ext_label_top, 0, 2)
        filter_top_layout.addWidget(self.filter_ext_combo, 0, 3)
        filter_top_layout.addWidget(self.analysis_export_btn, 0, 4)
        media_layout.addWidget(self.filter_group_top)

        self.table = QTableWidget(0, 14)
        self.table.setHorizontalHeaderLabels(
            [
                "Auswahl",
                "Datei",
                "Dauer",
                "Auflösung",
                "FPS",
                "Bitrate (kbps)",
                "Video",
                "Audio",
                "Kanäle",
                "Status",
                "Fortschritt",
                "Speed",
                "ETA",
                "Size",
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 14):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.setWordWrap(False)
        self.table.setAlternatingRowColors(True)
        media_layout.addWidget(self.table, 1)

        selection_row = QHBoxLayout()
        selection_row.addWidget(self.select_all_btn)
        selection_row.addWidget(self.select_none_btn)
        selection_row.addWidget(self.move_up_btn)
        selection_row.addWidget(self.move_down_btn)
        selection_row.addWidget(self.only_visible_check)
        selection_row.addWidget(self.only_changed_check)
        selection_row.addStretch(1)
        media_layout.addLayout(selection_row)
        self.tabs.addTab(page_media, "1) Source & Media")

        page_settings = QWidget()
        settings_layout = QVBoxLayout(page_settings)
        settings_layout.addWidget(self.help_hint_label)

        settings_grid_holder = QWidget()
        options_layout = QGridLayout(settings_grid_holder)
        options_layout.setHorizontalSpacing(12)
        options_layout.setVerticalSpacing(8)

        self.video_group = QGroupBox("Video")
        video_layout = QGridLayout(self.video_group)
        self.mode_label = QLabel("Export Mode")
        self.container_label = QLabel("Output Format")
        self.encoder_label = QLabel("Video Encoder")
        self.quality_label = QLabel("Quality")
        set_help(self.mode_label, "Exportmodus", "Video + Audio: normal. Nur Audio: extrahiert/konvertiert Ton. Nur Video: exportiert stummes Video.")
        set_help(self.container_label, "Container", "Ausgabeformat der Videodatei.")
        set_help(self.encoder_label, "Video-Encoder", "Video-Codec und Hardwarepfad.")
        set_help(self.quality_label, "Qualität", "Qualitäts-/Geschwindigkeitsprofil.")
        video_layout.addWidget(self.mode_label, 0, 0)
        video_layout.addWidget(self.export_mode_combo, 0, 1)
        video_layout.addWidget(self.container_label, 1, 0)
        video_layout.addWidget(self.container_combo, 1, 1)
        video_layout.addWidget(self.encoder_label, 2, 0)
        video_layout.addWidget(self.video_encoder_combo, 2, 1)
        video_layout.addWidget(self.quality_label, 3, 0)
        video_layout.addWidget(self.quality_combo, 3, 1)
        self.parallel_label = QLabel("Parallel Jobs")
        set_help(self.parallel_label, "Parallel-Jobs", "Mehr Jobs = schneller, aber höhere Systemlast.")
        video_layout.addWidget(self.parallel_label, 4, 0)
        video_layout.addWidget(self.parallel_spin, 4, 1)

        self.audio_group = QGroupBox("Audio")
        audio_layout = QGridLayout(self.audio_group)
        self.audio_label = QLabel("Audio Codec")
        set_help(self.audio_label, "Audio-Codec", "Definiert, wie Audiospuren übernommen/umkodiert werden. Empfehlung: aac stereo für breite Kompatibilität.")
        audio_layout.addWidget(self.audio_label, 0, 0)
        audio_layout.addWidget(self.audio_codec_combo, 0, 1)
        audio_layout.addWidget(self.test_run_check, 1, 0, 1, 2)

        self.naming_group = QGroupBox("Filename & Conflicts")
        naming_layout = QGridLayout(self.naming_group)
        self.prefix_label = QLabel("Prefix")
        self.suffix_label = QLabel("Suffix")
        self.conflict_label = QLabel("Conflict")
        naming_layout.addWidget(self.prefix_label, 0, 0)
        naming_layout.addWidget(self.name_prefix_edit, 0, 1)
        naming_layout.addWidget(self.suffix_label, 0, 2)
        naming_layout.addWidget(self.name_suffix_edit, 0, 3)
        naming_layout.addWidget(self.conflict_label, 1, 0)
        naming_layout.addWidget(self.conflict_policy_combo, 1, 1)
        naming_layout.addWidget(self.overwrite_existing_check, 1, 2, 1, 2)
        naming_layout.addWidget(self.name_timestamp_check, 2, 0, 1, 2)
        naming_layout.addWidget(self.mirror_subfolders_check, 2, 2, 1, 2)

        self.preset_tools_group = QGroupBox("Preset Manager")
        preset_tools_layout = QGridLayout(self.preset_tools_group)
        preset_tools_layout.addWidget(self.preset_save_btn, 0, 0)
        preset_tools_layout.addWidget(self.preset_delete_btn, 0, 1)
        preset_tools_layout.addWidget(self.preset_export_btn, 1, 0)
        preset_tools_layout.addWidget(self.preset_import_btn, 1, 1)

        self.advanced_group = QGroupBox("Optional Features")
        advanced_layout = QGridLayout(self.advanced_group)
        advanced_layout.addWidget(self.enable_hw_profile_check, 0, 0)
        advanced_layout.addWidget(self.enable_job_report_check, 0, 1)
        advanced_layout.addWidget(self.enable_dragdrop_check, 1, 0)
        advanced_layout.addWidget(self.enable_analysis_export_check, 1, 1)
        advanced_layout.addWidget(self.strict_target_check, 2, 0, 1, 2)

        self.template_group = QGroupBox("Batch Templates")
        template_layout = QGridLayout(self.template_group)
        template_layout.addWidget(self.template_combo, 0, 0, 1, 3)
        template_layout.addWidget(self.template_save_btn, 1, 0)
        template_layout.addWidget(self.template_load_btn, 1, 1)
        template_layout.addWidget(self.template_delete_btn, 1, 2)

        self.amf_group = QGroupBox("AMF (AMD GPU)")
        amf_layout = QGridLayout(self.amf_group)
        self.amf_quality_label = QLabel("AMF quality")
        self.amf_bv_label = QLabel("AMF b:v")
        self.amf_max_label = QLabel("AMF maxrate")
        self.amf_buf_label = QLabel("AMF bufsize")
        set_help(self.amf_quality_label, "AMF quality", "AMF Qualitätsmodus.")
        set_help(self.amf_bv_label, "AMF b:v", "Zielbitrate in kbps.")
        set_help(self.amf_max_label, "AMF maxrate", "Maximale Spitzenbitrate in kbps.")
        set_help(self.amf_buf_label, "AMF bufsize", "Bitratenpuffer in kbps.")
        amf_layout.addWidget(self.amf_quality_label, 0, 0)
        amf_layout.addWidget(self.amf_quality_combo, 0, 1)
        amf_layout.addWidget(self.amf_bv_label, 1, 0)
        amf_layout.addWidget(self.amf_bitrate_spin, 1, 1)
        amf_layout.addWidget(self.amf_max_label, 2, 0)
        amf_layout.addWidget(self.amf_maxrate_spin, 2, 1)
        amf_layout.addWidget(self.amf_buf_label, 3, 0)
        amf_layout.addWidget(self.amf_bufsize_spin, 3, 1)

        options_layout.addWidget(self.video_group, 0, 0)
        options_layout.addWidget(self.audio_group, 0, 1)
        options_layout.addWidget(self.amf_group, 1, 0, 1, 2)
        options_layout.addWidget(self.naming_group, 2, 0, 1, 2)
        options_layout.addWidget(self.preset_tools_group, 3, 0, 1, 2)
        options_layout.addWidget(self.template_group, 4, 0, 1, 2)
        options_layout.addWidget(self.advanced_group, 5, 0, 1, 2)
        settings_layout.addWidget(settings_grid_holder)
        settings_layout.addStretch(1)
        self.tabs.addTab(page_settings, "2) Conversion")

        page_summary = QWidget()
        summary_layout = QVBoxLayout(page_summary)
        self.feature_group = QGroupBox("Feature Checklist")
        feature_layout = QVBoxLayout(self.feature_group)
        self.feature_checklist_label = QLabel()
        self.feature_checklist_label.setWordWrap(True)
        self.feature_checklist_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.feature_checklist_label.setTextFormat(Qt.RichText)
        feature_layout.addWidget(self.feature_checklist_label)
        summary_layout.addWidget(self.feature_group)

        self.summary_group = QGroupBox("Summary")
        summary_group_layout = QVBoxLayout(self.summary_group)
        self.conflict_hint_label = QLabel("")
        self.conflict_hint_label.setWordWrap(True)
        self.conflict_hint_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.estimate_hint_label = QLabel("")
        self.estimate_hint_label.setWordWrap(True)
        self.estimate_hint_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        summary_group_layout.addWidget(self.conflict_hint_label)
        summary_group_layout.addWidget(self.estimate_hint_label)
        self.summary_view = QTextEdit()
        self.summary_view.setReadOnly(True)
        summary_group_layout.addWidget(self.summary_view)
        summary_layout.addWidget(self.summary_group, 1)

        control_row = QHBoxLayout()
        control_row.addWidget(self.start_btn)
        control_row.addWidget(self.stop_btn)
        control_row.addWidget(self.pause_btn)
        control_row.addWidget(self.retry_failed_btn)
        control_row.addStretch(1)
        summary_layout.addLayout(control_row)

        progress_row = QHBoxLayout()
        self.batch_progress = QProgressBar()
        self.batch_progress.setRange(0, 100)
        self.batch_progress.setValue(0)
        self.batch_label = QLabel("0 / 0 abgeschlossen")
        progress_row.addWidget(self.batch_progress, 1)
        progress_row.addWidget(self.batch_label)
        summary_layout.addLayout(progress_row)
        self.tabs.addTab(page_summary, "3) Summary")

        page_log = QWidget()
        log_page_layout = QVBoxLayout(page_log)
        log_progress_row = QHBoxLayout()
        self.batch_progress_log = QProgressBar()
        self.batch_progress_log.setRange(0, 100)
        self.batch_progress_log.setValue(0)
        self.batch_label_log = QLabel("0 / 0 abgeschlossen")
        log_progress_row.addWidget(self.batch_progress_log, 1)
        log_progress_row.addWidget(self.batch_label_log)
        log_page_layout.addLayout(log_progress_row)
        save_row = QHBoxLayout()
        save_row.addWidget(self.save_log_btn)
        save_row.addStretch(1)
        log_page_layout.addLayout(save_row)

        self.log_group = QGroupBox("Progress & Log")
        log_layout = QVBoxLayout(self.log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        log_page_layout.addWidget(self.log_group, 1)
        self.tabs.addTab(page_log, "4) Progress & Log")

        page_hardware = QWidget()
        hardware_layout = QVBoxLayout(page_hardware)
        hardware_header = QHBoxLayout()
        hardware_header.addWidget(self.hardware_refresh_btn)
        hardware_header.addWidget(self.generate_auto_presets_btn)
        hardware_header.addWidget(self.generate_top5_presets_btn)
        hardware_header.addWidget(self.reset_generated_presets_btn)
        hardware_header.addWidget(self.hw_stability_test_btn)
        hardware_header.addStretch(1)
        hardware_layout.addLayout(hardware_header)
        profile_row = QHBoxLayout()
        self.profile_row_label = QLabel("Auto-Preset Target Profile")
        profile_row.addWidget(self.profile_row_label)
        profile_row.addWidget(self.device_profile_combo)
        profile_row.addStretch(1)
        hardware_layout.addLayout(profile_row)

        self.hardware_group = QGroupBox("Hardware Status")
        hardware_group_layout = QVBoxLayout(self.hardware_group)
        hardware_group_layout.addWidget(self.hardware_status_label)
        hardware_group_layout.addWidget(self.generated_presets_count_label)
        hardware_layout.addWidget(self.hardware_group)

        self.codec_group = QGroupBox("Available Codecs (ffmpeg)")
        codec_group_layout = QVBoxLayout(self.codec_group)
        codec_group_layout.addWidget(self.codec_report_view)
        hardware_layout.addWidget(self.codec_group, 1)
        self.tabs.addTab(page_hardware, "5) Hardware & Codecs")

        root.addWidget(self.tabs, 1)

        self.setCentralWidget(central)

        self.save_action = QAction(self._t("Save settings", "Einstellungen speichern"), self)
        self.save_action.triggered.connect(self.save_config)
        self.menuBar().addAction(self.save_action)

        self.source_btn.clicked.connect(self.choose_source)
        self.target_btn.clicked.connect(self.choose_target)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.scan_btn.clicked.connect(self.start_scan)
        self.wizard_btn.clicked.connect(self.start_wizard)
        self.apply_preset_btn.clicked.connect(self.apply_selected_preset)
        self.preset_fav_add_btn.clicked.connect(self.add_current_preset_favorite)
        self.preset_fav_remove_btn.clicked.connect(self.remove_current_preset_favorite)
        self.select_all_btn.clicked.connect(self.select_all_rows)
        self.select_none_btn.clicked.connect(self.select_no_rows)
        self.move_up_btn.clicked.connect(self.move_selected_up)
        self.move_down_btn.clicked.connect(self.move_selected_down)
        self.retry_failed_btn.clicked.connect(self.retry_failed_jobs)
        self.start_btn.clicked.connect(self.start_queue)
        self.stop_btn.clicked.connect(self.stop_queue)
        self.pause_btn.clicked.connect(self.toggle_pause_queue)
        self.save_log_btn.clicked.connect(self.save_log_file)
        self.analysis_export_btn.clicked.connect(self.export_analysis)
        self.preset_save_btn.clicked.connect(self.save_custom_preset)
        self.preset_delete_btn.clicked.connect(self.delete_custom_preset)
        self.preset_export_btn.clicked.connect(self.export_custom_presets)
        self.preset_import_btn.clicked.connect(self.import_custom_presets)
        self.template_save_btn.clicked.connect(self.save_batch_template)
        self.template_load_btn.clicked.connect(self.load_batch_template)
        self.template_delete_btn.clicked.connect(self.delete_batch_template)
        self.hardware_refresh_btn.clicked.connect(self._force_refresh_hardware_codec_tab)
        self.generate_auto_presets_btn.clicked.connect(self.generate_auto_presets)
        self.generate_top5_presets_btn.clicked.connect(self.generate_top5_auto_presets)
        self.reset_generated_presets_btn.clicked.connect(self.reset_generated_auto_presets)
        self.hw_stability_test_btn.clicked.connect(self.run_hw_stability_test)
        self.show_favs_only_check.stateChanged.connect(lambda _: self._reload_preset_combo())
        self.show_favs_only_check.stateChanged.connect(lambda _: self.save_config())
        self.only_changed_check.stateChanged.connect(lambda _: self.refresh_summary())
        self.only_changed_check.stateChanged.connect(lambda _: self.save_config())
        self.device_profile_combo.currentTextChanged.connect(lambda _: self.save_config())
        self.device_profile_combo.currentTextChanged.connect(lambda _: self._refresh_hardware_codec_tab())
        self.video_encoder_combo.currentTextChanged.connect(self._update_amf_controls)
        self.filter_name_edit.textChanged.connect(self.apply_table_filters)
        self.filter_ext_combo.currentTextChanged.connect(self.apply_table_filters)
        self.only_visible_check.stateChanged.connect(lambda _: self.save_config())
        self.only_visible_check.stateChanged.connect(lambda _: self.refresh_summary())
        self.enable_hw_profile_check.stateChanged.connect(lambda _: self.save_config())
        self.enable_job_report_check.stateChanged.connect(lambda _: self.save_config())
        self.enable_dragdrop_check.stateChanged.connect(lambda _: self._apply_dragdrop_state())
        self.enable_dragdrop_check.stateChanged.connect(lambda _: self.save_config())
        self.enable_analysis_export_check.stateChanged.connect(lambda _: self._apply_analysis_export_state())
        self.enable_analysis_export_check.stateChanged.connect(lambda _: self.save_config())
        self.strict_target_check.stateChanged.connect(lambda _: self.save_config())
        self.enable_hw_profile_check.stateChanged.connect(lambda _: self._refresh_feature_checklist())
        self.enable_job_report_check.stateChanged.connect(lambda _: self._refresh_feature_checklist())
        self.enable_dragdrop_check.stateChanged.connect(lambda _: self._refresh_feature_checklist())
        self.enable_analysis_export_check.stateChanged.connect(lambda _: self._refresh_feature_checklist())
        self.strict_target_check.stateChanged.connect(lambda _: self._refresh_feature_checklist())
        self.preset_combo.currentTextChanged.connect(self._invalidate_preset_lock)
        self.preset_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.export_mode_combo.currentTextChanged.connect(self._invalidate_preset_lock)
        self.export_mode_combo.currentTextChanged.connect(lambda _: self._update_export_ui_by_mode())
        self.export_mode_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.container_combo.currentTextChanged.connect(self._invalidate_preset_lock)
        self.container_combo.currentTextChanged.connect(lambda _: self._update_export_ui_by_mode())
        self.container_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.video_encoder_combo.currentTextChanged.connect(self._invalidate_preset_lock)
        self.video_encoder_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.audio_codec_combo.currentTextChanged.connect(self._invalidate_preset_lock)
        self.audio_codec_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.quality_combo.currentTextChanged.connect(self._invalidate_preset_lock)
        self.quality_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.amf_quality_combo.currentTextChanged.connect(self._invalidate_preset_lock)
        self.amf_quality_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.amf_bitrate_spin.valueChanged.connect(self._invalidate_preset_lock)
        self.amf_bitrate_spin.valueChanged.connect(lambda _: self.refresh_summary())
        self.amf_maxrate_spin.valueChanged.connect(self._invalidate_preset_lock)
        self.amf_maxrate_spin.valueChanged.connect(lambda _: self.refresh_summary())
        self.amf_bufsize_spin.valueChanged.connect(self._invalidate_preset_lock)
        self.amf_bufsize_spin.valueChanged.connect(lambda _: self.refresh_summary())
        self.overwrite_existing_check.stateChanged.connect(lambda _: self.refresh_summary())
        self.overwrite_existing_check.stateChanged.connect(lambda _: self._normalize_conflict_policy())
        self.conflict_policy_combo.currentTextChanged.connect(lambda _: self._normalize_conflict_policy())
        self.conflict_policy_combo.currentTextChanged.connect(lambda _: self.refresh_summary())
        self.name_prefix_edit.textChanged.connect(lambda _: self.refresh_summary())
        self.name_suffix_edit.textChanged.connect(lambda _: self.refresh_summary())
        self.name_timestamp_check.stateChanged.connect(lambda _: self.refresh_summary())
        self.mirror_subfolders_check.stateChanged.connect(lambda _: self.refresh_summary())
        self.test_run_check.stateChanged.connect(lambda _: self.refresh_summary())
        self.test_run_check.stateChanged.connect(lambda _: self.save_config())
        self.name_prefix_edit.textChanged.connect(lambda _: self.save_config())
        self.name_suffix_edit.textChanged.connect(lambda _: self.save_config())
        self.name_timestamp_check.stateChanged.connect(lambda _: self.save_config())
        self.mirror_subfolders_check.stateChanged.connect(lambda _: self.save_config())
        self.overwrite_existing_check.stateChanged.connect(lambda _: self.save_config())
        self.conflict_policy_combo.currentTextChanged.connect(lambda _: self.save_config())
        self.tabs.currentChanged.connect(lambda _idx: self.refresh_summary())
        self._apply_ui_polish()

    def _apply_ui_polish(self) -> None:
        # Keine Symbol-/Emoji-Icons: rein textbasierte Buttons.
        return

    def _load_config_to_ui(self) -> None:
        lang_code = str(self.config.get("language", "en")).lower().strip() or "en"
        self.current_language = lang_code
        lang_idx = 0
        for i in range(self.language_combo.count()):
            if str(self.language_combo.itemData(i)) == lang_code:
                lang_idx = i
                break
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(lang_idx)
        self.language_combo.blockSignals(False)
        self.show_favs_only_check.setChecked(bool(self.config.get("show_favorite_presets_only", False)))
        self._reload_preset_combo()
        self._reload_template_combo()
        self.source_edit.setText(self.config.get("source_dir", ""))
        self.target_edit.setText(self.config.get("target_dir", ""))
        self.recursive_check.setChecked(bool(self.config.get("recursive", True)))
        self.parallel_spin.setValue(int(self.config.get("max_jobs", 1)))

        self._set_combo_value(self.preset_combo, self.config.get("preset", "MP4 schnell klein (GPU HEVC)"))
        self._set_combo_value(self.export_mode_combo, self.config.get("export_mode", "Video + Audio"))
        self._set_combo_value(self.container_combo, self.config.get("container", "mp4"))
        self._update_export_ui_by_mode()
        self._set_combo_value(self.video_encoder_combo, self.config.get("video_encoder", "libx264"))
        self._set_combo_value(self.audio_codec_combo, self.config.get("audio_codec", "aac stereo"))
        self._set_combo_value(self.quality_combo, self.config.get("quality", "Gut"))
        self._set_combo_value(self.amf_quality_combo, self.config.get("amf_quality", "quality"))
        self.amf_bitrate_spin.setValue(int(self.config.get("amf_bitrate_k", 8000)))
        self.amf_maxrate_spin.setValue(int(self.config.get("amf_maxrate_k", 12000)))
        self.amf_bufsize_spin.setValue(int(self.config.get("amf_bufsize_k", 16000)))
        self.overwrite_existing_check.setChecked(bool(self.config.get("overwrite_existing", False)))
        self._set_combo_value(self.conflict_policy_combo, self.config.get("conflict_policy", "Nummerieren"))
        self.name_prefix_edit.setText(self.config.get("name_prefix", ""))
        self.name_suffix_edit.setText(self.config.get("name_suffix", ""))
        self.name_timestamp_check.setChecked(bool(self.config.get("name_timestamp", False)))
        self.mirror_subfolders_check.setChecked(bool(self.config.get("mirror_subfolders", True)))
        self.test_run_check.setChecked(bool(self.config.get("test_run_30s", False)))
        self.enable_hw_profile_check.setChecked(bool(self.config.get("enable_hw_auto_profile", False)))
        self.enable_job_report_check.setChecked(bool(self.config.get("enable_job_report", False)))
        self.enable_dragdrop_check.setChecked(bool(self.config.get("enable_dragdrop", False)))
        self.enable_analysis_export_check.setChecked(bool(self.config.get("enable_analysis_export", False)))
        self.strict_target_check.setChecked(bool(self.config.get("strict_target_protection", False)))
        self.filter_name_edit.setText(self.config.get("filter_name", ""))
        self._set_combo_value(self.filter_ext_combo, self.config.get("filter_ext", "*"))
        self.only_visible_check.setChecked(bool(self.config.get("only_visible_selection", True)))
        self.only_changed_check.setChecked(bool(self.config.get("only_changed_since_last_run", False)))
        self._set_combo_value(self.device_profile_combo, self.config.get("device_profile", "Allgemein"))
        self._apply_dragdrop_state()
        self._apply_analysis_export_state()
        self._update_amf_controls()
        self._auto_apply_hw_profile()
        self._refresh_hardware_codec_tab()
        self._retranslate_ui()
        self.refresh_summary()

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx < 0:
            idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _all_presets(self) -> Dict[str, Dict]:
        all_presets = dict(PRESETS)
        all_presets.update(self.custom_presets)
        return all_presets

    def _reload_preset_combo(self) -> None:
        current = self._preset_value()
        names = list(PRESETS.keys()) + sorted(self.custom_presets.keys())
        if self.show_favs_only_check.isChecked():
            fav_set = set(self.favorite_presets)
            filtered = [n for n in names if n in fav_set]
            if filtered:
                names = filtered
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for key in names:
            self.preset_combo.addItem(self._preset_display_name(key), key)
        if current and current in names:
            self._set_combo_value(self.preset_combo, current)
        elif names:
            self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)

    def add_current_preset_favorite(self) -> None:
        name = self._preset_value().strip()
        if not name:
            return
        if name not in self.favorite_presets:
            self.favorite_presets.append(name)
            self.append_log(f"[Preset] Favorit hinzugefuegt: {name}")
            self.save_config()

    def remove_current_preset_favorite(self) -> None:
        name = self._preset_value().strip()
        if not name:
            return
        if name in self.favorite_presets:
            self.favorite_presets = [p for p in self.favorite_presets if p != name]
            self.append_log(f"[Preset] Favorit entfernt: {name}")
            self._reload_preset_combo()
            self.save_config()

    def _reload_template_combo(self) -> None:
        current = self.template_combo.currentText()
        names = sorted(self.custom_templates.keys())
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItems(names)
        if current and current in names:
            self.template_combo.setCurrentText(current)
        self.template_combo.blockSignals(False)

    def _current_settings_as_preset(self) -> Dict:
        return {
            "export_mode": self._export_mode_value(),
            "container": self.container_combo.currentText(),
            "video_encoder": self.video_encoder_combo.currentText(),
            "audio_codec": self.audio_codec_combo.currentText(),
            "quality": self._quality_value(),
            "amf_quality": self.amf_quality_combo.currentText(),
            "amf_bitrate_k": self.amf_bitrate_spin.value(),
            "amf_maxrate_k": self.amf_maxrate_spin.value(),
            "amf_bufsize_k": self.amf_bufsize_spin.value(),
            "auto_bitrate": False,
            "video_preset_override": None,
            "video_crf_override": None,
            "compatibility": False,
        }

    def save_custom_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "Preset speichern", "Name für neues Custom Preset:")
        if not ok or not name.strip():
            return
        clean = name.strip()
        if clean in PRESETS:
            self.msg_warn("Preset", "Name ist bereits als eingebautes Preset reserviert.")
            return
        self.custom_presets[clean] = self._current_settings_as_preset()
        self._reload_preset_combo()
        self._set_combo_value(self.preset_combo, clean)
        self.append_log(f"[Preset] Custom Preset gespeichert: {clean}")
        self.save_config()

    def delete_custom_preset(self) -> None:
        name = self._preset_value().strip()
        if name not in self.custom_presets:
            self.msg_info("Preset", "Kein Custom Preset ausgewählt.")
            return
        if not self.msg_question_yes_no("Preset löschen", f"Custom Preset '{name}' wirklich löschen?"):
            return
        del self.custom_presets[name]
        self.favorite_presets = [p for p in self.favorite_presets if p != name]
        self.generated_auto_preset_names = [p for p in self.generated_auto_preset_names if p != name]
        self._reload_preset_combo()
        self.append_log(f"[Preset] Custom Preset gelöscht: {name}")
        self.save_config()

    def export_custom_presets(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Custom Presets exportieren",
            str(Path.home() / "ffmpeg-konverter-custom-presets.json"),
            "JSON (*.json);;Alle Dateien (*.*)",
        )
        if not target:
            return
        try:
            Path(target).write_text(json.dumps(self.custom_presets, indent=2, ensure_ascii=False), encoding="utf-8")
            self.append_log(f"[Preset] Exportiert nach: {target}")
        except Exception as exc:
            self.msg_critical("Preset-Export", str(exc))

    def import_custom_presets(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Custom Presets importieren",
            str(Path.home()),
            "JSON (*.json);;Alle Dateien (*.*)",
        )
        if not source:
            return
        try:
            data = json.loads(Path(source).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON muss ein Objekt (Presetname -> Presetdaten) sein.")
            imported = 0
            for name, preset in data.items():
                if not isinstance(name, str) or not isinstance(preset, dict):
                    continue
                if name in PRESETS:
                    continue
                self.custom_presets[name] = preset
                imported += 1
            all_names = set(PRESETS.keys()) | set(self.custom_presets.keys())
            self.favorite_presets = [p for p in self.favorite_presets if p in all_names]
            self.generated_auto_preset_names = [p for p in self.generated_auto_preset_names if p in self.custom_presets]
            self._reload_preset_combo()
            self.append_log(f"[Preset] Import abgeschlossen, {imported} Presets übernommen.")
            self.save_config()
        except Exception as exc:
            self.msg_critical("Preset-Import", str(exc))

    def save_batch_template(self) -> None:
        name, ok = QInputDialog.getText(self, "Template speichern", "Name für Batch-Template:")
        if not ok or not name.strip():
            return
        clean = name.strip()
        self.custom_templates[clean] = {
            "source_dir": self.source_edit.text().strip(),
            "target_dir": self.target_edit.text().strip(),
            "recursive": self.recursive_check.isChecked(),
            "filter_name": self.filter_name_edit.text(),
            "filter_ext": self._filter_ext_value(),
            "only_visible_selection": self.only_visible_check.isChecked(),
            "preset": self._preset_value(),
            "options": self._build_effective_options_from_ui(),
        }
        self._reload_template_combo()
        self.template_combo.setCurrentText(clean)
        self.append_log(f"[Template] Gespeichert: {clean}")
        self.save_config()

    def load_batch_template(self) -> None:
        name = self.template_combo.currentText().strip()
        tpl = self.custom_templates.get(name)
        if not tpl:
            self.msg_info("Template", "Bitte ein Template auswählen.")
            return
        self.source_edit.setText(str(tpl.get("source_dir", self.source_edit.text())))
        self.target_edit.setText(str(tpl.get("target_dir", self.target_edit.text())))
        self.recursive_check.setChecked(bool(tpl.get("recursive", True)))
        self.filter_name_edit.setText(str(tpl.get("filter_name", "")))
        self._set_combo_value(self.filter_ext_combo, str(tpl.get("filter_ext", "*")))
        self.only_visible_check.setChecked(bool(tpl.get("only_visible_selection", True)))
        self._set_combo_value(self.preset_combo, str(tpl.get("preset", self._preset_value())))
        self.apply_selected_preset()
        opt = tpl.get("options", {})
        if isinstance(opt, dict):
            self._set_combo_value(self.export_mode_combo, str(opt.get("export_mode", self._export_mode_value())))
            self._update_export_ui_by_mode()
            self._set_combo_value(self.container_combo, str(opt.get("container", self.container_combo.currentText())))
            self._set_combo_value(self.video_encoder_combo, str(opt.get("video_encoder", self.video_encoder_combo.currentText())))
            self._set_combo_value(self.audio_codec_combo, str(opt.get("audio_codec", self.audio_codec_combo.currentText())))
            self._set_combo_value(self.quality_combo, str(opt.get("quality", self._quality_value())))
            self._set_combo_value(self.amf_quality_combo, str(opt.get("amf_quality", self.amf_quality_combo.currentText())))
            self.amf_bitrate_spin.setValue(int(opt.get("amf_bitrate_k", self.amf_bitrate_spin.value())))
            self.amf_maxrate_spin.setValue(int(opt.get("amf_maxrate_k", self.amf_maxrate_spin.value())))
            self.amf_bufsize_spin.setValue(int(opt.get("amf_bufsize_k", self.amf_bufsize_spin.value())))
            self.overwrite_existing_check.setChecked(bool(opt.get("overwrite_existing", self.overwrite_existing_check.isChecked())))
            self._set_combo_value(self.conflict_policy_combo, str(opt.get("conflict_policy", self._conflict_value())))
            self.name_prefix_edit.setText(str(opt.get("name_prefix", self.name_prefix_edit.text())))
            self.name_suffix_edit.setText(str(opt.get("name_suffix", self.name_suffix_edit.text())))
            self.name_timestamp_check.setChecked(bool(opt.get("name_timestamp", self.name_timestamp_check.isChecked())))
            self.mirror_subfolders_check.setChecked(bool(opt.get("mirror_subfolders", self.mirror_subfolders_check.isChecked())))
            self.test_run_check.setChecked(bool(opt.get("test_run_30s", self.test_run_check.isChecked())))
        self.append_log(f"[Template] Geladen: {name}")
        self.refresh_summary()
        self.save_config()

    def delete_batch_template(self) -> None:
        name = self.template_combo.currentText().strip()
        if name not in self.custom_templates:
            self.msg_info("Template", "Kein Template ausgewählt.")
            return
        if not self.msg_question_yes_no("Template löschen", f"Template '{name}' wirklich löschen?"):
            return
        del self.custom_templates[name]
        self._reload_template_combo()
        self.append_log(f"[Template] Gelöscht: {name}")
        self.save_config()

    def export_analysis(self) -> None:
        if not self.enable_analysis_export_check.isChecked():
            self.msg_info("Analyse-Export", "Bitte Option 'Analyse-Export aktivieren' einschalten.")
            return
        if not self.entries:
            self.msg_info("Analyse-Export", "Keine Analysedaten vorhanden.")
            return
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Analyse exportieren",
            str(Path(self.target_edit.text().strip() or Path.home()) / "analyse_export.json"),
            "JSON (*.json);;CSV (*.csv)",
        )
        if not target:
            return
        p = Path(target)
        try:
            if p.suffix.lower() == ".csv":
                lines = ["datei,dauer,auflösung,fps,bitrate_kbps,video_codec,audio_codec,kanäle"]
                for e in self.entries:
                    lines.append(
                        f"\"{e.relative_path}\",{e.duration:.2f},\"{e.resolution}\",{e.fps:.2f},{e.bitrate_kbps},\"{e.video_codec}\",\"{e.audio_codec}\",{e.audio_channels}"
                    )
                p.write_text("\n".join(lines), encoding="utf-8")
            else:
                payload = [
                    {
                        "file": str(e.relative_path),
                        "duration": e.duration,
                        "resolution": e.resolution,
                        "fps": e.fps,
                        "bitrate_kbps": e.bitrate_kbps,
                        "video_codec": e.video_codec,
                        "audio_codec": e.audio_codec,
                        "audio_channels": e.audio_channels,
                    }
                    for e in self.entries
                ]
                p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            self.append_log(f"[Analyse] Exportiert: {p}")
        except Exception as exc:
            self.msg_critical("Analyse-Export", str(exc))

    def _auto_apply_hw_profile(self) -> None:
        if not self.enable_hw_profile_check.isChecked():
            return
        rt = self._get_runtime_hw_status(force=False)
        enc = self._get_available_encoders() or set()
        if rt.get("amf_runtime", False) and "hevc_amf" in enc:
            self._set_combo_value(self.video_encoder_combo, "hevc_amf")
            self.parallel_spin.setValue(2)
            self.append_log("[HW-Profil] AMD AMF runtime erkannt: hevc_amf + 2 Jobs gesetzt.")
        elif rt.get("nvenc_runtime", False) and "hevc_nvenc" in enc:
            self._set_combo_value(self.video_encoder_combo, "hevc_nvenc")
            self.parallel_spin.setValue(2)
            self.append_log("[HW-Profil] NVENC runtime erkannt: hevc_nvenc + 2 Jobs gesetzt.")
        elif rt.get("qsv_runtime", False) and "hevc_qsv" in enc:
            self._set_combo_value(self.video_encoder_combo, "hevc_qsv")
            self.parallel_spin.setValue(2)
            self.append_log("[HW-Profil] Intel QSV runtime erkannt: hevc_qsv + 2 Jobs gesetzt.")
        else:
            self._set_combo_value(self.video_encoder_combo, "libx264")
            self.parallel_spin.setValue(1)
            self.append_log("[HW-Profil] CPU-Profil gesetzt: libx264 + 1 Job.")

    def move_selected_up(self) -> None:
        row = self.table.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self.table.selectRow(row - 1)
        self.refresh_summary()

    def move_selected_down(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self.table.selectRow(row + 1)
        self.refresh_summary()

    def _swap_rows(self, a: int, b: int) -> None:
        if a == b or a < 0 or b < 0 or a >= len(self.entries) or b >= len(self.entries):
            return
        self.entries[a], self.entries[b] = self.entries[b], self.entries[a]
        self.fill_table()

    def retry_failed_jobs(self) -> None:
        if not self.failed_rows:
            self.msg_info("Retry", "Keine fehlgeschlagenen Jobs vorhanden.")
            return
        self.select_no_rows()
        for row in self.failed_rows:
            if 0 <= row < self.table.rowCount():
                item = self.table.item(row, 0)
                if item:
                    item.setCheckState(Qt.Checked)
        self.tabs.setCurrentIndex(2)
        if self.msg_question_yes_no("Retry", "Fehlgeschlagene Jobs jetzt erneut starten?"):
            self.start_queue()

    def toggle_pause_queue(self) -> None:
        self.queue_paused = self.pause_btn.isChecked()
        self.pause_btn.setText(self._t("Resume Queue", "Queue fortsetzen") if self.queue_paused else self._t("Pause Queue", "Queue pausieren"))
        if self.active_conversion_worker:
            self.active_conversion_worker.set_paused(self.queue_paused)

    def _set_combo_items(self, combo: QComboBox, items: List[str], preferred: Optional[str] = None) -> None:
        current = preferred if preferred is not None else combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        if current in items:
            combo.setCurrentText(current)
        elif items:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _apply_dragdrop_state(self) -> None:
        self.setAcceptDrops(self.enable_dragdrop_check.isChecked())

    def _apply_analysis_export_state(self) -> None:
        self.analysis_export_btn.setEnabled(self.enable_analysis_export_check.isChecked())

    def dragEnterEvent(self, event):  # type: ignore[override]
        if not self.enable_dragdrop_check.isChecked():
            event.ignore()
            return
        md = event.mimeData()
        if md and md.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # type: ignore[override]
        if not self.enable_dragdrop_check.isChecked():
            event.ignore()
            return
        md = event.mimeData()
        if not md or not md.hasUrls():
            event.ignore()
            return
        for url in md.urls():
            local = Path(url.toLocalFile())
            if local.is_dir():
                self.source_edit.setText(str(local))
                self.append_log(f"[DragDrop] Quelle gesetzt: {local}")
                self.save_config()
                event.acceptProposedAction()
                return
            if local.is_file():
                self.source_edit.setText(str(local.parent))
                self.append_log(f"[DragDrop] Quelle gesetzt (Dateiordner): {local.parent}")
                self.save_config()
                event.acceptProposedAction()
                return
        event.ignore()

    def _normalize_conflict_policy(self) -> None:
        if self._conflict_value() == "Überschreiben" and not self.overwrite_existing_check.isChecked():
            self.conflict_policy_combo.blockSignals(True)
            self._set_combo_value(self.conflict_policy_combo, "Nummerieren")
            self.conflict_policy_combo.blockSignals(False)

    def _audio_codecs_for_format(self, export_mode: str, fmt: str) -> List[str]:
        if export_mode == "Nur Video":
            return []
        if export_mode == "Nur Audio":
            if fmt == "mp3":
                return ["mp3"]
            if fmt == "wav":
                return ["wav pcm_s16le"]
            if fmt == "flac":
                return ["flac"]
            if fmt in {"m4a", "aac"}:
                return ["aac stereo", "aac 320k stereo"]
            if fmt == "opus":
                return ["opus"]
            if fmt == "wma":
                return ["wma"]
            return ["aac stereo"]
        # Video + Audio
        if fmt == "mp4":
            return ["copy", "aac stereo", "aac 320k stereo", "aac 5.1", "mp3", "flac"]
        if fmt == "webm":
            return ["copy", "opus", "aac stereo", "aac 320k stereo"]
        return AUDIO_CODECS

    def _update_export_ui_by_mode(self) -> None:
        mode = self._export_mode_value()
        old_fmt = self.container_combo.currentText()

        if mode == "Nur Audio":
            fmt_items = list(AUDIO_FORMAT_PROFILES.keys())
        else:
            fmt_items = list(VIDEO_FORMAT_PROFILES.keys())
        self._set_combo_items(self.container_combo, fmt_items, old_fmt if old_fmt in fmt_items else None)
        fmt = self.container_combo.currentText()

        video_items = VIDEO_ENCODERS_BY_FORMAT.get(fmt, VIDEO_ENCODERS)
        if mode == "Nur Audio":
            video_items = VIDEO_ENCODERS
        available_enc = self._get_available_encoders()
        if available_enc:
            filtered = [enc for enc in video_items if enc in available_enc]
            if filtered:
                video_items = filtered
        self._set_combo_items(self.video_encoder_combo, video_items, self.video_encoder_combo.currentText())

        audio_items = self._audio_codecs_for_format(mode, fmt)
        self._set_combo_items(self.audio_codec_combo, audio_items, self.audio_codec_combo.currentText() if audio_items else None)

        is_audio_only = mode == "Nur Audio"
        is_video_only = mode == "Nur Video"
        self.video_encoder_combo.setEnabled(not is_audio_only)
        self.quality_combo.setEnabled(not is_audio_only)
        self.audio_codec_combo.setEnabled(not is_video_only)
        self.amf_quality_combo.setEnabled(not is_audio_only and self.video_encoder_combo.currentText() in {"h264_amf", "hevc_amf"})
        self.amf_bitrate_spin.setEnabled(not is_audio_only and self.video_encoder_combo.currentText() in {"h264_amf", "hevc_amf"})
        self.amf_maxrate_spin.setEnabled(not is_audio_only and self.video_encoder_combo.currentText() in {"h264_amf", "hevc_amf"})
        self.amf_bufsize_spin.setEnabled(not is_audio_only and self.video_encoder_combo.currentText() in {"h264_amf", "hevc_amf"})

        if self._conflict_value() == "Überschreiben" and not self.overwrite_existing_check.isChecked():
            self._set_combo_value(self.conflict_policy_combo, "Nummerieren")

        if mode == "Nur Audio":
            help_text = AUDIO_FORMAT_PROFILES.get(fmt, {}).get("help", "Audio-Exportformat.")
        else:
            help_text = VIDEO_FORMAT_PROFILES.get(fmt, {}).get("help", "Video-Exportformat.")
        self.container_combo.setToolTip(f"<b>Exportformat ({fmt})</b><br>{help_text}")
        if mode == "Nur Audio":
            self.video_encoder_combo.setToolTip(self._t("In 'Audio Only' mode, no video encoder is used.", "Im Modus 'Nur Audio' wird kein Video-Encoder verwendet."))
            self.audio_codec_combo.setToolTip(self._t("Audio codec selection is limited to meaningful codecs for the selected audio format.", "Audio-Codec-Auswahl ist auf sinnvolle Codecs für das gewählte Audioformat begrenzt."))
        elif mode == "Nur Video":
            self.audio_codec_combo.setToolTip(self._t("In 'Video Only' mode, no audio track is exported.", "Im Modus 'Nur Video' wird keine Audiospur exportiert."))
            self.video_encoder_combo.setToolTip(self._t("Video encoder for muted video export.", "Video-Encoder für den stummen Videoexport."))
        else:
            self.video_encoder_combo.setToolTip(self._t("Video encoder for normal video+audio export.", "Video-Encoder für normales Video+Audio-Exportprofil."))
            self.audio_codec_combo.setToolTip(self._t("Audio codec for the output file. Availability depends on export format.", "Audio-Codec für die Ausgabedatei. Verfügbarkeit hängt vom Exportformat ab."))

        self._update_amf_controls()
        self.save_config()

    def _update_amf_controls(self) -> None:
        is_amf = self.video_encoder_combo.currentText() in {"h264_amf", "hevc_amf"} and self._export_mode_value() != "Nur Audio"
        self.amf_quality_combo.setEnabled(is_amf)
        self.amf_bitrate_spin.setEnabled(is_amf)
        self.amf_maxrate_spin.setEnabled(is_amf)
        self.amf_bufsize_spin.setEnabled(is_amf)

    def refresh_summary(self) -> None:
        if not hasattr(self, "summary_view"):
            return
        selected_all = len(self._selected_rows(only_visible=False)) if hasattr(self, "table") else 0
        selected_visible = len(self._selected_rows(only_visible=True)) if hasattr(self, "table") else 0
        preview_rows = self._selected_rows(only_visible=self.only_visible_check.isChecked()) if hasattr(self, "table") else []
        if self.only_changed_check.isChecked():
            changed_preview: List[int] = []
            for row in preview_rows:
                if row < 0 or row >= len(self.entries):
                    continue
                src = self.entries[row].source_path
                try:
                    key = str(src.resolve())
                    mtime = float(src.stat().st_mtime)
                except Exception:
                    changed_preview.append(row)
                    continue
                old = float(self.last_run_mtimes.get(key, 0.0))
                if old <= 0.0 or abs(mtime - old) > 0.000001:
                    changed_preview.append(row)
            preview_rows = changed_preview
        effective_selected = len(preview_rows)
        options_preview = self._build_effective_options_from_ui()
        if self.active_preset_options:
            options_preview.update(self.active_preset_options)
        self._refresh_estimated_sizes_in_table(options_preview)
        total_estimated = 0
        for row in preview_rows:
            if 0 <= row < len(self.entries):
                total_estimated += self._estimate_entry_size_bytes(self.entries[row], options_preview)
        conflicts = self._compute_target_conflicts(preview_rows, options_preview)
        lock_state = self.active_preset_name if self.active_preset_name else "Kein Preset-Lock (manuell)"
        lines = [
            f"Quelle: {self.source_edit.text().strip() or '-'}",
            f"Ziel: {self.target_edit.text().strip() or '-'}",
            "",
            f"Aktuelles Preset (Dropdown): {self._preset_value()}",
            f"Aktiver Preset-Lock: {lock_state}",
            f"Wizard Präferenz (letzter Lauf): {self._wizard_pref_label(self.last_wizard_preference) if self.last_wizard_preference else '-'}",
            f"Wizard Empfehlung (letzter Lauf): {self.last_wizard_recommendation or '-'}",
            "",
            f"Exportmodus: {self.export_mode_combo.currentText()}",
            f"Container: {self.container_combo.currentText()}",
            f"Video-Encoder: {self.video_encoder_combo.currentText()}",
            f"Audio-Codec: {self.audio_codec_combo.currentText()}",
            f"Qualität: {self.quality_combo.currentText()}",
            f"AMF quality: {self.amf_quality_combo.currentText()}",
            f"AMF b:v/maxrate/bufsize: {self.amf_bitrate_spin.value()} / {self.amf_maxrate_spin.value()} / {self.amf_bufsize_spin.value()} kbps",
            f"Parallel-Jobs: {self.parallel_spin.value()}",
            f"Testlauf 30s: {'Ja' if self.test_run_check.isChecked() else 'Nein'}",
            f"Dateiname Prefix/Suffix: '{self.name_prefix_edit.text()}' / '{self.name_suffix_edit.text()}'",
            f"Zeitstempel anhängen: {'Ja' if self.name_timestamp_check.isChecked() else 'Nein'}",
            f"Unterordner spiegeln: {'Ja' if self.mirror_subfolders_check.isChecked() else 'Nein'}",
            f"Konfliktverhalten: {self.conflict_policy_combo.currentText()}",
            f"Überschreiben aktiv: {'Ja' if self.overwrite_existing_check.isChecked() else 'Nein'}",
            "",
            f"Dateien gesamt in Tabelle: {self.table.rowCount() if hasattr(self, 'table') else 0}",
            f"Markiert (alle): {selected_all}",
            f"Markiert (sichtbar): {selected_visible}",
            f"Effektiv für nächsten Start: {effective_selected}",
            f"Nur geaenderte Dateien aktiv: {'Ja' if self.only_changed_check.isChecked() else 'Nein'}",
        ]
        self.summary_view.setPlainText(self._tr_dynamic("\n".join(lines)))
        if conflicts:
            sample = ", ".join(str(p.name) for p in conflicts[:3])
            more = f" (+{len(conflicts)-3})" if len(conflicts) > 3 else ""
            self.conflict_hint_label.setText(self._tr_dynamic(f"Warnung Zielkonflikte: {len(conflicts)} vorhandene Zieldatei(en), z. B. {sample}{more}"))
            self.conflict_hint_label.setStyleSheet("color: #a11b1b;")
        else:
            self.conflict_hint_label.setText(self._tr_dynamic("Keine Zielkonflikte in aktueller Auswahl erkannt."))
            self.conflict_hint_label.setStyleSheet("color: #127a2f;")
        self.estimate_hint_label.setText(self._tr_dynamic(f"Geschaetzte Gesamtausgabe (aktuelle Auswahl/Einstellungen): {self._human_bytes(total_estimated)}"))
        self._refresh_feature_checklist()

    def _refresh_feature_checklist(self) -> None:
        if not hasattr(self, "feature_checklist_label"):
            return

        def state(flag: bool) -> str:
            if flag:
                return f"<span style='color:#127a2f; font-weight:600;'>{self._t('ON', 'AKTIV')}</span>"
            return f"<span style='color:#a11b1b; font-weight:600;'>{self._t('OFF', 'INAKTIV')}</span>"

        ready = f"<span style='color:#1d4f91; font-weight:600;'>{self._t('AVAILABLE', 'VERFUEGBAR')}</span>"
        html = (
            f"<b>{self._t('Optional items (only active when enabled):', 'Optionale Punkte (nur aktiv, wenn eingeschaltet):')}</b><br>"
            f"1) {self._t('Auto hardware profile', 'Auto Hardware-Profil')}: {state(self.enable_hw_profile_check.isChecked())}<br>"
            f"2) Job-Report JSON: {state(self.enable_job_report_check.isChecked())}<br>"
            f"3) Drag&amp;Drop: {state(self.enable_dragdrop_check.isChecked())}<br>"
            f"4) {self._t('Analysis export', 'Analyse-Export')}: {state(self.enable_analysis_export_check.isChecked())}<br>"
            f"5) {self._t('Target must not be replaced (hard abort on start)', 'Ziel darf nicht ersetzt werden (harter Start-Abbruch)')}: {state(self.strict_target_check.isChecked())}<br><br>"
            f"<b>{self._t('Always available functions:', 'Immer verfuegbare Funktionen:')}</b><br>"
            f"6) {self._t('Queue pause/resume', 'Queue Pause/Fortsetzen')}: {ready}<br>"
            f"7) {self._t('Retry failed jobs', 'Fehlgeschlagene Jobs erneut starten')}: {ready}<br>"
            f"8) {self._t('Extended progress/status display (file + global)', 'Erweiterte Fortschritts-/Statusanzeige (Datei + global)')}: {ready}"
        )
        self.feature_checklist_label.setText(html)

    def _update_binary_status(self) -> None:
        ok = bool(self.ffmpeg_path and self.ffprobe_path)
        if ok:
            ffmpeg_name = Path(self.ffmpeg_path).name if self.ffmpeg_path else "?"
            ffprobe_name = Path(self.ffprobe_path).name if self.ffprobe_path else "?"
            self.binary_status.setText(f"ffmpeg OK ({ffmpeg_name}) | ffprobe OK ({ffprobe_name})")
            self.binary_status.setToolTip(f"<b>ffmpeg</b>: {self.ffmpeg_path}<br><b>ffprobe</b>: {self.ffprobe_path}")
        else:
            self.binary_status.setText(
                self._t(
                    "ffmpeg/ffprobe not found (PATH or local ffmpeg.exe/ffprobe.exe required).",
                    "ffmpeg/ffprobe nicht gefunden (PATH oder lokale ffmpeg.exe/ffprobe.exe nötig).",
                )
            )

        self.scan_btn.setEnabled(ok)
        self.start_btn.setEnabled(ok)
        self._refresh_hardware_codec_tab()

    def _startup_ffmpeg_check(self) -> None:
        self.ffmpeg_path, self.ffprobe_path = find_binaries()
        self._update_binary_status()
        if self.ffmpeg_path and self.ffprobe_path:
            return

        if not self.msg_question_yes_no(
            self._t("ffmpeg missing", "ffmpeg fehlt"),
            self._t(
                "ffmpeg/ffprobe were not found.\n\nDo you want to install ffmpeg automatically via winget now?",
                "ffmpeg/ffprobe wurden nicht gefunden.\n\nSoll ffmpeg jetzt automatisch via winget installiert werden?",
            ),
        ):
            self.msg_warn(
                self._t("Conversion requires ffmpeg", "Ohne ffmpeg keine Konvertierung"),
                self._t(
                    "Please install ffmpeg/ffprobe manually or restart the app and use automatic installation.",
                    "Bitte installiere ffmpeg/ffprobe manuell oder starte die App erneut und nutze die Auto-Installation.",
                ),
            )
            return
        self._start_ffmpeg_winget_install()

    def _start_ffmpeg_winget_install(self) -> None:
        self.install_dialog = QDialog(self)
        self.install_dialog.setWindowTitle(self._t("ffmpeg installation running", "ffmpeg Installation läuft"))
        self.install_dialog.setModal(True)
        self.install_dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        layout = QVBoxLayout(self.install_dialog)
        title = QLabel(self._t("ffmpeg/ffprobe are being installed. Please wait...", "ffmpeg/ffprobe werden installiert. Bitte kurz warten..."))
        title.setWordWrap(True)
        layout.addWidget(title)
        self.install_status_label = QLabel(self._t("Initializing...", "Initialisiere..."))
        self.install_status_label.setWordWrap(True)
        layout.addWidget(self.install_status_label)
        bar = QProgressBar()
        bar.setRange(0, 0)
        layout.addWidget(bar)
        self.install_dialog.resize(520, 170)

        self.install_poll_timer = QTimer(self)
        self.install_poll_timer.setInterval(1500)
        self.install_poll_timer.timeout.connect(self._poll_install_binary_check)
        self.install_poll_timer.start()

        self.install_thread = QThread(self)
        self.install_worker = WingetInstallWorker()
        self.install_worker.moveToThread(self.install_thread)
        self.install_thread.started.connect(self.install_worker.run)
        self.install_worker.status.connect(self._on_install_status)
        self.install_worker.finished.connect(self._on_install_finished)
        self.install_worker.finished.connect(self.install_thread.quit)
        self.install_thread.finished.connect(self.install_thread.deleteLater)
        self.install_thread.start()
        self.install_dialog.exec()

    def _poll_install_binary_check(self) -> None:
        ffmpeg, ffprobe = find_binaries()
        if ffmpeg and ffprobe:
            self.ffmpeg_path, self.ffprobe_path = ffmpeg, ffprobe
            self._update_binary_status()
            if self.install_status_label:
                self.install_status_label.setText(self._t("ffmpeg/ffprobe detected. Finalizing installation...", "ffmpeg/ffprobe erkannt. Installation wird finalisiert..."))

    def _on_install_status(self, message: str) -> None:
        if self.install_status_label:
            text = self._tr_dynamic(message)
            if self.current_language == "en":
                low_raw = message.lower().strip()
                # Winget can output localized lines. In EN mode we enforce clean EN status text.
                german_markers = [
                    " der ",
                    " die ",
                    " das ",
                    " und ",
                    " nicht ",
                    " wird ",
                    " werden ",
                    "paket",
                    "quelle",
                    "herunter",
                    "abgebrochen",
                    "erfolgreich",
                    "gefunden",
                    "installation",
                    "aktualisierung",
                    "verarbeitung",
                    "bereit",
                    "fortschritt",
                ]
                looks_german = any(m in f" {low_raw} " for m in german_markers)
                is_explicit_error = any(k in low_raw for k in ["error", "failed", "could not", "exit", "exception"])
                if looks_german and not is_explicit_error:
                    text = "Installing ffmpeg via winget... please wait."
                elif looks_german and is_explicit_error:
                    text = "winget reported an installation error. Please check your network/permissions and try again."
            self.install_status_label.setText(text[:300])

    def _restart_application(self) -> None:
        try:
            if getattr(sys, "frozen", False):
                executable = sys.executable
                args = []
            else:
                executable = sys.executable
                args = [str(Path(__file__).resolve())]
            subprocess.Popen([executable, *args], close_fds=True)
        except Exception as exc:
            self.msg_warn(
                self._t("Restart", "Neustart"),
                self._t("Automatic restart failed:", "Automatischer Neustart fehlgeschlagen:") + f" {exc}",
            )
        QApplication.quit()

    def _on_install_finished(self, success: bool, message: str) -> None:
        if self.install_poll_timer:
            self.install_poll_timer.stop()
            self.install_poll_timer.deleteLater()
            self.install_poll_timer = None

        self.ffmpeg_path, self.ffprobe_path = find_binaries()
        self._update_binary_status()

        if self.install_dialog and self.install_dialog.isVisible():
            self.install_dialog.accept()
        self.install_dialog = None

        if not success:
            self.msg_critical("Installation fehlgeschlagen", message)
            return

        if self.ffmpeg_path and self.ffprobe_path:
            self.msg_info(
                self._t("Installation completed", "Installation abgeschlossen"),
                self._t("ffmpeg/ffprobe are now available.", "ffmpeg/ffprobe sind jetzt verfügbar."),
            )
            return

        if self.msg_question_yes_no(
            self._t("Restart recommended", "Neustart empfohlen"),
            self._t(
                "Installation is complete, but ffmpeg/ffprobe are not yet visible in the current process.\n\nRestart the app now?",
                "Die Installation ist abgeschlossen, aber ffmpeg/ffprobe sind noch nicht im aktuellen Prozess sichtbar.\n\nApp jetzt neu starten?",
            ),
        ):
            self._restart_application()

    def choose_source(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self._t("Choose source folder", "Quellordner wählen"), self.source_edit.text() or str(Path.home()))
        if folder:
            self.source_edit.setText(folder)
            self.save_config()

    def choose_target(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self._t("Choose target folder", "Zielordner wählen"), self.target_edit.text() or str(Path.home()))
        if folder:
            self.target_edit.setText(folder)
            self.save_config()

    def _suggest_preset_name(self, preference_key: str) -> str:
        encoders = self._get_available_encoders() or set()
        has_amf = "hevc_amf" in encoders
        has_nvenc = "hevc_nvenc" in encoders
        has_qsv = "hevc_qsv" in encoders
        max_h = max((e.height for e in self.entries), default=0)
        pref = (preference_key or "").strip()

        if pref == "audio_podcast_mp3":
            return "Audio Podcast (MP3 192k)"
        if pref == "audio_master_wav":
            return "Audio Master (WAV PCM)"
        if pref == "audio_archive_flac":
            return "Audio Archiv (FLAC)"
        if pref == "video_web_mp4":
            return "Nur Video Web (MP4 H.264)"
        if pref == "video_archive_mkv":
            return "Nur Video Archiv (MKV x265)"

        if pref == "best_quality":
            if has_amf:
                return "MKV beste Qualität (GPU HEVC + Audio Copy)"
            if has_nvenc or has_qsv:
                return "MKV Archiv (x265 CRF18)"
            return "MP4 beste CPU Qualität (x264 CRF16)"

        if pref == "smallest_size":
            if has_amf:
                return "MP4 schnell klein (GPU HEVC)"
            if has_nvenc or has_qsv:
                return "MKV Archiv (x265 CRF18)"
            return "MKV Archiv (x265 CRF18)"

        if pref == "fastest":
            if has_amf:
                return "MP4 schnell klein (GPU HEVC)"
            if has_nvenc or has_qsv:
                return "MKV kompatibel (CPU x264 + AAC Stereo)"
            return "MKV kompatibel (CPU x264 + AAC Stereo)"

        if pref == "archive":
            return "MKV Archiv (x265 CRF18)"

        # Ausgewogen oder unbekannt
        if has_amf:
            if max_h >= 1080:
                return "MKV beste Qualität (GPU HEVC + Audio Copy)"
            return "MP4 schnell klein (GPU HEVC)"
        return "MKV kompatibel (CPU x264 + AAC Stereo)"

    def _ask_wizard_preference(self) -> Optional[str]:
        labels = [self._wizard_pref_label(k) for k in WIZARD_PREFERENCE_KEYS]
        default_index = min(3, max(0, len(labels) - 1))
        choice, ok = QInputDialog.getItem(
            self,
            self._t("Wizard Preference", "Wizard Präferenz"),
            self._t("Which priority should the wizard prefer?", "Welche Priorität soll der Wizard bevorzugen?"),
            labels,
            default_index,
            False,
        )
        if not ok:
            return None
        try:
            idx = labels.index(str(choice))
            return WIZARD_PREFERENCE_KEYS[idx]
        except Exception:
            return "balanced"

    def start_wizard(self) -> None:
        if self.active_conversion_worker:
            self.msg_warn("Wizard", "Bitte warte, bis die aktuelle Queue beendet ist.")
            return

        self.tabs.setCurrentIndex(0)
        self.msg_info(
            "Wizard",
            "Der Wizard führt dich jetzt durch den kompletten Ablauf:\n"
            "1) Quelle/Ziel prüfen\n2) Analyse\n3) Einstellungsvorschlag\n4) optional direkt starten",
        )
        preference = self._ask_wizard_preference()
        if not preference:
            self.msg_info("Wizard", "Wizard abgebrochen.")
            return
        self.last_wizard_preference = preference

        if not Path(self.source_edit.text().strip()).is_dir():
            self.msg_info("Wizard", "Bitte zuerst den Quellordner wählen.")
            self.choose_source()
        if not Path(self.target_edit.text().strip()).is_dir():
            self.msg_info("Wizard", "Bitte den Zielordner wählen.")
            self.choose_target()

        source_ok = Path(self.source_edit.text().strip()).is_dir()
        target_ok = Path(self.target_edit.text().strip()).is_dir()
        if not source_ok or not target_ok:
            self.msg_warn("Wizard", "Wizard abgebrochen: Quelle oder Ziel fehlt.")
            return

        if not self.entries:
            self.wizard_waiting_scan = True
            self.msg_info("Wizard", "Analyse wird gestartet. Bitte kurz warten...")
            self.start_scan()
            return

        self._wizard_after_scan()

    def _wizard_after_scan(self) -> None:
        if not self.entries:
            self.msg_warn("Wizard", "Keine Videodateien gefunden.")
            return

        self.select_all_rows()
        suggested = self._suggest_preset_name(self.last_wizard_preference or "balanced")
        self.last_wizard_recommendation = suggested
        self._set_combo_value(self.preset_combo, suggested)
        self.apply_selected_preset()
        self.refresh_summary()

        self.msg_info(
            "Wizard Vorschlag",
            f"Gewählte Präferenz: {self._wizard_pref_label(self.last_wizard_preference) if self.last_wizard_preference else '-'}\n"
            f"Vorgeschlagene Konvertierungseinstellung:\n{suggested}\n\n"
            "Du kannst in Tab 2 anpassen oder direkt mit dem Vorschlag starten.",
        )
        self.tabs.setCurrentIndex(2)
        if self.msg_question_yes_no("Wizard", "Konvertierung jetzt mit dem Vorschlag starten?"):
            self.start_queue()
            self.tabs.setCurrentIndex(3)

    def append_log(self, text: str) -> None:
        self.log_view.append(self._tr_dynamic(text))

    def start_scan(self) -> None:
        source = Path(self.source_edit.text().strip())
        if not source.exists() or not source.is_dir():
            self.msg_warn("Ungültiger Quellordner", "Bitte einen gültigen Quellordner auswählen.")
            return
        if not self.ffprobe_path:
            self.msg_warn("ffprobe fehlt", "ffprobe wurde nicht gefunden.")
            return

        self.append_log(f"Starte Analyse in: {source}")
        self.scan_btn.setEnabled(False)
        self.entries.clear()
        self.table.setRowCount(0)
        self.batch_progress.setValue(0)
        self.batch_progress_log.setValue(0)
        empty_text = self._t("0 / 0 completed", "0 / 0 abgeschlossen")
        self.batch_label.setText(empty_text)
        self.batch_label_log.setText(empty_text)

        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(source, self.recursive_check.isChecked(), self.ffprobe_path)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self.append_log)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.failed.connect(self.on_scan_failed)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.failed.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.start()

    def on_scan_finished(self, entries: List[VideoEntry]) -> None:
        self.entries = entries
        self.fill_table()
        self.scan_btn.setEnabled(True)
        self.append_log(f"Analyse abgeschlossen: {len(entries)} Datei(en) bereit.")
        self.refresh_summary()
        if self.wizard_waiting_scan:
            self.wizard_waiting_scan = False
            self._wizard_after_scan()

    def on_scan_failed(self, message: str) -> None:
        self.scan_btn.setEnabled(True)
        self.append_log(f"Analyse fehlgeschlagen: {message}")
        self.msg_critical("Analysefehler", message)

    def fill_table(self) -> None:
        previous_checks: Dict[str, Qt.CheckState] = {}
        for row in range(self.table.rowCount()):
            path_item = self.table.item(row, 1)
            check_item = self.table.item(row, 0)
            if path_item and check_item:
                previous_checks[path_item.text()] = check_item.checkState()
        self.table.setRowCount(0)
        for entry in self.entries:
            row = self.table.rowCount()
            self.table.insertRow(row)

            check_item = QTableWidgetItem()
            check_item.setFlags(check_item.flags() | Qt.ItemIsUserCheckable)
            check_item.setCheckState(previous_checks.get(str(entry.relative_path), Qt.Checked))
            self.table.setItem(row, 0, check_item)

            self.table.setItem(row, 1, QTableWidgetItem(str(entry.relative_path)))
            self.table.setItem(row, 2, QTableWidgetItem(duration_to_text(entry.duration)))
            self.table.setItem(row, 3, QTableWidgetItem(entry.resolution))
            self.table.setItem(row, 4, QTableWidgetItem(f"{entry.fps:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(str(entry.bitrate_kbps)))
            self.table.setItem(row, 6, QTableWidgetItem(entry.video_codec))
            self.table.setItem(row, 7, QTableWidgetItem(entry.audio_codec))
            self.table.setItem(row, 8, QTableWidgetItem(str(entry.audio_channels)))
            self.table.setItem(row, 9, QTableWidgetItem(self._t("Ready", "Bereit")))
            self.table.setItem(row, 10, QTableWidgetItem("0%"))
            self.table.setItem(row, 11, QTableWidgetItem("-"))
            self.table.setItem(row, 12, QTableWidgetItem("-"))
            self.table.setItem(row, 13, QTableWidgetItem("-"))
            self._set_row_status_style(row, self._t("Ready", "Bereit"))
        self.apply_table_filters()
        self.refresh_summary()

    def _set_row_status_style(self, row: int, status: str) -> None:
        item = self.table.item(row, 9)
        if not item:
            return
        low = status.lower()
        if low.startswith("ok"):
            item.setBackground(Qt.darkGreen)
            item.setForeground(Qt.white)
        elif low.startswith("fehler") or low.startswith("error"):
            item.setBackground(Qt.darkRed)
            item.setForeground(Qt.white)
        elif low.startswith("läuft") or low.startswith("running"):
            item.setBackground(Qt.darkBlue)
            item.setForeground(Qt.white)
        elif low.startswith("übersprungen") or low.startswith("skipped"):
            item.setBackground(Qt.darkYellow)
            item.setForeground(Qt.black)
        elif low.startswith("wartet") or low.startswith("waiting"):
            item.setBackground(Qt.darkCyan)
            item.setForeground(Qt.white)
        else:
            item.setBackground(Qt.transparent)
            item.setForeground(Qt.white)

    def _row_matches_filters(self, row: int) -> bool:
        if row < 0 or row >= len(self.entries):
            return True
        entry = self.entries[row]
        name_filter = self.filter_name_edit.text().strip().lower()
        ext_filter = self._filter_ext_value().strip().lower()
        filename = entry.relative_path.name.lower()
        ext = entry.relative_path.suffix.lower()

        if name_filter and name_filter not in filename:
            return False
        if ext_filter and ext_filter != "*" and ext != ext_filter:
            return False
        return True

    def apply_table_filters(self) -> None:
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, not self._row_matches_filters(row))
        self.refresh_summary()

    def select_all_rows(self) -> None:
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
        self.refresh_summary()

    def select_no_rows(self) -> None:
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self.refresh_summary()

    def apply_selected_preset(self) -> None:
        name = self._preset_value()
        preset = self._all_presets().get(name)
        if not preset:
            return
        preset_use = dict(preset)
        container = str(preset_use.get("container", "mp4"))
        preferred_encoder = str(preset_use.get("video_encoder", "libx264"))
        resolved_encoder = self._resolve_encoder_with_fallback(preferred_encoder, container)
        if resolved_encoder != preferred_encoder:
            preset_use["video_encoder"] = resolved_encoder
            self.append_log(
                f"[Preset] Encoder-Fallback: {preferred_encoder} nicht verfuegbar, nutze {resolved_encoder}."
            )
        self._set_combo_value(self.export_mode_combo, preset.get("export_mode", "Video + Audio"))
        self._set_combo_value(self.container_combo, preset_use["container"])
        self._set_combo_value(self.video_encoder_combo, preset_use["video_encoder"])
        self._set_combo_value(self.audio_codec_combo, preset_use["audio_codec"])
        self._set_combo_value(self.quality_combo, preset_use["quality"])
        self._set_combo_value(self.amf_quality_combo, preset_use.get("amf_quality", "quality"))
        self.amf_bitrate_spin.setValue(int(preset_use.get("amf_bitrate_k", self.amf_bitrate_spin.value())))
        self.amf_maxrate_spin.setValue(int(preset_use.get("amf_maxrate_k", self.amf_maxrate_spin.value())))
        self.amf_bufsize_spin.setValue(int(preset_use.get("amf_bufsize_k", self.amf_bufsize_spin.value())))
        self.active_preset_name = name
        self.active_preset_options = dict(preset_use)
        self.active_preset_options.setdefault("export_mode", "Video + Audio")
        self._update_export_ui_by_mode()
        self._update_amf_controls()
        self._check_conflicts_after_setting_change()
        self.append_log(f"Preset angewendet: {name}")
        self.refresh_summary()
        self.save_config()

    def _invalidate_preset_lock(self, *_args) -> None:
        if self.active_preset_name is None:
            return
        self.active_preset_name = None
        self.active_preset_options = None
        self.append_log("[Info] Preset-Lock aufgehoben (manuelle Aenderung erkannt).")
        self.refresh_summary()

    def _selected_rows(self, only_visible: bool = False) -> List[int]:
        rows = []
        for row in range(self.table.rowCount()):
            if only_visible and self.table.isRowHidden(row):
                continue
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                rows.append(row)
        return rows

    def _check_conflicts_after_setting_change(self) -> None:
        try:
            rows = self._selected_rows(only_visible=self.only_visible_check.isChecked())
            if not rows:
                return
            options = self._build_effective_options_from_ui()
            if self.active_preset_options:
                options.update(self.active_preset_options)
            conflicts = self._compute_target_conflicts(rows, options)
            if conflicts:
                self.append_log(f"[Warnung] Zielkonflikte nach Einstellungswechsel erkannt: {len(conflicts)}")
        except Exception:
            return

    def _compute_target_conflicts(self, rows: List[int], options: Dict) -> List[Path]:
        conflicts: List[Path] = []
        for row in rows:
            if row < 0 or row >= len(self.entries):
                continue
            out_path = self._preview_output_path(self.entries[row], options)
            if out_path.exists():
                conflicts.append(out_path)
        return conflicts

    def _estimated_audio_kbps(self, audio_codec: str, quality: str) -> int:
        q_map = {"Schnell": 128, "Gut": 160, "Beste Qualität": 192, "Klein": 96}
        if audio_codec == "copy":
            return 192
        if audio_codec == "aac stereo":
            return 192
        if audio_codec == "aac 320k stereo":
            return 320
        if audio_codec == "aac 5.1":
            return 384
        if audio_codec == "mp3":
            return q_map.get(quality, 160)
        if audio_codec == "opus":
            return 128
        if audio_codec == "flac":
            return 900
        if audio_codec == "wav pcm_s16le":
            return 1411
        if audio_codec == "wma":
            return 192
        return 160

    def _estimated_video_kbps(self, entry: VideoEntry, options: Dict) -> int:
        encoder = str(options.get("video_encoder", "libx264"))
        quality = str(options.get("quality", "Gut"))
        auto_bitrate = bool(options.get("auto_bitrate", False))

        if encoder in {"h264_amf", "hevc_amf"} and not auto_bitrate:
            return int(options.get("amf_bitrate_k", 8000))

        base_k, _, _ = bitrate_profile_for_resolution(entry.width, entry.height)
        if auto_bitrate:
            return base_k

        quality_factor = {"Schnell": 0.9, "Gut": 1.0, "Beste Qualität": 1.25, "Klein": 0.7}.get(quality, 1.0)
        encoder_factor = 1.0
        if encoder in {"libx265", "hevc_amf", "hevc_nvenc", "hevc_qsv", "libvpx-vp9"}:
            encoder_factor = 0.8
        elif encoder in {"libvpx"}:
            encoder_factor = 0.9
        elif encoder in {"mpeg2video", "wmv2"}:
            encoder_factor = 1.2
        return max(300, int(base_k * quality_factor * encoder_factor))

    def _estimate_entry_size_bytes(self, entry: VideoEntry, options: Dict) -> int:
        mode = str(options.get("export_mode", "Video + Audio"))
        audio_codec = str(options.get("audio_codec", "aac stereo"))
        quality = str(options.get("quality", "Gut"))
        duration = max(0.0, float(entry.duration or 0.0))
        if duration <= 0.0:
            return 0
        if mode == "Nur Audio":
            total_kbps = self._estimated_audio_kbps(audio_codec, quality)
        elif mode == "Nur Video":
            total_kbps = self._estimated_video_kbps(entry, options)
        else:
            total_kbps = self._estimated_video_kbps(entry, options) + self._estimated_audio_kbps(audio_codec, quality)
        return int(duration * (total_kbps * 1000.0 / 8.0))

    def _refresh_estimated_sizes_in_table(self, options: Dict) -> None:
        if not hasattr(self, "table"):
            return
        for row in range(self.table.rowCount()):
            if row < 0 or row >= len(self.entries):
                continue
            status_item = self.table.item(row, 9)
            size_item = self.table.item(row, 13)
            if not status_item or not size_item:
                continue
            status = status_item.text().lower()
            if status.startswith("läuft") or status.startswith("running") or status.startswith("ok") or status.startswith("fehler") or status.startswith("error") or status.startswith("übersprungen") or status.startswith("skipped"):
                continue
            est_bytes = self._estimate_entry_size_bytes(self.entries[row], options)
            size_item.setText(f"~{self._human_bytes(est_bytes)}")

    @staticmethod
    def _human_bytes(num_bytes: int) -> str:
        if num_bytes <= 0:
            return "-"
        value = float(num_bytes)
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if value < 1024.0 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{num_bytes} B"

    def _build_effective_options_from_ui(self) -> Dict:
        return {
            "export_mode": self._export_mode_value(),
            "container": self.container_combo.currentText(),
            "video_encoder": self.video_encoder_combo.currentText(),
            "audio_codec": self.audio_codec_combo.currentText(),
            "quality": self._quality_value(),
            "amf_quality": self.amf_quality_combo.currentText(),
            "amf_bitrate_k": self.amf_bitrate_spin.value(),
            "amf_maxrate_k": self.amf_maxrate_spin.value(),
            "amf_bufsize_k": self.amf_bufsize_spin.value(),
            "overwrite_existing": self.overwrite_existing_check.isChecked(),
            "conflict_policy": self._conflict_value(),
            "name_prefix": self.name_prefix_edit.text(),
            "name_suffix": self.name_suffix_edit.text(),
            "name_timestamp": self.name_timestamp_check.isChecked(),
            "mirror_subfolders": self.mirror_subfolders_check.isChecked(),
            "test_run_30s": self.test_run_check.isChecked(),
            "auto_bitrate": False,
            "compatibility": False,
            "video_preset_override": None,
            "video_crf_override": None,
        }

    def _preview_output_path(self, entry: VideoEntry, options: Dict) -> Path:
        container = str(options.get("container", "mp4"))
        mirror = bool(options.get("mirror_subfolders", True))
        target_root = Path(self.target_edit.text().strip())
        rel_parent = entry.relative_path.parent if mirror else Path("")
        out_dir = target_root / rel_parent
        stem = entry.source_path.stem
        prefix = str(options.get("name_prefix", "") or "")
        suffix = str(options.get("name_suffix", "") or "")
        if bool(options.get("name_timestamp", False)):
            suffix = f"{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        out_name = f"{prefix}{stem}{suffix}.{container}"
        return out_dir / out_name

    def _get_available_encoders(self) -> Optional[set]:
        if self.available_encoders_cache is not None:
            return self.available_encoders_cache
        if not self.ffmpeg_path:
            return None
        try:
            cmd = [self.ffmpeg_path, "-hide_banner", "-encoders"]
            completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
            encoders = set()
            for line in completed.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Encoders:") or line.startswith("------"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    encoders.add(parts[1].strip())
            self.available_encoders_cache = encoders
            return encoders
        except Exception as exc:
            self.append_log(f"[Warnung] Encoder-Pruefung fehlgeschlagen: {exc}")
            return None

    def _get_available_decoders(self) -> Optional[set]:
        if self.available_decoders_cache is not None:
            return self.available_decoders_cache
        if not self.ffmpeg_path:
            return None
        try:
            cmd = [self.ffmpeg_path, "-hide_banner", "-decoders"]
            completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
            decoders = set()
            for line in completed.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Decoders:") or line.startswith("------"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    decoders.add(parts[1].strip())
            self.available_decoders_cache = decoders
            return decoders
        except Exception as exc:
            self.append_log(f"[Warnung] Decoder-Pruefung fehlgeschlagen: {exc}")
            return None

    @staticmethod
    def _state_badge(ok: bool) -> str:
        if ok:
            return "<span style='color:#127a2f; font-weight:600;'>JA</span>"
        return "<span style='color:#a11b1b; font-weight:600;'>NEIN</span>"

    @staticmethod
    def _run_text_command(cmd: List[str], timeout: int = 8) -> str:
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = (completed.stdout or "").strip()
            if out:
                return out
            return (completed.stderr or "").strip()
        except Exception:
            return ""

    def _detect_system_vendors(self) -> Dict[str, bool]:
        cpu_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name) -join '; '",
        ]
        gpu_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join '; '",
        ]
        cpu_text = self._run_text_command(cpu_cmd).lower()
        gpu_text = self._run_text_command(gpu_cmd).lower()
        return {
            "cpu_amd": ("amd" in cpu_text) or ("ryzen" in cpu_text) or ("epyc" in cpu_text),
            "cpu_intel": ("intel" in cpu_text) or ("xeon" in cpu_text) or ("core(tm)" in cpu_text),
            "gpu_amd": ("amd" in gpu_text) or ("radeon" in gpu_text),
            "gpu_nvidia": ("nvidia" in gpu_text) or ("geforce" in gpu_text) or ("quadro" in gpu_text) or ("rtx" in gpu_text),
            "gpu_intel": ("intel" in gpu_text) or ("arc" in gpu_text) or ("iris" in gpu_text) or ("uhd graphics" in gpu_text),
        }

    def _runtime_test_encoder(self, encoder: str) -> bool:
        if not self.ffmpeg_path:
            return False
        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:sample_rate=48000",
            "-t",
            "1",
            "-c:v",
            encoder,
        ]
        if encoder in {"h264_amf", "hevc_amf"}:
            cmd.extend(["-quality", "speed", "-rc", "vbr_peak", "-b:v", "1200k", "-maxrate", "1800k", "-bufsize", "2400k", "-pix_fmt", "yuv420p"])
        elif encoder in {"h264_nvenc", "hevc_nvenc"}:
            cmd.extend(["-preset", "p4", "-rc", "vbr", "-b:v", "1200k"])
        elif encoder in {"h264_qsv", "hevc_qsv"}:
            cmd.extend(["-global_quality", "26", "-b:v", "1200k", "-vf", "format=nv12"])
        cmd.extend(["-c:a", "aac", "-b:a", "96k", "-f", "null", "NUL"])
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            return completed.returncode == 0
        except Exception:
            return False

    def _get_runtime_hw_status(self, force: bool = False) -> Dict[str, bool]:
        if self.hw_runtime_status_cache is not None and not force:
            return dict(self.hw_runtime_status_cache)
        enc = self._get_available_encoders() or set()
        has_amf_build = any(x in enc for x in {"h264_amf", "hevc_amf"})
        has_nvenc_build = any(x in enc for x in {"h264_nvenc", "hevc_nvenc"})
        has_qsv_build = any(x in enc for x in {"h264_qsv", "hevc_qsv"})

        amf_runtime = False
        nvenc_runtime = False
        qsv_runtime = False

        if has_amf_build:
            amf_runtime = self._runtime_test_encoder("hevc_amf") or self._runtime_test_encoder("h264_amf")
        if has_nvenc_build:
            nvenc_runtime = self._runtime_test_encoder("hevc_nvenc") or self._runtime_test_encoder("h264_nvenc")
        if has_qsv_build:
            qsv_runtime = self._runtime_test_encoder("hevc_qsv") or self._runtime_test_encoder("h264_qsv")

        status = {
            "amf_build": has_amf_build,
            "nvenc_build": has_nvenc_build,
            "qsv_build": has_qsv_build,
            "amf_runtime": amf_runtime,
            "nvenc_runtime": nvenc_runtime,
            "qsv_runtime": qsv_runtime,
        }
        self.hw_runtime_status_cache = dict(status)
        return status

    def _force_refresh_hardware_codec_tab(self) -> None:
        self.available_encoders_cache = None
        self.available_decoders_cache = None
        self.hw_runtime_status_cache = None
        self._refresh_hardware_codec_tab()

    def _refresh_hardware_codec_tab(self) -> None:
        if not hasattr(self, "hardware_status_label"):
            return

        enc = self._get_available_encoders() or set()
        dec = self._get_available_decoders() or set()
        vendors = self._detect_system_vendors()
        rt = self._get_runtime_hw_status(force=False)

        has_cpu = any(x in enc for x in {"libx264", "libx265"})

        ffmpeg_text = self.ffmpeg_path or "-"
        ffprobe_text = self.ffprobe_path or "-"
        status_html = (
            f"<b>ffmpeg:</b> {ffmpeg_text}<br>"
            f"<b>ffprobe:</b> {ffprobe_text}<br><br>"
            f"<b>{self._t('Active target profile for auto presets', 'Aktives Zielprofil fuer Auto-Presets')}:</b> {self.device_profile_combo.currentText()}<br>"
            f"<b>{self._t('CPU AMD detected', 'CPU AMD erkannt')}:</b> {self._state_badge(vendors.get('cpu_amd', False))}<br>"
            f"<b>{self._t('CPU Intel detected', 'CPU Intel erkannt')}:</b> {self._state_badge(vendors.get('cpu_intel', False))}<br>"
            f"<b>{self._t('GPU AMD detected', 'GPU AMD erkannt')}:</b> {self._state_badge(vendors.get('gpu_amd', False))}<br>"
            f"<b>{self._t('GPU NVIDIA detected', 'GPU NVIDIA erkannt')}:</b> {self._state_badge(vendors.get('gpu_nvidia', False))}<br>"
            f"<b>{self._t('AMD AMF runtime-capable', 'AMD AMF runtime-faehig')}:</b> {self._state_badge(rt.get('amf_runtime', False))} "
            f"({self._t('Build', 'Build')}: {self._state_badge(rt.get('amf_build', False))})<br>"
            f"<b>{self._t('NVIDIA NVENC runtime-capable', 'NVIDIA NVENC runtime-faehig')}:</b> {self._state_badge(rt.get('nvenc_runtime', False))} "
            f"({self._t('Build', 'Build')}: {self._state_badge(rt.get('nvenc_build', False))})<br>"
            f"<b>{self._t('Intel QSV runtime-capable', 'Intel QSV runtime-faehig')}:</b> {self._state_badge(rt.get('qsv_runtime', False))} "
            f"({self._t('Build', 'Build')}: {self._state_badge(rt.get('qsv_build', False))})<br>"
            f"<b>{self._t('CPU x264/x265', 'CPU x264/x265')}:</b> {self._state_badge(has_cpu)}<br>"
            f"<b>{self._t('Detected encoders', 'Gefundene Encoder')}:</b> {len(enc)} | <b>{self._t('Detected decoders', 'Gefundene Decoder')}:</b> {len(dec)}"
        )
        self.hardware_status_label.setText(status_html)
        current_generated = [n for n in self.generated_auto_preset_names if n in self.custom_presets]
        top5_count = sum(1 for n in current_generated if n.startswith("AUTO TOP5 "))
        auto_count = len(current_generated) - top5_count
        self.generated_presets_count_label.setText(
            self._t(
                f"Generated auto presets: {len(current_generated)} (AUTO: {auto_count}, TOP5: {top5_count})",
                f"Generierte Auto-Presets: {len(current_generated)} (AUTO: {auto_count}, TOP5: {top5_count})",
            )
        )

        audio_encoder_map = {
            "copy": "",
            "aac stereo": "aac",
            "aac 320k stereo": "aac",
            "aac 5.1": "aac",
            "opus": "libopus",
            "mp3": "libmp3lame",
            "flac": "flac",
            "wav pcm_s16le": "pcm_s16le",
            "wma": "wmav2",
        }
        video_ok = [v for v in VIDEO_ENCODERS if v in enc]
        video_missing = [v for v in VIDEO_ENCODERS if v not in enc]
        audio_ok = []
        audio_missing = []
        for ui_name in AUDIO_CODECS:
            enc_name = audio_encoder_map.get(ui_name, "")
            if not enc_name:
                audio_ok.append(ui_name)
                continue
            if enc_name in enc:
                audio_ok.append(ui_name)
            else:
                audio_missing.append(ui_name)

        container_lines = []
        for fmt, choices in VIDEO_ENCODERS_BY_FORMAT.items():
            valid = [c for c in choices if c in enc]
            if not valid:
                valid = ["-"]
            container_lines.append(f"  - {fmt}: {', '.join(valid)}")

        lines = [
            self._t(
                "Video encoders (supported by tool and available in your ffmpeg build):",
                "Video-Encoder (im Tool moeglich, in deiner ffmpeg-Build verfuegbar):",
            ),
            "  " + (", ".join(video_ok) if video_ok else "-"),
            "",
            self._t(
                "Video encoders (supported by tool but missing in your ffmpeg build):",
                "Video-Encoder (im Tool moeglich, aber in deiner ffmpeg-Build nicht verfuegbar):",
            ),
            "  " + (", ".join(video_missing) if video_missing else "-"),
            "",
            self._t(
                "Audio options (supported by tool and available in your ffmpeg build):",
                "Audio-Optionen (im Tool moeglich, in deiner ffmpeg-Build verfuegbar):",
            ),
            "  " + (", ".join(audio_ok) if audio_ok else "-"),
            "",
            self._t(
                "Audio options (supported by tool but missing in your ffmpeg build):",
                "Audio-Optionen (im Tool moeglich, aber in deiner ffmpeg-Build nicht verfuegbar):",
            ),
            "  " + (", ".join(audio_missing) if audio_missing else "-"),
            "",
            self._t("Container -> available video encoders:", "Container -> verfuegbare Video-Encoder:"),
            *container_lines,
        ]
        self.codec_report_view.setPlainText("\n".join(lines))

    @staticmethod
    def _is_gpu_encoder(encoder: str) -> bool:
        return encoder in {
            "h264_amf",
            "hevc_amf",
            "h264_nvenc",
            "hevc_nvenc",
            "h264_qsv",
            "hevc_qsv",
        }

    def _best_encoder_for_container(self, fmt: str, available_enc: set, profile: str = "Allgemein") -> Optional[str]:
        choices = VIDEO_ENCODERS_BY_FORMAT.get(fmt, VIDEO_ENCODERS)
        if profile == "Smartphone":
            priority = [
                "h264_amf",
                "h264_nvenc",
                "h264_qsv",
                "libx264",
                "hevc_amf",
                "hevc_nvenc",
                "hevc_qsv",
                "libx265",
                "libvpx-vp9",
                "libvpx",
                "mpeg2video",
                "wmv2",
            ]
        elif profile == "Archiv":
            priority = [
                "libx265",
                "hevc_amf",
                "hevc_nvenc",
                "hevc_qsv",
                "libvpx-vp9",
                "libx264",
                "h264_amf",
                "h264_nvenc",
                "h264_qsv",
                "libvpx",
                "mpeg2video",
                "wmv2",
            ]
        elif profile == "YouTube":
            priority = [
                "libx264",
                "h264_amf",
                "h264_nvenc",
                "h264_qsv",
                "libx265",
                "hevc_amf",
                "hevc_nvenc",
                "hevc_qsv",
                "libvpx-vp9",
                "libvpx",
                "mpeg2video",
                "wmv2",
            ]
        else:
            priority = [
                "hevc_amf",
                "hevc_nvenc",
                "hevc_qsv",
                "h264_amf",
                "h264_nvenc",
                "h264_qsv",
                "libx265",
                "libx264",
                "libvpx-vp9",
                "libvpx",
                "mpeg2video",
                "wmv2",
            ]
        for enc in priority:
            if enc in choices and enc in available_enc:
                return enc
        return None

    def _default_audio_for_container(self, fmt: str, available_enc: set) -> str:
        has_aac = "aac" in available_enc
        has_opus = "libopus" in available_enc
        has_mp3 = "libmp3lame" in available_enc

        if fmt == "webm":
            if has_opus:
                return "opus"
            return "copy"
        if fmt in {"mp4", "mov", "flv"}:
            if has_aac:
                return "aac stereo"
            if has_mp3:
                return "mp3"
            return "copy"
        if fmt in {"avi", "asf", "mpg"}:
            if has_aac:
                return "aac stereo"
            if has_mp3:
                return "mp3"
            return "copy"
        if fmt == "mkv":
            if has_aac:
                return "aac stereo"
            if has_opus:
                return "opus"
            return "copy"
        if has_aac:
            return "aac stereo"
        if has_mp3:
            return "mp3"
        return "copy"

    def _best_audio_codec_for_audio_format(self, fmt: str, available_enc: set) -> Optional[str]:
        has_aac = "aac" in available_enc
        has_opus = "libopus" in available_enc
        has_mp3 = "libmp3lame" in available_enc
        has_flac = "flac" in available_enc
        has_pcm = "pcm_s16le" in available_enc
        has_wma = "wmav2" in available_enc

        if fmt == "mp3":
            return "mp3" if has_mp3 else None
        if fmt == "wav":
            return "wav pcm_s16le" if has_pcm else None
        if fmt == "flac":
            return "flac" if has_flac else None
        if fmt == "m4a":
            return "aac stereo" if has_aac else None
        if fmt == "aac":
            return "aac stereo" if has_aac else None
        if fmt == "opus":
            return "opus" if has_opus else None
        if fmt == "wma":
            return "wma" if has_wma else None
        return None

    def _apply_device_profile_to_preset(self, preset: Dict) -> Dict:
        profile = self._device_profile_value()
        p = dict(preset)
        mode = str(p.get("export_mode", "Video + Audio"))
        container = str(p.get("container", "mp4"))

        if profile == "Smartphone":
            if mode != "Nur Video":
                p["audio_codec"] = "aac stereo"
            if mode != "Nur Audio":
                p["quality"] = "Gut"
                if container == "mp4":
                    p["compatibility"] = True
        elif profile == "TV":
            if mode != "Nur Video":
                p["audio_codec"] = "aac stereo"
            if mode != "Nur Audio":
                p["quality"] = "Gut"
        elif profile == "YouTube":
            if mode != "Nur Video":
                p["audio_codec"] = "aac stereo"
            if mode != "Nur Audio":
                p["quality"] = "Gut"
                if container == "mp4":
                    p["compatibility"] = True
        elif profile == "Archiv":
            if mode == "Video + Audio" and container in {"mkv", "mov"}:
                p["audio_codec"] = "copy"
            if mode != "Nur Audio":
                p["quality"] = "Beste Qualität"
        return p

    def generate_auto_presets(self) -> None:
        enc = self._get_available_encoders() or set()
        if not enc:
            self.msg_warn("Auto-Presets", "Keine Encoderinformationen verfügbar.")
            return
        profile = self._device_profile_value()
        profile_label = self.device_profile_combo.currentText()

        existing_auto = [k for k in self.custom_presets.keys() if k in set(self.generated_auto_preset_names)]
        if existing_auto:
            if not self.msg_question_yes_no("Auto-Presets", f"Es existieren bereits {len(existing_auto)} Auto-Presets. Diese ersetzen?"):
                return
            for name in existing_auto:
                self.custom_presets.pop(name, None)
            self.generated_auto_preset_names = [n for n in self.generated_auto_preset_names if n not in set(existing_auto)]

        created = 0

        # Video + Audio Presets je Container
        for fmt in VIDEO_FORMAT_PROFILES.keys():
            best = self._best_encoder_for_container(fmt, enc, profile)
            if not best:
                continue
            audio_codec = self._default_audio_for_container(fmt, enc)
            auto_bitrate = self._is_gpu_encoder(best)
            if best == "libx265":
                quality = "Beste Qualität"
            elif best == "libx264":
                quality = "Gut"
            else:
                quality = "Gut"
            name = f"AUTO {profile_label} {fmt.upper()} Video+Audio ({best})"
            preset_data = {
                "export_mode": "Video + Audio",
                "container": fmt,
                "video_encoder": best,
                "audio_codec": audio_codec,
                "quality": quality,
                "amf_quality": "quality",
                "amf_bitrate_k": 8000,
                "amf_maxrate_k": 12000,
                "amf_bufsize_k": 16000,
                "auto_bitrate": auto_bitrate,
                "video_preset_override": None,
                "video_crf_override": None,
                "compatibility": fmt == "mp4" and best == "libx264",
            }
            self.custom_presets[name] = self._apply_device_profile_to_preset(preset_data)
            if name not in self.generated_auto_preset_names:
                self.generated_auto_preset_names.append(name)
            created += 1

        # Nur Video Presets je Container
        for fmt in VIDEO_FORMAT_PROFILES.keys():
            best = self._best_encoder_for_container(fmt, enc, profile)
            if not best:
                continue
            auto_bitrate = self._is_gpu_encoder(best)
            name = f"AUTO {profile_label} {fmt.upper()} Nur Video ({best})"
            preset_data = {
                "export_mode": "Nur Video",
                "container": fmt,
                "video_encoder": best,
                "audio_codec": "copy",
                "quality": "Gut",
                "amf_quality": "quality",
                "amf_bitrate_k": 8000,
                "amf_maxrate_k": 12000,
                "amf_bufsize_k": 16000,
                "auto_bitrate": auto_bitrate,
                "video_preset_override": None,
                "video_crf_override": None,
                "compatibility": fmt == "mp4" and best == "libx264",
            }
            self.custom_presets[name] = self._apply_device_profile_to_preset(preset_data)
            if name not in self.generated_auto_preset_names:
                self.generated_auto_preset_names.append(name)
            created += 1

        # Nur Audio Presets je Audioformat
        for fmt in AUDIO_FORMAT_PROFILES.keys():
            codec = self._best_audio_codec_for_audio_format(fmt, enc)
            if not codec:
                continue
            name = f"AUTO {profile_label} {fmt.upper()} Nur Audio ({codec})"
            preset_data = {
                "export_mode": "Nur Audio",
                "container": fmt,
                "video_encoder": "libx264",
                "audio_codec": codec,
                "quality": "Gut",
                "amf_quality": "quality",
                "amf_bitrate_k": 8000,
                "amf_maxrate_k": 12000,
                "amf_bufsize_k": 16000,
                "auto_bitrate": False,
                "video_preset_override": None,
                "video_crf_override": None,
                "compatibility": False,
            }
            self.custom_presets[name] = self._apply_device_profile_to_preset(preset_data)
            if name not in self.generated_auto_preset_names:
                self.generated_auto_preset_names.append(name)
            created += 1

        self._reload_preset_combo()
        self.save_config()
        self._refresh_hardware_codec_tab()
        self.append_log(f"[Preset] Auto-Presets erzeugt: {created}")
        self.msg_info("Auto-Presets", f"{created} kompatible Auto-Presets wurden erstellt.")

    def generate_top5_auto_presets(self) -> None:
        enc = self._get_available_encoders() or set()
        if not enc:
            self.msg_warn("Top 5 Auto-Presets", "Keine Encoderinformationen verfügbar.")
            return
        profile = self._device_profile_value()
        profile_label = self.device_profile_combo.currentText()

        existing_top5 = [k for k in self.custom_presets.keys() if k in set(self.generated_auto_preset_names) and k.startswith("AUTO TOP5 ")]
        if existing_top5:
            if not self.msg_question_yes_no("Top 5 Auto-Presets", f"Es existieren bereits {len(existing_top5)} Top-5-Presets. Diese ersetzen?"):
                return
            for name in existing_top5:
                self.custom_presets.pop(name, None)
            self.generated_auto_preset_names = [n for n in self.generated_auto_preset_names if n not in set(existing_top5)]

        def add(name: str, export_mode: str, container: str, encoder: str, audio_codec: str, quality: str) -> bool:
            if not encoder or (export_mode != "Nur Audio" and encoder not in enc):
                return False
            auto_bitrate = self._is_gpu_encoder(encoder)
            preset_data = {
                "export_mode": export_mode,
                "container": container,
                "video_encoder": encoder,
                "audio_codec": audio_codec,
                "quality": quality,
                "amf_quality": "quality",
                "amf_bitrate_k": 8000,
                "amf_maxrate_k": 12000,
                "amf_bufsize_k": 16000,
                "auto_bitrate": auto_bitrate if export_mode != "Nur Audio" else False,
                "video_preset_override": None,
                "video_crf_override": None,
                "compatibility": container == "mp4" and encoder == "libx264",
            }
            self.custom_presets[name] = self._apply_device_profile_to_preset(preset_data)
            if name not in self.generated_auto_preset_names:
                self.generated_auto_preset_names.append(name)
            return True

        created = 0
        best_mp4 = self._best_encoder_for_container("mp4", enc, profile)
        best_mkv = self._best_encoder_for_container("mkv", enc, profile)
        best_webm = self._best_encoder_for_container("webm", enc, profile)
        cpu_encoder = "libx265" if "libx265" in enc else ("libx264" if "libx264" in enc else (best_mkv or best_mp4 or ""))

        if best_mp4:
            audio_mp4 = self._default_audio_for_container("mp4", enc)
            if add(f"AUTO TOP5 {profile_label} 1 MP4 Alltag", "Video + Audio", "mp4", best_mp4, audio_mp4, "Gut"):
                created += 1
        if best_mkv:
            audio_mkv = self._default_audio_for_container("mkv", enc)
            q = "Beste Qualität" if best_mkv in {"libx265", "hevc_amf", "hevc_nvenc", "hevc_qsv"} else "Gut"
            if add(f"AUTO TOP5 {profile_label} 2 MKV Qualitaet", "Video + Audio", "mkv", best_mkv, audio_mkv, q):
                created += 1
        if cpu_encoder:
            if add(f"AUTO TOP5 {profile_label} 3 MKV Archiv CPU", "Video + Audio", "mkv", cpu_encoder, "copy", "Beste Qualität"):
                created += 1
        if best_webm:
            audio_webm = self._default_audio_for_container("webm", enc)
            if add(f"AUTO TOP5 {profile_label} 4 WebM Web", "Video + Audio", "webm", best_webm, audio_webm, "Gut"):
                created += 1

        audio_candidates = [
            ("mp3", self._best_audio_codec_for_audio_format("mp3", enc)),
            ("flac", self._best_audio_codec_for_audio_format("flac", enc)),
            ("wav", self._best_audio_codec_for_audio_format("wav", enc)),
            ("m4a", self._best_audio_codec_for_audio_format("m4a", enc)),
        ]
        chosen_audio_fmt = None
        chosen_audio_codec = None
        for fmt, codec in audio_candidates:
            if codec:
                chosen_audio_fmt = fmt
                chosen_audio_codec = codec
                break
        if chosen_audio_fmt and chosen_audio_codec:
            if add(f"AUTO TOP5 {profile_label} 5 Nur Audio", "Nur Audio", chosen_audio_fmt, "libx264", chosen_audio_codec, "Gut"):
                created += 1

        self._reload_preset_combo()
        self.save_config()
        self._refresh_hardware_codec_tab()
        self.append_log(f"[Preset] Top-5 Auto-Presets erzeugt: {created}")
        self.msg_info("Top 5 Auto-Presets", f"{created} empfohlene Auto-Presets wurden erstellt.")

    def run_hw_stability_test(self) -> None:
        if not self.ffmpeg_path:
            self.msg_warn("Hardware-Stabilitaetstest", "ffmpeg wurde nicht gefunden.")
            return
        enc = self._get_available_encoders() or set()
        to_test = [e for e in ["h264_amf", "hevc_amf", "h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv"] if e in enc]
        if not to_test:
            self.msg_info("Hardware-Stabilitaetstest", "Keine Hardware-Encoder in dieser ffmpeg-Build gefunden.")
            return
        if not self.msg_question_yes_no("Hardware-Stabilitaetstest", f"Es werden {len(to_test)} Kurztests a 10 Sekunden ausgefuehrt. Fortfahren?"):
            return

        result_lines = []
        for enc_name in to_test:
            cmd = [
                self.ffmpeg_path,
                "-hide_banner",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=1280x720:rate=30",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:sample_rate=48000",
                "-t",
                "10",
                "-c:v",
                enc_name,
            ]
            if enc_name in {"h264_amf", "hevc_amf"}:
                cmd.extend(["-quality", "speed", "-rc", "vbr_peak", "-b:v", "2500k", "-maxrate", "3500k", "-bufsize", "5000k", "-pix_fmt", "yuv420p"])
            elif enc_name in {"h264_nvenc", "hevc_nvenc"}:
                cmd.extend(["-preset", "p4", "-rc", "vbr", "-b:v", "2500k"])
            elif enc_name in {"h264_qsv", "hevc_qsv"}:
                cmd.extend(["-global_quality", "26", "-b:v", "2500k"])
            cmd.extend(["-c:a", "aac", "-b:a", "128k", "-f", "null", "NUL"])

            self.append_log(f"[HW-Test] Starte {enc_name} ...")
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode == 0:
                line = f"{enc_name}: OK"
                self.append_log(f"[HW-Test] {line}")
            else:
                hint = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else f"Exit {completed.returncode}"
                line = f"{enc_name}: FEHLER ({hint})"
                self.append_log(f"[HW-Test] {line}")
            result_lines.append(line)

        self.msg_info("Hardware-Stabilitaetstest Ergebnis", "\n".join(result_lines))

    def reset_generated_auto_presets(self) -> None:
        names = [n for n in self.generated_auto_preset_names if n in self.custom_presets]
        if not names:
            self.msg_info("Auto-Presets resetten", "Keine generierten Auto-Presets vorhanden.")
            return
        if not self.msg_question_yes_no("Auto-Presets resetten", f"Sollen {len(names)} generierte Auto-Presets entfernt werden?"):
            return
        for name in names:
            self.custom_presets.pop(name, None)
        removed = set(names)
        self.generated_auto_preset_names = [n for n in self.generated_auto_preset_names if n not in removed]
        self.favorite_presets = [p for p in self.favorite_presets if p not in removed]
        self._reload_preset_combo()
        self.save_config()
        self.append_log(f"[Preset] Generierte Auto-Presets entfernt: {len(names)}")
        self.msg_info("Auto-Presets resetten", f"{len(names)} generierte Auto-Presets wurden entfernt.")

    def _resolve_encoder_with_fallback(self, preferred: str, container: str) -> str:
        available = self._get_available_encoders()
        if not available:
            return preferred
        if preferred in available:
            return preferred

        container_choices = VIDEO_ENCODERS_BY_FORMAT.get(container, VIDEO_ENCODERS)
        ordered_fallback = [
            "hevc_amf",
            "hevc_nvenc",
            "hevc_qsv",
            "h264_amf",
            "h264_nvenc",
            "h264_qsv",
            "libx265",
            "libx264",
            "mpeg2video",
            "wmv2",
            "libvpx-vp9",
            "libvpx",
        ]
        allowed = [enc for enc in ordered_fallback if enc in container_choices]
        for enc in allowed:
            if enc in available:
                return enc
        return preferred

    def start_queue(self) -> None:
        if not self.ffmpeg_path:
            self.msg_warn("ffmpeg fehlt", "ffmpeg wurde nicht gefunden.")
            return

        source = Path(self.source_edit.text().strip())
        target = Path(self.target_edit.text().strip())
        if not source.exists() or not source.is_dir():
            self.msg_warn("Ungültiger Quellordner", "Bitte Quellordner prüfen.")
            return
        if not target.exists() or not target.is_dir():
            self.msg_warn("Ungültiger Zielordner", "Bitte Zielordner prüfen.")
            return
        if not self.entries:
            self.msg_warn("Keine Daten", "Bitte zuerst Scan/Analyse durchführen.")
            return

        selected_rows = self._selected_rows(only_visible=self.only_visible_check.isChecked())
        if not selected_rows:
            self.msg_warn("Keine Auswahl", "Bitte mindestens eine Datei markieren.")
            return

        if self.only_changed_check.isChecked():
            changed_rows: List[int] = []
            skipped_unchanged = 0
            for row in selected_rows:
                if row < 0 or row >= len(self.entries):
                    continue
                src = self.entries[row].source_path
                key = str(src.resolve())
                try:
                    mtime = float(src.stat().st_mtime)
                except Exception:
                    changed_rows.append(row)
                    continue
                old = float(self.last_run_mtimes.get(key, 0.0))
                if old <= 0.0 or abs(mtime - old) > 0.000001:
                    changed_rows.append(row)
                else:
                    skipped_unchanged += 1
                    self.table.item(row, 9).setText(self._status_text("skipped"))
                    self._set_row_status_style(row, self._status_text("skipped"))
                    self.table.item(row, 10).setText("100%")
                    self.table.item(row, 12).setText("00:00:00")
            selected_rows = changed_rows
            if skipped_unchanged:
                self.append_log(f"[Info] Unveraendert seit letztem Lauf uebersprungen: {skipped_unchanged}")
            if not selected_rows:
                self.msg_info("Keine geaenderten Dateien", "Es gibt keine geaenderten Dateien seit dem letzten Lauf.")
                return

        options = self._build_effective_options_from_ui()
        if self.active_preset_options:
            options.update(self.active_preset_options)
            self.append_log(f"[Info] Aktiver Preset-Lock fuer Job: {self.active_preset_name}")
        if self.strict_target_check.isChecked():
            conflicts = [str(p) for p in self._compute_target_conflicts(selected_rows, options)]
            if conflicts:
                preview = "\n".join(conflicts[:8])
                if len(conflicts) > 8:
                    preview += f"\n... +{len(conflicts) - 8} weitere"
                self.msg_critical("Start abgebrochen", "Ziel darf nicht ersetzt werden ist aktiv und es gibt vorhandene Zieldateien:\n\n" + preview)
                return
        export_mode = options.get("export_mode", "Video + Audio")
        available_encoders = self._get_available_encoders()
        if export_mode != "Nur Audio":
            encoder_to_check = str(options.get("video_encoder", "")).strip()
            if available_encoders is not None and encoder_to_check and encoder_to_check not in available_encoders:
                self.msg_critical("Encoder nicht verfuegbar", f"Der Encoder '{encoder_to_check}' ist in deiner ffmpeg-Build nicht verfuegbar.")
                return
        if export_mode != "Nur Video":
            audio_codec = str(options.get("audio_codec", "")).strip()
            audio_encoder_map = {
                "mp3": "libmp3lame",
                "opus": "libopus",
                "flac": "flac",
                "aac stereo": "aac",
                "aac 320k stereo": "aac",
                "aac 5.1": "aac",
                "wma": "wmav2",
                "wav pcm_s16le": "pcm_s16le",
                "copy": "",
            }
            enc_name = audio_encoder_map.get(audio_codec, "")
            if enc_name and available_encoders is not None and enc_name not in available_encoders:
                self.msg_critical("Audio-Encoder nicht verfuegbar", f"Der Audio-Encoder '{enc_name}' für '{audio_codec}' ist in deiner ffmpeg-Build nicht verfügbar.")
                return

        for row in selected_rows:
            self.table.item(row, 9).setText(self._status_text("waiting"))
            self.table.item(row, 10).setText("0%")
            self.table.item(row, 11).setText("-")
            self.table.item(row, 12).setText("-")
            self.table.item(row, 13).setText("-")

        self.completed_count = 0
        self.total_count = len(selected_rows)
        self.job_results = []
        self.failed_rows = []
        self.failed_messages = {}
        self.selected_rows_active = list(selected_rows)
        self.selected_rows_runtime = list(selected_rows)
        self.progress_by_row = {row: 0.0 for row in selected_rows}
        self.batch_progress.setValue(0)
        self.batch_progress_log.setValue(0)
        self.batch_label.setText(self._t(f"0 / {self.total_count} completed | Total: 0.0%", f"0 / {self.total_count} abgeschlossen | Gesamt: 0.0%"))
        self.batch_label_log.setText(self._t(f"0 / {self.total_count} completed | Total: 0.0%", f"0 / {self.total_count} abgeschlossen | Gesamt: 0.0%"))

        self.start_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setChecked(False)
        self.pause_btn.setText(self._t("Pause Queue", "Queue pausieren"))
        self.queue_paused = False

        self.active_conversion_thread = QThread(self)
        self.active_conversion_worker = ConvertWorker(
            entries=self.entries,
            selected_rows=selected_rows,
            source_dir=source,
            target_dir=target,
            ffmpeg_path=self.ffmpeg_path,
            options=options,
            max_jobs=self.parallel_spin.value(),
        )
        self.active_conversion_worker.moveToThread(self.active_conversion_thread)

        self.active_conversion_thread.started.connect(self.active_conversion_worker.run)
        self.active_conversion_worker.log.connect(self.append_log)
        self.active_conversion_worker.file_started.connect(self.on_file_started)
        self.active_conversion_worker.file_progress.connect(self.on_file_progress)
        self.active_conversion_worker.file_metrics.connect(self.on_file_metrics)
        self.active_conversion_worker.file_finished.connect(self.on_file_finished)
        self.active_conversion_worker.all_finished.connect(self.on_queue_finished)
        self.active_conversion_worker.all_finished.connect(self.active_conversion_thread.quit)
        self.active_conversion_thread.finished.connect(self.active_conversion_thread.deleteLater)
        self.active_conversion_thread.start()
        self.tabs.setCurrentIndex(2)

        self.save_config()
        self.refresh_summary()

    def stop_queue(self) -> None:
        if self.active_conversion_worker:
            self.active_conversion_worker.stop()
            self.append_log("Stop angefordert. Bereits laufende Dateien werden noch abgeschlossen.")

    def on_file_started(self, row: int) -> None:
        self.table.item(row, 9).setText(self._status_text("running"))
        self._set_row_status_style(row, self._status_text("running"))

    def on_file_progress(self, row: int, value: float) -> None:
        self.table.item(row, 10).setText(f"{value:.1f}%")
        self.progress_by_row[row] = max(0.0, min(100.0, value))
        self._refresh_global_progress()

    def on_file_metrics(self, row: int, speed: str, eta: str, size: str) -> None:
        status = self.table.item(row, 9).text()
        if status.lower().startswith("läuft") or status.lower().startswith("running"):
            self.table.item(row, 9).setText(self._status_text("running"))
            self.table.item(row, 11).setText(speed or "-")
            self.table.item(row, 12).setText(eta or "-")
            self.table.item(row, 13).setText(size or "-")

    def on_file_finished(self, row: int, success: bool, message: str) -> None:
        self.completed_count += 1
        src_name = self.entries[row].source_path.name if 0 <= row < len(self.entries) else str(row)
        if success:
            if message == "SKIPPED_EXISTING":
                self.table.item(row, 9).setText(self._status_text("skipped"))
                self._set_row_status_style(row, self._status_text("skipped"))
                self.table.item(row, 10).setText("100%")
                self.table.item(row, 12).setText("00:00:00")
                self.progress_by_row[row] = 100.0
                self.job_results.append({"row": row, "file": src_name, "status": "skipped", "detail": message})
            else:
                self.table.item(row, 9).setText("OK")
                self._set_row_status_style(row, "OK")
                self.table.item(row, 10).setText("100%")
                self.table.item(row, 12).setText("00:00:00")
                self.progress_by_row[row] = 100.0
                self.job_results.append({"row": row, "file": src_name, "status": "ok", "detail": message})
                if 0 <= row < len(self.entries):
                    src = self.entries[row].source_path
                    try:
                        self.last_run_mtimes[str(src.resolve())] = float(src.stat().st_mtime)
                    except Exception:
                        pass
        else:
            self.table.item(row, 9).setText(self._status_text("error"))
            self._set_row_status_style(row, self._status_text("error"))
            self.failed_rows.append(row)
            self.failed_messages[row] = message
            self.job_results.append({"row": row, "file": src_name, "status": "error", "detail": message})
            current = self.table.item(row, 10).text()
            if not current.endswith("%"):
                self.table.item(row, 10).setText("0%")
                self.progress_by_row[row] = 0.0

        self._refresh_global_progress()

    def on_queue_finished(self) -> None:
        self.append_log("Queue beendet.")
        ok_count = self.total_count - len(self.failed_rows)
        self.append_log(f"[Summary] Erfolgreich: {ok_count} | Fehler: {len(self.failed_rows)} | Gesamt: {self.total_count}")
        if self.failed_rows:
            for row in self.failed_rows:
                src = self.entries[row].source_path.name if 0 <= row < len(self.entries) else str(row)
                msg = self.failed_messages.get(row, "Unbekannter Fehler")
                self.append_log(f"[Summary][Fehler] {src}: {msg}")
        self._refresh_global_progress(force_complete=True)
        self.start_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setChecked(False)
        self.pause_btn.setText(self._t("Pause Queue", "Queue pausieren"))
        self.active_conversion_worker = None
        self.active_conversion_thread = None
        if self.enable_job_report_check.isChecked():
            self._write_job_report()
        self.save_config()

    def _write_job_report(self) -> None:
        target_dir = Path(self.target_edit.text().strip() or Path.home())
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = target_dir / f"ffmpeg_report_{ts}.json"
            payload = {
                "timestamp": ts,
                "source_dir": self.source_edit.text().strip(),
                "target_dir": self.target_edit.text().strip(),
                "summary": {
                    "total": self.total_count,
                    "failed": len(self.failed_rows),
                    "ok": self.total_count - len(self.failed_rows),
                },
                "options": self._build_effective_options_from_ui(),
                "results": self.job_results,
            }
            report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            self.append_log(f"[Report] Job-Report gespeichert: {report_path}")
        except Exception as exc:
            self.append_log(f"[Report][Fehler] Speichern fehlgeschlagen: {exc}")

    def save_log_file(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Log speichern",
            str(Path(self.target_edit.text().strip() or Path.home()) / "ffmpeg-konverter-log.txt"),
            "Textdatei (*.txt);;Alle Dateien (*.*)",
        )
        if not target:
            return
        try:
            Path(target).write_text(self.log_view.toPlainText(), encoding="utf-8")
            self.append_log(f"[Info] Log gespeichert: {target}")
        except Exception as exc:
            self.msg_critical("Log speichern fehlgeschlagen", str(exc))

    def _refresh_global_progress(self, force_complete: bool = False) -> None:
        total = len(self.selected_rows_active)
        if total <= 0:
            self.batch_progress.setValue(0)
            self.batch_progress_log.setValue(0)
            empty_text = self._t("0 / 0 completed", "0 / 0 abgeschlossen")
            self.batch_label.setText(empty_text)
            self.batch_label_log.setText(empty_text)
            return
        if force_complete and self.completed_count >= total:
            total_pct = 100.0
        else:
            summed = sum(self.progress_by_row.get(row, 0.0) for row in self.selected_rows_active)
            total_pct = summed / total
        self.batch_progress.setValue(int(total_pct))
        self.batch_progress_log.setValue(int(total_pct))
        text = self._t(
            f"{self.completed_count} / {total} completed | Total: {total_pct:.1f}%",
            f"{self.completed_count} / {total} abgeschlossen | Gesamt: {total_pct:.1f}%",
        )
        self.batch_label.setText(text)
        self.batch_label_log.setText(text)

    def save_config(self) -> None:
        data = {
            "source_dir": self.source_edit.text().strip(),
            "target_dir": self.target_edit.text().strip(),
            "recursive": self.recursive_check.isChecked(),
            "max_jobs": self.parallel_spin.value(),
            "preset": self._preset_value(),
            "export_mode": self._export_mode_value(),
            "container": self.container_combo.currentText(),
            "video_encoder": self.video_encoder_combo.currentText(),
            "audio_codec": self.audio_codec_combo.currentText(),
            "quality": self._quality_value(),
            "amf_quality": self.amf_quality_combo.currentText(),
            "amf_bitrate_k": self.amf_bitrate_spin.value(),
            "amf_maxrate_k": self.amf_maxrate_spin.value(),
            "amf_bufsize_k": self.amf_bufsize_spin.value(),
            "overwrite_existing": self.overwrite_existing_check.isChecked(),
            "conflict_policy": self._conflict_value(),
            "name_prefix": self.name_prefix_edit.text(),
            "name_suffix": self.name_suffix_edit.text(),
            "name_timestamp": self.name_timestamp_check.isChecked(),
            "mirror_subfolders": self.mirror_subfolders_check.isChecked(),
            "test_run_30s": self.test_run_check.isChecked(),
            "auto_bitrate": self._all_presets().get(self._preset_value(), {}).get("auto_bitrate", False),
            "filter_name": self.filter_name_edit.text(),
            "filter_ext": self._filter_ext_value(),
            "only_visible_selection": self.only_visible_check.isChecked(),
            "only_changed_since_last_run": self.only_changed_check.isChecked(),
            "custom_presets": self.custom_presets,
            "custom_templates": self.custom_templates,
            "favorite_presets": self.favorite_presets,
            "show_favorite_presets_only": self.show_favs_only_check.isChecked(),
            "device_profile": self._device_profile_value(),
            "last_run_mtimes": self.last_run_mtimes,
            "generated_auto_preset_names": self.generated_auto_preset_names,
            "language": self.current_language,
            "enable_hw_auto_profile": self.enable_hw_profile_check.isChecked(),
            "enable_job_report": self.enable_job_report_check.isChecked(),
            "enable_dragdrop": self.enable_dragdrop_check.isChecked(),
            "enable_analysis_export": self.enable_analysis_export_check.isChecked(),
            "strict_target_protection": self.strict_target_check.isChecked(),
        }
        self.config_manager.save(data)

    def closeEvent(self, event):
        try:
            if self.install_worker:
                self.install_worker.stop()
        except Exception:
            pass
        self.save_config()
        super().closeEvent(event)


def main() -> None:
    if os.name != "nt":
        print("Dieses Programm ist fuer Windows vorgesehen.")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
