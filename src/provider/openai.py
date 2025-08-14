import os
from openai import OpenAI

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

client = OpenAI(
    api_key=OPENAI_API_KEY
)

def chat_stream(message: str, model='gpt-4o'):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": message}
        ],
        stream=True
    )

    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content