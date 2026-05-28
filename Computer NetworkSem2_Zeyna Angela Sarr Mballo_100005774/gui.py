import tkinter as tk

# module-level helpers (will be wired when ChatGUI is instantiated)
window = None
chat_display = None
local_username = None

def set_local_username(name: str):
    """Set the local client's username so GUI can show 'You' locally."""
    global local_username
    local_username = name

def display_message(msg: str):
    """Module-level helper so client code can call gui.display_message(...)"""
    global chat_display, window, local_username
    if chat_display is None or window is None:
        return

    # Replace local username with "You" for local display.
    display = msg
    if local_username:
        # expected format: "[HH:MM:SS] username: message"
        display = display.replace(f"] {local_username}:", "] You:")
        # fallback if format differs
        display = display.replace(f"{local_username}:", "You:")

    # ensure thread-safe UI update
    window.after(0, lambda: (chat_display.config(state="normal"),
                             chat_display.insert(tk.END, display + "\n"),
                             chat_display.config(state="disabled"),
                             chat_display.see(tk.END)))

class ChatGUI:
    def __init__(self, send_callback=None):
        global window, chat_display
        self.send_callback = send_callback

        window = tk.Tk()
        window.title("Encrypted Chat Application")
        window.geometry("420x540")
        window.configure(bg="#061f3d")

        # prettier chat display with blue font
        chat_display = tk.Text(window, state="disabled", wrap="word",
                               fg="#000000", bg="#f7fbff",
                               font=("Segoe UI", 10), padx=8, pady=8, bd=0)
        chat_display.pack(padx=12, pady=12, fill="both", expand=True)

        entry_frame = tk.Frame(window, bg="#eef6ff")
        entry_frame.pack(fill="x", padx=12, pady=(0,12))

        self.message_entry = tk.Entry(entry_frame, font=("Segoe UI", 10))
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0,8))

        self.send_button = tk.Button(entry_frame, text="Send", command=self.send_message,
                                     bg="#1a73e8", fg="white", activebackground="#155ab6",
                                     font=("Segoe UI", 9, "bold"), padx=12, pady=6)
        self.send_button.pack(side="right")

        # store references for module-level helpers
        self.window = window
        self.chat_display = chat_display

    def send_message(self):
        message = self.message_entry.get().strip()
        if not message or not self.send_callback:
            return

        # Call external send callback; if it returns the formatted message string,
        # display that (GUI owns display logic).
        formatted = None
        try:
            formatted = self.send_callback(message)
        except Exception:
            formatted = None

        # Clear entry regardless
        self.message_entry.delete(0, tk.END)

        if isinstance(formatted, str):
            display_message(formatted)
        else:
            # fallback display (no timestamp)
            display_message(f"You: {message}")

    def run(self):
        self.window.mainloop()