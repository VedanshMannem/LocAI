import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import os
import datetime
from response import ask_ai
from RAG import build_embeddings, retrieve_relevant_chunks, build_prompt, load_faiss_index_and_metadata
from sentence_transformers import SentenceTransformer
                
class AIModelGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Personal AI Assistant")
        self.root.geometry("1200x700")
        self.root.minsize(800, 600)
        
        self.pages = {}
        self.current_page = None
        
        self.conversation_history = []
        self.max_history_pairs = 10  
        
        self.is_generating = False
        self.stop_generation = threading.Event()
        self.current_generation_thread = None

        # Store context data for each message
        self.message_contexts = {} 
        self.current_message_id = 0
        
        # settings
        self.max_tokens_var = ctk.StringVar(value="256")
        self.threads_var = ctk.StringVar(value=str(os.cpu_count() // 2))
        self.theme_var = ctk.StringVar(value="dark")
        self.history_length_var = ctk.StringVar(value="10")
        self.rag_enabled = True  # RAG switch state

        model_path = "./models/all-MiniLM-L6-v2"  # . for source and .. for build
        self.embedder = SentenceTransformer(model_path)
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
        
        # Main horizontal container for chat and context
        main_horizontal = ctk.CTkFrame(chat_page)
        main_horizontal.pack(fill="both", expand=True, padx=10, pady=(0,5))
        
        # chat
        chat_container = ctk.CTkFrame(main_horizontal)
        chat_container.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Chat display
        self.chat_display = ctk.CTkTextbox(
            chat_container,
            height=300,
            font=ctk.CTkFont(size=12)
        )
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure tags for clickable user messages
        self.chat_display._textbox.tag_configure("user_clickable", 
                                                foreground="#4A9EFF", 
                                                underline=True)
        self.chat_display._textbox.tag_bind("user_clickable", "<Button-1>", self.on_user_message_click)
        self.chat_display._textbox.tag_bind("user_clickable", "<Enter>", lambda e: self.chat_display._textbox.configure(cursor="hand2"))
        self.chat_display._textbox.tag_bind("user_clickable", "<Leave>", lambda e: self.chat_display._textbox.configure(cursor=""))
        
        # Right side - Context panel (takes 30% of width)
        context_container = ctk.CTkFrame(main_horizontal)
        context_container.pack(side="right", fill="both", padx=(5, 0))
        context_container.configure(width=350)
        context_container.pack_propagate(False)
        
        # Context panel title
        context_title = ctk.CTkLabel(
            context_container, 
            text="RAG Context",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        context_title.pack(pady=(10, 5), padx=10)
        
        # Context info label
        self.context_info = ctk.CTkLabel(
            context_container,
            text="Click on any of your messages to see the context used",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.context_info.pack(pady=(0, 10), padx=10)
        
        # Context display
        self.context_display = ctk.CTkTextbox(
            context_container,
            font=ctk.CTkFont(size=10, family="Courier"),
            wrap="word"
        )
        self.context_display.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Input section at bottom
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
        
        # RAG switch
        self.rag_switch = ctk.CTkSwitch(
            button_frame,
            text="Enable RAG Context",
            command=self.toggle_rag,
            onvalue=True,
            offvalue=False
        )
        self.rag_switch.pack(side="left", padx=(0, 10), pady=5)

        rag_switch_info = ctk.CTkLabel(
            button_frame,
            text="Enable for longer inference time for more context",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            wraplength=400
        )
        rag_switch_info.pack(side="left", padx=(0, 10), pady=5)

        # Set initial state
        if self.rag_enabled:
            self.rag_switch.select()
        
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

        # Keyboard shortcuts
        def on_enter(event):
            self.send_message()
            return "break"
        
        def on_ctrl_backspace(event):
            cursor_pos = self.input_text.index(tk.INSERT)
            text_before = self.input_text.get("1.0", cursor_pos)
            
            i = len(text_before) - 1
            
            while i >= 0 and text_before[i].isspace():
                i -= 1
            
            word_end = i + 1  
            while i >= 0 and not text_before[i].isspace():
                i -= 1
            
            word_start = i + 1
            
            lines_before_start = text_before[:word_start].count('\n')
            if '\n' in text_before[:word_start]:
                last_newline_pos = text_before[:word_start].rfind('\n')
                char_pos_start = word_start - last_newline_pos - 1
            else:
                char_pos_start = word_start
            
            delete_from = f"{lines_before_start + 1}.{char_pos_start}"
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

        # TODO: Add downloading models functionality
        
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

    def toggle_rag(self):
        self.rag_enabled = self.rag_switch.get()
        status = "enabled" if self.rag_enabled else "disabled"
        
        # Update context panel info
        if hasattr(self, 'context_info'):
            if self.rag_enabled:
                self.context_info.configure(text="Click on any of your messages to see the context used")
            else:
                self.context_info.configure(text="RAG is disabled - AI responds without document context")

    def update_RAG(self):
        build_embeddings(r"") # Change to your downloads directory
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
            
    def on_user_message_click(self, event):
        index = self.chat_display._textbox.index(f"@{event.x},{event.y}")
        
        # Find which message was clicked by looking at tags
        tags = self.chat_display._textbox.tag_names(index)
        
        for tag in tags:
            if tag.startswith("msg_"):
                message_id = int(tag.split("_")[1])
                self.show_context_for_message(message_id)
                break
    
    def show_context_for_message(self, message_id):
        if message_id not in self.message_contexts:
            self.context_display.delete("1.0", "end")
            self.context_display.insert("1.0", "No context available for this message.")
            return
        
        context_data = self.message_contexts[message_id]
        chunks = context_data.get('chunks', [])
        query = context_data.get('query', '')
        
        if not chunks:
            self.context_display.delete("1.0", "end")
            self.context_display.insert("1.0", "No context chunks found for this query.")
            return
        
        # Format the context display
        context_text = f"Query: {query}\n"
        context_text += "=" * 50 + "\n\n"
        
        for i, chunk in enumerate(chunks):
            context_text += f"Context Chunk {i+1}:\n"
            context_text += "-" * 30 + "\n"
            # Show full chunk in context panel
            context_text += chunk + "\n\n"
        
        self.context_display.delete("1.0", "end")
        self.context_display.insert("1.0", context_text)
        
        # Update info label
        self.context_info.configure(text=f"Context for: \"{query[:50]}{'...' if len(query) > 50 else ''}\"")

    # send message to ai
    def add_message(self, sender, message):
        self.chat_display.configure(state="normal")
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        if sender == "You":
            # Make user messages clickable
            message_tag = f"msg_{self.current_message_id}"
            self.chat_display.insert("end", f"[{timestamp}] You:\n", "user")
            self.chat_display.insert("end", f"{message}\n\n", ("user_message", "user_clickable", message_tag))
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

        # Store the current message ID for context association
        current_msg_id = self.current_message_id
        self.add_message("You", user_input)
        self.current_message_id += 1
        
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
                
                # Get RAG context only if enabled
                chunks = []
                if self.rag_enabled:
                    chunks = retrieve_relevant_chunks(user_input, self.embedder, self.index, self.metadata)
                
                # Store context for this message
                self.message_contexts[current_msg_id] = {
                    'chunks': chunks,
                    'query': user_input
                }
                
                # Build prompt with or without RAG context
                if self.rag_enabled and chunks:
                    prompt = build_prompt(chunks, user_input)
                else:
                    prompt = user_input
                
                response = ask_ai(prompt, max_tokens, n_threads=threads, conversation_history=self.conversation_history[:-1])

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
        
        # Clear context panel
        self.context_display.delete("1.0", "end")
        self.context_info.configure(text="Click on any of your messages to see the context used")
        
        # Clear stored data
        self.conversation_history = []
        self.message_contexts = {}
        self.current_message_id = 0
        
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
