# Real search with yt_dlp (no official API)
# Filters:
#  - shorts_only: True → include only Shorts (<=60s or shorts URL)
#  - duration_filter: string bucket: "Any", "< 5 min", "5–15 min", "15–30 min", "30–60 min", "> 60 min"

from yt_dlp import YoutubeDL

def _duration_ok(seconds, bucket):
    if seconds is None: return bucket == "Any"
    if bucket == "Any": return True
    if bucket == "< 5 min": return seconds < 5*60
    if bucket == "5–15 min": return 5*60 <= seconds < 15*60
    if bucket == "15–30 min": return 15*60 <= seconds < 30*60
    if bucket == "30–60 min": return 30*60 <= seconds < 60*60
    if bucket == "> 60 min": return seconds >= 60*60
    return True

def yt_search(query: str, max_results: int = 10, shorts_only: bool = False, duration_filter: str = "Any"):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
        "nocheckcertificate": True,
        "default_search": "ytsearch{}".format(max_results),
    }
    results = []
    with YoutubeDL(ydl_opts) as ydl:
        data = ydl.extract_info(query, download=False)
        entries = data.get("entries", []) if isinstance(data, dict) else []
        for e in entries:
            if not e: continue
            url = e.get("webpage_url") or e.get("url")
            title = e.get("title", "Untitled")
            ch = e.get("channel") or e.get("uploader")
            dur = e.get("duration")
            is_short = ("/shorts/" in (url or "").lower()) or (dur is not None and dur <= 60)

            if shorts_only and not is_short:
                continue
            if not _duration_ok(dur, duration_filter):
                continue

            results.append({
                "title": title,
                "url": url,
                "duration": dur,
                "duration_str": _fmt_dur(dur),
                "channel": ch
            })
    return results

def _fmt_dur(s):
    if s is None: return None
    m, s = divmod(int(s), 60)
    h, m = divmod(m, 60)
    if h: return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"
