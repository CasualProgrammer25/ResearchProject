import sqlite3
import Levenshtein
from rouge_score import rouge_scorer
import ollama

def calculate_metrics(ai_code, ground_truth):
    """Calculates textual and keyword overlap metrics between AI code and ground truth."""
    ai_clean = "\n".join([line.strip() for line in ai_code.splitlines() if line.strip()])
    gt_clean = "\n".join([line.strip() for line in ground_truth.splitlines() if line.strip()])
    
    max_len = max(len(ai_clean), len(gt_clean))
    if max_len == 0:
        lev_similarity = 1.0
    else:
        lev_dist = Levenshtein.distance(ai_clean, gt_clean)
        lev_similarity = 1.0 - (lev_dist / max_len)
        
    scorer = rouge_scorer.RougeScorer(['rouge1'], use_stemmer=True)
    scores = scorer.score(gt_clean, ai_clean)
    rouge1_fmeasure = scores['rouge1'].fmeasure
    
    return {
        "levenshtein_similarity": round(lev_similarity * 100, 2),
        "rouge1_f1": round(rouge1_fmeasure * 100, 2)
    }

def run_benchmark():
    connection = sqlite3.connect('refactoring_benchmark.db')
    cursor = connection.cursor()
    
    cursor.execute('''
        SELECT p.pattern_name, b.code_before, b.code_after 
        FROM benchmark_pairs b
        JOIN refactoring_patterns p ON b.pattern_id = p.id
        WHERE b.programming_language = 'java'
    ''')
    rows = cursor.fetchall()
    
    print(f"[+] Found {len(rows)} patterns to evaluate.\n" + "="*50)

    for pattern_name, code_before, code_after in rows:
        print(f"\n[~] Evaluating Pattern: {pattern_name}")
        
        system_instruction = (
            "You are an expert Java refactoring tool. Your task is to refactor the provided code snippet. "
            "You MUST output ONLY the raw, executable Java code. Do not include any explanation. "
            "Do not wrap your answer in markdown code blocks like ```java or ```."
        )
        user_prompt = f"Refactor this Java code using the '{pattern_name}' pattern:\n\n{code_before}"
        
        try:
            # Request refactoring from local Ollama service using gemma3:4b
            response = ollama.chat(
                model='gemma3:4b',
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                options={
                    "temperature": 0.0  # Force deterministic output for consistent metric tracking
                }
            )
            
            ai_generated_code = response.message.content.strip()
            
            # Compute evaluation metrics
            metrics = calculate_metrics(ai_generated_code, code_after)
            
            print(f"    -> Levenshtein Text Match: {metrics['levenshtein_similarity']}%")
            print(f"    -> ROUGE-1 Token Overlap:   {metrics['rouge1_f1']}%")
            
        except Exception as e:
            print(f"    [-] Error processing pattern {pattern_name}: {e}")
            
    connection.close()

if __name__ == "__main__":
    run_benchmark()

# Verify the python package is installed in your virtual environment
#pip install ollama

# Run your benchmark script
#python /Users/nilendubhattacharya/Desktop/ResearchProject/full-workflow.py