# 英语六级单词拼写闯关游戏

一个有趣的英语六级单词拼写学习游戏，通过拖拽音节的方式帮助用户记忆单词拼写。

## 功能特点

- 三种难度级别
  - 简单：1-2音节单词
  - 一般：3音节单词
  - 困难：4+音节单词

- 游戏机制
  - 拖拽音节组合单词
  - 实时发音（美式/英式）
  - 音标提示
  - 连击奖励系统
  - 提示和跳过功能
  - 关卡进度系统

- 学习辅助
  - 中文释义显示
  - 音标标注
  - 在线发音功能

## 项目结构

```
english-study/
├── index.html              # 主页面
├── style.css              # 样式文件
├── app.js                 # 游戏逻辑
├── generate_words.py      # 词库生成脚本
├── generate_words.js      # 词库生成脚本（JS版本）
├── words.js               # 单词数据
├── data/
│   ├── words_easy.js      # 简单难度词库
│   ├── words_normal.js    # 一般难度词库
│   ├── words_hard.js      # 困难难度词库
│   └── phonetic_cache.json # 音标缓存
└── README.md              # 项目说明
```

## 如何使用

### 在线使用

直接在浏览器中打开 `index.html` 文件即可开始游戏。

### 本地运行

1. 克隆仓库
```bash
git clone https://github.com/your-username/english-spelling-game.git
cd english-spelling-game
```

2. 启动本地服务器（可选）
```bash
# 使用 Python
python -m http.server 3000

# 或使用 Node.js
npx serve
```

3. 在浏览器中访问 `http://localhost:3000`

## 游戏玩法

1. 选择难度级别
2. 查看中文释义和音标
3. 点击发音按钮听取单词发音
4. 拖拽音节卡片到正确位置
5. 点击"确认提交"验证答案
6. 答对得分，连续答对获得连击奖励
7. 使用提示功能（扣5分）或跳过（扣10分）

## 词库生成

项目包含词库生成脚本，可以自定义单词库：

```bash
python generate_words.py
```

## 技术栈

- HTML5
- CSS3
- JavaScript (ES6+)
- Web Speech API（发音功能）
- Python（词库生成）

## 浏览器支持

- Chrome（推荐）
- Firefox
- Safari
- Edge

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
