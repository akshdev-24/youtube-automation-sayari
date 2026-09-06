# 💔 Hinglish Shayari Shorts Automation

Automated YouTube Shorts generator for original **Roman Hindi / Hinglish Shayari**.

The system generates Shayari using Gemini, creates a static 1080×1920 vertical video with a fixed background and music, and uploads it to YouTube Shorts.

---

## ✨ Features

- 🤖 Gemini AI Shayari generation
- 💔 Sad / Love / Heartbreak / Attitude / Zindagi Shayari
- 🔤 Roman Hindi / Hinglish only
- 🚫 No Devanagari
- 🎙️ No voice
- 🔇 No TTS
- ✨ No text animation
- 🖼️ Fixed background image or video
- 🎵 Fixed background music
- 📱 1080×1920 vertical video
- 📺 YouTube Shorts upload
- 🏷️ Automatic title
- 📝 Automatic description
- #️⃣ Automatic hashtags
- 🔖 Automatic SEO tags
- ♻️ Duplicate Shayari protection
- 📚 Content history
- 🔄 Retry system
- ☁️ GitHub Actions automation
- ⏰ Daily 9 AM + 2 PM IST

---

# 📁 Project Structure

```text
youtube-automation/
│
├── assets/
│   ├── background.jpg
│   ├── fallback.jpg
│   │
│   ├── fonts/
│   │   ├── arial.ttf
│   │   └── arialbd.ttf
│   │
│   └── music/
│       └── bg_music.mp3
│
├── src/
│   ├── __init__.py
│   ├── generator.py
│   ├── shayari_generator.py
│   ├── shayari_video.py
│   └── uploader.py
│
├── output/
│
├── content_history.json
├── main.py
├── requirements.txt
│
└── .github/
    └── workflows/
        └── main.yml
