class translate_core:
    def __init__(self, model):
        self.llm = model
        
    def translate_text(self, text):
        prompt = "You are a export of academic translate, proper nouns need to be marked in English, statements as concise and academic as possible, please translate the following English to Chinese:"+text
        response = self.llm.create_chat_completion(
        messages=prompt,
        max_tokens=1000,
        stream=False
        )
        result = ""
        for choice in response["choices"]:
            result += choice["message"]["content"]
            
        return result