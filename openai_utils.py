import openai

def chat_search(query, relevant_docs):
    chat_history = [
        {
            "role": "system",
            "content": ("""
                You are a helpful search engine that will answer the user's query about the 
                city of Iqaluit's Bylaws based on the documents provided. Each document will be sent as an individual message.
                You will carefully read each document
                thoroughly and then accurately answer their question with information from
                the bylaws found. State the file name you found the information from at the end. 
                They may ask about the existence of a certain bylaw, so if found please
                just name the relevant bylaw for them
                If there is no answer found within the files, request the user to ask again 
                but with more clear or specific language"""
            )
        }
    ]

    for doc, name in relevant_docs:
        chat_history.append({"role": "user", "content": f"Document: {name}\nContent: {doc}"})
    chat_history.append({"role": "user", "content": f"""Based on the context above, answer the user's query about any relevant bylaws:
                {query}"""})
    
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=chat_history
    )
    return response["choices"][0]["message"]["content"]

# filter keywords out of the query
def filter_keywords(query):
    chat_history = [
        {
            "role": "system",
            "content": ("""
                        Filter out only the keywords from the following query, and give me a list with
                        all those keywords along with any synonyms of those keywords that one may find
                        in legal documents. Please give me the list of all the words with only commas separating them
                        Please ONLY GIVE ME IMPORTANT, RELEVANT KEY WORDS""")
        }
    ]

    chat_history.append({"role": "user", "content": query})

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=chat_history
    )

    return response["choices"][0]["message"]["content"]