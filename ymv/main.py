import os
import sys
import threading
import io
import requests
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import downloader

# 기본 설정
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube 미디어 다운로더 (동영상 & 음악)")
        self.geometry("780x780")
        self.minsize(720, 720)

        # 상태 변수
        self.current_video_info = None
        self.is_downloading = False
        self.thumbnail_image = None

        # 기본 다운로드 경로
        default_dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.output_dir_var = ctk.StringVar(value=default_dl_dir)

        # 옵션 변수들
        self.download_type_var = ctk.StringVar(value="video")  # 기본: 동영상
        self.video_quality_var = ctk.StringVar(value="1080p FHD (권장)")
        self.video_format_var = ctk.StringVar(value="MP4")
        self.audio_format_var = ctk.StringVar(value="MP3")
        self.audio_quality_var = ctk.StringVar(value="320 kbps (최고음질)")
        self.embed_thumb_var = ctk.BooleanVar(value=True)
        self.embed_subs_var = ctk.BooleanVar(value=False)
        self.download_playlist_var = ctk.BooleanVar(value=False)

        self._build_ui()

        # 초기 모드 적용 (동영상 모드 활성화)
        self._on_mode_change("🎬 동영상 (비디오 다운로드)")

    def _build_ui(self):
        # 상단 헤더
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray85", "#1e1e24"))
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="🎬 YouTube 미디어 다운로더",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(pady=(10, 2))

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="유튜브 영상(MP4) 및 음악/오디오(MP3, FLAC 등)를 고화질로 간편하게 다운로드하세요",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 10))

        # 메인 스크롤 가능 컨테이너
        content_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        content_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # 1. URL 입력 프레임
        url_frame = ctk.CTkFrame(content_frame, corner_radius=8)
        url_frame.pack(fill="x", pady=6, padx=5)

        ctk.CTkLabel(
            url_frame,
            text="🔗 유튜브 영상 또는 재생목록 URL:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=12, pady=(10, 4))

        input_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=12, pady=(0, 10))

        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="https://www.youtube.com/watch?v=... 주소를 붙여넣으세요",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.start_fetch_info())

        paste_btn = ctk.CTkButton(
            input_row,
            text="📋 붙여넣기",
            width=85,
            height=38,
            command=self.paste_from_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 6))

        self.fetch_btn = ctk.CTkButton(
            input_row,
            text="🔍 정보 확인",
            width=95,
            height=38,
            fg_color="#e02424",
            hover_color="#b81c1c",
            command=self.start_fetch_info
        )
        self.fetch_btn.pack(side="left")

        # 2. 영상 정보 미리보기 카드 (기본 숨김/placeholder)
        self.preview_frame = ctk.CTkFrame(content_frame, corner_radius=8)
        self.preview_frame.pack(fill="x", pady=6, padx=5)

        self.preview_placeholder = ctk.CTkLabel(
            self.preview_frame,
            text="💡 URL을 입력하고 '정보 확인' 버튼을 누르면 썸네일과 영상 정보가 여기에 표시됩니다.",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.preview_placeholder.pack(pady=20)

        # 정보 내용 담을 프레임 (초기에는 숨김)
        self.info_content_box = ctk.CTkFrame(self.preview_frame, fg_color="transparent")

        self.thumb_label = ctk.CTkLabel(self.info_content_box, text="")
        self.thumb_label.pack(side="left", padx=10, pady=10)

        info_details_frame = ctk.CTkFrame(self.info_content_box, fg_color="transparent")
        info_details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.video_title_label = ctk.CTkLabel(
            info_details_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=420,
            justify="left"
        )
        self.video_title_label.pack(anchor="w", pady=(0, 4))

        self.video_channel_label = ctk.CTkLabel(
            info_details_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#9e9e9e"
        )
        self.video_channel_label.pack(anchor="w", pady=(0, 2))

        self.video_extra_label = ctk.CTkLabel(
            info_details_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#00a8ff"
        )
        self.video_extra_label.pack(anchor="w")

        self.playlist_checkbox = ctk.CTkCheckBox(
            info_details_frame,
            text="재생목록 전체 일괄 다운로드",
            variable=self.download_playlist_var,
            font=ctk.CTkFont(size=12)
        )

        # 3. 다운로드 모드 및 옵션
        options_frame = ctk.CTkFrame(content_frame, corner_radius=8)
        options_frame.pack(fill="x", pady=6, padx=5)

        ctk.CTkLabel(
            options_frame,
            text="⚙️ 다운로드 모드 선택",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=12, pady=(10, 6))

        # 모드 선택 세그먼트 버튼
        self.mode_segment = ctk.CTkSegmentedButton(
            options_frame,
            values=["🎬 동영상 (비디오 다운로드)", "🎵 음악 (오디오 추출)"],
            command=self._on_mode_change,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.mode_segment.set("🎬 동영상 (비디오 다운로드)")
        self.mode_segment.pack(fill="x", padx=12, pady=(0, 10))

        # 비디오 옵션 서브프레임
        self.video_options_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        self.video_options_frame.pack(fill="x", padx=12, pady=(0, 10))

        video_row1 = ctk.CTkFrame(self.video_options_frame, fg_color="transparent")
        video_row1.pack(fill="x", pady=2)

        ctk.CTkLabel(video_row1, text="영상 화질:", width=90, anchor="w").pack(side="left")
        self.video_quality_menu = ctk.CTkOptionMenu(
            video_row1,
            variable=self.video_quality_var,
            values=[
                "1080p FHD (권장)",
                "720p HD (빠른 다운로드)",
                "최고 화질 (4K/2K/원본)",
                "480p",
                "360p"
            ],
            width=180
        )
        self.video_quality_menu.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(video_row1, text="저장 포맷:", width=80, anchor="w").pack(side="left")
        self.video_format_menu = ctk.CTkOptionMenu(
            video_row1,
            variable=self.video_format_var,
            values=["MP4", "MKV"],
            width=100
        )
        self.video_format_menu.pack(side="left")

        video_row2 = ctk.CTkFrame(self.video_options_frame, fg_color="transparent")
        video_row2.pack(fill="x", pady=(8, 2))

        self.video_thumb_cb = ctk.CTkCheckBox(
            video_row2,
            text="영상 썸네일 커버 포함",
            variable=self.embed_thumb_var,
            font=ctk.CTkFont(size=12)
        )
        self.video_thumb_cb.pack(side="left", padx=(0, 20))

        self.video_subs_cb = ctk.CTkCheckBox(
            video_row2,
            text="자막 자동 포함 (한국어/영어)",
            variable=self.embed_subs_var,
            font=ctk.CTkFont(size=12)
        )
        self.video_subs_cb.pack(side="left")

        # 오디오 옵션 서브프레임 (모드 전환 시 표시)
        self.audio_options_frame = ctk.CTkFrame(options_frame, fg_color="transparent")

        audio_row1 = ctk.CTkFrame(self.audio_options_frame, fg_color="transparent")
        audio_row1.pack(fill="x", pady=2)

        ctk.CTkLabel(audio_row1, text="오디오 포맷:", width=90, anchor="w").pack(side="left")
        self.audio_format_menu = ctk.CTkOptionMenu(
            audio_row1,
            variable=self.audio_format_var,
            values=["MP3", "M4A", "FLAC", "WAV"],
            width=130
        )
        self.audio_format_menu.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(audio_row1, text="음질(비트레이트):", width=110, anchor="w").pack(side="left")
        self.audio_quality_menu = ctk.CTkOptionMenu(
            audio_row1,
            variable=self.audio_quality_var,
            values=["320 kbps (최고음질)", "256 kbps (고음질)", "192 kbps (표준)", "128 kbps (경량)"],
            width=170
        )
        self.audio_quality_menu.pack(side="left")

        audio_row2 = ctk.CTkFrame(self.audio_options_frame, fg_color="transparent")
        audio_row2.pack(fill="x", pady=(8, 2))

        self.audio_thumb_cb = ctk.CTkCheckBox(
            audio_row2,
            text="앨범 커버(썸네일) 및 메타데이터 음원에 삽입",
            variable=self.embed_thumb_var,
            font=ctk.CTkFont(size=12)
        )
        self.audio_thumb_cb.pack(side="left")

        # 4. 저장 위치 설정
        dir_frame = ctk.CTkFrame(content_frame, corner_radius=8)
        dir_frame.pack(fill="x", pady=6, padx=5)

        ctk.CTkLabel(
            dir_frame,
            text="📁 저장할 폴더:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=12, pady=(10, 4))

        dir_row = ctk.CTkFrame(dir_frame, fg_color="transparent")
        dir_row.pack(fill="x", padx=12, pady=(0, 10))

        self.dir_entry = ctk.CTkEntry(
            dir_row,
            textvariable=self.output_dir_var,
            height=34,
            font=ctk.CTkFont(size=12)
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            dir_row,
            text="📂 찾아보기",
            width=90,
            height=34,
            command=self.browse_directory
        )
        browse_btn.pack(side="left", padx=(0, 6))

        open_dir_btn = ctk.CTkButton(
            dir_row,
            text="열기",
            width=65,
            height=34,
            fg_color="#3a3a44",
            hover_color="#4d4d5a",
            command=self.open_output_directory
        )
        open_dir_btn.pack(side="left")

        # 하단 다운로드 및 진행률 프레임
        bottom_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray85", "#1e1e24"))
        bottom_frame.pack(fill="x", padx=20, pady=(5, 15))

        # 진행률 바 및 퍼센트
        progress_info_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        progress_info_row.pack(fill="x", padx=16, pady=(10, 4))

        self.status_label = ctk.CTkLabel(
            progress_info_row,
            text="준비 완료",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3b82f6"
        )
        self.status_label.pack(side="left")

        self.percent_label = ctk.CTkLabel(
            progress_info_row,
            text="0%",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.percent_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(bottom_frame, height=14)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 6))
        self.progress_bar.set(0)

        # 상세 상태 정보 (속도, 남은 시간, 용량)
        self.detail_stats_label = ctk.CTkLabel(
            bottom_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.detail_stats_label.pack(anchor="w", padx=16, pady=(0, 8))

        # 다운로드 시작 버튼
        self.download_btn = ctk.CTkButton(
            bottom_frame,
            text="🎬 동영상 다운로드 시작",
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.start_download
        )
        self.download_btn.pack(fill="x", padx=16, pady=(0, 12))

    def _on_mode_change(self, value):
        if "음악" in value:
            self.download_type_var.set("audio")
            self.video_options_frame.pack_forget()
            self.audio_options_frame.pack(fill="x", padx=12, pady=(0, 10))
            self.download_btn.configure(text="🎵 음악(오디오) 다운로드 시작", fg_color="#10b981", hover_color="#059669")
        else:
            self.download_type_var.set("video")
            self.audio_options_frame.pack_forget()
            self.video_options_frame.pack(fill="x", padx=12, pady=(0, 10))
            self.download_btn.configure(text="🎬 동영상 다운로드 시작", fg_color="#3b82f6", hover_color="#2563eb")

    def paste_from_clipboard(self):
        try:
            text = self.clipboard_get()
            if text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text.strip())
                self.start_fetch_info()
        except Exception:
            pass

    def browse_directory(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if chosen:
            self.output_dir_var.set(chosen)

    def open_output_directory(self):
        path = self.output_dir_var.get()
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("폴더 없음", f"폴더가 존재하지 않습니다:\n{path}")

    def start_fetch_info(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("입력 필요", "유튜브 URL을 입력해주세요.")
            return

        self.fetch_btn.configure(state="disabled", text="조회 중...")
        self.status_label.configure(text="영상 정보를 불러오는 중입니다...", text_color="#f59e0b")

        threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True).start()

    def _fetch_info_thread(self, url):
        info, error = downloader.get_video_info(url)
        self.after(0, self._on_info_fetched, info, error)

    def _on_info_fetched(self, info, error):
        self.fetch_btn.configure(state="normal", text="🔍 정보 확인")

        if error or not info:
            self.status_label.configure(text=f"정보 조회 실패: {error}", text_color="#ef4444")
            messagebox.showerror("오류", f"영상 정보를 불러오지 못했습니다:\n{error}")
            return

        self.current_video_info = info
        self.status_label.configure(text="영상 정보 조회 완료!", text_color="#10b981")

        # 미리보기 카드 업데이트
        self.preview_placeholder.pack_forget()
        self.info_content_box.pack(fill="x", padx=10, pady=5)

        self.video_title_label.configure(text=info.get('title', ''))
        self.video_channel_label.configure(text=f"채널: {info.get('uploader', '알 수 없음')}")

        if info.get('is_playlist'):
            self.video_extra_label.configure(text=f"📋 재생목록 | {info.get('duration', '')}")
            self.playlist_checkbox.pack(anchor="w", pady=(6, 0))
            self.download_playlist_var.set(True)
        else:
            self.video_extra_label.configure(text=f"⏱️ 재생 시간: {info.get('duration', '00:00')}")
            self.playlist_checkbox.pack_forget()
            self.download_playlist_var.set(False)

        # 썸네일 이미지 비동기 다운로드 및 표시
        thumb_url = info.get('thumbnail')
        if thumb_url:
            threading.Thread(target=self._load_thumbnail, args=(thumb_url,), daemon=True).start()

    def _load_thumbnail(self, thumb_url):
        try:
            resp = requests.get(thumb_url, timeout=5)
            if resp.status_code == 200:
                image_data = resp.content
                img = Image.open(io.BytesIO(image_data))
                w, h = img.size
                ratio = 160 / w
                new_h = int(h * ratio)
                img = img.resize((160, new_h), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, new_h))
                self.after(0, self._display_thumbnail, ctk_img)
        except Exception:
            pass

    def _display_thumbnail(self, ctk_img):
        self.thumb_label.configure(image=ctk_img)
        self.thumb_label.image = ctk_img

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("입력 오류", "유튜브 URL을 입력해주세요.")
            return

        if self.is_downloading:
            messagebox.showinfo("안내", "이미 다운로드가 진행 중입니다.")
            return

        out_dir = self.output_dir_var.get().strip()
        if not out_dir:
            out_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            self.output_dir_var.set(out_dir)

        os.makedirs(out_dir, exist_ok=True)

        # UI 상태 다운로드 모드로 전환
        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ 다운로드 진행 중...")
        self.fetch_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.percent_label.configure(text="0%")
        self.status_label.configure(text="다운로드 준비 중...", text_color="#3b82f6")
        self.detail_stats_label.configure(text="유튜브 서버 연결 중...")

        # 옵션 파싱
        dtype = self.download_type_var.get()

        # 품질 텍스트 매핑
        quality_map = {
            "1080p FHD (권장)": "1080",
            "720p HD (빠른 다운로드)": "720",
            "최고 화질 (4K/2K/원본)": "best",
            "480p": "480",
            "360p": "360",
        }
        v_quality = quality_map.get(self.video_quality_var.get(), "1080")
        v_format = self.video_format_var.get().lower()

        # 오디오 비트레이트 매핑
        a_quality_raw = self.audio_quality_var.get()
        a_quality = "320"
        for q in ["320", "256", "192", "128"]:
            if q in a_quality_raw:
                a_quality = q
                break

        a_format = self.audio_format_var.get().lower()
        embed_thumb = self.embed_thumb_var.get()
        embed_subs = self.embed_subs_var.get()
        download_playlist = self.download_playlist_var.get()

        # 다운로드 스레드 시작
        threading.Thread(
            target=self._download_worker,
            args=(url, dtype, v_quality, v_format, a_format, a_quality, embed_thumb, embed_subs, download_playlist, out_dir),
            daemon=True
        ).start()

    def _progress_callback(self, data):
        self.after(0, self._update_progress_ui, data)

    def _update_progress_ui(self, data):
        status = data.get('status')
        pct = data.get('percent', 0.0)
        step_msg = data.get('step_msg', '')
        speed = data.get('speed_str', '')
        eta = data.get('eta_str', '')
        size = data.get('size_str', '')

        self.progress_bar.set(min(max(pct / 100.0, 0.0), 1.0))
        self.percent_label.configure(text=f"{pct:.1f}%")

        if step_msg:
            self.status_label.configure(text=step_msg, text_color="#3b82f6")

        if speed or eta or size:
            info_parts = []
            if speed:
                info_parts.append(f"속도: {speed}")
            if eta and eta != "계산 중...":
                info_parts.append(f"남은 시간: {eta}")
            if size:
                info_parts.append(f"용량: {size}")
            self.detail_stats_label.configure(text=" | ".join(info_parts))

        if status == 'finished' and pct >= 99.0:
            self.progress_bar.set(1.0)
            self.percent_label.configure(text="100%")
            self.status_label.configure(text="🎉 다운로드 및 합성 완료!", text_color="#10b981")
            self.detail_stats_label.configure(text="파일 저장이 완료되었습니다.")

    def _status_callback(self, text):
        self.after(0, self._update_status_ui, text)

    def _update_status_ui(self, text):
        self.status_label.configure(text=text, text_color="#f59e0b")

    def _download_worker(self, url, dtype, v_quality, v_format, a_format, a_quality, embed_thumb, embed_subs, download_playlist, out_dir):
        success, message = downloader.download_media(
            url=url,
            download_type=dtype,
            video_quality=v_quality,
            video_format=v_format,
            audio_format=a_format,
            audio_quality=a_quality,
            embed_thumbnail=embed_thumb,
            embed_subtitles=embed_subs,
            download_playlist=download_playlist,
            output_dir=out_dir,
            progress_callback=self._progress_callback,
            status_callback=self._status_callback
        )
        self.after(0, self._on_download_complete, success, message)

    def _on_download_complete(self, success, message):
        self.is_downloading = False
        self.fetch_btn.configure(state="normal")
        self._on_mode_change(self.mode_segment.get())  # 버튼 텍스트 복구

        if success:
            self.status_label.configure(text="🎉 다운로드가 완료되었습니다!", text_color="#10b981")
            self.progress_bar.set(1.0)
            self.percent_label.configure(text="100%")
            self.detail_stats_label.configure(text="저장 폴더에서 파일을 확인하실 수 있습니다.")

            ans = messagebox.askyesno(
                "다운로드 완료",
                f"다운로드가 성공적으로 완료되었습니다!\n\n저장 경로:\n{self.output_dir_var.get()}\n\n지금 저장 폴더를 여시겠습니까?"
            )
            if ans:
                self.open_output_directory()
        else:
            self.status_label.configure(text=f"❌ 다운로드 실패", text_color="#ef4444")
            self.detail_stats_label.configure(text=message)
            messagebox.showerror("다운로드 실패", f"다운로드 중 오류가 발생했습니다:\n\n{message}")


if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
