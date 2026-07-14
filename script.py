import sqlite3
import requests
from bs4 import BeautifulSoup  

def init_db():
    connection = sqlite3.connect('refactoring_benchmark.db')
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS refactoring_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS benchmark_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER,
            programming_language TEXT NOT NULL,
            problem_description TEXT,
            code_before TEXT NOT NULL,
            code_after TEXT NOT NULL,
            FOREIGN KEY (pattern_id) REFERENCES refactoring_patterns(id)
        )
    ''')
    connection.commit()
    return connection

def scrape_refactoring_page(url, connection):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return 
    except requests.RequestException as e:
        print(f"[-] Connection error for {url}: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    cursor = connection.cursor()

    title_element = soup.find('h1', class_='title')
    if not title_element:
        return

    pattern_name = title_element.text.replace('Refactoring', '').strip()

    try:
        cursor.execute("INSERT INTO refactoring_patterns (pattern_name, url) VALUES (?, ?)", (pattern_name, url))
        pattern_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM refactoring_patterns WHERE url = ?", (url,))
        pattern_id = cursor.fetchone()[0]

    # --- NEW: Extract Problem Description ---
    problem_description = None
    # Find the header element that announces the problem section
    problem_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and 'problem' in tag.text.lower())
    
    if problem_header:
        desc_paragraphs = []
        # Walk through the siblings immediately following the header
        for sibling in problem_header.find_next_siblings():
            # Stop if we hit another header or the code container block
            if sibling.name in ['h2', 'h3', 'h4'] or 'before' in sibling.get('class', []):
                break
            if sibling.name == 'p':
                desc_paragraphs.append(sibling.text.strip())
        
        if desc_paragraphs:
            problem_description = "\n".join(desc_paragraphs)
    # ----------------------------------------

    # Target problem and solution containers
    problem_divs = soup.select('.before pre, .challenge pre, .problem pre')
    solution_divs = soup.select('.after pre, .solution pre')

    if not problem_divs or not solution_divs:
        problem_divs = soup.find_all('pre')
        solution_divs = soup.find_all('pre')

    code_before, code_after = None, None
    
    for prob, sol in zip(problem_divs, solution_divs):
        prob_text = prob.text
        sol_text = sol.text
        
        if "System.out" in prob_text or "void " in prob_text or "String" in prob_text:
            code_before = prob_text.strip()
            code_after = sol_text.strip()
            break 

    if not code_before and problem_divs:
        code_before = problem_divs[0].text.strip()
        code_after = solution_divs[0].text.strip()

    if code_before and code_after:
        # UPDATED: Included problem_description in the SQL query execution
        cursor.execute('''
            INSERT INTO benchmark_pairs (pattern_id, programming_language, problem_description, code_before, code_after)
            VALUES (?, ?, ?, ?, ?)
        ''', (pattern_id, 'java', problem_description, code_before, code_after))
        connection.commit()
        print(f"[+] Successfully processed '{pattern_name}' for Java.")
    else:
        print(f"[!] Warning: Could not isolate Java code for '{pattern_name}'.")

if __name__ == "__main__":
    db_connection = init_db()

    cursor = db_connection.cursor()
    #Comment out the line below so the current data is saved when more urls are added :D
    cursor.execute("DELETE FROM benchmark_pairs;")  # Wipes out the old rows with NULL descriptions
    db_connection.commit()
    print("[+] Reset benchmark_pairs table to update descriptions.")

    # Removed the base domain homepage to prevent the previous AttributeError
    target_urls = [
        "https://refactoring.guru",
        "https://refactoring.guru/extract-method",
        "https://refactoring.guru/inline-method",
        "https://refactoring.guru/extract-variable",
        "https://refactoring.guru/inline-temp",
        "https://refactoring.guru/replace-temp-with-query",
        "https://refactoring.guru/split-temporary-variable",
        "https://refactoring.guru/remove-assignments-to-parameters",
        "https://refactoring.guru/replace-method-with-method-object",
        "https://refactoring.guru/substitute-algorithm"
    ]

    for target in target_urls:
        scrape_refactoring_page(target, db_connection)
    
    db_connection.close()




        