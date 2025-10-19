import requests
import json

def ask_question(question, lang=None, top_k=6):
    """Query the HTU RAG system"""
    url = "http://127.0.0.1:8000/ask"
    
    payload = {
        "question": question,
        "top_k": top_k
    }
    
    if lang:
        payload["lang"] = lang
    
    try:
        # Increase timeout based on number of results
        timeout = 30 + (top_k * 15)  # 30s base + 15s per result
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        result = response.json()
        
        print("=" * 60)
        print(f"Question: {question}")
        print("=" * 60)
        print(f"Answer: {result['answer']}")
        print("\nSources:")
        for i, source in enumerate(result['sources'], 1):
            print(f"  {i}. {source}")
        print("=" * 60)
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        print("Make sure the API is running with: uvicorn main:app --reload")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def interactive_mode():
    """Run in interactive mode"""
    print("HTU RAG System Query Tool")
    print("Type 'quit' to exit")
    print("-" * 40)
    
    while True:
        question = input("\nEnter your question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            break
            
        if not question:
            continue
            
        # Ask for language preference
        lang = input("Language (en/ar) [default: auto-detect]: ").strip()
        if not lang:
            lang = None
        elif lang not in ['en', 'ar']:
            print("Invalid language. Using auto-detect.")
            lang = None
        
        # Ask for number of results
        try:
            top_k = input("Number of results [default: 6]: ").strip()
            top_k = int(top_k) if top_k else 6
        except ValueError:
            top_k = 6
        
        ask_question(question, lang, top_k)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Command line mode
        question = " ".join(sys.argv[1:])
        ask_question(question)
    else:
        # Interactive mode
        interactive_mode()
