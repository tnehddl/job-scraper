from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__, template_folder="templates")

HEADERS = {
      'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      'Accept':
      'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.5',
}

def scrape_berlinstartup(term):
    url = f"https://berlinstartupjobs.com/skill-areas/{term}/"
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"[Berlin Startup] Status Code: {response.status_code}") # ← 상태 코드 확인용
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 여러 태그 구조에 대응하도록 보다 유연하게 파싱합니다.
            items = soup.find_all(lambda tag: tag.name == "li" and ("bjs-jlid" in (tag.get("class") or []) or tag.find("h4")))
            for item in items:
                try:
                    title_elem = item.find("h4") or item.find("a")
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    company_elem = item.find(lambda t: t.name in ["a", "p", "div"] and ("bjs-jlid__b" in (t.get("class") or []) or t.get("class") is None))
                    company = company_elem.get_text(strip=True) if company_elem else ""
                    link_tag = item.find("a")
                    link = link_tag["href"] if link_tag and link_tag.has_attr("href") else url
                    jobs.append({"title": title, "company": company, "link": link, "source": "Berlin Startup Jobs"})
                except Exception as e:
                    print(f"Berlin item 파싱 에러: {e}")
    except Exception as e:
        print(f"Berlin Startup 에러: {e}")
    return jobs

def scrape_web3(term):
    url = f"https://web3.career/{term}-jobs"
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"[Web3 Career] Status Code: {response.status_code}") # ← 상태 코드 확인용
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 사이트 구조가 바뀔 수 있으니 여러 선택자를 시도합니다.
            # 테이블 형태 또는 카드 형태 모두 대응
            # 1) 테이블 행
            rows = soup.find_all("tr")
            for row in rows:
                try:
                    title = ""
                    company = ""
                    link = ""
                    # 제목 찾기
                    if row.find("h2"):
                        title = row.find("h2").get_text(strip=True)
                    elif row.find("a"):
                        title = row.find("a").get_text(strip=True)
                    # 회사
                    cmp = row.find(class_="text-muted") or row.find("td", class_=lambda c: c and "company" in c)
                    if cmp:
                        company = cmp.get_text(strip=True)
                    # 링크
                    a = row.find("a", href=True)
                    if a:
                        link = a["href"]
                        if link.startswith("/"):
                            link = "https://web3.career" + link
                    if title:
                        jobs.append({"title": title, "company": company, "link": link or url, "source": "Web3 Career"})
                except Exception as e:
                    print(f"Web3 row 파싱 에러: {e}")
            # 2) 카드형 리스트도 추가 검사
            cards = soup.find_all(class_=lambda c: c and ("job" in c or "card" in c))
            for card in cards:
                try:
                    t = card.find(lambda t: t.name in ["h2", "h3", "a"]) or card
                    title = t.get_text(strip=True)
                    a = card.find("a", href=True)
                    link = a["href"] if a else url
                    company = card.find(class_=lambda c: c and "company" in c)
                    company = company.get_text(strip=True) if company else ""
                    if title:
                        if link.startswith("/"):
                            link = "https://web3.career" + link
                        jobs.append({"title": title, "company": company, "link": link, "source": "Web3 Career"})
                except Exception:
                    pass
    except Exception as e:
        print(f"Web3 에러: {e}")
    return jobs

def scrape_weworkremotely(term):
    url = f"https://weworkremotely.com/remote-jobs/search?utf8=%E2%9C%93&term={term}"
    jobs = []
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"[We Work Remotely] Status Code: {response.status_code}") # ← 상태 코드 확인용
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            sections = soup.find_all("section", class_=lambda c: c and "jobs" in c)
            for section in sections:
                posts = section.find_all("li")
                for post in posts:
                    try:
                        if "view-all" in (post.get("class") or []):
                            continue
                        title_elem = post.find("span", class_=lambda c: c and "title" in c) or post.find("a")
                        company_elem = post.find("span", class_=lambda c: c and "company" in c)
                        link_tag = post.find("a", href=True)
                        if title_elem and link_tag:
                            job_link = link_tag["href"]
                            href = job_link if job_link.startswith("http") else f"https://weworkremotely.com{job_link}"
                            jobs.append({
                                "title": title_elem.get_text(strip=True),
                                "company": company_elem.get_text(strip=True) if company_elem else "",
                                "link": href,
                                "source": "We Work Remotely"
                            })
                    except Exception as e:
                        print(f"WWR post 파싱 에러: {e}")
    except Exception as e:
        print(f"WWR 에러: {e}")
    return jobs

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/search")
def search():
    # `term` 또는 `keyword` 파라미터 모두 허용
    term = request.args.get("term") or request.args.get("keyword")
    if not term:
        return render_template("index.html")

    keyword = term.strip()
    if not keyword:
        return render_template("index.html")

    q = keyword.lower()
    all_jobs = []
    all_jobs.extend(scrape_berlinstartup(q))
    all_jobs.extend(scrape_web3(q))
    all_jobs.extend(scrape_weworkremotely(q))

    error = None
    if not all_jobs:
        error = f'"{keyword}"에 대한 결과를 찾지 못했습니다.'

    # 통합된 프런트엔드 템플릿으로 렌더
    return render_template("index.html", keyword=keyword, jobs=all_jobs, error=error)

if __name__ == "__main__":
    app.run(debug=True)
