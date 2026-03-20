class SpellingGame {
  constructor() {
    this.score = 0;
    this.level = 1;
    this.combo = 0;
    this.currentWord = null;
    this.usedWords = [];
    this.hintUsed = false;
    this.difficulty = null;
    this.wordsData = [];
    this.audioCache = {};
    this.currentAudio = null;

    this.initElements();
    this.initEventListeners();
    this.loadAllWords();
  }

  initElements() {
    this.difficultySelector = document.getElementById("difficulty-selector");
    this.gameArea = document.getElementById("game-area");
    this.dropZone = document.getElementById("drop-zone");
    this.syllablePool = document.getElementById("syllable-pool");
    this.wordChinese = document.getElementById("word-chinese");
    this.wordPhonetic = document.getElementById("word-phonetic");
    this.scoreEl = document.getElementById("score");
    this.levelEl = document.getElementById("level");
    this.comboEl = document.getElementById("combo");
    this.resultModal = document.getElementById("result-modal");
    this.wordCountEl = document.getElementById("word-count");
    this.pronUsBtn = document.getElementById("pron-us-btn");
    this.pronUkBtn = document.getElementById("pron-uk-btn");
  }

  async loadAllWords() {
    try {
      const difficulties = ["easy", "normal", "hard"];
      let totalWords = 0;

      for (const diff of difficulties) {
        const script = document.createElement("script");
        script.src = `data/words_${diff}.js`;
        document.head.appendChild(script);
      }

      await new Promise((resolve) => setTimeout(resolve, 500));

      this.updateWordCount();
    } catch (error) {
      console.error("加载词库失败:", error);
    }
  }

  updateWordCount() {
    const easyCount = window.WORDS_EASY ? window.WORDS_EASY.length : 0;
    const normalCount = window.WORDS_NORMAL ? window.WORDS_NORMAL.length : 0;
    const hardCount = window.WORDS_HARD ? window.WORDS_HARD.length : 0;
    const total = easyCount + normalCount + hardCount;
    if (this.wordCountEl) {
      this.wordCountEl.textContent = total;
    }
  }

  initEventListeners() {
    document.querySelectorAll(".difficulty-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const difficulty = e.currentTarget.dataset.difficulty;
        this.selectDifficulty(difficulty);
      });
    });

    document
      .getElementById("submit-btn")
      .addEventListener("click", () => this.checkAnswer());
    document
      .getElementById("hint-btn")
      .addEventListener("click", () => this.showHint());
    document
      .getElementById("skip-btn")
      .addEventListener("click", () => this.skipWord());
    document
      .getElementById("back-btn")
      .addEventListener("click", () => this.backToMenu());
    document
      .getElementById("next-btn")
      .addEventListener("click", () => this.nextRound());

    this.pronUsBtn.addEventListener("click", () =>
      this.playPronunciation("us"),
    );
    this.pronUkBtn.addEventListener("click", () =>
      this.playPronunciation("uk"),
    );

    this.dropZone.addEventListener("dragover", (e) => this.handleDragOver(e));
    this.dropZone.addEventListener("dragleave", () => this.handleDragLeave());
    this.dropZone.addEventListener("drop", (e) => this.handleDrop(e));
  }

  selectDifficulty(difficulty) {
    this.difficulty = difficulty;

    switch (difficulty) {
      case "easy":
        this.wordsData = window.WORDS_EASY || [];
        break;
      case "normal":
        this.wordsData = window.WORDS_NORMAL || [];
        break;
      case "hard":
        this.wordsData = window.WORDS_HARD || [];
        break;
    }

    if (this.wordsData.length === 0) {
      alert("该难度词库加载中，请稍后再试！");
      return;
    }

    this.difficultySelector.style.display = "none";
    this.gameArea.style.display = "block";

    this.score = 0;
    this.level = 1;
    this.combo = 0;
    this.usedWords = [];
    this.updateStats();
    this.startNewRound();
  }

  backToMenu() {
    this.difficultySelector.style.display = "block";
    this.gameArea.style.display = "none";
    this.resultModal.classList.remove("show");
  }

  startNewRound() {
    const availableWords = this.wordsData.filter(
      (w) => !this.usedWords.includes(w.word),
    );

    if (availableWords.length === 0) {
      this.usedWords = [];
      this.startNewRound();
      return;
    }

    const randomIndex = Math.floor(Math.random() * availableWords.length);
    this.currentWord = availableWords[randomIndex];
    this.usedWords.push(this.currentWord.word);
    this.hintUsed = false;

    this.renderWord();
  }

  renderWord() {
    this.wordChinese.textContent = this.currentWord.chinese;
    this.wordPhonetic.textContent = this.currentWord.phonetic || "";

    this.dropZone.innerHTML =
      '<div class="drop-placeholder">拖拽音节到此处</div>';
    this.syllablePool.innerHTML = "";

    const shuffledSyllables = this.shuffleArray([
      ...this.currentWord.syllables,
    ]);

    shuffledSyllables.forEach((syllable, index) => {
      const el = document.createElement("div");
      el.className = "syllable";
      el.textContent = syllable;
      el.draggable = true;
      el.dataset.index = index;
      el.dataset.syllable = syllable;

      el.addEventListener("dragstart", (e) => this.handleDragStart(e));
      el.addEventListener("dragend", (e) => this.handleDragEnd(e));
      el.addEventListener("click", () => this.handleSyllableClick(el));

      this.syllablePool.appendChild(el);
    });
  }

  shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  handleDragStart(e) {
    e.target.classList.add("dragging");
    e.dataTransfer.setData("text/plain", e.target.dataset.index);
    e.dataTransfer.effectAllowed = "move";
  }

  handleDragEnd(e) {
    e.target.classList.remove("dragging");
  }

  handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    this.dropZone.classList.add("drag-over");
  }

  handleDragLeave() {
    this.dropZone.classList.remove("drag-over");
  }

  handleDrop(e) {
    e.preventDefault();
    this.dropZone.classList.remove("drag-over");

    const index = e.dataTransfer.getData("text/plain");
    const syllableEl = this.syllablePool.querySelector(
      `[data-index="${index}"]`,
    );

    if (syllableEl && !syllableEl.classList.contains("in-drop-zone")) {
      this.moveSyllableToDropZone(syllableEl);
    }
  }

  handleSyllableClick(el) {
    if (el.classList.contains("in-drop-zone")) {
      this.moveSyllableToPool(el);
    } else {
      this.moveSyllableToDropZone(el);
    }
  }

  moveSyllableToDropZone(el) {
    const placeholder = this.dropZone.querySelector(".drop-placeholder");
    if (placeholder) {
      placeholder.remove();
    }

    el.classList.add("in-drop-zone");
    el.draggable = true;

    el.removeEventListener("dragstart", this.handleDragStart);
    el.removeEventListener("dragend", this.handleDragEnd);

    el.addEventListener("dragstart", (e) => {
      e.target.classList.add("dragging");
      e.dataTransfer.setData("text/plain", e.target.dataset.index);
      e.dataTransfer.effectAllowed = "move";
    });

    el.addEventListener("dragend", (e) => {
      e.target.classList.remove("dragging");
    });

    this.dropZone.appendChild(el);
  }

  moveSyllableToPool(el) {
    el.classList.remove("in-drop-zone");
    this.syllablePool.appendChild(el);

    if (this.dropZone.querySelectorAll(".syllable").length === 0) {
      this.dropZone.innerHTML =
        '<div class="drop-placeholder">拖拽音节到此处</div>';
    }
  }

  getAnswerFromDropZone() {
    const syllables = this.dropZone.querySelectorAll(".syllable");
    return Array.from(syllables).map((el) => el.dataset.syllable);
  }

  checkAnswer() {
    const userAnswer = this.getAnswerFromDropZone();
    const correctAnswer = this.currentWord.syllables;

    if (userAnswer.length === 0) {
      this.showMessage("请先组合单词！", "warning");
      return;
    }

    const isCorrect = userAnswer.join("") === correctAnswer.join("");

    if (isCorrect) {
      this.handleCorrectAnswer();
    } else {
      this.handleWrongAnswer();
    }
  }

  handleCorrectAnswer() {
    const syllables = this.dropZone.querySelectorAll(".syllable");
    syllables.forEach((el) => el.classList.add("correct"));

    this.combo++;
    const baseScore = 10;
    const comboBonus = Math.min(this.combo * 2, 20);
    const totalScore = baseScore + comboBonus;

    this.score += totalScore;
    this.updateStats();

    this.showScoreChange(`+${totalScore}`, "positive");

    setTimeout(() => {
      this.showResult(true, totalScore);
    }, 500);
  }

  handleWrongAnswer() {
    const syllables = this.dropZone.querySelectorAll(".syllable");
    syllables.forEach((el) => el.classList.add("wrong"));

    this.combo = 0;
    const penalty = 5;
    this.score = Math.max(0, this.score - penalty);
    this.updateStats();

    this.showScoreChange(`-${penalty}`, "negative");

    setTimeout(() => {
      this.showResult(false, -penalty);
    }, 500);
  }

  showHint() {
    if (this.hintUsed) {
      this.showMessage("本关已使用过提示！", "warning");
      return;
    }

    this.hintUsed = true;
    const penalty = 5;
    this.score = Math.max(0, this.score - penalty);
    this.updateStats();

    this.showScoreChange(`-${penalty}`, "negative");

    const firstSyllable = this.currentWord.syllables[0];
    const syllableEl = this.syllablePool.querySelector(
      `[data-syllable="${firstSyllable}"]`,
    );

    if (syllableEl && !syllableEl.classList.contains("in-drop-zone")) {
      syllableEl.classList.add("hint");
      this.moveSyllableToDropZone(syllableEl);
    }
  }

  skipWord() {
    this.combo = 0;
    const penalty = 10;
    this.score = Math.max(0, this.score - penalty);
    this.updateStats();

    this.showScoreChange(`-${penalty}`, "negative");

    setTimeout(() => {
      this.showResult(false, -penalty, true);
    }, 300);
  }

  showResult(success, scoreChange, skipped = false) {
    const modal = this.resultModal;
    const icon = document.getElementById("result-icon");
    const text = document.getElementById("result-text");
    const word = document.getElementById("result-word");

    if (success) {
      icon.textContent = "🎉";
      text.textContent = "回答正确！";
      text.className = "result-text success";
    } else {
      icon.textContent = skipped ? "⏭️" : "😢";
      text.textContent = skipped ? "已跳过" : "回答错误";
      text.className = "result-text fail";
    }

    word.innerHTML = `
            <div><strong>${this.currentWord.word}</strong></div>
            <div>${this.currentWord.phonetic || ""}</div>
            <div>${this.currentWord.chinese}</div>
        `;

    modal.classList.add("show");
  }

  nextRound() {
    this.resultModal.classList.remove("show");
    this.level++;
    this.updateStats();
    this.startNewRound();
  }

  showScoreChange(text, type) {
    const el = document.createElement("div");
    el.className = `score-change ${type}`;
    el.textContent = text;
    document.body.appendChild(el);

    setTimeout(() => el.remove(), 1000);
  }

  showMessage(text, type) {
    console.log(`${type}: ${text}`);
  }

  updateStats() {
    this.scoreEl.textContent = this.score;
    this.levelEl.textContent = this.level;
    this.comboEl.textContent = this.combo;
  }

  async playPronunciation(type) {
    if (!this.currentWord) return;

    const word = this.currentWord.word;
    const btn = type === "us" ? this.pronUsBtn : this.pronUkBtn;

    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }

    btn.classList.add("playing");

    try {
      const audioUrl = await this.getAudioUrl(word, type);
      if (audioUrl) {
        const audio = new Audio(audioUrl);
        this.currentAudio = audio;
        audio.onended = () => {
          btn.classList.remove("playing");
          this.currentAudio = null;
        };
        audio.onerror = () => {
          btn.classList.remove("playing");
          this.showMessage("发音加载失败", "error");
        };
        await audio.play();
      } else {
        btn.classList.remove("playing");
        this.showMessage("暂无该发音", "warning");
      }
    } catch (error) {
      btn.classList.remove("playing");
      this.showMessage("发音播放失败", "error");
    }
  }

  async getAudioUrl(word, type) {
    const cacheKey = `${word}_${type}`;
    if (this.audioCache[cacheKey]) {
      return this.audioCache[cacheKey];
    }

    try {
      const response = await fetch(
        `https://api.dictionaryapi.dev/api/v2/entries/en/${word}`,
      );
      if (!response.ok) return null;

      const data = await response.json();
      if (!data || !data[0]) return null;

      const phonetics = data[0].phonetics || [];

      for (const p of phonetics) {
        const audio = p.audio || "";
        if (type === "us" && audio.includes("-us")) {
          this.audioCache[cacheKey] = audio;
          return audio;
        }
        if (type === "uk" && audio.includes("-uk")) {
          this.audioCache[cacheKey] = audio;
          return audio;
        }
      }

      for (const p of phonetics) {
        const audio = p.audio || "";
        if (audio) {
          this.audioCache[cacheKey] = audio;
          return audio;
        }
      }

      return null;
    } catch (error) {
      return null;
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new SpellingGame();
});
