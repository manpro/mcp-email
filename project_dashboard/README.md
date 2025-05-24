# 🚀 Project Dashboard

En modern webbapplikation som automatiskt hittar och visar alla mjukvaruprojekt på servern.

## 📋 Översikt

Project Dashboard skannar servern efter mjukvaruprojekt och visar dem i en snygg webbinterface. Den identifierar projekt baserat på:

- **Projektfiler**: `main.py`, `app.py`, `Dockerfile`, `requirements.txt`, `README.md`, `package.json`, etc.
- **Git-repositories**: Kataloger med `.git`
- **Kodfiler**: Många `.py`, `.js`, `.ts`, `.java`, `.go`, `.sh` filer

## 🎯 Funktioner

- **Automatisk projektdetektering** - Skannar hela servern efter projekt
- **Modern UI** - Responsiv design med TailwindCSS
- **Filterering** - Filtrera efter projekttyp (Python, Node.js, Docker, etc.)
- **Sökning** - Sök efter projektnamn eller beskrivning
- **Projektdetaljer** - Visa fullständig information om varje projekt
- **Direktlänkar** - Kopiera projektets sökväg till urklipp

## 🚀 Snabbstart

### Starta servern
```bash
cd /home/micke/project_dashboard
./start.sh
```

### Stoppa servern
```bash
cd /home/micke/project_dashboard
./stop.sh
```

### Åtkomst
- **Webbgränssnitt**: http://172.16.16.148:6888
- **Lokalt**: http://localhost:6888

## 📁 Filstruktur

```
/home/micke/project_dashboard/
├── app.py              # Flask-server
├── scan_projects.py    # Projektskanner
├── projects.json       # Projektdata (genereras automatiskt)
├── start.sh           # Startskript
├── stop.sh            # Stoppskript
├── dashboard.log      # Serverloggar
└── README.md          # Denna fil
```

## 🔧 API-endpoints

- `GET /` - Huvudsida med webbgränssnitt
- `GET /api/projects` - JSON-lista över alla projekt
- `GET /api/scan` - Starta ny projektsökning

## 📊 Projekttyper som identifieras

- **Python** - `requirements.txt`, `main.py`, `app.py`, `pyproject.toml`
- **Node.js/JavaScript** - `package.json`, `yarn.lock`
- **Docker** - `Dockerfile`
- **Java** - `pom.xml`, `.java`-filer
- **Go** - `go.mod`, `.go`-filer
- **Rust** - `Cargo.toml`, `.rs`-filer
- **Web/HTML** - `index.html`
- **Git Repository** - `.git`-katalog

## 🛠️ Kommandon

### Manuell projektsökning
```bash
python3 /home/micke/project_dashboard/scan_projects.py
```

### Visa loggar
```bash
tail -f /home/micke/project_dashboard/dashboard.log
```

### Kontrollera status
```bash
ps aux | grep app.py
```

### Testa API
```bash
curl http://localhost:6888/api/projects
```

## 🔍 Felsökning

### Servern startar inte
1. Kontrollera att port 6888 är ledig: `lsof -i :6888`
2. Kolla loggarna: `cat /home/micke/project_dashboard/dashboard.log`
3. Kontrollera Python-dependencies: `pip3 list | grep flask`

### Inga projekt visas
1. Kör manual sökning: `python3 scan_projects.py`
2. Kontrollera `projects.json`: `cat projects.json`
3. Verifiera sökvägar i skriptet

### Webbsidan laddar inte
1. Kontrollera att servern körs: `ps aux | grep app.py`
2. Testa lokalt: `curl http://localhost:6888`
3. Kontrollera brandvägg och nätverksanslutning

## 🎨 Anpassning

### Lägg till fler projekttyper
Redigera `scan_projects.py` och lägg till fler fil-extensions i:
- `project_files` listan
- `code_extensions` listan
- `detect_project_type()` funktionen

### Ändra sökvägar
Modifiera `search_paths` listan i `scan_projects.py`:
```python
search_paths = [
    '/home/micke',
    '/opt',
    '/srv',
    '/ditt/egen/sökväg'  # Lägg till här
]
```

### Ändra port
Redigera `app.py` och ändra port-numret:
```python
app.run(host='0.0.0.0', port=6888, debug=True)  # Ändra 6888
```

## 📝 Dependencies

- **Python 3** - Redan installerat
- **Flask** - Installeras automatiskt vid första körning
- **TailwindCSS** - Laddas via CDN (ingen installation krävs)

## 🔐 Säkerhet

- Servern körs endast lokalt (ingen extern åtkomst som standard)
- Inga känsliga filer exponeras (bara projektlistor)
- Loggar sparas lokalt

## 📈 Kommande funktioner

- [ ] Projektstatistik (antal filer, storlek, etc.)
- [ ] Git-commit information
- [ ] Dependency-analys
- [ ] Projektmall-generator
- [ ] Export till olika format

---

**Skapat med ❤️ för att hålla koll på alla projekt på servern!**