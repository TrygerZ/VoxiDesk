"""Dialogs for VoxiDesk."""

import customtkinter as ctk


def show_error(title: str, message: str, detail: str | None = None, master=None):
    """Show error dialog with option to copy details."""
    if master is not None:
        dialog = ctk.CTkToplevel(master)
    else:
        dialog = ctk.CTkToplevel()
    dialog.title(title)
    dialog.geometry("500x300")
    dialog.resizable(False, False)
    if master is not None:
        dialog.transient(master)
    dialog.grab_set()

    # Center on parent
    dialog.update_idletasks()
    if master is not None:
        x = master.winfo_x() + (master.winfo_width() - 500) // 2
        y = master.winfo_y() + (master.winfo_height() - 300) // 2
        dialog.geometry(f"+{x}+{y}")

    # Icon error
    label_icon = ctk.CTkLabel(dialog, text="❌", font=("Segoe UI", 36))
    label_icon.pack(pady=(15, 5))

    label_msg = ctk.CTkLabel(
        dialog, text=message, wraplength=450, font=("Segoe UI", 13)
    )
    label_msg.pack(pady=(5, 10), padx=20, fill="both", expand=True)

    # Detail textbox (jika ada)
    if detail:
        text_detail = ctk.CTkTextbox(dialog, height=80, font=("Consolas", 11))
        text_detail.pack(padx=20, pady=(0, 10), fill="x")
        text_detail.insert("0.0", detail)
        text_detail.configure(state="disabled")

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=(0, 15))

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
            btn_frame, text="📋 Copy Details", command=copy_detail, width=120
        )
        btn_copy.pack(side="left", padx=5)

    btn_ok = ctk.CTkButton(btn_frame, text="OK", command=close, width=80)
    btn_ok.pack(side="left", padx=5)

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
    if master is not None:
        dialog.transient(master)
    dialog.grab_set()

    # Center on parent
    dialog.update_idletasks()
    if master is not None:
        x = master.winfo_x() + (master.winfo_width() - 400) // 2
        y = master.winfo_y() + (master.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")

    label_icon = ctk.CTkLabel(dialog, text="ℹ️", font=("Segoe UI", 36))
    label_icon.pack(pady=(15, 5))

    label_msg = ctk.CTkLabel(
        dialog, text=message, wraplength=350, font=("Segoe UI", 13)
    )
    label_msg.pack(pady=(5, 15), padx=20, fill="both", expand=True)

    def close_info():
        dialog.grab_release()
        if master is not None:
            master.focus_set()
        dialog.destroy()

    btn_ok = ctk.CTkButton(dialog, text="OK", command=close_info, width=80)
    btn_ok.pack(pady=(0, 15))

    dialog.wait_window()


def show_about(master=None):
    """Show About dialog."""
    if master is not None:
        dialog = ctk.CTkToplevel(master)
    else:
        dialog = ctk.CTkToplevel()
    dialog.title("About VoxiDesk")
    dialog.geometry("420x300")
    dialog.resizable(False, False)
    if master is not None:
        dialog.transient(master)
    dialog.grab_set()

    # Center on parent
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
        label_icon = ctk.CTkLabel(dialog, text="🎙️", font=("Segoe UI", 48))
    label_icon.pack(pady=(15, 5))

    label_title = ctk.CTkLabel(
        dialog, text="VoxiDesk", font=("Segoe UI", 18, "bold")
    )
    label_title.pack()

    label_ver = ctk.CTkLabel(dialog, text="Version 1.0.0", font=("Segoe UI", 12))
    label_ver.pack()

    label_desc = ctk.CTkLabel(
        dialog,
        text="A desktop application for transcribing audio/video files\ninto text using OpenAI Whisper.",
        wraplength=380,
        font=("Segoe UI", 12),
        justify="center",
    )
    label_desc.pack(pady=(10, 5))

    label_engine = ctk.CTkLabel(
        dialog,
        text="Engine: OpenAI Whisper\nFramework: CustomTkinter",
        font=("Segoe UI", 11),
        text_color="gray",
        justify="center",
    )
    label_engine.pack(pady=(5, 10))

    def close_about():
        dialog.grab_release()
        if master is not None:
            master.focus_set()
        dialog.destroy()

    btn_ok = ctk.CTkButton(dialog, text="Close", command=close_about, width=80)
    btn_ok.pack(pady=(0, 15))

    dialog.wait_window()
