import openai
import json
import tiktoken
from scipy import spatial
from dotenv import load_dotenv

class UCLAChatBot:
    def __init__(self, API_KEY, CHAT_MODEL, EMBEDDING_MODEL, df):
        self.client = openai.OpenAI(api_key=API_KEY)
        self.CHAT_MODEL = CHAT_MODEL
        self.EMBEDDING_MODEL = EMBEDDING_MODEL
        self.df = df

    def num_tokens(self, text):
        model = self.CHAT_MODEL
        if(model == "gpt-4o"):
            model = "gpt-4"
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))

    def strings_rank(self, query, relatededness_fn=lambda x,y: 1 - spatial.distance.cosine(x,y), top_n = 100):
        query_embedding_respond = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=query
        )
        query_embedding = query_embedding_respond.data[0].embedding

        strings_and_relatedness = [
            (row["text"], relatededness_fn(query_embedding, json.loads(row["embeddings"]))) for i, row in self.df.iterrows()
        ]

        strings_and_relatedness.sort(key=lambda x: x[1], reverse=True)
        strings, relatednesses = zip(*strings_and_relatedness)
        return strings[:top_n], relatednesses[:top_n] 
    
    def query_message(self, user, query, token_budget):
        strings, relatednesses = self.strings_rank(query)
        introduction = 'Use the webpages and articles on UCLA transfering to answer the subsequent questions. If the answer cannot be found in the articles, write "I could not find an answer." Please go staight into the response, do not include starters like "Answer:"'
        history = "\nI will now give you the User's previous queries and your responses:\n"
        for h in user.history:
            history += f"{h['type']}: {h['message']}\n"
        question = f"Question: \"{query}\""
        message = introduction

        for string in strings:
            next_article = f'\n\nWebpage:\n"""\n{string}\n"""'
            if self.num_tokens(message + next_article + question) > token_budget:
                break
            else:
                message += next_article

        message += history
        return message + "\n" + question
    
    def ask(self, user, query, token_budget = 4096 - 500, print_message = False):
        message = self.query_message(user, query, token_budget=token_budget)
        user.addHistory('User', query)
        if print_message:
            print(message)

        messages =[
            {"role": "system", "content": "You answer prompts about the UCLA transfer process."},
            {"role": "user", "content": message},
        ]

        response = self.client.chat.completions.create(
            model=self.CHAT_MODEL,
            messages=messages,
            temperature=0
        )

        response_message = response.choices[0].message.content
        user.addHistory('Bot', response_message)

        return response_message


    