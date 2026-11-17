import os
import sys
import shutil
import yt_dlp

def find_ffmpeg():
    """FFmpeg bin 디렉토리 경로 탐색"""
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return os.path.dirname(ffmpeg_in_path)

    winget_base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.exists(winget_base):
        for root, dirs, files in os.walk(winget_base):
            if "ffmpeg.exe" in files:
                return root

    candidate_dirs = [
        os.path.join(os.path.dirname(__file__), "ffmpeg"),
        r"C:\ffmpeg\bin",
        os.path.expandvars(r"%LOCALAPPDATA%\ffmpeg\bin"),
        os.path.expandvars(r"%PROGRAMFILES%\ffmpeg\bin"),
    ]
    for d in candidate_dirs:
        if os.path.exists(os.path.join(d, "ffmpeg.exe")):
            return d

    return None


def find_deno():
    """Deno JavaScript 런타임 탐색 (유튜브 JS 챌린지 해결용)"""
    deno_in_path = shutil.which("deno")
    if deno_in_path:
        return os.path.dirname(deno_in_path)

    winget_base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.exists(winget_base):
        for root, dirs, files in os.walk(winget_base):
            if "deno.exe" in files:
                return root

    return None


def init_env():
    """FFmpeg 및 Deno를 PATH 환경변수에 등록"""
    ff = find_ffmpeg()
    if ff and ff not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ff + os.pathsep + os.environ.get("PATH", "")

    dn = find_deno()
    if dn and dn not in os.environ.get("PATH", ""):
        os.environ["PATH"] = dn + os.pathsep + os.environ.get("PATH", "")


init_env()


def format_duration(seconds):
    if not seconds:
        return "알 수 없음"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def format_bytes(b):
    if not b:
        return "0 MB"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def get_video_info(url):
    """
    유튜브 URL 메타정보(제목, 채널, 썸네일, 길이 등) 추출
    """
    init_env()
    ffmpeg_dir = find_ffmpeg()

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': 'in_playlist',
        'remote_components': ['ejs:github'],
    }
    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None, "영상 정보를 찾을 수 없습니다."

            is_playlist = 'entries' in info and bool(info.get('entries'))

            if is_playlist:
                entries = list(info.get('entries', []))
                first_entry = entries[0] if entries else {}
                title = info.get('title', '재생목록')
                uploader = info.get('uploader') or first_entry.get('uploader') or "알 수 없음"
                thumbnail = info.get('thumbnail') or first_entry.get('thumbnail') or ""
                count = len(entries)
                return {
                    'is_playlist': True,
                    'title': title,
                    'uploader': uploader,
                    'thumbnail': thumbnail,
                    'video_count': count,
                    'duration': f"총 {count}개 영상",
                    'id': info.get('id', '')
                }, None
            else:
                title = info.get('title', '제목 없음')
                uploader = info.get('uploader') or info.get('channel') or "알 수 없음"
                thumbnail = info.get('thumbnail', '')
                duration_sec = info.get('duration', 0)
                duration_str = format_duration(duration_sec)
                view_count = info.get('view_count', 0)

                return {
                    'is_playlist': False,
                    'title': title,
                    'uploader': uploader,
                    'thumbnail': thumbnail,
                    'duration': duration_str,
                    'view_count': view_count,
                    'id': info.get('id', '')
                }, None

    except Exception as e:
        return None, str(e)


