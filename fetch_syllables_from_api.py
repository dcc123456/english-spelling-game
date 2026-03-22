#!/usr/bin/env python3
"""
从专业词典API获取准确的音节划分
使用 Free Dictionary API (https://dictionaryapi.dev/)
多线程并发版本
"""

import json
import os
import re
import ssl
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import threading

ssl._create_default_https_context = ssl._create_unverified_context

print_lock = threading.Lock()


@dataclass
class SyllableResult:
    word: str
    syllables: List[str]
    phonetic: str
    source: str


def get_syllables_from_dictionary_api(word: str) -> Optional[SyllableResult]:
    """
    从 Free Dictionary API 获取音节划分
    """
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data and len(data) > 0:
                entry = data[0]
                
                phonetic = ""
                if entry.get('phonetic'):
                    phonetic = entry['phonetic']
                else:
                    phonetics = entry.get('phonetics', [])
                    for p in phonetics:
                        text = p.get('text', '')
                        if text:
                            phonetic = text
                            break
                
                syllables = extract_syllables_from_phonetic(word, phonetic)
                
                if syllables:
                    return SyllableResult(
                        word=word,
                        syllables=syllables,
                        phonetic=phonetic,
                        source="dictionaryapi.dev"
                    )
        
        return None
    except:
        return None


def extract_syllables_from_phonetic(word: str, phonetic: str) -> Optional[List[str]]:
    """
    从音标中提取音节划分
    """
    if not phonetic or not phonetic.strip():
        return None
    
    phonetic = phonetic.strip()
    if phonetic.startswith('[') and phonetic.endswith(']'):
        phonetic = phonetic[1:-1]
    if phonetic.startswith('/') and phonetic.endswith('/'):
        phonetic = phonetic[1:-1]
    
    if '.' not in phonetic:
        return None
    
    phonetic_parts = phonetic.split('.')
    syllables = infer_syllables_from_phonetic_parts(word.lower(), phonetic_parts)
    
    return syllables


def infer_syllables_from_phonetic_parts(word: str, phonetic_parts: List[str]) -> List[str]:
    """
    根据音标音节推断单词的音节划分
    """
    word_lower = word.lower()
    num_syllables = len(phonetic_parts)
    
    if num_syllables <= 1:
        return [word_lower]
    
    vowels = 'aeiou'
    vowel_positions = []
    
    for i, char in enumerate(word_lower):
        if char in vowels:
            vowel_positions.append(i)
    
    if len(vowel_positions) < num_syllables:
        return [word_lower]
    
    if len(vowel_positions) == num_syllables:
        return split_by_vowels(word_lower, vowel_positions)
    
    return split_into_n_syllables(word_lower, num_syllables)


def split_by_vowels(word: str, vowel_positions: List[int]) -> List[str]:
    if not vowel_positions:
        return [word]
    
    syllables = []
    prev_end = 0
    
    for i, vowel_pos in enumerate(vowel_positions):
        if i == len(vowel_positions) - 1:
            syllables.append(word[prev_end:])
        else:
            next_vowel = vowel_positions[i + 1]
            consonants = next_vowel - vowel_pos - 1
            
            if consonants <= 0:
                split_pos = vowel_pos + 1
            elif consonants == 1:
                split_pos = vowel_pos + 1
            else:
                split_pos = vowel_pos + 1 + consonants // 2
            
            syllables.append(word[prev_end:split_pos])
            prev_end = split_pos
    
    return syllables if syllables else [word]


def split_into_n_syllables(word: str, n: int) -> List[str]:
    if n <= 1:
        return [word]
    
    vowels = 'aeiou'
    vowel_positions = []
    
    for i, char in enumerate(word):
        if char in vowels:
            vowel_positions.append(i)
    
    if len(vowel_positions) < n:
        return [word]
    
    syllables = []
    split_points = []
    
    vowels_per_syllable = len(vowel_positions) / n
    
    for s in range(1, n):
        target_vowel_idx = int(s * vowels_per_syllable)
        if target_vowel_idx < len(vowel_positions):
            vowel_pos = vowel_positions[target_vowel_idx]
            
            for i in range(vowel_pos + 1, len(word)):
                if word[i] not in vowels:
                    if i + 1 < len(word) and word[i + 1] in vowels:
                        split_points.append(i)
                        break
    
    split_points = sorted(set(split_points))[:n-1]
    
    if not split_points:
        return split_by_vowels(word, vowel_positions[:n])
    
    prev = 0
    for sp in split_points:
        if sp > prev and sp < len(word):
            syllables.append(word[prev:sp])
            prev = sp
    syllables.append(word[prev:])
    
    result = [s for s in syllables if s]
    return result if result else [word]


