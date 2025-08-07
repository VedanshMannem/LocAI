import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import os
import datetime
from response import ask_ai
from RAG import build_embeddings, retrieve_relevant_chunks, build_prompt, load_faiss_index_and_metadata
from sentence_transformers import SentenceTransformer

class ContextTooltip:
    def __init__(self, widget, get_context_func):
        self.widget = widget
        self.get_context_func = get_context_func
        self.tooltip = None
        self.delay = 500 
        self.tooltip_job = None

        if hasattr(widget, '_canvas'):
            self.bind_widget = widget._canvas
        else:
            self.bind_widget = widget

        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)

        chunks = self.get_context_func()
        if not chunks:
            return

    def on_enter(self, event):
        self.schedule_tooltip()
    
    def on_leave(self, event):
        self.hide_tooltip()

    def on_motion(self, event):
        if self.tooltip:
            self.hide_tooltip()
        self.schedule_tooltip()

    def schedule_tooltip(self):
        self.cancel_tooltip()
        self.tooltip_job = self.widget.after(self.delay, self.show_tooltip)
    
    def cancel_tooltip(self):
        if self.tooltip_job:
            self.widget.after_cancel(self.tooltip_job)
            self.tooltip_job = None

    def show_tooltip(self):
        
        if self.tooltip:
            return
        
        chunks = self.get_context_func()
        if not chunks:
            return

        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() - 250

        if y < 0:
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        self.tooltip.configure(bg="black", relief="solid", bd=1)

        frame = tk.Frame(self.tooltip, bg="black")
        frame.pack(fill="both", expand=True)

        # title
        title = tk.Label(
            frame, 
            text="Context fetched from RAG:",
            bg="black",
            fg="white",
            font=("Arial", 10, "bold"),
            pady=5
        )
        title.pack(anchor="w", padx=5)

        text_frame = tk.Frame(frame, bg="black")
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)

        text_widget = tk.Text(
            text_frame, 
            text =  self.get_context_func(), 
            width=80,
            height=15,
            bg="gray20",
            fg="white",
            font=("Courier", 9),
            wrap=tk.WORD,
            relief="flat"
        )

        scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        text_widget.insert("1.0", chunks)
        text_widget.configure(state="disabled")

        close_label = tk.Label(
            frame, 
            text="Move mouse away to close",
            bg="black",
            fg="gray",
            font=("Arial", 8, "italic"),
            pady = 2
        )
        close_label.pack()

    def hide_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
                
class AIModelGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Personal AI Assistant")
        self.root.geometry("800x600")
        self.root.minsize(500, 800)
        
        self.pages = {}
        self.current_page = None
        
        self.conversation_history = []
        self.max_history_pairs = 10  
        
        self.is_generating = False
        self.stop_generation = threading.Event()
        self.current_generation_thread = None

        self.chunks = []
        self.last_user_query = ""
        
        # settings
        self.max_tokens_var = ctk.StringVar(value="256")
        self.threads_var = ctk.StringVar(value=str(os.cpu_count() // 2))
        self.theme_var = ctk.StringVar(value="dark")
        self.history_length_var = ctk.StringVar(value="10")

        self.embedder = SentenceTransformer("./models/all-MiniLM-L6-v2")
        self.index, self.metadata = load_faiss_index_and_metadata()

        self.create_main_layout()
        self.create_chat_page()
        self.create_settings_page()
        self.show_page("chat")  

    def show_page(self, page_name):
        if self.current_page:
            self.pages[self.current_page].pack_forget()
        
        if page_name in self.pages:
            self.pages[page_name].pack(fill="both", expand=True)
            self.current_page = page_name
            
            for name, button in self.nav_buttons.items():
                if name == page_name:
                    button.configure(fg_color=("gray75", "gray25"))  # active
                else:
                    button.configure(fg_color=("gray50", "gray40"))  # inactive
    
    # base layout
    def create_main_layout(self):
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # title
        title_frame = ctk.CTkFrame(main_container)
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        title_label = ctk.CTkLabel(
            title_frame, 
            text="LocAI", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=10)
        
        # nav bar
        nav_frame = ctk.CTkFrame(main_container)
        nav_frame.pack(padx=10, pady=5) 

        self.nav_buttons = {}
        
        # chat
        self.nav_buttons["chat"] = ctk.CTkButton(
            nav_frame, 
            text="💬 Chat",
            command=lambda: self.show_page("chat"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.nav_buttons["chat"].pack(side="left", padx=(10, 5), pady=10)
        
        # settings 
        self.nav_buttons["settings"] = ctk.CTkButton(
            nav_frame, 
            text="⚙️ Settings",
            command=lambda: self.show_page("settings"),
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.nav_buttons["settings"].pack(side="left", padx=5, pady=10)
        
        self.content_frame = ctk.CTkFrame(main_container)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(5, 5))
    
    # chat layout
    def create_chat_page(self):
        chat_page = ctk.CTkFrame(self.content_frame)
        
        chat_frame = ctk.CTkFrame(chat_page)
        chat_frame.pack(fill="both", expand=True, padx=10, pady=(0,5))
        
        self.chat_display = ctk.CTkTextbox(
            chat_frame,
            height=300,
            font=ctk.CTkFont(size=12)
        )
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=10)
        
        # input
        input_frame = ctk.CTkFrame(chat_page)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))        
        input_label = ctk.CTkLabel(input_frame, text="Question:")
        input_label.pack(anchor="w", padx=10, pady=(10, 5))
        self.input_text = ctk.CTkTextbox(
            input_frame, 
            height=120,
            font=ctk.CTkFont(size=12)
        )
        self.input_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # buttons
        button_frame = ctk.CTkFrame(input_frame)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # submit
        self.submit_button = ctk.CTkButton(
            button_frame, 
            text="Send",
            command=self.handle_submit_button,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.submit_button.pack(side="right", padx=(0, 10), pady=5)

        # clear
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear Chat",
            command=self.clear_chat,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            font=ctk.CTkFont(size=12)
        )
        self.clear_button.pack(side="right", padx=5, pady=5)
        
        def get_current_chunks():
            if not self.chunks:
                return "No context available."
            
            context = []
            context.append("Last Query: ", self.last_user_query)
            context.append("=" * 30)
            context.append("")

            for i, chunk in enumerate(self.chunks):
                context.append(f"Context Chunk {i+1}")
                context.append("-" * 30)

                displayed = chunk[:500] + "..." if len(chunk) > 500 else chunk
                context.append(displayed)
                context.append("")

            return "\n".join(context)

        ContextTooltip(self.submit_button, get_current_chunks)

        # enter
        def on_enter(event):
            self.send_message()
            return "break"  # Prevents Enter from adding a new line
        
        # ctrl+backspace
        def on_ctrl_backspace(event):
        
            cursor_pos = self.input_text.index(tk.INSERT)
            text_before = self.input_text.get("1.0", cursor_pos)
            
            i = len(text_before) - 1
            
            while i >= 0 and text_before[i].isspace():
                i -= 1
            
            word_end = i + 1  
            while i >= 0 and not text_before[i].isspace():
                i -= 1
            
            word_start = i + 1  # Start of the word
            
            lines_before_start = text_before[:word_start].count('\n')
            if '\n' in text_before[:word_start]:
                last_newline_pos = text_before[:word_start].rfind('\n')
                char_pos_start = word_start - last_newline_pos - 1
            else:
                char_pos_start = word_start
            
            delete_from = f"{lines_before_start + 1}.{char_pos_start}"
            
            # Delete from word start to cursor
            self.input_text.delete(delete_from, cursor_pos)
    
            return "break"
        
        self.input_text.bind("<Return>", on_enter)
        self.input_text.bind("<Control-BackSpace>", on_ctrl_backspace)
        
        self.add_message("System", "Welcome! Ask me anything.")
        
        self.pages["chat"] = chat_page
    
    def create_settings_page(self):
        settings_page = ctk.CTkFrame(self.content_frame)
        
        settings_frame = ctk.CTkScrollableFrame(settings_page)
        settings_frame.pack(fill="both", expand=True, padx=20, pady=(0,10))
        
        # tokens
        tokens_frame = ctk.CTkFrame(settings_frame)
        tokens_frame.pack(fill="x", padx=20, pady=10)
        tokens_label = ctk.CTkLabel(tokens_frame, text="Max Response Length:")
        tokens_label.pack(anchor="w", padx=10, pady=(10, 5))
        self.max_tokens_entry = ctk.CTkEntry(
            tokens_frame,
            textvariable=self.max_tokens_var,
            placeholder_text="256"
        )
        self.max_tokens_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # threads
        threads_frame = ctk.CTkFrame(settings_frame)
        threads_frame.pack(fill="x", padx=20, pady=10)
        threads_label = ctk.CTkLabel(threads_frame, text="CPU Threads:")
        threads_label.pack(anchor="w", padx=10, pady=(10, 5))
        self.threads_entry = ctk.CTkEntry(
            threads_frame,
            textvariable=self.threads_var,
            placeholder_text=str(os.cpu_count() // 2)
        )
        self.threads_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # theme
        theme_frame = ctk.CTkFrame(settings_frame)
        theme_frame.pack(fill="x", padx=20, pady=10)
        theme_label = ctk.CTkLabel(theme_frame, text="Appearance Mode:")
        theme_label.pack(anchor="w", padx=10, pady=(10, 5))
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["dark", "light", "system"],
            variable=self.theme_var,
            command=self.change_theme
        )
        theme_menu.pack(fill="x", padx=10, pady=(0, 10))
        
        # RAG updates
        rag_update = ctk.CTkFrame(settings_frame)
        rag_update.pack(fill="x", padx=20, pady=10)
        rag_label = ctk.CTkLabel(rag_update, text="RAG Updates:")
        rag_label.pack(anchor="w", padx=10, pady=(10, 0))
        rag_button = ctk.CTkButton(
            rag_update,
            text="Retrieve new data",
            command=self.update_RAG,
            font=ctk.CTkFont(size=12)
        )
        rag_button.pack(anchor="w", padx=10, pady=(0, 0))

        rag_info = ctk.CTkLabel(
            rag_update, 
            text="RAG updates will be applied automatically when you run the RAG script.",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        rag_info.pack(anchor="w", padx=10, pady=(0, 10))

        # Download models
        

        # conversation history length
        history_frame = ctk.CTkFrame(settings_frame)
        history_frame.pack(fill="x", padx=20, pady=10)
        history_label = ctk.CTkLabel(history_frame, text="Conversation Memory (message pairs):")
        history_label.pack(anchor="w", padx=10, pady=(10, 5))
        self.history_entry = ctk.CTkEntry(
            history_frame,
            textvariable=self.history_length_var,
            placeholder_text="10"
        )
        self.history_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # help text
        help_label = ctk.CTkLabel(
            history_frame, 
            text="Lower values = faster responses, less memory\nHigher values = more context, slower responses",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        help_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # save
        save_button = ctk.CTkButton(
            settings_frame,
            text="Save Settings",
            command=self.save_settings,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        save_button.pack(pady=20)
        
        self.pages["settings"] = settings_page

    def change_theme(self, theme):
        ctk.set_appearance_mode(theme)

    def update_RAG(self):
        build_embeddings(r"C:\Users\manne\Downloads\LocAI-Test")
        messagebox.showinfo("RAG Update", "RAG data updated successfully!")
        self.index, self.metadata = load_faiss_index_and_metadata()
        return True

    # making sure settings are good
    def save_settings(self):
        try:
            max_tokens = int(self.max_tokens_var.get())
            threads = int(self.threads_var.get())
            history_length = int(self.history_length_var.get())
            
            if max_tokens < 1 or max_tokens > 2048:
                raise ValueError("Max tokens must be between 1 and 2048")
            if threads < 1 or threads > os.cpu_count():
                raise ValueError(f"Threads must be between 1 and {os.cpu_count()}")
            if history_length < 1 or history_length > 50:
                raise ValueError("Conversation memory must be between 1 and 50 pairs")
            
            # Update the history length setting
            self.max_history_pairs = history_length
            self.manage_conversation_history()  # Apply new limit immediately
            
            messagebox.showinfo("Settings", "Settings saved successfully!")
            
        except ValueError as e:
            messagebox.showerror("Invalid Settings", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            
    # send message to ai
    def add_message(self, sender, message):
        self.chat_display.configure(state="normal")
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        if sender == "You":
            self.chat_display.insert("end", f"[{timestamp}] You:\n", "user")
            self.chat_display.insert("end", f"{message}\n\n", "user_message")
        elif sender == "AI":
            self.chat_display.insert("end", f"[{timestamp}] AI Assistant:\n", "ai")
            self.chat_display.insert("end", f"{message}\n\n", "ai_message")
        else:
            self.chat_display.insert("end", f"[{timestamp}] {sender}:\n", "system")
            self.chat_display.insert("end", f"{message}\n\n", "system_message")
        
        # scroll
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
    
    # send message or stop generation
    def handle_submit_button(self):
        if self.is_generating:
            self.stop_ai_generation()
        else:
            self.send_message()
    
    def stop_ai_generation(self):
        self.stop_generation.set()
        self.submit_button.configure(text="Stopping...", state="disabled")
        
        self.root.after(100, lambda: self.add_message("System", "Generation stopped by user."))
        
        self.root.after(1000, self.reset_submit_button)
    
    def reset_submit_button(self):
        self.is_generating = False
        self.stop_generation.clear()
        self.submit_button.configure(state="normal", text="Send")
    
    def manage_conversation_history(self):
        max_messages = self.max_history_pairs * 2
        
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]
    
    # send message & add to history
    def send_message(self):
        user_input = self.input_text.get("1.0", "end-1c").strip()
        
        if not user_input:
            return

        self.conversation_history.append({
            'role': 'user',
            'content': user_input
        })

        self.add_message("You", user_input)
        self.input_text.delete("1.0", "end")
        
        self.is_generating = True
        self.stop_generation.clear()
        self.submit_button.configure(state="normal", text="Stop")

        def get_ai_response():
            try:
                max_tokens = int(self.max_tokens_var.get()) if self.max_tokens_var.get().isdigit() else 256
                threads = int(self.threads_var.get()) if self.threads_var.get().isdigit() else os.cpu_count() // 2
                
                if self.stop_generation.is_set():
                    return
                
                chunks = retrieve_relevant_chunks(user_input, self.embedder, self.index, self.metadata)
                self.chunks = chunks
                self.last_user_query = user_input
                response = ask_ai(build_prompt(chunks, user_input), max_tokens, n_threads=threads, conversation_history=self.conversation_history[:-1])

                if self.stop_generation.is_set():
                    if self.conversation_history and self.conversation_history[-1]['role'] == 'user':
                        self.conversation_history.pop()
                    return
                
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response
                })
                
                self.manage_conversation_history()
                
                self.root.after(0, lambda: self.add_message("AI", response))
                
            except Exception as e:
                if not self.stop_generation.is_set():
                    error_msg = f"Error generating response: {str(e)}"
                    self.root.after(0, lambda: self.add_message("Error", error_msg))

            finally:
                if not self.stop_generation.is_set():
                    self.root.after(0, self.reset_submit_button)

        self.current_generation_thread = threading.Thread(target=get_ai_response, daemon=True)
        self.current_generation_thread.start()
    
    # clear full chat
    def clear_chat(self):
        if self.is_generating:
            self.stop_ai_generation()
        
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        
        self.conversation_history = []
        
        self.add_message("System", "Chat cleared. How can I help you?")
    
    def run(self):
        self.root.mainloop()

def main():

    try:
        app = AIModelGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Application Error", f"Failed to start application: {str(e)}")

if __name__ == "__main__":
    main()
