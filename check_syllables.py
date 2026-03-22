#!/usr/bin/env python3
"""
音节切分错误检测工具
使用多线程方式检测词库中音节切分不正确的单词
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class WordError:
    word: str
    current_syllables: List[str]
    suggested_syllables: List[str]
    phonetic: str
    chinese: str
    error_type: str


def count_phonetic_syllables(phonetic: str) -> int:
    """
    从音标中计算音节数
    音标中使用 `.` 作为音节分隔符
    如果没有 `.`，则通过音节核数量估算
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
    
    syllable_nuclei = re.findall(
        r'(?:aɪ|aʊ|eɪ|oʊ|ɔɪ|ɪə|ɛə|ʊə|aɪə|aʊə|' +
        r'[aeiouæɑɒəɜɪʊɛɔʌ])',
        phonetic,
        re.IGNORECASE
    )
    
    return len(syllable_nuclei) if syllable_nuclei else 1


def split_word_into_syllables(word: str, num_syllables: int) -> List[str]:
    """
    将单词按指定音节数切分
    使用更准确的音节切分规则
    """
    word_lower = word.lower()
    
    if num_syllables <= 1:
        return [word_lower]
    
    if len(word_lower) <= num_syllables:
        return list(word_lower)
    
    vowels = 'aeiou'
    vowel_positions = []
    
    for i, char in enumerate(word_lower):
        if char in vowels:
            vowel_positions.append(i)
    
    if len(vowel_positions) < num_syllables:
        return [word_lower]
    
    syllables = []
    split_points = []
    
    vowels_per_syllable = len(vowel_positions) / num_syllables
    
    for s in range(1, num_syllables):
        target_vowel_idx = int(s * vowels_per_syllable)
        if target_vowel_idx < len(vowel_positions):
            vowel_pos = vowel_positions[target_vowel_idx]
            split_pos = find_split_position(word_lower, vowel_pos)
            if split_pos and split_pos < len(word_lower):
                split_points.append(split_pos)
    
    split_points = sorted(set(split_points))[:num_syllables-1]
    
    if not split_points:
        for i in range(1, num_syllables):
            pos = int(len(word_lower) * i / num_syllables)
            for j in range(pos, min(pos + 3, len(word_lower))):
                if word_lower[j] in vowels:
                    split_points.append(j + 1)
                    break
        split_points = sorted(set(split_points))[:num_syllables-1]
    
    if not split_points:
        return [word_lower]
    
    prev = 0
    for sp in split_points:
        if sp > prev and sp < len(word_lower):
            syllables.append(word_lower[prev:sp])
            prev = sp
    syllables.append(word_lower[prev:])
    
    return syllables if syllables else [word_lower]


def find_split_position(word: str, vowel_pos: int) -> Optional[int]:
    """
    在元音位置后找到合适的切分点
    音节切分规则：VCV -> V-CV, VCCV -> VC-CV
    """
    vowels = 'aeiou'
    
    for i in range(vowel_pos + 1, len(word)):
        if i + 1 < len(word) and word[i+1] in vowels:
            if word[i] not in vowels:
                consonants_before_next_vowel = 0
                for j in range(i, len(word)):
                    if word[j] not in vowels:
                        consonants_before_next_vowel += 1
                    else:
                        break
                
                if consonants_before_next_vowel >= 2:
                    return i + 1
                else:
                    return i
    
    return None


def validate_syllables(word: str, syllables: List[str]) -> Tuple[bool, str]:
    """
    验证音节切分是否合理
    """
    word_lower = word.lower()
    combined = ''.join(s.lower() for s in syllables)
    
    if combined != word_lower:
        return False, f"切分后组合不等于原单词: '{combined}' != '{word_lower}'"
    
    for i, syl in enumerate(syllables):
        if len(syl) == 0:
            return False, f"第{i+1}个音节为空"
        
        if len(syl) == 1 and syl.lower() not in ['a', 'i']:
            return False, f"第{i+1}个音节 '{syl}' 只有一个字母(非a/i)"
    
    return True, ""