def load_words_file(filepath: str) -> Tuple[List[Dict], str]:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    var_match = re.search(r'window\.(WORDS_\w+)', content)
    var_name = var_match.group(1) if var_match else "WORDS"
    
    match = re.search(r'window\.WORDS_\w+\s*=\s*(\[.*\]);?\s*$', content, re.DOTALL)
    if match:
        json_str = match.group(1)
        return json.loads(json_str), var_name
    return [], var_name


def save_words_file(filepath: str, words: List[Dict], var_name: str):
    content = f"window.{var_name} = {json.dumps(words, ensure_ascii=False, indent=2)};"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def process_word_api(word_data: Dict) -> Tuple[str, Optional[List[str]], str]:
    """
    处理单个单词，从API获取音节
    返回 (word, syllables, phonetic)
    """
    word = word_data.get('word', '')
    current_phonetic = word_data.get('phonetic', '')
    
    if current_phonetic and '.' in current_phonetic:
        syllables = extract_syllables_from_phonetic(word, current_phonetic)
        if syllables:
            return word, syllables, current_phonetic
    
    result = get_syllables_from_dictionary_api(word)
    
    if result and result.syllables:
        return word, result.syllables, result.phonetic
    
    return word, None, ""


def process_file_concurrent(filepath: str, cache: Dict, max_workers: int = 10) -> Tuple[int, List[str], Dict]:
    """
    并发处理词库文件
    """
    words, var_name = load_words_file(filepath)
    fixed_count = 0
    fixes = []
    results_map = {}
    
    words_to_fetch = []
    for word_data in words:
        word = word_data.get('word', '')
        if word in cache:
            results_map[word] = cache[word]
        else:
            words_to_fetch.append(word_data)
    
    if words_to_fetch:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_word_api, wd): wd for wd in words_to_fetch}
            
            for future in as_completed(futures):
                word, syllables, phonetic = future.result()
                if syllables:
                    results_map[word] = {'syllables': syllables, 'phonetic': phonetic}
    
    for i, word_data in enumerate(words):
        word = word_data.get('word', '')
        current_syllables = word_data.get('syllables', [])
        
        if word in results_map and results_map[word].get('syllables'):
            new_syllables = results_map[word]['syllables']
            if new_syllables != current_syllables:
                words[i] = word_data.copy()
                words[i]['syllables'] = new_syllables
                if results_map[word].get('phonetic'):
                    words[i]['phonetic'] = results_map[word]['phonetic']
                fixed_count += 1
                fixes.append(f"  - {word}: {'-'.join(current_syllables)} -> {'-'.join(new_syllables)}")
    
    if fixed_count > 0:
        save_words_file(filepath, words, var_name)
    
    return fixed_count, fixes, results_map


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    
    cache_file = os.path.join(script_dir, 'syllable_cache.json')
    cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f"已加载缓存: {len(cache)} 个单词")
    
    words_files = [
        os.path.join(data_dir, 'words_easy.js'),
        os.path.join(data_dir, 'words_normal.js'),
        os.path.join(data_dir, 'words_hard.js')
    ]
    
    existing_files = [f for f in words_files if os.path.exists(f)]
    
    if not existing_files:
        print("未找到词库文件!")
        return
    
    print(f"找到 {len(existing_files)} 个词库文件")
    print("开始从词典API获取音节划分（多线程并发）...\n")
    
    total_fixed = 0
    
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        print(f"处理 {filename}...")
        
        try:
            start_time = time.time()
            fixed_count, fixes, results_map = process_file_concurrent(filepath, cache, max_workers=15)
            elapsed = time.time() - start_time
            
            total_fixed += fixed_count
            cache.update(results_map)
            
            print(f"  修正了 {fixed_count} 个单词 (耗时 {elapsed:.1f}秒)")
            for fix in fixes[:10]:
                print(fix)
            if len(fixes) > 10:
                print(f"  ... 还有 {len(fixes) - 10} 个修正")
            print()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"  处理 {filepath} 时出错: {e}")
    
    print(f"\n修正完成! 共修正 {total_fixed} 个单词的音节切分")
    print(f"缓存已保存: {cache_file} ({len(cache)} 个单词)")


if __name__ == '__main__':
    main()
