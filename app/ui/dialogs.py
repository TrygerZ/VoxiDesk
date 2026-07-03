"""Dialogs for VoxiDesk."""

import customtkinter as ctk

from app.ui import theme


def show_error(title: str, message: str, detail: str | None = None, master=None):
    """Show error dialog with option to copy details."""
    if master is not None:
        dialog = ctk.CTkToplevel(master)
    else:
        dialog = ctk.CTkToplevel()
    dialog.title(title)
    dialog.geometry("500x300")
    dialog.resizable(False, False)
    dialog.configure(fg_color=theme.BG_BASE)
    if master is not None:
        dialog.transient(master)
    dialog.grab_set()

    dialog.update_idletasks()
    if master is not None:
        x = master.winfo_x() + (master.winfo_width() - 500) // 2
        y = master.winfo_y() + (master.winfo_height() - 300) // 2
        dialog.geometry(f"+{x}+{y}")

    label_title = ctk.CTkLabel(
        dialog, text="Error", font=theme.FONT_TITLE, text_color=theme.DANGER,
    )
    label_title.pack(pady=(20, 6))

    label_msg = ctk.CTkLabel(
        dialog, text=message, wraplength=450, font=theme.FONT_BODY,
        text_color=theme.TEXT,
    )
    label_msg.pack(pady=(4, 12), padx=theme.PAD_X, fill="both", expand=True)

    if detail:
        text_detail = ctk.CTkTextbox(
            dialog, height=80, font=theme.FONT_LOG,
            corner_radius=theme.RADIUS_BTN,
        )
        text_detail.pack(padx=theme.PAD_X, pady=(0, 12), fill="x")
        text_detail.insert("0.0", detail)
        text_detail.configure(state="disabled")

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=(0, 18))

    def copy_detail():
        if detail:
            dialog.clipboard_clear()
            dialog.clipboard_append(detail)

    def close():
        dialog.grab_release()
        if master is not None:
            master.focus_set()
        dialog.destroy()

    if detail:
        btn_copy = ctk.CTkButton(
            btn_frame, text="Copy details", command=copy_detail, width=120,
            height=34, font=theme.FONT_BODY, corner_radius=theme.RADIUS_BTN,
        )
        btn_copy.pack(side="left", padx=6)

    btn_ok = ctk.CTkButton(
        btn_frame, text="OK", command=close, width=80, height=34,
        font=theme.FONT_BODY, fg_color=theme.ACCENT,
        hover_color=theme.ACCENT_HOVER, text_color=theme.TEXT_ON_ACCENT,
        corner_radius=theme.RADIUS_BTN,
    )
    btn_ok.pack(side="left", padx=6)

    dialog.protocol("WM_DELETE_WINDOW", close)
    dialog.wait_window()