def check_syllable_count_match(word: str, syllables: List[str], phonetic: str) -> Tuple[bool, str, int]:
    """
    检查音节切分数是否与音标音节数匹配
    返回 (是否匹配, 错误信息, 音标音节数)
    """
    phonetic_count = count_phonetic_syllables(phonetic)
    current_count = len(syllables)
    
    if phonetic_count == 0:
        return True, "", 0
    
    if current_count != phonetic_count:
        return False, f"音节数不匹配: 当前{current_count}个, 音标显示{phonetic_count}个", phonetic_count
    
    return True, "", phonetic_count


def check_word(word_data: Dict) -> Optional[WordError]:
    """
    检查单个单词的音节切分是否正确
    """
    word = word_data.get('word', '')
    current_syllables = word_data.get('syllables', [])
    phonetic = word_data.get('phonetic', '')
    chinese = word_data.get('chinese', '')
    
    is_valid, error_msg = validate_syllables(word, current_syllables)
    if not is_valid:
        suggested = split_word_into_syllables(word, len(current_syllables))
        return WordError(
            word=word,
            current_syllables=current_syllables,
            suggested_syllables=suggested,
            phonetic=phonetic,
            chinese=chinese,
            error_type=error_msg
        )
    
    if phonetic and phonetic.strip():
        is_match, error_msg, phonetic_count = check_syllable_count_match(word, current_syllables, phonetic)
        if not is_match:
            suggested = split_word_into_syllables(word, phonetic_count)
            return WordError(
                word=word,
                current_syllables=current_syllables,
                suggested_syllables=suggested,
                phonetic=phonetic,
                chinese=chinese,
                error_type=error_msg
            )
    
    return None


def load_words_file(filepath: str) -> List[Dict]:
    """
    加载词库JS文件
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'window\.WORDS_\w+\s*=\s*(\[.*\]);?\s*$', content, re.DOTALL)
    if match:
        json_str = match.group(1)
        return json.loads(json_str)
    return []


def process_words_file(filepath: str) -> List[WordError]:
    """
    处理单个词库文件
    """
    errors = []
    words = load_words_file(filepath)
    
    for word_data in words:
        error = check_word(word_data)
        if error:
            errors.append(error)
    
    return errors


def generate_report(errors: List[WordError], output_dir: str):
    """
    生成错误报告
    """
    errors_data = []
    for e in errors:
        errors_data.append({
            'word': e.word,
            'current_syllables': e.current_syllables,
            'suggested_syllables': e.suggested_syllables,
            'phonetic': e.phonetic,
            'chinese': e.chinese,
            'error_type': e.error_type
        })
    
    json_path = os.path.join(output_dir, 'syllable_errors.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(errors_data, f, ensure_ascii=False, indent=2)
    print(f"JSON报告已保存: {json_path}")
    
    txt_path = os.path.join(output_dir, 'syllable_errors.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"音节切分错误报告\n")
        f.write(f"共发现 {len(errors)} 个切分错误的单词\n")
        f.write("=" * 80 + "\n\n")
        
        for i, e in enumerate(errors, 1):
            f.write(f"{i}. {e.word}\n")
            f.write(f"   中文: {e.chinese}\n")
            f.write(f"   音标: {e.phonetic}\n")
            f.write(f"   当前切分: {'-'.join(e.current_syllables)}\n")
            f.write(f"   建议切分: {'-'.join(e.suggested_syllables)}\n")
            f.write(f"   错误类型: {e.error_type}\n")
            f.write("\n")
    
    print(f"文本报告已保存: {txt_path}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    output_dir = script_dir
    
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
    print("开始多线程检测...")
    
    all_errors = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_file = {executor.submit(process_words_file, f): f for f in existing_files}
        
        for future in as_completed(future_to_file):
            filepath = future_to_file[future]
            try:
                errors = future.result()
                filename = os.path.basename(filepath)
                print(f"  {filename}: 发现 {len(errors)} 个错误")
                all_errors.extend(errors)
            except Exception as e:
                print(f"  处理 {filepath} 时出错: {e}")
    
    print(f"\n检测完成! 共发现 {len(all_errors)} 个音节切分错误的单词")
    
    generate_report(all_errors, output_dir)


if __name__ == '__main__':
    main()
