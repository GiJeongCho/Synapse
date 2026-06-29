from xml.etree import ElementTree as ET
import re

def parse_and_summarize_news(content="", **kwargs):
    """Parse RSS XML and extract article summaries with deduplication."""
    try:
        if not content:
            return {"status": "error", "summary": "", "reason": "No content provided"}
        
        root = ET.fromstring(content)
        articles = []
        seen_titles = set()
        
        for item in root.findall(".//item"):
            title_elem = item.find("title")
            desc_elem = item.find("description")
            link_elem = item.find("link")
            pub_elem = item.find("pubDate")
            
            title = title_elem.text if title_elem is not None else "No title"
            description = desc_elem.text if desc_elem is not None else "No description"
            link = link_elem.text if link_elem is not None else ""
            pub_date = pub_elem.text if pub_elem is not None else ""
            
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            clean_desc = re.sub(r"<[^>]+>", "", description)[:300]
            articles.append({
                "title": title[:100],
                "summary": clean_desc,
                "link": link,
                "date": pub_date
            })
            
            if len(articles) >= 10:
                break
        
        if not articles:
            return {"status": "error", "summary": "", "reason": "No articles found in RSS"}
        
        summary_text = "Bloomberg News Summary\n" + "="*50 + "\n\n"
        for i, article in enumerate(articles, 1):
            summary_text += f"{i}. {article['title']}\n"
            summary_text += f"   {article['summary']}\n"
            if article['link']:
                summary_text += f"   Link: {article['link']}\n"
            summary_text += "\n"
        
        summary_text = summary_text[:15000]
        
        return {"status": "success", "summary": summary_text, "content": summary_text, "article_count": len(articles)}
    
    except ET.ParseError as e:
        return {"status": "error", "summary": "", "reason": f"XML parse error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "summary": "", "reason": f"Parse error: {str(e)}"}
