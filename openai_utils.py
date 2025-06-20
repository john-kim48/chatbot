import openai

def chat_search(query, relevant_docs):
    chat_history = [
        {
            "role": "system",
            "content": f"""
                You are a helpful search engine that will answer the user's query about the city of Iqaluit's Bylaws 
                based on the documents provided. Each document will be sent as an individual message. You will carefully 
                read each document thoroughly and then accurately answer their question with information from the bylaws found.
                Make sure to only use the information from the documents provided to you.
                If there were no documents sent, please ask the user to ask again in a few minutes, as there is a problem with
                the databae connection.
                If there is no answer found within the files, request the user to ask again but with more clear or specific language. 
                When you answer, please give a list of links by appending the EXACT file name or names you used (excluding the .txt at the end)
                to the end of the following link: https://iqaluit.ca/content/
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

def document_keywords(document):
    chat_history = [
        {
            "role": "system",
            "content": ("""
                        You are a legal keyword extraction assistant. Your job is to read municipal bylaw 
                        documents and return a concise, comma-separated list of important keywords that capture 
                        the legal concepts, regulatory terms, and practical topics in the document.

                        Focus on:
                        Legal jargon and official terms used in municipal regulations
                        Practical subjects (e.g., pets, vehicles, noise, property)
                        Specific restrictions or permissions
                        Generalized synonyms or categories that improve searchability (e.g., “animals” for “dogs and cats”, “vehicles” for “cars”)

                        Return only the keywords — do not summarize or explain the content. Format them as a comma-separated list. You may include short phrases, but no full sentences.

                        Your goal is to help optimize the document for semantic search by extracting keywords that are both representative and discoverable.""")
        }
    ]

    chat_history.append({"role": "user", "content": document})

    response = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=chat_history
    )

    return response["choices"][0]["message"]["content"]