from dotenv import load_dotenv
import os
from openai import OpenAI

# Load environment variables
load_dotenv()

def test_openai_connection():
    try:
        # Get the API key
        api_key = os.getenv('OPENAI_API_KEY')
        print("API Key found:", "Yes" if api_key else "No")
        
        # Create OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Test the connection
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            temperature=0.7,
            max_tokens=50
        )
        
        print("OpenAI Response:", response.choices[0].message.content)
        print("Connection test successful!")
        
    except Exception as e:
        print("Error testing OpenAI connection:", str(e))

if __name__ == "__main__":
    test_openai_connection()
