from llama_cpp import Llama

def ask_ai(prompt, tokens, n_threads=4, conversation_history=None):
    llm = Llama(
        model_path="models/Phi-3-mini-4k-instruct-q4.gguf",
        n_ctx=4096,
        n_threads=n_threads,
        n_gpu_layers=0,
        verbose=False
    )

    conversation_text = ""
    
    if conversation_history:
        for message in conversation_history:
            if message['role'] == 'user':
                conversation_text += f"<|user|>\n{message['content']}<|end|>\n"
            elif message['role'] == 'assistant':
                conversation_text += f"<|assistant|>\n{message['content']}<|end|>\n"
    
    conversation_text += f"<|user|>\n{prompt}<|end|>\n<|assistant|>"

    output = llm(
        conversation_text,
        max_tokens=tokens, 
        stop=["<|end|>"], 
        echo=False
    )

    return output['choices'][0]['text']
