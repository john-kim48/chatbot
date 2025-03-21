import openai

openai.api_key = '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'

def chat_search(query, relevant_docs):
    # relevant_docs = ((doc_name, content), (doc_name, content), ...)
    # so iterate through relevant_docts and send it in multiple messages
    # Construct the context from the relevant documents
    context = "\n".join([f"Document: {name}\nContent: {doc}" for doc, name in relevant_docs])

    # Query the OpenAI API with the constructed context
    prompt = f"""Read through all of the above documents carefully as your context:
                {context}
                Based on the context, answer the user's query about any relevant bylaws:
                {query}"""

    chat_history = [
        {
            "role": "system",
            "content": ("""
                You are a helpful search engine that will answer the user's query about the 
                city of Iqaluit's Bylaws based on the documents provided. 
                 Then you will carefully read each document
                thoroughly and then accurately answer their question with information from
                the bylaws found. State the file name you found the information from at the end. 
                They may ask about the existence of a certain bylaw, so if found please
                just name the relevant bylaw for them
                If there is no answer found within the files, request the user to ask again 
                but with more clear or specific language"""
            )
        }
    ]

    # for doc, name in relevant_docs:
    #     chat_history.append({"role": "user", "content": f"Content: {doc}"})
    # chat_history.append({"role": "user", "content": prompt})
    chat_history.append({"role": "user", "content": prompt})

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=chat_history
    )
    return response["choices"][0]["message"]["content"] # message too large, figure out how to fix

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
