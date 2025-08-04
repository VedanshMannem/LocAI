import os
import sys
from response import ask_ai

def get_model_path():
    if getattr(sys, 'frozen', False): # exe
        application_path = os.path.dirname(sys.executable)
    else: # script
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    model_path = os.path.join(application_path, "models", "Phi-3-mini-4k-instruct-q4.gguf")
    
    if os.path.exists(model_path):
        return model_path
    
    cwd_model_path = os.path.join(os.getcwd(), "models", "Phi-3-mini-4k-instruct-q4.gguf") # working directory
    if os.path.exists(cwd_model_path):
        return cwd_model_path
    
    return None

def main():
    print("Personal AI Assistant - Console Version")
    print("=" * 40)
    
    print("Loading AI model...")
    model_path = get_model_path()
    
    if not model_path:
        sys.stderr.write("Error: Model file not found!\n")
        sys.exit(1)

    try:
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            print("AI: ", end="", flush=True)
            
            print(ask_ai(user_input, n_threads=os.cpu_count() // 2))
    
    except Exception as e:
        print(f"Error loading model: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
