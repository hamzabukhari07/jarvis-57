# 🎙️ ZEZO OS — Voice & Desktop Test Scripts

> **Created For:** Hamza Bukhari (Creator & Lead Architect)  
> **How to run:** Run `python main.py` in terminal, wait for ZEZO to go online, and speak these prompts.

---

### 🧪 Scenario 1: Figma Frame & Dimension Compound Macro (Phase 2 & 3 Test)
1. `"Figma open karo aur isko full screen par le jao."`
2. `"Canvas par ek naya frame add karo."`
3. `"Frame ka width aur height 400 400 set karo."`  
   *(Check: 1 second mein Width ➡️ Tab ➡️ Height compound macro execute hoga).*
4. `"Isko undo kar do."`  
   *(Check: Contextual Ctrl+Z chalega).*

---

### 🧪 Scenario 2: Notepad Typing & Save Flow (Proactive Voice & UIA Test)
1. `"Notepad open karo."`  
   *(Check: Foran bolega "Opening Notepad for you" — zero dead silence).*
2. `"Isme type karo: Hello Zezo, autonomous OS is live."`
3. `"File menu par click karo aur Save as select karo."`
4. `"Desktop select karo aur file save kar do."`
5. `"Screen dekho aur batao kya file desktop par save ho gayi?"`  
   *(Check: Screen inspect karke bolega "Hello Zezo.txt is saved on Desktop").*

---

### 🧪 Scenario 3: Groq Fast Code Generation & Web Scraping (Anti-403 Test)
1. `"Wikipedia se headlines scrape karne ka Python script likho."`  
   *(Check: Sub-1.5s generation + browser headers, no 403 error).*
2. `"Python mein Fibonacci generator function banao."`

---

### 🧪 Scenario 4: Live Web Search & Circuit Breaker (DDG + Groq)
1. `"Aaj ki latest tech news kya hai?"`
2. `"Karachi se Dubai ki flights search karo."`

---

### 🧪 Scenario 5: System Telemetry & Proactive Voice Chat
1. `"System ka CPU aur RAM usage batao."`
2. `"System ka volume 80 percent karo."`
3. `"Tumhe kisne banaya hai?"`  
   *(Check: Replies "I was created and architected by Hamza Bukhari...").*

---

## 📌 Checklist: What to Observe During Testing
- [ ] **Zero Silence:** Did ZEZO speak an immediate acknowledgement within 1 second of your command?
- [ ] **Sub-Second Speed:** Did property clicks (Width/Height) happen in under 0.5 seconds?
- [ ] **Tab Navigation:** Did Figma resize in 1 compound macro turn instead of 8 separate clicks?
- [ ] **No WebSocket 1011 Disconnects:** Did the session stay connected and smooth throughout all actions?
