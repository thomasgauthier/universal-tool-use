import argparse
from core.api import app, configure_client

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DeepSeek OpenAI Tools Proxy')
    parser.add_argument('--api-key', default="lol", help='API key for authentication')
    parser.add_argument('--base-url', default="http://0.0.0.0:4000/v1", help='Base URL for the API')
    parser.add_argument('--port', type=int, default=8001, help='Port to run the server on')
    
    args = parser.parse_args()
    
    # Configure the OpenAI client with command line arguments
    configure_client(args.api_key, args.base_url)
    
    app.run(debug=True, port=args.port)
