import os
from zhipuai import ZhipuAI
os.environ["API_KEY"] = ""

def get_completion(prompt,model="glm-4-flash",temperature=0):
    api_key = os.environ.get('API_KEY')
    client = ZhipuAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature
    )
    if len(response.choices) > 0:
        return response.choices[0].message.content
    else:
        return "generate answer error"

