from ai_engine.openai_service import get_openai_client


client = get_openai_client()

def normalize(text):

    response = client.chat.completions.create(

        model="gpt-4.1-mini",

        messages=[
        {"role":"user","content":text}
        ]

    )

    return response.choices[0].message.content
