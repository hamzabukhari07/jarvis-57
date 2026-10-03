# 🎙️ ZEZO OS — Complete Voice & Desktop Test Scripts

> **Lead Architect:** Hamza Bukhari  
> **How to Run:** Terminal mein `python main.py` chalayein, jab `ZEZO online` aur green orb activate ho jaye, toh neeche diye gaye scenarios test karein.

---

### 🧪 Scenario 1: Browser In-Place Navigation & Tab Management (Recently Fixed)
*Testing: Active tab navigation, tab cycling, blank tab closing without duplicate window spawns.*

1. **Open Chrome:**
   - `"Chrome open karo."`
   - *(Expected: Chrome window activate / focus hogi).*
2. **Open New Tab:**
   - `"New tab kholo."`
   - *(Expected: Active browser mein new tab create hoga).*
3. **Open Website in Current Tab:**
   - `"Isi tab ke andar Docker ki website kholo."`
   - *(Expected: Naya separate window ya duplicate tab nahi khulega, current tab mein address bar se https://www.docker.com khulega).*
4. **Tab Cycling (Next / Previous Tab):**
   - `"Previous tab par jao."` ya `"Agla tab dikhao."`
   - *(Expected: Tab switch hoga bina crash ke).*
5. **Close Tab & Close Browser:**
   - `"Ye wala tab close kar do."`
   - `"Chrome band kar do."`

---

### 🧪 Scenario 2: Calculator App & Continuous Formula Calculation (Recently Fixed)
*Testing: Safe typing without destructive clear, math chaining (+, -, *, /).*

1. **Launch Calculator:**
   - `"Calculator open karo."`
   - *(Expected: Calculator app foreground par focus hoga).*
2. **First Calculation:**
   - `"Iske andar 25 + 80 karo."`
   - *(Expected: Direct input type hoga aur answer 105 screen par show hoga).*
3. **Chained Operation (Division):**
   - `"Isko divide by 3 kar do."`
   - *(Expected: `/3=` execute hoga aur result 35 aayega).*
4. **Chained Operation (Multiplication):**
   - `"Ab isme multiply by 90 karo."`
   - *(Expected: `*90=` execute hoga aur result 3150 aayega).*
5. **Close App:**
   - `"Calculator band kar do."`

---

### 🧪 Scenario 3: YouTube Transcription & Task Output (Recently Fixed)
*Testing: Background task resolution without hallucinated terminal commands (`cat output/...`).*

1. **Fetch Trending / Video:**
   - `"YouTube par trending videos check karo."`
2. **Extract Transcript:**
   - `"Kisi bhi trending video ka transcript nikal ke summarize karo."`
   - *(Expected: Background task run hoga, task complete hone par ZEZO live voice mein 1-2 sentence summary bolega aur detail HUD panel par render hogi, koi broken `cat` shell command nahi chalega).*

---

### 🧪 Scenario 4: Desktop File Creation & Code Helper
*Testing: Local file operations & syntax generation.*

1. **Create Python File on Desktop:**
   - `"Desktop par ek Python file banao with a random function."`
   - *(Expected: `C:\Users\Hamza\Desktop\random_function.py` create hoga aur ZEZO confirm karega).*
2. **Code Generation:**
   - `"Python mein quicksort ka simple function likho."`

---

### 🧪 Scenario 5: System Telemetry & Hardware Control
*Testing: Native OS metrics & audio volume.*

1. **System Status:**
   - `"System ka CPU aur RAM usage batao."`
2. **Volume Control:**
   - `"Volume 70 percent par set karo."`
3. **Identity & Architecture Attribution:**
   - `"Tumhe kisne design kiya hai?"`
   - *(Expected: "I was created and architected by Hamza Bukhari as an autonomous agent OS...").*

---

## 📌 Observation & Quality Checklist
- [ ] **Zero Latency Acknowledgement:** Har command ke foran baad (within 1 second) conversational acknowledgement aani chahiye.
- [ ] **No Terminal Errors:** Tasks complete hone par koi broken shell commands execute nahi honi chahiye.
- [ ] **Clean Tab Switching:** Active tabs switch karte waqt multiple windows duplicate nahi hone chahiye.
- [ ] **Safe Math Typing:** Calculator mein digits drop ya replace hone ke bajaye direct calculate hone chahiye.
