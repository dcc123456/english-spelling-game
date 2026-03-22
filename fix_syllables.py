#!/usr/bin/env python3
"""
音节切分修正工具 - 仅修正音标中有明确音节分隔符的单词
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple


def count_phonetic_syllables_with_dot(phonetic: str) -> int:
    """
    只计算音标中有 `.` 分隔符的音节数
    如果没有 `.` 则返回 0（不处理）
    """
    if not phonetic or not phonetic.strip():
        return 0
    
    phonetic = phonetic.strip()
    if phonetic.startswith('[') and phonetic.endswith(']'):
        phonetic = phonetic[1:-1]
    if phonetic.startswith('/') and phonetic.endswith('/'):
        phonetic = phonetic[1:-1]
    
    if '.' in phonetic:
        return len(phonetic.split('.'))
    
    return 0


def split_into_syllables(word: str, num_syllables: int) -> List[str]:
    """
    将单词切分成指定数量的音节
    使用基于原始算法的改进版本
    """
    word_lower = word.lower()
    
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
        return split_by_vowel_count(word_lower, vowel_positions)
    
    syllables = []
    current = ''
    i = 0
    
    digraphs = ['th', 'ch', 'sh', 'ph', 'wh', 'qu', 'ck', 'ng', 'bl', 'br', 
                'cl', 'cr', 'dr', 'fl', 'fr', 'gl', 'gr', 'pl', 'pr', 'sc', 
                'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'sw', 'tr', 'tw']
    
    while i < len(word_lower):
        char = word_lower[i]
        current += char
        
        if char in vowels:
            if i < len(word_lower) - 1:
                remaining = word_lower[i+1:]
                next_vowel_pos = -1
                for j, c in enumerate(remaining):
                    if c in vowels:
                        next_vowel_pos = j
                        break
                
                if next_vowel_pos > 1:
                    consonants = remaining[:next_vowel_pos]
                    
                    split_point = 1
                    for digraph in digraphs:
                        if consonants.startswith(digraph):
                            split_point = len(digraph)
                            break
                    
                    if len(consonants) > split_point:
                        current += consonants[:split_point]
                        i += split_point
                        syllables.append(current)
                        current = ''
        
        i += 1
    
    if current:
        syllables.append(current)
    
    if not syllables:
        return [word_lower]
    
    if len(syllables) == num_syllables:
        return syllables
    
    if len(syllables) > num_syllables:
        return merge_syllables(syllables, num_syllables)
    
    return split_by_vowel_count(word_lower, vowel_positions)


def split_by_vowel_count(word: str, vowel_positions: List[int]) -> List[str]:
    """
    按元音位置切分
    """
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


def merge_syllables(syllables: List[str], target_count: int) -> List[str]:
    """
    合并音节以达到目标数量
    """
    if len(syllables) <= target_count:
        return syllables
    
    result = []
    merge_count = len(syllables) - target_count + 1
    
    i = 0
    while i < len(syllables):
        if merge_count > 0 and i + 1 < len(syllables):
            result.append(syllables[i] + syllables[i + 1])
            i += 2
            merge_count -= 1
        else:
            result.append(syllables[i])
            i += 1
    
    return result


def fix_word_syllables(word_data: Dict) -> Tuple[Dict, bool, str]:
    """
    修正单个单词的音节切分
    只修正音标中有明确 `.` 分隔符的单词
    """
    word = word_data.get('word', '')
    current_syllables = word_data.get('syllables', [])
    phonetic = word_data.get('phonetic', '')
    
    if not phonetic or not phonetic.strip():
        return word_data, False, ""
    
    phonetic_count = count_phonetic_syllables_with_dot(phonetic)
    current_count = len(current_syllables)
    
    if phonetic_count == 0:
        return word_data, False, ""
    
    combined = ''.join(s.lower() for s in current_syllables)
    if combined != word.lower():
        return word_data, False, ""
    
    if current_count == phonetic_count:
        return word_data, False, ""
    
    new_syllables = split_into_syllables(word, phonetic_count)
    
    new_combined = ''.join(s.lower() for s in new_syllables)
    if new_combined != word.lower():
        return word_data, False, ""
    
    if new_syllables == current_syllables:
        return word_data, False, ""
    
    fixed_data = word_data.copy()
    fixed_data['syllables'] = new_syllables
    
    return fixed_data, True, f"{word}: {'-'.join(current_syllables)} -> {'-'.join(new_syllables)} (音标: {phonetic})"


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


def process_file(filepath: str) -> Tuple[int, List[str]]:
    words, var_name = load_words_file(filepath)
    fixed_count = 0
    fixes = []
    
    for i, word_data in enumerate(words):
        fixed_data, was_fixed, fix_note = fix_word_syllables(word_data)
        if was_fixed:
            words[i] = fixed_data
            fixed_count += 1
            fixes.append(f"  - {fix_note}")
    
    if fixed_count > 0:
        save_words_file(filepath, words, var_name)
    
    return fixed_count, fixes


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    
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
    print("开始多线程修正音节切分（仅修正音标中有明确分隔符的单词）...\n")
    
    total_fixed = 0
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_file = {executor.submit(process_file, f): f for f in existing_files}
        
        for future in as_completed(future_to_file):
            filepath = future_to_file[future]
            filename = os.path.basename(filepath)
            try:
                fixed_count, fixes = future.result()
                total_fixed += fixed_count
                print(f"{filename}: 修正了 {fixed_count} 个单词")
                for fix in fixes:
                    print(fix)
                print()
            except Exception as e:
                print(f"  处理 {filepath} 时出错: {e}")
    
    print(f"修正完成! 共修正 {total_fixed} 个单词的音节切分")


if __name__ == '__main__':
    main()