def download_media(
    url,
    download_type="video",       # 'video' or 'audio'
    video_quality="best",        # 'best', '2160', '1440', '1080', '720', '480', '360'
    video_format="mp4",          # 'mp4', 'mkv'
    audio_format="mp3",          # 'mp3', 'm4a', 'flac', 'wav'
    audio_quality="320",         # '320', '256', '192', '128'
    embed_thumbnail=True,
    embed_subtitles=False,
    download_playlist=False,
    output_dir=None,
    progress_callback=None,
    status_callback=None
):
    """
    유튜브 영상 또는 음악(오디오) 다운로드
    """
    init_env()
    if not output_dir:
        output_dir = os.path.expanduser(r"~\Downloads")

    ffmpeg_dir = find_ffmpeg()

    # 진행률 계산 상태 (스트림 다운로드 2단계 추적)
    state = {
        'current_step': 1,
        'total_steps': 2 if download_type == "video" else 1
    }

    def my_hook(d):
        if not progress_callback:
            return

        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            raw_percent = (downloaded / total * 100) if total > 0 else 0
            speed = d.get('speed', 0) or 0
            eta = d.get('eta', 0) or 0
            raw_filename = os.path.basename(d.get('filename', ''))

            # 비디오/오디오 스트림 구분
            is_audio_stream = any(raw_filename.endswith(ext) for ext in ['.webm', '.m4a', '.opus']) and download_type == "video"
            if is_audio_stream and state['current_step'] == 1:
                state['current_step'] = 2

            # 부드러운 가중치 퍼센트 계산 (영상: 0~75% 비디오, 75~90% 오디오, 90~100% 합성)
            if download_type == "video":
                if state['current_step'] == 1:
                    overall_pct = (raw_percent * 0.75)
                    step_msg = "🎬 비디오 스트림 다운로드 중 (1/2)"
                else:
                    overall_pct = 75.0 + (raw_percent * 0.15)
                    step_msg = "🎵 오디오 스트림 다운로드 중 (2/2)"
            else:
                overall_pct = raw_percent * 0.90
                step_msg = "🎵 오디오 스트림 다운로드 중"

            speed_str = f"{format_bytes(speed)}/s" if speed else "계산 중..."
            eta_str = f"{eta}초" if eta else "계산 중..."
            size_str = f"{format_bytes(downloaded)} / {format_bytes(total)}" if total else format_bytes(downloaded)

            progress_callback({
                'status': 'downloading',
                'percent': overall_pct,
                'speed_str': speed_str,
                'eta_str': eta_str,
                'size_str': size_str,
                'step_msg': step_msg,
                'filename': raw_filename
            })

        elif status == 'finished':
            if download_type == "video" and state['current_step'] == 1:
                state['current_step'] = 2
                progress_callback({
                    'status': 'downloading',
                    'percent': 75.0,
                    'speed_str': "",
                    'eta_str': "",
                    'size_str': "",
                    'step_msg': "🎵 오디오 스트림 준비 중 (2/2)",
                    'filename': ""
                })
            else:
                progress_callback({
                    'status': 'finished',
                    'percent': 90.0,
                    'step_msg': "⚡ 파일 합성 및 고화질 인코딩 중...",
                    'filename': ""
                })

    def postprocessor_hook(d):
        if not status_callback:
            return
        status = d.get('status')
        pp_name = d.get('postprocessor', '')
        if status == 'started':
            if 'ExtractAudio' in pp_name or 'FFmpegExtractAudio' in pp_name:
                status_callback(f"🎵 {audio_format.upper()} 고음질 오디오 변환 중...")
            elif 'ThumbnailsConvertor' in pp_name or 'EmbedThumbnail' in pp_name:
                status_callback("🖼️ 썸네일 커버 및 메타데이터 삽입 중...")
            elif 'FFmpegMerger' in pp_name or 'Merger' in pp_name:
                status_callback("🎬 비디오와 오디오 고화질 합성 중 (FFmpeg)...")
            else:
                status_callback("⚡ 파일 후처리 작업 중...")
        elif status == 'finished':
            status_callback("✅ 변환 처리 완료!")

    # 아웃풋 템플릿 설정
    outtmpl = os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s")

    ydl_opts = {
        'outtmpl': outtmpl,
        'progress_hooks': [my_hook],
        'postprocessor_hooks': [postprocessor_hook],
        'noplaylist': not download_playlist,
        'windowsfilenames': True,
        'no_warnings': True,
        'quiet': True,
        'remote_components': ['ejs:github'],
    }

    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    postprocessors = []

    if download_type == "audio":
        # 오디오 전용 다운로드 및 변환
        ydl_opts['format'] = 'bestaudio/best'
        postprocessors.append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format.lower(),
            'preferredquality': audio_quality,
        })

        if embed_thumbnail:
            ydl_opts['writethumbnail'] = True
            postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
            postprocessors.append({'key': 'EmbedThumbnail'})

        postprocessors.append({'key': 'FFmpegMetadata'})

    else:
        # 영상(비디오) 다운로드
        # 재생 호환성(Windows Media Player 등)을 위해 MP4 선택 시 H.264(mp4) + AAC(m4a) 우선 매칭
        # 세로 영상(쇼츠 등)도 높이/너비 모두 고려
        if video_format.lower() == "mp4":
            if video_quality == "best":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
            else:
                q = video_quality
                ydl_opts['format'] = (
                    f'bestvideo[height<={q}][ext=mp4]+bestaudio[ext=m4a]/'
                    f'bestvideo[width<={q}][ext=mp4]+bestaudio[ext=m4a]/'
                    f'bestvideo[height<={q}]+bestaudio/'
                    f'bestvideo[width<={q}]+bestaudio/'
                    f'best[height<={q}]/best'
                )
        else:
            # MKV 포맷
            if video_quality == "best":
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            else:
                q = video_quality
                ydl_opts['format'] = (
                    f'bestvideo[height<={q}]+bestaudio/'
                    f'bestvideo[width<={q}]+bestaudio/'
                    f'best[height<={q}]/best'
                )

        ydl_opts['merge_output_format'] = video_format.lower()

        if embed_subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['ko', 'en']
            postprocessors.append({'key': 'FFmpegEmbedSubtitle'})

        if embed_thumbnail:
            ydl_opts['writethumbnail'] = True
            postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
            postprocessors.append({'key': 'EmbedThumbnail'})

        postprocessors.append({'key': 'FFmpegMetadata'})

    if postprocessors:
        ydl_opts['postprocessors'] = postprocessors

    try:
        if status_callback:
            status_callback("다운로드 준비 중...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if progress_callback:
            progress_callback({
                'status': 'finished',
                'percent': 100.0,
                'step_msg': "🎉 다운로드 및 합성 완료!",
                'filename': ""
            })

        if status_callback:
            status_callback("다운로드 및 저장이 완료되었습니다!")
        return True, "성공"

    except Exception as e:
        err_msg = str(e)
        if status_callback:
            status_callback(f"오류 발생: {err_msg}")
        return False, err_msg
