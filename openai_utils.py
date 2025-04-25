import openai

def chat_search(query, relevant_docs):
    chat_history = [
        {
            "role": "system",
            "content": f"""
                You are a helpful search engine that will answer the user's query about the city of Iqaluit's Bylaws 
                based on the documents provided. Each document will be sent as an individual message. You will carefully 
                read each document thoroughly and then accurately answer their question with information from the bylaws found. 
                If there is no answer found within the files, request the user to ask again but with more clear or specific language. 
                When you answer them, please give a link or list of links by appending the file name or names (without the .txt at the end)
                you used for the answer to the end of the following link: https://iqaluit.ca/content/
                The query is: {query}"""
        }
    ]

    for doc, name in relevant_docs:
        chat_history.append({"role": "user", "content": f"Document: {name}\nContent: {doc}"})
    
    response = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=chat_history
    )
    return response["choices"][0]["message"]["content"]

# filter keywords out of the query
def filter_keywords(query):
    chat_history = [
        {
            "role": "system",
            "content": ("""
                        Filter out only the keywords from the following query, and give me a list with all 
                        those keywords along with any synonyms of those keywords that one may find in legal documents 
                        pertaining to bylaws or laws. Please give me the list of all the words with only commas separating them. 
                        Please ONLY GIVE ME IMPORTANT, RELEVANT KEYWORDS""")
        }
    ]

    chat_history.append({"role": "user", "content": query})

    response = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=chat_history
    )

    return response["choices"][0]["message"]["content"]