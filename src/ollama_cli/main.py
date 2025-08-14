from provider.openai import chat_stream

def main():
    for chunk in chat_stream('자기소개 부탁해'):
        print(chunk, end='', flush=True)

if __name__ == "__main__":
    main()