def show_info(title: str, message: str, master=None):
    """Show information dialog."""
    if master is not None:
        dialog = ctk.CTkToplevel(master)
    else:
        dialog = ctk.CTkToplevel()
    dialog.title(title)
    dialog.geometry("400x200")
    dialog.resizable(False, False)
    dialog.configure(fg_color=theme.BG_BASE)
    if master is not None:
        dialog.transient(master)
    dialog.grab_set()

    dialog.update_idletasks()
    if master is not None:
        x = master.winfo_x() + (master.winfo_width() - 400) // 2
        y = master.winfo_y() + (master.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")

    label_title = ctk.CTkLabel(
        dialog, text=title, font=theme.FONT_TITLE, text_color=theme.ACCENT,
    )
    label_title.pack(pady=(20, 6))

    label_msg = ctk.CTkLabel(
        dialog, text=message, wraplength=350, font=theme.FONT_BODY,
        text_color=theme.TEXT,
    )
    label_msg.pack(pady=(4, 18), padx=theme.PAD_X, fill="both", expand=True)

    def close_info():
        dialog.grab_release()
        if master is not None:
            master.focus_set()
        dialog.destroy()

    btn_ok = ctk.CTkButton(
        dialog, text="OK", command=close_info, width=80, height=34,
        font=theme.FONT_BODY, fg_color=theme.ACCENT,
        hover_color=theme.ACCENT_HOVER, text_color=theme.TEXT_ON_ACCENT,
        corner_radius=theme.RADIUS_BTN,
    )
    btn_ok.pack(pady=(0, 18))

    dialog.protocol("WM_DELETE_WINDOW", close_info)
    dialog.wait_window()


def show_confirm(title: str, message: str, master=None) -> bool:
    """Show confirmation dialog and return True if Yes."""
    if master is not None:
        dialog = ctk.CTkToplevel(master)
    else:
        dialog = ctk.CTkToplevel()
    dialog.title(title)
    dialog.geometry("400x200")
    dialog.resizable(False, False)
    dialog.configure(fg_color=theme.BG_BASE)
    if master is not None:
        dialog.transient(master)
    dialog.grab_set()

    dialog.update_idletasks()
    if master is not None:
        x = master.winfo_x() + (master.winfo_width() - 400) // 2
        y = master.winfo_y() + (master.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")

    label_title = ctk.CTkLabel(
        dialog, text=title, font=theme.FONT_TITLE, text_color=theme.TEXT,
    )
    label_title.pack(pady=(20, 6))

    label_msg = ctk.CTkLabel(
        dialog, text=message, wraplength=350, font=theme.FONT_BODY,
        text_color=theme.TEXT_MUTED,
    )
    label_msg.pack(pady=(4, 12), padx=theme.PAD_X, fill="both", expand=True)

    result = [False]

    def on_yes():
        result[0] = True
        close()

    def on_no():
        result[0] = False
        close()

    def close():
        dialog.grab_release()
        if master is not None:
            master.focus_set()
        dialog.destroy()

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=(0, 18))

    btn_yes = ctk.CTkButton(
        btn_frame, text="Yes", command=on_yes, width=90, height=34,
        font=theme.FONT_BODY, fg_color=theme.ACCENT,
        hover_color=theme.ACCENT_HOVER, text_color=theme.TEXT_ON_ACCENT,
        corner_radius=theme.RADIUS_BTN,
    )
    btn_yes.pack(side="left", padx=8)

    btn_no = ctk.CTkButton(
        btn_frame, text="No", command=on_no, width=90, height=34,
        font=theme.FONT_BODY, fg_color="transparent",
        hover_color=theme.SURFACE_HI, text_color=theme.TEXT_MUTED,
        border_width=1, border_color=theme.BORDER,
        corner_radius=theme.RADIUS_BTN,
    )
    btn_no.pack(side="left", padx=8)

    dialog.protocol("WM_DELETE_WINDOW", on_no)
    dialog.wait_window()
    return result[0]


def show_about(master=None):
    """Show About dialog."""
    if master is not None:
        dialog = ctk.CTkToplevel(master)
    else:
        dialog = ctk.CTkToplevel()
    dialog.title("About VoxiDesk")
    dialog.geometry("420x300")
    dialog.resizable(False, False)
    dialog.configure(fg_color=theme.BG_BASE)
    if master is not None:
        dialog.transient(master)
    dialog.grab_set()

    dialog.update_idletasks()
    if master is not None:
        x = master.winfo_x() + (master.winfo_width() - 420) // 2
        y = master.winfo_y() + (master.winfo_height() - 300) // 2
        dialog.geometry(f"+{x}+{y}")

    # Try to load app icon PNG for about dialog
    try:
        from PIL import Image
        from pathlib import Path
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "app.png"
        if icon_path.exists():
            icon_img = ctk.CTkImage(Image.open(str(icon_path)), size=(64, 64))
            label_icon = ctk.CTkLabel(dialog, image=icon_img, text="")
        else:
            raise FileNotFoundError
    except Exception:
        # Fallback: accent-colored wordmark instead of emoji
        label_icon = ctk.CTkLabel(
            dialog, text="V", font=theme.font(36, "bold"),
            text_color=theme.ACCENT,
        )
    label_icon.pack(pady=(18, 6))

    label_title = ctk.CTkLabel(
        dialog, text="VoxiDesk", font=theme.font(18, "bold"),
        text_color=theme.TEXT,
    )
    label_title.pack()

    from app.app import VERSION
    label_ver = ctk.CTkLabel(
        dialog, text=f"Version {VERSION}", font=theme.FONT_BODY,
        text_color=theme.TEXT_MUTED,
    )
    label_ver.pack()

    label_desc = ctk.CTkLabel(
        dialog,
        text="A desktop application for transcribing audio/video files\ninto text using faster-whisper.",
        wraplength=380,
        font=theme.FONT_BODY,
        text_color=theme.TEXT,
        justify="center",
    )
    label_desc.pack(pady=(12, 6))

    label_engine = ctk.CTkLabel(
        dialog,
        text="Engine: faster-whisper + CTranslate2\nFramework: CustomTkinter",
        font=theme.FONT_CAPTION,
        text_color=theme.TEXT_MUTED,
        justify="center",
    )
    label_engine.pack(pady=(4, 12))

    def close_about():
        dialog.grab_release()
        if master is not None:
            master.focus_set()
        dialog.destroy()

    btn_ok = ctk.CTkButton(
        dialog, text="Close", command=close_about, width=80, height=34,
        font=theme.FONT_BODY, corner_radius=theme.RADIUS_BTN,
    )
    btn_ok.pack(pady=(0, 18))

    dialog.protocol("WM_DELETE_WINDOW", close_about)
    dialog.wait_window()
