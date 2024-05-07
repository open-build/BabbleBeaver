import feedparser

url = "https://www.buildly.io/news/feed/"

def fetch_and_format_rss_feed(url):
    # Parse the RSS feed
    feed = feedparser.parse(url)
    prompts = []
    
    for entry in feed.entries:
        # Create a prompt based on the article's title and a summary
        prompt = {
            'title': entry.title,
            'prompt': f"Generate a summary for the following article titled '{entry.title}': {entry.summary}"
        }
        prompts.append(prompt)
    
    return prompts



def search_rss_feed(url, keyword):
    # Parse the RSS feed
    feed = feedparser.parse(url)
    filtered_articles = []
    
    for entry in feed.entries:
        # Check if the keyword is in the title or summary
        if keyword.lower() in entry.title.lower() or keyword.lower() in entry.summary.lower():
            article_info = {
                'title': entry.title,
                'link': entry.link
            }
            filtered_articles.append(article_info)
    
    return filtered_articles

