from bs4 import BeautifulSoup
import requests
import weaviate
import cohere
import streamlit as st
from dotenv import load_dotenv
import os


def get_news_data(client):
    url = 'https://www.wrps.on.ca/Modules/News/en'
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html')

    news = soup.find('div', {"id": "blogContentContainer"})
    news_links = news.find_all('a', class_='newsTitle')
    titles = [temp.text for temp in news_links]

    hrefs = [link.get('href') for link in news_links]
    text = []
    curText = ""
    for href in hrefs:
        print(href)
        page = requests.get(href)
        soup = BeautifulSoup(page.text, 'html')
        content = soup.find('div', {"id": "printAreaContent"})
        temp = content.find_all('p')
        for c in temp:
            curText += c.text
        text.append(curText)

    for i in range(len(titles)):
        client.batch.configure(batch_size=1)
        with client.batch as batch:
            #Define data of current object (title, text)
            print(text[i])
            properties = {
                "title": titles[i],
                "text": text[i],
            }
            #Add current Memory object to Weaviate
            batch.add_data_object(
                data_object=properties,
                class_name="News"
                )




def generate_response(query, client, co):
    response = (
        client.query
        .get("News", ["title", "text"])
        .with_near_text({"concepts": [query]})
        .with_limit(2)
        .do()
    )
    responses = response["data"]["Get"]["News"]
    ARTICLE = []

    ARTICLE.append(f"You are a conversational AI that can search through the news, with access to contexts. Do not mention anything about me providing new articles. Answer the query: '{query}', using the title, text from the following news: ")

    for r in responses:
        ARTICLE.append(f"Title:")
        ARTICLE.append(r.get("title"))
        ARTICLE.append(f"Text: ")
        ARTICLE.append(r.get("text"))

    co_summary = co.summarize(text=' '.join(ARTICLE))
    return co_summary.summary
    return ''


def main():
    load_dotenv()

    COHERE_API_KEY = os.getenv('COHERE_API_KEY')
    auth_config = weaviate.AuthApiKey(api_key=os.getenv('WEAVIATE_API_KEY'))
    client = weaviate.Client(
        #Database URL and access key, imported from environment variables
        url = os.getenv('WEAVIATE_URL'),
        auth_client_secret=auth_config,
        additional_headers = {
            #Cohere API key, imported from environment variables
            "X-Cohere-Api-Key": COHERE_API_KEY
        }
    )
    # news_obj = {
    #     #Object name
    #     "class": "News",
    #     #Defines use of Cohere modules
    #     "vectorizer": "text2vec-cohere",
    #     "moduleConfig": {
    #         #Module for adding vectors
    #         "text2vec-cohere": {},
    #         #Module for retrieving vectors
    #         "generative-cohere": {}
    #     }
    # }
    # client.schema.create_class(news_obj)

    co = cohere.Client(COHERE_API_KEY)
    get_news_data(client)
    st.title("Crime Chatbot")
    user_input = st.text_input("You: ", "")
    button_placeholder = st.empty()
    if st.button("Send"):
        bot_response = generate_response(user_input, client, co)
        st.text_area("Bot:", value=bot_response, height=100)
    button_id = button_placeholder._button_id
    js_script = f"""
    <script>
        document.getElementById("{button_id}").setAttribute("onclick", "this.click();");
        document.addEventListener("keypress", function(event) {{
            if (event.key === "Enter") {{
                document.getElementById("{button_id}").click();
            }}
        }});
    </script>
    """
    st.markdown(js_script, unsafe_allow_html=True)

if __name__ == "__main__":
    main()