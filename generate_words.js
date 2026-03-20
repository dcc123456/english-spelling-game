const https = require('https');
const fs = require('fs');
const path = require('path');

const CET6_URL = 'https://raw.githubusercontent.com/KyleBing/english-vocabulary/main/cet6.txt';

function downloadFile(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(data));
            res.on('error', reject);
        }).on('error', reject);
    });
}

function splitIntoSyllables(word) {
    const vowels = 'aeiouAEIOU';
    const syllables = [];
    let currentSyllable = '';
    let prevIsVowel = false;
    
    for (let i = 0; i < word.length; i++) {
        const char = word[i];
        const isVowel = vowels.includes(char);
        
        currentSyllable += char;
        
        if (isVowel && !prevIsVowel && i < word.length - 1) {
            const nextChars = word.slice(i + 1);
            const nextVowelIndex = nextChars.split('').findIndex(c => vowels.includes(c));
            
            if (nextVowelIndex > 1) {
                const consonantsAfter = nextChars.slice(0, nextVowelIndex);
                if (consonantsAfter.length >= 2 && !['th', 'ch', 'sh', 'ph', 'wh', 'qu', 'ck', 'ng'].includes(consonantsAfter.slice(0, 2))) {
                    const splitPoint = Math.floor(consonantsAfter.length / 2);
                    currentSyllable += consonantsAfter.slice(0, splitPoint);
                    i += splitPoint;
                    syllables.push(currentSyllable);
                    currentSyllable = consonantsAfter.slice(splitPoint);
                }
            }
        }
        
        prevIsVowel = isVowel;
    }
    
    if (currentSyllable) {
        syllables.push(currentSyllable);
    }
    
    if (syllables.length === 0) {
        return [word];
    }
    
    return syllables;
}

function parseWordData(line) {
    const parts = line.split('\t');
    if (parts.length < 2) return null;
    
    const word = parts[0].trim();
    const meaning = parts.slice(1).join(' ').trim();
    
    if (!word || !meaning || word.length < 2) return null;
    
    const syllables = splitIntoSyllables(word);
    
    return {
        word: word.toLowerCase(),
        phonetic: '',
        chinese: meaning,
        syllables: syllables.map(s => s.toLowerCase())
    };
}

function getDifficulty(syllables) {
    const len = syllables.length;
    if (len <= 2) return 'easy';
    if (len <= 3) return 'normal';
    return 'hard';
}

async function main() {
    console.log('正在下载六级词库...');
    
    let data;
    try {
        data = await downloadFile(CET6_URL);
        console.log('下载完成！');
    } catch (error) {
        console.error('下载失败:', error.message);
        console.log('使用内置词库...');
        data = fs.readFileSync(path.join(__dirname, 'cet6_sample.txt'), 'utf-8');
    }
    
    const lines = data.split('\n').filter(line => line.trim());
    console.log(`共 ${lines.length} 行数据`);
    
    const words = [];
    let skipped = 0;
    
    for (const line of lines) {
        const wordData = parseWordData(line);
        if (wordData) {
            words.push(wordData);
        } else {
            skipped++;
        }
    }
    
    console.log(`解析成功: ${words.length} 个单词`);
    console.log(`跳过: ${skipped} 行`);
    
    const easyWords = words.filter(w => getDifficulty(w.syllables) === 'easy');
    const normalWords = words.filter(w => getDifficulty(w.syllables) === 'normal');
    const hardWords = words.filter(w => getDifficulty(w.syllables) === 'hard');
    
    console.log(`\n难度分布:`);
    console.log(`  简单 (1-2音节): ${easyWords.length} 个`);
    console.log(`  一般 (3音节): ${normalWords.length} 个`);
    console.log(`  困难 (4+音节): ${hardWords.length} 个`);
    
    const outputDir = path.join(__dirname, 'data');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir);
    }
    
    const writeJson = (filename, data) => {
        const content = `const WORDS_${filename.toUpperCase()} = ${JSON.stringify(data, null, 2)};`;
        fs.writeFileSync(path.join(outputDir, `words_${filename}.js`), content, 'utf-8');
        console.log(`已保存: words_${filename}.js`);
    };
    
    writeJson('easy', easyWords);
    writeJson('normal', normalWords);
    writeJson('hard', hardWords);
    
    const allWordsContent = `
const WORDS_EASY = require('./words_easy.js').WORDS_EASY;
const WORDS_NORMAL = require('./words_normal.js').WORDS_NORMAL;
const WORDS_HARD = require('./words_hard.js').WORDS_HARD;

module.exports = {
    easy: WORDS_EASY,
    normal: WORDS_NORMAL,
    hard: WORDS_HARD,
    all: [...WORDS_EASY, ...WORDS_NORMAL, ...WORDS_HARD]
};
`;
    fs.writeFileSync(path.join(outputDir, 'index.js'), allWordsContent, 'utf-8');
    
    console.log('\n词库生成完成！');
}

main().catch(console.error);
