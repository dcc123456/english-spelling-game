import urllib.request
import json
import os
import re
import time

CET6_URL = "https://raw.githubusercontent.com/KyleBing/english-vocabulary/master/4%20%E5%85%AD%E7%BA%A7-%E4%B9%B1%E5%BA%8F.txt"
DICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/"

def download_file(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"下载失败: {e}")
        return None

def get_phonetic(word):
    try:
        url = DICT_API + word
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data and len(data) > 0:
                entry = data[0]
                if entry.get('phonetic'):
                    return entry['phonetic']
                phonetics = entry.get('phonetics', [])
                for p in phonetics:
                    text = p.get('text', '')
                    if text:
                        return text
        return ''
    except Exception as e:
        return ''

def split_into_syllables(word):
    vowels = 'aeiouAEIOU'
    word = word.lower().strip()
    
    if len(word) <= 2:
        return [word]
    
    syllables = []
    current = ''
    i = 0
    
    while i < len(word):
        char = word[i]
        current += char
        
        if char in vowels:
            if i < len(word) - 1:
                remaining = word[i+1:]
                next_vowel_pos = -1
                for j, c in enumerate(remaining):
                    if c in vowels:
                        next_vowel_pos = j
                        break
                
                if next_vowel_pos > 1:
                    consonants = remaining[:next_vowel_pos]
                    digraphs = ['th', 'ch', 'sh', 'ph', 'wh', 'qu', 'ck', 'ng', 'bl', 'br', 'cl', 'cr', 'dr', 'fl', 'fr', 'gl', 'gr', 'pl', 'pr', 'sc', 'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'sw', 'tr', 'tw']
                    
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
        return [word]
    
    return syllables

def parse_word_data(line):
    parts = line.split('\t')
    if len(parts) < 2:
        return None
    
    word = parts[0].strip()
    meaning = '\t'.join(parts[1:]).strip()
    
    if not word or not meaning or len(word) < 2:
        return None
    
    if not re.match(r'^[a-zA-Z\-]+$', word):
        return None
    
    syllables = split_into_syllables(word)
    
    return {
        'word': word.lower(),
        'phonetic': '',
        'chinese': meaning,
        'syllables': syllables
    }

def get_difficulty(syllables):
    length = len(syllables)
    if length <= 2:
        return 'easy'
    elif length == 3:
        return 'normal'
    else:
        return 'hard'

def main():
    print("正在下载六级词库...")
    
    data = download_file(CET6_URL)
    if not data:
        print("下载失败，请检查网络连接")
        return
    
    print("下载完成！")
    
    lines = [line.strip() for line in data.split('\n') if line.strip()]
    print(f"共 {len(lines)} 行数据")
    
    words = []
    skipped = 0
    
    for line in lines:
        word_data = parse_word_data(line)
        if word_data:
            words.append(word_data)
        else:
            skipped += 1
    
    print(f"解析成功: {len(words)} 个单词")
    print(f"跳过: {skipped} 行")
    
    easy_words = []
    normal_words = []
    hard_words = []
    
    for word in words:
        difficulty = get_difficulty(word['syllables'])
        if difficulty == 'easy':
            easy_words.append(word)
        elif difficulty == 'normal':
            normal_words.append(word)
        else:
            hard_words.append(word)
    
    print(f"\n难度分布:")
    print(f"  简单 (1-2音节): {len(easy_words)} 个")
    print(f"  一般 (3音节): {len(normal_words)} 个")
    print(f"  困难 (4+音节): {len(hard_words)} 个")
    
    output_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    cache_file = os.path.join(output_dir, 'phonetic_cache.json')
    phonetic_cache = {}
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            phonetic_cache = json.load(f)
        print(f"已加载音标缓存: {len(phonetic_cache)} 个")
    
    print("\n正在获取音标...")
    total = len(words)
    for i, word in enumerate(words):
        word_text = word['word']
        if word_text in phonetic_cache:
            word['phonetic'] = phonetic_cache[word_text]
        else:
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)
            
            phonetic = get_phonetic(word_text)
            word['phonetic'] = phonetic
            phonetic_cache[word_text] = phonetic
            
            if i % 100 == 0:
                print(f"进度: {i}/{total} ({i*100//total}%)")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(phonetic_cache, f, ensure_ascii=False, indent=2)
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(phonetic_cache, f, ensure_ascii=False, indent=2)
    
    def write_js(filename, data):
        content = f"window.WORDS_{filename.upper()} = {json.dumps(data, ensure_ascii=False, indent=2)};"
        filepath = os.path.join(output_dir, f'words_{filename}.js')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已保存: words_{filename}.js ({len(data)} 个单词)")
    
    write_js('easy', easy_words)
    write_js('normal', normal_words)
    write_js('hard', hard_words)
    
    print("\n词库生成完成！")
    print(f"文件保存在: {output_dir}")

if __name__ == '__main__':
    main()
